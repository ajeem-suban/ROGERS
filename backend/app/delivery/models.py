from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class DeliveryPackageMetadata(BaseModel):
    project_id: str = Field(..., description="Unique identifier of the project")
    project_name: str = Field(..., description="Human-readable name of the project")
    package_filename: str = Field(..., description="Name of the generated archive file")
    package_path: str = Field(..., description="Server path to the package archive")
    package_size_bytes: int = Field(..., description="Size of the package archive in bytes")
    sha256_checksum: str = Field(..., description="Cryptographic SHA-256 hash of the archive")
    files_count: int = Field(..., description="Total number of files included in the package")
    verification_status: Literal["verified", "completed", "unverified", "failed"] = Field(
        ..., description="Verification status at time of packaging"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    download_url: str = Field(..., description="API endpoint to download the package archive")


class VerificationSummary(BaseModel):
    total_tasks: int = Field(default=0, description="Total development tasks in blueprint")
    verified_tasks: int = Field(default=0, description="Tasks with passing automated tests")
    completed_tasks: int = Field(default=0, description="Tasks compiled but without tests")
    failed_tasks: int = Field(default=0, description="Tasks that failed implementation or tests")
    pending_tasks: int = Field(default=0, description="Tasks waiting for implementation")
    tests_discovered: int = Field(default=0, description="Total tests discovered across verified tasks")
    tests_passed: int = Field(default=0, description="Total passing tests")
    tests_failed: int = Field(default=0, description="Total failing tests")
    pass_rate_percent: float = Field(default=0.0, description="Percentage of passed tests")
    status: Literal["verified", "completed", "unverified", "failed"] = Field(
        default="unverified", description="Aggregate verification status"
    )


class MissionReport(BaseModel):
    project_id: str = Field(..., description="Unique project ID")
    project_name: str = Field(..., description="Project name")
    idea: str = Field(..., description="Original user project idea")
    status: str = Field(..., description="Current project lifecycle status")
    current_stage: Optional[str] = Field(default=None, description="Active or final stage name")
    stages_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of multi-stage pipeline")
    blueprint_summary: Optional[Dict[str, Any]] = Field(default=None, description="Overview of generated blueprint")
    verification_summary: VerificationSummary = Field(..., description="Verification and test suite summary")
    security_audit: Dict[str, bool] = Field(default_factory=dict, description="Security sandbox defense guarantees")
    files_modified: List[str] = Field(default_factory=list, description="All files modified across verified tasks")
    package_metadata: Optional[DeliveryPackageMetadata] = Field(default=None, description="Delivery package details")
    generated_at: str = Field(..., description="ISO 8601 report generation timestamp")
    recommended_next_steps: List[str] = Field(default_factory=list, description="Tactical next steps for deployment")
    tagline: str = Field(default="I CAN DO THIS ALL DAY.", description="Mission motto")
