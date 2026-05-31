"""
发票智能分类服务

根据发票的开票内容(items字段)，匹配预设分类的关键词，自动判定分类。
匹配逻辑：将items文本与各分类的keywords进行子串匹配，统计命中关键词数量；
取命中数量最高的分类，无命中归为"其他"。
"""
import logging
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


# 预设默认分类及其关键词
DEFAULT_CATEGORIES: List[dict] = [
    {
        "name": "办公用品",
        "keywords": "办公,文具,打印,复印,耗材,纸张,墨盒,硒鼓",
        "color": "#409EFF",
        "description": "办公文具、耗材类支出",
    },
    {
        "name": "交通费",
        "keywords": "交通,出租车,滴滴,打车,高铁,火车,飞机,机票,车票,地铁,公交,停车,过路费,加油,燃油",
        "color": "#67C23A",
        "description": "出行、车辆相关费用",
    },
    {
        "name": "餐饮费",
        "keywords": "餐饮,餐费,饮食,餐厅,外卖,食品,酒店餐饮",
        "color": "#E6A23C",
        "description": "餐饮、外卖等支出",
    },
    {
        "name": "住宿费",
        "keywords": "住宿,酒店,宾馆,旅馆,客房",
        "color": "#F56C6C",
        "description": "差旅住宿费用",
    },
    {
        "name": "通讯费",
        "keywords": "通讯,电话,话费,流量,宽带,网络,通信",
        "color": "#909399",
        "description": "通讯网络相关费用",
    },
    {
        "name": "服务费",
        "keywords": "服务,咨询,顾问,技术服务,软件,系统,开发,维护,设计",
        "color": "#9B59B6",
        "description": "技术、咨询类服务费",
    },
    {
        "name": "设备购置",
        "keywords": "设备,电脑,服务器,显示器,键盘,鼠标,硬件",
        "color": "#3498DB",
        "description": "IT设备及硬件采购",
    },
    {
        "name": "其他",
        "keywords": "",
        "color": "#BDC3C7",
        "description": "未匹配到其他分类的发票",
    },
]

# 兜底分类名(必须存在于DEFAULT_CATEGORIES中)
FALLBACK_CATEGORY = "其他"


def _split_keywords(raw: Optional[str]) -> List[str]:
    """切分关键词字符串为去重去空的列表(支持中英文逗号/换行)"""
    if not raw:
        return []
    # 兼容中英文逗号、分号、空白换行
    import re

    parts = re.split(r"[,，;；\s\r\n]+", raw)
    seen = set()
    out: List[str] = []
    for p in parts:
        kw = p.strip()
        if kw and kw not in seen:
            seen.add(kw)
            out.append(kw)
    return out


def _count_hits(text: str, keywords: Iterable[str]) -> int:
    """统计文本中命中的关键词数量"""
    if not text:
        return 0
    hits = 0
    for kw in keywords:
        if kw and kw in text:
            hits += 1
    return hits


def classify_invoice(items_text: Optional[str], db: Optional[Session] = None) -> str:
    """
    根据开票内容匹配最合适的分类。

    Args:
        items_text: 发票的开票明细文本
        db: 可选的Session，传入时将基于数据库中的分类配置匹配；否则使用DEFAULT_CATEGORIES。

    Returns:
        匹配到的分类名称；无匹配时返回"其他"。
    """
    if not items_text:
        return FALLBACK_CATEGORY

    # 优先使用数据库中已启用的分类
    categories: List[dict] = []
    if db is not None:
        try:
            db_cats = (
                db.query(Category).filter(Category.is_active.is_(True)).all()
            )
            if db_cats:
                categories = [
                    {"name": c.name, "keywords": c.keywords or ""} for c in db_cats
                ]
        except Exception as e:
            logger.warning(f"读取数据库分类失败，回退到默认分类: {e}")

    if not categories:
        categories = [
            {"name": c["name"], "keywords": c["keywords"]} for c in DEFAULT_CATEGORIES
        ]

    best_name = FALLBACK_CATEGORY
    best_hits = 0
    for cat in categories:
        kws = _split_keywords(cat.get("keywords"))
        if not kws:
            continue
        hits = _count_hits(items_text, kws)
        if hits > best_hits:
            best_hits = hits
            best_name = cat["name"]

    return best_name if best_hits > 0 else FALLBACK_CATEGORY


def init_default_categories(db: Session) -> int:
    """
    初始化默认分类(按名称去重，已存在则跳过)。

    Returns:
        本次新创建的分类数量。
    """
    created = 0
    try:
        existing_names = {row[0] for row in db.query(Category.name).all()}
        for cat in DEFAULT_CATEGORIES:
            if cat["name"] in existing_names:
                continue
            entity = Category(
                name=cat["name"],
                keywords=cat.get("keywords") or None,
                description=cat.get("description"),
                color=cat.get("color") or "#409EFF",
                is_active=True,
            )
            db.add(entity)
            created += 1
        if created:
            db.commit()
            logger.info(f"已初始化默认分类 {created} 个")
        else:
            logger.info("默认分类已存在，跳过初始化")
    except Exception as e:
        logger.error(f"初始化默认分类失败: {e}")
        db.rollback()
    return created


def batch_classify(db: Session, invoice_ids: Optional[List[int]] = None) -> dict:
    """
    批量重新分类。

    Args:
        db: 数据库会话
        invoice_ids: 指定的发票ID列表；若为None则对所有未分类(category为空)的发票分类。

    Returns:
        {"total": ..., "updated": ..., "skipped": ...}
    """
    query = db.query(Invoice)
    if invoice_ids:
        query = query.filter(Invoice.id.in_(invoice_ids))
    else:
        # 默认仅处理未分类的发票
        query = query.filter(
            (Invoice.category.is_(None)) | (Invoice.category == "")
        )

    invoices = query.all()
    total = len(invoices)
    updated = 0
    skipped = 0

    for inv in invoices:
        if not inv.items:
            skipped += 1
            continue
        new_cat = classify_invoice(inv.items, db=db)
        if new_cat and new_cat != inv.category:
            inv.category = new_cat
            updated += 1

    if updated:
        db.commit()
    logger.info(
        f"批量分类完成: total={total}, updated={updated}, skipped={skipped}"
    )
    return {"total": total, "updated": updated, "skipped": skipped}
