"""
发票打印排版服务

将多张发票文件(PDF/图片)合并为A4打印PDF, 每页放2张发票(上下排列)。
- 图片格式 (.jpg/.jpeg/.png): 直接通过 reportlab.drawImage 嵌入
- PDF格式 (.pdf): 优先使用 PyMuPDF(fitz) 渲染为图片再嵌入;
  若不可用, 则使用 Pillow 尝试打开(只对图像式PDF有效);
  仍失败时, 在该区域绘制文件名及错误提示, 跳过该发票内容。

输出文件统一保存到 storage/print_output/print_{timestamp}.pdf。
"""
from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


# 输出目录(相对于项目根目录)
PRINT_OUTPUT_DIR = Path("storage/print_output")


def ensure_output_dir() -> Path:
    """确保打印输出目录存在并返回绝对路径"""
    out_dir = (Path.cwd() / PRINT_OUTPUT_DIR).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


class PrintService:
    """发票打印排版服务 - A4纸上下排列2张发票"""

    A4_WIDTH, A4_HEIGHT = A4  # 595.28, 841.89 points
    MARGIN = 10 * mm  # 页边距
    SPACING = 5 * mm  # 两张发票之间的间距

    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}
    PDF_EXTS = {".pdf"}

    def __init__(self) -> None:
        self._tmp_files: List[str] = []

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------
    def generate_print_pdf(
        self,
        invoice_file_paths: List[str],
        output_path: Optional[str] = None,
    ) -> str:
        """
        将发票文件排版为打印PDF。

        :param invoice_file_paths: 发票源文件路径列表(PDF或图片)
        :param output_path: 可选, 输出路径(绝对路径); 不传则自动生成
        :return: 生成的PDF绝对路径
        """
        if not invoice_file_paths:
            raise ValueError("没有可打印的发票文件")

        out_dir = ensure_output_dir()
        if output_path:
            out = Path(output_path).resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
        else:
            ts = int(time.time() * 1000)
            out = out_dir / f"print_{ts}.pdf"

        # 1. 把每个发票文件展开为图片路径列表
        # 一个PDF可能多页 -> 多张图; 每张图占一个"半页"槽位
        image_slots: List[Tuple[str, str]] = []  # (image_path, original_source)
        for src in invoice_file_paths:
            try:
                imgs = self._invoice_to_images(src)
                for img in imgs:
                    image_slots.append((img, src))
            except Exception as e:
                logger.exception(f"处理发票文件失败: {src}")
                # 加入占位记录, 在PDF上提示该发票无法显示
                image_slots.append(("", f"{src} (错误: {e})"))

        if not image_slots:
            raise ValueError("没有可渲染的发票内容")

        # 2. 排版: 每页2个槽位
        c = canvas.Canvas(str(out), pagesize=A4)
        slot_w, slot_h = self._get_half_page_size()

        # 上槽位的左下角Y坐标 (PDF坐标系原点在左下)
        upper_y = self.MARGIN + slot_h + self.SPACING
        # 下槽位的左下角Y坐标
        lower_y = self.MARGIN
        slot_x = self.MARGIN

        try:
            for idx, (img_path, source_label) in enumerate(image_slots):
                pos = idx % 2  # 0 -> 上槽, 1 -> 下槽
                y = upper_y if pos == 0 else lower_y

                # 绘制边框(浅灰), 方便裁剪/对齐
                c.setStrokeColorRGB(0.85, 0.85, 0.85)
                c.setLineWidth(0.3)
                c.rect(slot_x, y, slot_w, slot_h, stroke=1, fill=0)

                if img_path and os.path.exists(img_path):
                    self._draw_invoice_image(c, img_path, slot_x, y, slot_w, slot_h)
                else:
                    # 绘制错误提示
                    c.setFillColorRGB(0.6, 0.2, 0.2)
                    c.setFont("Helvetica", 10)
                    c.drawString(slot_x + 6, y + slot_h / 2, f"[无法显示] {os.path.basename(source_label)}")
                    c.setFillColorRGB(0, 0, 0)

                # 一页放完2张, 或到最后一张, 翻页
                if pos == 1 and idx != len(image_slots) - 1:
                    c.showPage()

            c.save()
        finally:
            self._cleanup_tmp_files()

        logger.info(f"已生成打印PDF: {out} (共 {len(image_slots)} 张发票)")
        return str(out)

    # ------------------------------------------------------------------
    # 排版辅助
    # ------------------------------------------------------------------
    def _get_half_page_size(self) -> Tuple[float, float]:
        """计算每张发票可用的区域大小(A4一半减去边距与间距)"""
        width = self.A4_WIDTH - 2 * self.MARGIN
        height = (self.A4_HEIGHT - 2 * self.MARGIN - self.SPACING) / 2
        return width, height

    def _draw_invoice_image(
        self,
        c: canvas.Canvas,
        image_path: str,
        x: float,
        y: float,
        max_width: float,
        max_height: float,
    ) -> None:
        """在指定区域绘制发票图片(等比缩放居中)"""
        try:
            with Image.open(image_path) as img:
                iw, ih = img.size
        except Exception as e:
            logger.warning(f"无法读取图片尺寸: {image_path}, error={e}")
            iw, ih = max_width, max_height

        # 等比缩放
        ratio = min(max_width / iw, max_height / ih)
        draw_w = iw * ratio
        draw_h = ih * ratio
        # 居中
        draw_x = x + (max_width - draw_w) / 2
        draw_y = y + (max_height - draw_h) / 2

        try:
            c.drawImage(
                image_path,
                draw_x,
                draw_y,
                width=draw_w,
                height=draw_h,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        except Exception as e:
            logger.exception(f"绘制图片失败: {image_path}")
            c.setFillColorRGB(0.6, 0.2, 0.2)
            c.setFont("Helvetica", 9)
            c.drawString(x + 6, y + max_height / 2, f"[绘制失败] {os.path.basename(image_path)}: {e}")
            c.setFillColorRGB(0, 0, 0)

    # ------------------------------------------------------------------
    # 文件 -> 图片
    # ------------------------------------------------------------------
    def _invoice_to_images(self, file_path: str) -> List[str]:
        """
        将发票文件转为可被 reportlab 嵌入的图片路径列表。
        - 图片直接返回原路径
        - PDF 通过 fitz/Pillow 渲染为临时PNG
        """
        # 解析为绝对路径
        p = Path(file_path)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.exists():
            raise FileNotFoundError(f"发票文件不存在: {p}")

        ext = p.suffix.lower()
        if ext in self.IMAGE_EXTS:
            return [str(p)]
        if ext in self.PDF_EXTS:
            return self._pdf_to_images(str(p))
        raise ValueError(f"不支持的文件类型: {ext}")

    def _pdf_to_images(self, pdf_path: str) -> List[str]:
        """将PDF每页转为临时图片(优先 fitz, 退化到 Pillow)"""
        # 1) 优先尝试 PyMuPDF (fitz) - 矢量PDF也能渲染
        try:
            import fitz  # type: ignore

            outputs: List[str] = []
            doc = fitz.open(pdf_path)
            try:
                for page_idx in range(doc.page_count):
                    page = doc.load_page(page_idx)
                    # 200 DPI 渲染, 兼顾清晰度与速度
                    matrix = fitz.Matrix(200 / 72, 200 / 72)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    tmp = tempfile.NamedTemporaryFile(
                        suffix=f"_p{page_idx}.png", delete=False
                    )
                    tmp.close()
                    pix.save(tmp.name)
                    self._tmp_files.append(tmp.name)
                    outputs.append(tmp.name)
            finally:
                doc.close()
            if outputs:
                return outputs
        except ImportError:
            logger.info("PyMuPDF 未安装, 尝试使用 Pillow 处理PDF")
        except Exception as e:
            logger.warning(f"fitz 渲染PDF失败, 尝试 Pillow: {e}")

        # 2) 退化方案: Pillow (仅对图像式PDF有效)
        try:
            outputs: List[str] = []
            with Image.open(pdf_path) as img:
                idx = 0
                while True:
                    tmp = tempfile.NamedTemporaryFile(
                        suffix=f"_p{idx}.png", delete=False
                    )
                    tmp.close()
                    img.save(tmp.name, format="PNG")
                    self._tmp_files.append(tmp.name)
                    outputs.append(tmp.name)
                    idx += 1
                    try:
                        img.seek(idx)
                    except EOFError:
                        break
            if outputs:
                return outputs
        except Exception as e:
            logger.warning(f"Pillow 处理PDF失败: {pdf_path}, error={e}")

        raise RuntimeError(
            f"无法渲染PDF为图片(请安装 PyMuPDF: pip install pymupdf): {pdf_path}"
        )

    def _cleanup_tmp_files(self) -> None:
        """清理本次生成过程中产生的临时图片"""
        for f in self._tmp_files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except OSError:
                pass
        self._tmp_files.clear()


def cleanup_old_print_files(days: int = 7) -> int:
    """
    清理打印输出目录下早于 N 天的文件。

    :param days: 保留天数
    :return: 已删除的文件数
    """
    out_dir = ensure_output_dir()
    cutoff = time.time() - days * 86400
    removed = 0
    for f in out_dir.iterdir():
        if not f.is_file():
            continue
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError as e:
            logger.warning(f"清理失败: {f}, error={e}")
    logger.info(f"打印文件清理完成: 删除 {removed} 个早于 {days} 天的文件")
    return removed


def list_print_files() -> List[dict]:
    """列出当前打印输出目录下的所有文件(按时间倒序)"""
    out_dir = ensure_output_dir()
    items: List[dict] = []
    for f in out_dir.iterdir():
        if not f.is_file() or f.suffix.lower() != ".pdf":
            continue
        try:
            stat = f.stat()
            items.append(
                {
                    "filename": f.name,
                    "size": stat.st_size,
                    "created_at": stat.st_mtime,
                }
            )
        except OSError:
            continue
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items
