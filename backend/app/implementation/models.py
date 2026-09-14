from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class FileOperation(BaseModel):
    path: str = Field(..., description="Relative path within the project root")
    operation: Literal["create", "modify"] = Field(..., description="File operation: create or modify")
    content: str = Field(..., description="Complete new or updated file content")
    before_content: Optional[str] = Field(default=None, description="Original file content before modification (for diffs)")


class ImplementationProposal(BaseModel):
    summary: str = Field(..., description="High-level summary of the implementation changes")
    changes: List[FileOperation] = Field(default_factory=list, description="List of discrete file operations")
    tests: List[str] = Field(default_factory=list, description="Verification checks or test assertions performed")


class ValidationResult(BaseModel):
    status: Literal["passed", "failed"] = Field(..., description="Validation outcome")
    command: str = Field(..., description="Safe validation command executed")
    output: str = Field(default="", description="Command standard output")
    error: Optional[str] = Field(default=None, description="Validation failure details or standard error")


class TaskImplementationResult(BaseModel):
    status: Literal["success", "failed"] = Field(..., description="Overall implementation outcome")
    task_id: str = Field(..., description="Unique task identifier")
    summary: str = Field(..., description="Summary of work completed")
    files_changed: List[str] = Field(default_factory=list, description="List of relative file paths changed")
    changes: List[FileOperation] = Field(default_factory=list, description="Detailed file changes with before/after content")
    validation: ValidationResult = Field(..., description="Validation check results")
    snapshot_id: Optional[str] = Field(default=None, description="Snapshot identifier for rollback")
