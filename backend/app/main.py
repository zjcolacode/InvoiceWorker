from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base, SessionLocal
from app.core.init_db import init_db
from app.api import auth, users, recognition, email, invoices, categories, export, dashboard, workflow, reimbursement
from app.api import print as print_api
# 确保所有模型被加载，使 Base.metadata 包含新增的 categories 表
from app import models  # noqa: F401
from app.services.print_service import ensure_output_dir as ensure_print_output_dir
from app.services.excel_exporter import ensure_export_dir
from app.services.invoice_classifier import init_default_categories
from app.tasks.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title="InvoiceWorker API",
    description="发票智能管理系统后端API",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户管理"])
app.include_router(recognition.router, prefix="/api/recognition", tags=["发票识别"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["发票管理"])
app.include_router(email.router, prefix="/api/email", tags=["邮箱接入"])
app.include_router(print_api.router, prefix="/api/print", tags=["打印"])
app.include_router(categories.router, prefix="/api/categories", tags=["发票分类"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["月度整理流程"])
app.include_router(export.router, prefix="/api/export", tags=["数据导出"])
app.include_router(reimbursement.router, prefix="/api/reimbursement", tags=["报销单管理"])


@app.on_event("startup")
async def startup():
    """应用启动时创建数据库表并初始化数据"""
    Base.metadata.create_all(bind=engine)
    init_db()
    # 初始化默认发票分类
    db = SessionLocal()
    try:
        init_default_categories(db)
    finally:
        db.close()
    # 确保打印输出目录存在
    ensure_print_output_dir()
    # 确保导出输出目录存在
    ensure_export_dir()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时停止调度器"""
    stop_scheduler()


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "message": "InvoiceWorker API is running"}


# 路由注册占位 - 后续添加
# from app.api import tasks
# app.include_router(tasks.router, prefix="/api/tasks", tags=["任务管理"])
