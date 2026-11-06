from __future__ import annotations

from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field

AgentRole = Literal[
    "researcher",
    "architect",
    "developer",
    "tester",
    "reviewer"
]

AgentStatus = Literal[
    "idle",
    "busy",
    "completed",
    "failed"
]

ParallelMissionStatus = Literal[
    "ready",
    "running",
    "paused",
    "blocked",
    "failed",
    "cancelled",
    "completed"
]


class AgentInfo(BaseModel):
    agent_id: str
    role: AgentRole
    name: str
    specialization: str
    status: AgentStatus = "idle"
    current_task_id: Optional[str] = None
    current_task_title: Optional[str] = None
    tasks_completed: int = 0
    recent_logs: List[str] = Field(default_factory=list)


class AgentLogEntry(BaseModel):
    timestamp: str
    agent_id: str
    role: AgentRole
    task_id: Optional[str] = None
    message: str
    level: Literal["info", "success", "warning", "error"] = "info"


class ParallelMissionConfig(BaseModel):
    max_concurrent_agents: int = Field(default=3, ge=1, le=5, description="Maximum concurrent development agents")


class ParallelPlanItem(BaseModel):
    task_id: str
    title: str
    priority: str
    depends_on: List[str] = Field(default_factory=list)
    stage_index: int = 0
    assigned_role: AgentRole = "developer"
    estimated_files: List[str] = Field(default_factory=list)


class ParallelExecutionPlan(BaseModel):
    project_id: str
    project_name: str
    is_valid: bool
    total_tasks: int
    parallel_batches: List[List[str]] = Field(default_factory=list)
    tasks: List[ParallelPlanItem] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)


class ParallelMissionState(BaseModel):
    project_id: str
    status: ParallelMissionStatus = "ready"
    config: ParallelMissionConfig = Field(default_factory=ParallelMissionConfig)
    agents: List[AgentInfo] = Field(default_factory=list)
    file_locks: Dict[str, str] = Field(default_factory=dict, description="Active locked files mapped to task_id")
    running_task_ids: List[str] = Field(default_factory=list)
    completed_task_ids: List[str] = Field(default_factory=list)
    failed_task_ids: List[str] = Field(default_factory=list)
    blocked_task_ids: List[str] = Field(default_factory=list)
    parallel_batches: List[List[str]] = Field(default_factory=list)
    logs: List[AgentLogEntry] = Field(default_factory=list)
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


class ParallelMissionActionRequest(BaseModel):
    action: Literal["start", "pause", "resume", "cancel"] = "start"
    max_concurrent_agents: Optional[int] = Field(default=3, ge=1, le=5)


class ParallelMissionReport(BaseModel):
    project_id: str
    project_name: str
    status: ParallelMissionStatus
    total_tasks: int
    completed_count: int
    failed_count: int
    blocked_count: int
    concurrent_limit: int
    duration_seconds: float = 0.0
    agents_summary: List[AgentInfo] = Field(default_factory=list)
    summary: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
