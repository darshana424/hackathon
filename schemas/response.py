from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    state: str = "running"
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ActionItem(BaseModel):
    id: str
    type: str
    description: str
    priority: str = "medium"
    status: str = "pending"

class ModuleIssue(BaseModel):
    issue_type: str
    description: str
    remediation: str
    severity: str = "low"

class ModuleResult(BaseModel):
    name: str
    issues: List[ModuleIssue] = []
    data: Dict[str, Any] = {}

class SEOTaskResult(BaseModel):
    task_id: str
    domain: str
    seo_score: float = 0.0
    pages_crawled: int = 0
    actions: List[ActionItem] = []
    modules: Dict[str, ModuleResult] = {}
    files_generated: List[str] = []
    automation_summary: Dict[str, Any] = {}
    completed_at: datetime
