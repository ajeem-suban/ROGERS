from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


MissionStatus = Literal[
    "ready",
    "running",
    "paused",
    "blocked",
    "failed",
    "cancelled",
    "completed"
]

TaskExecutionState = Literal[
    "pending",
    "eligible",
    "running",
    "verified",
    "failed",
    "blocked",
    "skipped"
]


class TaskPlanItem(BaseModel):
    task_id: str
    title: str
    priority: str
    depends_on: List[str] = Field(default_factory=list)
    state: TaskExecutionState = "pending"
    order_index: int = 0
    blocked_by: List[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    project_id: str
    project_name: str
    is_valid: bool
    total_tasks: int
    execution_order: List[str]
    tasks: List[TaskPlanItem]
    has_cycles: bool = False
    missing_dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    validation_errors: List[str] = Field(default_factory=list)


class TaskProgressItem(BaseModel):
    task_id: str
    title: str
    status: str
    depends_on: List[str] = Field(default_factory=list)
    verified: bool = False
    snapshot_id: Optional[str] = None
    tests_passed: int = 0
    tests_total: int = 0
    repair_attempts_count: int = 0
    error_message: Optional[str] = None


class MissionState(BaseModel):
    project_id: str
    status: MissionStatus = "ready"
    current_task_id: Optional[str] = None
    current_task_title: Optional[str] = None
    execution_order: List[str] = Field(default_factory=list)
    completed_task_ids: List[str] = Field(default_factory=list)
    failed_task_ids: List[str] = Field(default_factory=list)
    blocked_task_ids: List[str] = Field(default_factory=list)
    skipped_task_ids: List[str] = Field(default_factory=list)
    tasks_progress: Dict[str, TaskProgressItem] = Field(default_factory=dict)
    active_worker_id: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


class MissionActionRequest(BaseModel):
    action: Literal["start", "pause", "resume", "cancel"] = "start"


class MissionExecutionReport(BaseModel):
    project_id: str
    project_name: str
    status: MissionStatus
    total_tasks: int
    completed_count: int
    failed_count: int
    blocked_count: int
    skipped_count: int
    duration_seconds: float = 0.0
    tasks: List[TaskProgressItem] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    summary: str = ""
