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


class TestResult(BaseModel):
    __test__ = False
    status: Literal["not_run", "running", "passed", "failed", "timeout", "no_tests", "blocked", "error"] = Field(
        default="not_run", description="Status of the test execution"
    )
    exit_code: Optional[int] = Field(default=None, description="Process exit code")
    stdout: str = Field(default="", description="Standard output from test runner")
    stderr: str = Field(default="", description="Standard error output from test runner")
    duration_seconds: float = Field(default=0.0, description="Execution time in seconds")
    tests_total: int = Field(default=0, description="Total number of tests discovered")
    tests_passed: int = Field(default=0, description="Number of tests passing")
    tests_failed: int = Field(default=0, description="Number of tests failing")
    tests_skipped: int = Field(default=0, description="Number of tests skipped")
    failure_summary: Optional[str] = Field(default=None, description="Concise summary of failure details")


class FailureAnalysis(BaseModel):
    root_cause: str = Field(..., description="Identified root cause of test or validation failure")
    affected_files: List[str] = Field(default_factory=list, description="Files directly implicated in the failure")
    explanation: str = Field(..., description="Technical breakdown of why the error occurred")
    proposed_fix: str = Field(..., description="Actionable plan to resolve the failure")
    confidence: float = Field(default=0.9, description="Confidence score between 0.0 and 1.0")


class RepairAttempt(BaseModel):
    attempt_number: int = Field(..., description="Attempt sequence number (1-3)")
    snapshot_id: Optional[str] = Field(default=None, description="Pre-repair snapshot ID")
    summary: str = Field(..., description="Summary of repairs applied")
    changes: List[FileOperation] = Field(default_factory=list, description="File operations applied during repair")
    validation: ValidationResult = Field(..., description="Static validation outcome after repair")
    test_result: TestResult = Field(..., description="Test results after repair")
    failure_analysis: Optional[FailureAnalysis] = Field(default=None, description="Failure diagnosis leading to this repair")


class MissionLogEntry(BaseModel):
    timestamp: str = Field(..., description="Time of event")
    level: Literal["info", "success", "warning", "error"] = Field(default="info", description="Log level")
    stage: str = Field(..., description="Mission stage, e.g., RECON, IMPLEMENT, SECURE, SNAPSHOT, VALIDATE, TEST, REPAIR, VERIFY")
    message: str = Field(..., description="Log message")


class TaskImplementationResult(BaseModel):
    status: Literal["success", "verified", "completed", "failed"] = Field(..., description="Overall implementation outcome")
    task_id: str = Field(..., description="Unique task identifier")
    summary: str = Field(..., description="Summary of work completed")
    files_changed: List[str] = Field(default_factory=list, description="List of relative file paths changed")
    changes: List[FileOperation] = Field(default_factory=list, description="Detailed file changes with before/after content")
    validation: ValidationResult = Field(..., description="Validation check results")
    snapshot_id: Optional[str] = Field(default=None, description="Initial snapshot identifier for rollback")
    test_result: Optional[TestResult] = Field(default=None, description="Outcome of automated tests")
    repair_attempts: List[RepairAttempt] = Field(default_factory=list, description="Chronological record of bounded repair attempts")
    mission_logs: List[MissionLogEntry] = Field(default_factory=list, description="Chronological mission execution log")
    verified: bool = Field(default=False, description="True only if automated tests executed and passed")
    security_checks: dict[str, bool] = Field(default_factory=dict, description="Verifiable security guarantees executed")
