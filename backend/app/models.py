from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TechStack(BaseModel):
    frontend: str = Field(..., description="Recommended frontend framework and tools")
    backend: str = Field(..., description="Recommended backend framework and runtime")
    database: str = Field(..., description="Recommended primary database and caching layer")
    ai: str = Field(..., description="Recommended AI/ML models, libraries, and frameworks")


class Architecture(BaseModel):
    description: str = Field(..., description="High-level architecture overview and data flow")
    components: List[str] = Field(default_factory=list, description="Core system components")


from pydantic import BaseModel, Field, field_validator, model_validator
from .implementation.models import TaskImplementationResult


class DevelopmentTask(BaseModel):
    id: Optional[str] = Field(default=None, description="Unique task identifier")
    title: str = Field(..., description="Actionable development task title")
    description: str = Field(..., description="Detailed description of the task requirements")
    priority: str = Field(default="medium", description="Priority level: high, medium, or low")
    status: str = Field(default="pending", description="Task implementation status: pending, implementing, completed, failed")
    implementation_result: Optional[TaskImplementationResult] = Field(default=None, description="Result of code implementation")

    @model_validator(mode="after")
    def ensure_id(self) -> "DevelopmentTask":
        if not self.id and self.title:
            import re
            clean_title = re.sub(r"[^a-zA-Z0-9]", "_", self.title.lower()).strip("_")[:30]
            self.id = f"task_{clean_title}"
        return self


class Blueprint(BaseModel):
    summary: str = Field(..., description="Concise, executive technical summary of the project")
    requirements: List[str] = Field(default_factory=list, description="Key functional requirements")
    tech_stack: TechStack = Field(..., description="Selected technology stack")
    architecture: Architecture = Field(..., description="System architecture design")
    development_tasks: List[DevelopmentTask] = Field(default_factory=list, description="Actionable development tasks")
    next_steps: List[str] = Field(default_factory=list, description="Recommended immediate next steps")


class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name")
    idea: str = Field(..., description="Detailed description of the project idea")

    @field_validator("name", "idea")
    @classmethod
    def validate_non_empty(cls, v: str, info) -> str:
        s = v.strip()
        if not s:
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} cannot be empty.")
        return s


# Slice 2 Stage Data Models
class StageData(BaseModel):
    name: str = Field(..., description="Stage name identifier")
    label: str = Field(..., description="Human-readable stage title")
    status: str = Field(default="pending", description="pending, running, waiting_approval, approved, modified, skipped, failed")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Structured output produced by this stage agent")
    user_modifications: Optional[Dict[str, Any]] = Field(default=None, description="User edits to this stage")
    guidance: Optional[str] = Field(default=None, description="User guidance provided during generation/regeneration")
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Project(BaseModel):
    id: str = Field(..., description="Unique project identifier (UUID)")
    name: str = Field(..., description="Project name")
    idea: str = Field(..., description="Project idea description")
    status: str = Field(default="created", description="Project status: created, generating, waiting_approval, completed, failed")
    current_stage: Optional[str] = Field(default="research", description="Current active stage")
    stages: Dict[str, StageData] = Field(default_factory=dict, description="Detailed stage progression")
    blueprint: Optional[Blueprint] = Field(default=None, description="Synthesized technical blueprint (Slice 1 & 2)")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BlueprintResponse(BaseModel):
    project_id: str
    status: str
    blueprint: Blueprint


class StageActionPayload(BaseModel):
    guidance: Optional[str] = Field(default=None, description="Optional prompt guidance for regeneration")
    modifications: Optional[Dict[str, Any]] = Field(default=None, description="Optional manual edits to stage output")


class ScaffoldResponse(BaseModel):
    project_id: str
    project_dir: str
    files_created: List[str]
    message: str
