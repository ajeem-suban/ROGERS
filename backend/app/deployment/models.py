"""
Data models for ROGERS Deployment Automation (Slice 9).
"""
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

DeploymentPlatform = Literal["docker", "render", "vercel", "netlify", "railway", "local_container"]
ReadinessStatus = Literal["ready", "ready_with_warnings", "blocked", "failed"]
DeploymentStatus = Literal["pending", "deploying", "healthy", "failed", "rolled_back"]
HealthCheckStatus = Literal["pending", "passing", "failing", "skipped"]


class ProjectStackDetection(BaseModel):
    language: str = Field(..., description="Detected primary programming language (python, typescript, javascript, etc.)")
    framework: str = Field(..., description="Detected primary framework (fastapi, flask, react, vite, express, static, etc.)")
    package_manager: str = Field(default="none", description="Package manager (pip, poetry, uv, npm, yarn, pnpm)")
    build_command: Optional[str] = Field(default=None, description="Inferred build command (e.g. npm run build)")
    start_command: Optional[str] = Field(default=None, description="Inferred production start command")
    default_port: int = Field(default=8000, description="Recommended runtime port")
    output_dir: Optional[str] = Field(default=None, description="Static build output directory if applicable (e.g. dist, build)")
    detected_configs: List[str] = Field(default_factory=list, description="List of existing config files found")
    required_env_vars: List[str] = Field(default_factory=list, description="Inferred environment variable names")


class ReadinessCheckItem(BaseModel):
    id: str = Field(..., description="Unique check identifier")
    title: str = Field(..., description="Human-readable check title")
    status: Literal["pass", "warning", "blocked"] = Field(..., description="Outcome of check")
    severity: Literal["info", "warning", "critical"] = Field(default="info", description="Severity level")
    details: str = Field(..., description="Detailed explanation of findings")
    recommendation: Optional[str] = Field(default=None, description="Guidance to resolve issue if not passing")


class DeploymentReadinessReport(BaseModel):
    overall_status: ReadinessStatus = Field(..., description="Overall readiness: ready, ready_with_warnings, blocked, failed")
    can_deploy: bool = Field(..., description="True if no critical blockers prevent deployment")
    score: int = Field(default=100, description="Readiness score from 0 to 100")
    checks: List[ReadinessCheckItem] = Field(default_factory=list, description="Detailed check items")
    blockers: List[str] = Field(default_factory=list, description="List of blocking issue descriptions")
    warnings: List[str] = Field(default_factory=list, description="List of non-blocking warning descriptions")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GeneratedConfigFile(BaseModel):
    filename: str = Field(..., description="Relative file name (e.g. Dockerfile, render.yaml)")
    path: str = Field(..., description="Target relative file path within project")
    content: str = Field(..., description="Full content of the generated configuration file")
    file_type: str = Field(default="dockerfile", description="Type: dockerfile, yaml, json, toml, procfile")


class DeploymentPlan(BaseModel):
    plan_id: str = Field(..., description="Unique deployment plan ID")
    project_id: str = Field(..., description="Associated project ID")
    platform: DeploymentPlatform = Field(..., description="Target platform")
    environment: str = Field(default="production", description="Target environment name")
    build_command: Optional[str] = Field(default=None, description="Build command to execute")
    start_command: Optional[str] = Field(default=None, description="Runtime launch command")
    target_port: int = Field(default=8000, description="Application network port")
    health_check_path: str = Field(default="/health", description="HTTP endpoint for health check")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Configured environment variables (values can be redacted)")
    generated_configs: List[GeneratedConfigFile] = Field(default_factory=list, description="Configuration files to be applied")
    steps: List[str] = Field(default_factory=list, description="Step-by-step deployment procedure")
    risks: List[str] = Field(default_factory=list, description="Identified risks and operational caveats")
    is_approved: bool = Field(default=False, description="Whether plan has been explicitly approved by a human")
    approved_by: Optional[str] = Field(default=None, description="Identity of approver")
    approved_at: Optional[str] = Field(default=None, description="Timestamp of approval")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DeploymentRecord(BaseModel):
    deployment_id: str = Field(..., description="Unique deployment execution ID")
    project_id: str = Field(..., description="Project ID")
    platform: DeploymentPlatform = Field(..., description="Platform targeted")
    environment: str = Field(default="production", description="Environment deployed to")
    status: DeploymentStatus = Field(default="pending", description="Deployment status")
    deployment_url: Optional[str] = Field(default=None, description="Live URL where app is reachable")
    health_status: HealthCheckStatus = Field(default="pending", description="Health check outcome")
    health_status_code: Optional[int] = Field(default=None, description="HTTP status code from health check probe")
    health_message: Optional[str] = Field(default=None, description="Health verification probe details")
    logs: List[str] = Field(default_factory=list, description="Execution and build logs")
    snapshot_id: Optional[str] = Field(default=None, description="Pre-deployment snapshot ID for instant rollback")
    duration_seconds: float = Field(default=0.0, description="Total execution duration in seconds")
    error_message: Optional[str] = Field(default=None, description="Error details if deployment failed")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = Field(default=None, description="Completion timestamp")


class DeploymentState(BaseModel):
    project_id: str = Field(..., description="Project ID")
    active_deployment: Optional[DeploymentRecord] = Field(default=None, description="Currently active or most recent deployment")
    current_plan: Optional[DeploymentPlan] = Field(default=None, description="Current prepared deployment plan")
    readiness: Optional[DeploymentReadinessReport] = Field(default=None, description="Last readiness evaluation")
    stack: Optional[ProjectStackDetection] = Field(default=None, description="Detected stack metadata")
    history: List[DeploymentRecord] = Field(default_factory=list, description="Chronological log of past deployments")


class DeploymentPlanRequest(BaseModel):
    platform: DeploymentPlatform = Field(default="docker", description="Target platform for plan generation")
    target_port: Optional[int] = Field(default=None, description="Custom target port override")
    health_check_path: Optional[str] = Field(default=None, description="Custom health check path")
    env_vars: Optional[Dict[str, str]] = Field(default=None, description="Custom environment variable overrides")


class ApprovePlanRequest(BaseModel):
    approved_by: str = Field(default="Commander", description="Name/title of user approving deployment")
    notes: Optional[str] = Field(default=None, description="Optional approval comments or audit notes")


class DeployActionRequest(BaseModel):
    simulate_only: bool = Field(default=False, description="If true, executes dry-run simulation without altering real external services")


class RollbackRequest(BaseModel):
    target_deployment_id: Optional[str] = Field(default=None, description="Specific previous deployment ID to rollback to (default is latest healthy)")
