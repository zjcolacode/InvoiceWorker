"""
发票识别服务 - 调用DashScope qwen-vl-max模型进行发票图片/PDF识别
"""
import asyncio
import base64
import json
import logging
import os
import re
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# DashScope OpenAI兼容接口地址
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen-vl-max"

# 图片大小限制 (4MB)
MAX_IMAGE_SIZE = 4 * 1024 * 1024


def _build_recognition_prompt() -> str:
    """构建发票识别Prompt"""
    return """请仔细识别这张发票图片中的所有信息，并严格按照以下JSON格式返回结果。如果某个字段无法识别，请填写null。

{
  "invoice_no": "发票号码(纯数字)",
  "invoice_code": "发票代码(如有)",
  "invoice_date": "开票日期，格式：YYYY-MM-DD",
  "seller_name": "销售方/收款方名称",
  "seller_tax_no": "销售方纳税人识别号",
  "buyer_name": "购买方/付款方名称",
  "buyer_tax_no": "购买方纳税人识别号",
  "items": "开票内容/商品或服务名称(多项用逗号分隔)",
  "amount": 金额(不含税，数字类型),
  "tax_rate": "税率(如13%、6%等)",
  "tax": 税额(数字类型),
  "total": 价税合计(数字类型),
  "invoice_type": "发票类型(增值税普通发票/增值税专用发票/增值税电子普通发票/增值税电子专用发票等)",
  "remarks": "备注信息(如有)"
}

注意：金额相关字段请返回数字而非字符串，日期请统一为YYYY-MM-DD格式。"""


def _compress_image(image_data: bytes, max_size: int = MAX_IMAGE_SIZE) -> bytes:
    """压缩图片到指定大小以内"""
    if len(image_data) <= max_size:
        return image_data

    img = Image.open(BytesIO(image_data))

    # 逐步降低质量压缩
    quality = 85
    while quality > 10:
        buffer = BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buffer, format="JPEG", quality=quality)
        compressed = buffer.getvalue()
        if len(compressed) <= max_size:
            return compressed
        quality -= 10

    # 如果降低质量还不够，缩小尺寸
    width, height = img.size
    while len(compressed) > max_size and width > 800:
        width = int(width * 0.8)
        height = int(height * 0.8)
        resized = img.resize((width, height), Image.LANCZOS)
        buffer = BytesIO()
        resized.save(buffer, format="JPEG", quality=60)
        compressed = buffer.getvalue()

    return compressed


def _image_to_base64(file_path: str) -> str:
    """读取图片文件并转为base64编码"""
    with open(file_path, "rb") as f:
        image_data = f.read()

    # 如果图片过大，先压缩
    image_data = _compress_image(image_data)

    return base64.b64encode(image_data).decode("utf-8")


def _pdf_to_base64(file_path: str) -> str:
    """将PDF第一页转为图片base64编码"""
    try:
        # 使用Pillow尝试直接打开（某些PDF可以直接打开）
        # 对于标准PDF，先读取原始数据用base64编码
        with open(file_path, "rb") as f:
            pdf_data = f.read()

        # 直接将PDF以base64编码发送
        return base64.b64encode(pdf_data).decode("utf-8")
    except Exception as e:
        logger.error(f"PDF转换失败: {file_path}, 错误: {e}")
        raise


def _get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取MIME类型"""
    ext = Path(file_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
    }
    return mime_map.get(ext, "image/png")


def _parse_recognition_result(response_text: str) -> dict:
    """从模型返回文本中解析JSON结果"""
    # 尝试从markdown代码块中提取JSON
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # 尝试直接解析整个文本
        json_str = response_text.strip()

    try:
        result = json.loads(json_str)
    except json.JSONDecodeError:
        # 再尝试找到第一个 { 和最后一个 } 之间的内容
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1:
            json_str = response_text[start : end + 1]
            result = json.loads(json_str)
        else:
            raise ValueError(f"无法从返回内容中解析JSON: {response_text[:200]}")

    # 金额字段转为float类型
    for field in ("amount", "tax", "total"):
        if field in result and result[field] is not None:
            try:
                result[field] = float(result[field])
            except (ValueError, TypeError):
                result[field] = None

    # 验证日期格式
    if result.get("invoice_date"):
        date_str = result["invoice_date"]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            # 尝试常见格式转换
            for fmt_pattern, fmt_replace in [
                (r"(\d{4})年(\d{1,2})月(\d{1,2})日", r"\1-\2-\3"),
                (r"(\d{4})/(\d{1,2})/(\d{1,2})", r"\1-\2-\3"),
                (r"(\d{4})\.(\d{1,2})\.(\d{1,2})", r"\1-\2-\3"),
            ]:
                new_date = re.sub(fmt_pattern, fmt_replace, date_str)
                if new_date != date_str:
                    # 补齐月份和日期为两位
                    parts = new_date.split("-")
                    if len(parts) == 3:
                        result["invoice_date"] = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                    break

    return result


async def recognize_invoice(file_path: str) -> dict:
    """
    识别单张发票

    Args:
        file_path: 发票文件路径

    Returns:
        dict: {"success": bool, "data": dict|None, "error": str|None}
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {"success": False, "data": None, "error": f"文件不存在: {file_path}"}

    # 检查API Key
    api_key = settings.DASHSCOPE_API_KEY
    if not api_key or api_key == "your-dashscope-api-key":
        return {"success": False, "data": None, "error": "DASHSCOPE_API_KEY未配置"}

    # 获取文件类型并转为base64
    ext = Path(file_path).suffix.lower()
    try:
        if ext == ".pdf":
            base64_data = _pdf_to_base64(file_path)
            mime_type = "application/pdf"
        elif ext in (".jpg", ".jpeg", ".png"):
            base64_data = _image_to_base64(file_path)
            mime_type = _get_mime_type(file_path)
        else:
            return {"success": False, "data": None, "error": f"不支持的文件格式: {ext}"}
    except Exception as e:
        logger.error(f"文件处理失败: {file_path}, 错误: {e}")
        return {"success": False, "data": None, "error": f"文件处理失败: {str(e)}"}

    # 构建请求消息
    prompt = _build_recognition_prompt()
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]

    # 调用API（带重试）
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            logger.info(f"开始识别发票: {file_path} (第{attempt + 1}次尝试)")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    DASHSCOPE_API_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": DASHSCOPE_MODEL,
                        "messages": messages,
                    },
                )

            if response.status_code != 200:
                error_msg = f"API调用失败，状态码: {response.status_code}, 响应: {response.text[:200]}"
                logger.warning(error_msg)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return {"success": False, "data": None, "error": error_msg}

            # 解析API响应
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]

            logger.info(f"发票识别API返回成功: {file_path}")
            logger.debug(f"原始返回内容: {content[:300]}")

            # 解析识别结果
            result = _parse_recognition_result(content)
            logger.info(f"发票识别解析成功: {file_path}, 发票号: {result.get('invoice_no')}")

            return {"success": True, "data": result, "error": None}

        except json.JSONDecodeError as e:
            error_msg = f"JSON解析失败: {str(e)}"
            logger.error(f"{error_msg}, 原始内容: {content[:300] if 'content' in dir() else 'N/A'}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            return {"success": False, "data": None, "error": error_msg}

        except httpx.TimeoutException:
            error_msg = f"API调用超时 (第{attempt + 1}次)"
            logger.warning(error_msg)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            return {"success": False, "data": None, "error": "API调用超时，已重试3次"}

        except Exception as e:
            error_msg = f"识别过程异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            return {"success": False, "data": None, "error": error_msg}

    return {"success": False, "data": None, "error": "未知错误"}


async def batch_recognize(file_paths: list[str]) -> list[dict]:
    """
    批量识别发票

    Args:
        file_paths: 发票文件路径列表

    Returns:
        list[dict]: 每个文件的识别结果列表
    """
    results = []
    for i, file_path in enumerate(file_paths):
        logger.info(f"批量识别进度: {i + 1}/{len(file_paths)}, 文件: {file_path}")
        result = await recognize_invoice(file_path)
        results.append(result)

        # 每次识别间隔1秒，避免限流（最后一次不需要等待）
        if i < len(file_paths) - 1:
            await asyncio.sleep(1)

    return results
