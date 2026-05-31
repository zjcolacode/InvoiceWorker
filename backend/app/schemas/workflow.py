"""月度整理流程相关 Schemas"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowStartRequest(BaseModel):
    """启动流程请求"""

    email_fetch: bool = Field(True, description="是否拉取邮件")
    recognize: bool = Field(True, description="是否执行识别")
    classify: bool = Field(True, description="是否执行分类")
    organize: bool = Field(True, description="是否执行文件归档")


class WorkflowStartResponse(BaseModel):
    """启动流程响应"""

    task_id: int
    status: str
    message: str = "流程已启动"


class WorkflowStepDetail(BaseModel):
    """流程步骤详情"""

    step: str  # 步骤名称(中文)
    key: str  # 步骤键: email_fetch/recognize/classify/organize
    status: str  # pending / processing / completed / failed / skipped
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowStatus(BaseModel):
    """流程状态"""

    task_id: int
    status: str  # pending, processing, completed, failed, cancelled
    current_step: str = ""
    progress: int = 0  # 0 - 100
    steps_detail: List[WorkflowStepDetail] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_log: Optional[str] = None
    invoice_count: int = 0


class WorkflowHistoryItem(BaseModel):
    """历史流程项"""

    task_id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    invoice_count: int = 0
    error_log: Optional[str] = None
    summary: Optional[str] = None  # 步骤汇总(从error_log/result中析出)


class WorkflowHistoryPage(BaseModel):
    """历史流程分页"""

    total: int
    page: int
    page_size: int
    items: List[WorkflowHistoryItem] = Field(default_factory=list)


__all__ = [
    "WorkflowStartRequest",
    "WorkflowStartResponse",
    "WorkflowStepDetail",
    "WorkflowStatus",
    "WorkflowHistoryItem",
    "WorkflowHistoryPage",
]
