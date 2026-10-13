from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class RemoteConfig(BaseModel):
    name: str = Field(..., description="Remote alias, e.g., 'origin'")
    fetch_url: str = Field(..., description="Sanitized/redacted fetch URL")
    push_url: str = Field(..., description="Sanitized/redacted push URL")


class GitFileChange(BaseModel):
    path: str = Field(..., description="Relative path within generated project")
    status: Literal["modified", "added", "deleted", "untracked", "renamed", "conflicted"] = Field(
        ..., description="Git status of the file"
    )
    is_staged: bool = Field(default=False, description="Whether the file is currently in the index")
    has_secret_risk: bool = Field(default=False, description="Whether file flagged by secret scanner")
    risk_reason: Optional[str] = Field(default=None, description="Explanation of secret or security risk")


class GitStatusResponse(BaseModel):
    git_installed: bool = Field(..., description="Whether Git CLI executable is available")
    initialized: bool = Field(..., description="Whether project directory is an initialized Git repository")
    branch: Optional[str] = Field(default=None, description="Current branch name")
    head_commit: Optional[str] = Field(default=None, description="Current HEAD commit SHA (short or full)")
    is_clean: bool = Field(default=True, description="True if no uncommitted or untracked changes exist")
    is_detached: bool = Field(default=False, description="True if repository is in detached HEAD state")
    changes: List[GitFileChange] = Field(default_factory=list, description="List of detected file changes")
    remotes: List[RemoteConfig] = Field(default_factory=list, description="List of configured Git remotes")
    ahead_count: int = Field(default=0, description="Number of local commits ahead of tracking remote")
    behind_count: int = Field(default=0, description="Number of commits behind tracking remote")
    diverged: bool = Field(default=False, description="True if branch has diverged from tracking remote")
    error: Optional[str] = Field(default=None, description="Sanitized error description if probing failed")


class GitDiffResponse(BaseModel):
    diff: str = Field(default="", description="Bounded git diff output")
    truncated: bool = Field(default=False, description="True if diff was truncated for safety")
    file_count: int = Field(default=0, description="Number of files changed in diff")


class GitInitRequest(BaseModel):
    default_branch: str = Field(default="main", description="Default branch name for initialization")


class GitCommitRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=500, description="Commit message describing approved changes")
    approved_files: List[str] = Field(..., min_length=1, description="Explicit list of relative file paths to stage and commit")


class GitCommitResponse(BaseModel):
    success: bool = Field(..., description="True if commit succeeded")
    commit_hash: Optional[str] = Field(default=None, description="Created commit SHA")
    branch: Optional[str] = Field(default=None, description="Branch committed to")
    files_committed: List[str] = Field(default_factory=list, description="List of files committed")
    message: str = Field(..., description="Status summary or error message")


class GitRemoteAddRequest(BaseModel):
    name: str = Field(default="origin", min_length=1, max_length=50, description="Remote name")
    url: str = Field(..., min_length=5, max_length=500, description="Remote repository URL (HTTPS or SSH)")


class GitPushRequest(BaseModel):
    remote_name: str = Field(default="origin", description="Target remote name")
    branch_name: Optional[str] = Field(default=None, description="Target branch name (defaults to current branch)")
    auto_publish: bool = Field(default=False, description="Whether triggered via auto-publish policy")


class GitPushResponse(BaseModel):
    success: bool = Field(..., description="True if push succeeded")
    remote_name: str = Field(..., description="Remote pushed to")
    branch_name: str = Field(..., description="Branch pushed to")
    commit_hash: Optional[str] = Field(default=None, description="HEAD commit pushed")
    message: str = Field(..., description="Push summary message")
    error_detail: Optional[str] = Field(default=None, description="Sanitized failure reason")


class PublishingHistoryEntry(BaseModel):
    id: str = Field(..., description="Unique audit record UUID")
    project_id: str = Field(..., description="Associated project ID")
    commit_hash: Optional[str] = Field(default=None, description="Git commit SHA")
    commit_message: str = Field(..., description="Commit message")
    branch: str = Field(..., description="Git branch")
    remote_name: Optional[str] = Field(default=None, description="Remote pushed to")
    files_committed: List[str] = Field(default_factory=list, description="Files included in commit")
    verification_status: str = Field(..., description="Verification status at time of publishing")
    push_status: Literal["committed_local", "pushed", "push_failed"] = Field(
        ..., description="Outcome of the publishing operation"
    )
    timestamp: str = Field(..., description="ISO 8601 operation timestamp")
    error_detail: Optional[str] = Field(default=None, description="Sanitized error detail if push failed")
