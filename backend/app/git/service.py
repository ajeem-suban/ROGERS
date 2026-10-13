from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from ..models import Project
from ..scaffolder import GENERATED_BASE_DIR, slugify
from .models import (
    GitStatusResponse,
    GitDiffResponse,
    GitCommitResponse,
    GitPushResponse,
    GitFileChange,
    RemoteConfig,
    PublishingHistoryEntry,
)

# Repo Root safety check: ROGERS application root directory
ROGERS_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Files and patterns strictly blocked from commits to prevent secret leaks
BLOCKED_EXACT_FILES: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    "id_rsa",
    "id_ed25519",
    "id_dsa",
    "id_ecdsa",
}

BLOCKED_PATTERNS = [
    re.compile(r"^\.env($|\..*)", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*\.pkcs12$", re.IGNORECASE),
    re.compile(r".*\.pfx$", re.IGNORECASE),
]

# Sensitive content patterns inside files
SECRET_CONTENT_PATTERNS = [
    re.compile(r"-----BEGIN (RSA|OPENSSH|DSA|EC|PRIVATE) KEY-----"),
    re.compile(r"(api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),  # GitHub Personal Access Token
    re.compile(r"github_pat_[A-Za-z0-9_]{50,}"),  # Fine-grained PAT
]

MAX_DIFF_BYTES = 50 * 1024  # 50 KB max diff


class GitSecurityError(Exception):
    """Raised when repository path validation, secret scanning, or safety checks fail."""
    pass


class GitExecutionError(Exception):
    """Raised when controlled git CLI operations return failure."""
    pass


def redact_url_credentials(url: str) -> str:
    """Redacts embedded usernames, passwords, or tokens in git remote URLs."""
    if not url:
        return ""
    # Matches http://user:token@host or https://token@host
    redacted = re.sub(r"(https?://)([^@/]+)@", r"\1***@", url)
    return redacted


def is_git_installed() -> bool:
    """Checks whether git executable is available on the host system."""
    return shutil.which("git") is not None


def resolve_and_validate_project_repo(project: Project) -> Path:
    """
    Validates and resolves the target project repository path.
    Guarantees:
    1. Must reside strictly inside GENERATED_BASE_DIR.
    2. Must NOT point to D:\\ROGERS application directory.
    3. Blocks path traversal, non-existent directories, and symlink breakouts.
    """
    project_slug = slugify(project.name)
    target_dir = (GENERATED_BASE_DIR / project_slug).resolve()
    base_resolved = GENERATED_BASE_DIR.resolve()
    rogers_resolved = ROGERS_ROOT.resolve()

    # Safety check: Cannot target ROGERS application root directly or its parent
    if target_dir == rogers_resolved:
        raise GitSecurityError("CRITICAL SAFETY VIOLATION: Target repository cannot be ROGERS source repository.")

    # Safety check: Must be inside GENERATED_BASE_DIR
    try:
        target_dir.relative_to(base_resolved)
    except ValueError:
        raise GitSecurityError(f"Directory traversal violation: Target '{target_dir}' is outside approved workspace.")

    if not target_dir.exists() or not target_dir.is_dir():
        raise GitSecurityError(f"Project directory '{project_slug}' does not exist. Please scaffold the project first.")

    return target_dir


def run_git_command(repo_path: Path, args: List[str], timeout: float = 30.0) -> Tuple[int, str, str]:
    """
    Executes a controlled Git command array with shell=False, timeouts, and sanitized output.
    """
    if not is_git_installed():
        raise GitExecutionError("Git CLI is not installed or not available in system PATH.")

    cmd = ["git"] + args
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False,
            encoding="utf-8",
            errors="replace"
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        raise GitExecutionError(f"Git operation timed out after {timeout} seconds.")
    except Exception as e:
        raise GitExecutionError(f"Git operation failed to execute: {str(e)}")


def scan_file_for_secret_risk(file_path: Path, rel_path: str) -> Tuple[bool, Optional[str]]:
    """
    Scans filename and content for sensitive material, tokens, and credentials.
    """
    name = file_path.name
    # Explicit files blocked
    if name in BLOCKED_EXACT_FILES:
        return True, f"File '{name}' is a sensitive configuration file and cannot be committed."

    # Pattern matches
    for pattern in BLOCKED_PATTERNS:
        if pattern.match(name) or pattern.match(rel_path):
            if name == ".env.example":
                continue  # Templates are allowed
            return True, f"File '{rel_path}' matches sensitive credential pattern."

    # Inspect file content if it exists and is under 1MB
    if file_path.exists() and file_path.is_file():
        try:
            size = file_path.stat().st_size
            if size > 1024 * 1024:
                return False, None  # Skip binary/large files from deep text scanning
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for sp in SECRET_CONTENT_PATTERNS:
                if sp.search(content):
                    return True, f"File '{rel_path}' contains detected credentials or private keys."
        except Exception:
            pass

    return False, None


class GitService:
    @staticmethod
    def get_status(project: Project) -> GitStatusResponse:
        """Inspects git status of the scaffolded project repository."""
        if not is_git_installed():
            return GitStatusResponse(
                git_installed=False,
                initialized=False,
                is_clean=True,
                error="Git executable not found on host."
            )

        try:
            repo_path = resolve_and_validate_project_repo(project)
        except GitSecurityError as e:
            return GitStatusResponse(
                git_installed=True,
                initialized=False,
                is_clean=True,
                error=str(e)
            )

        git_dir = repo_path / ".git"
        if not git_dir.exists() or not git_dir.is_dir():
            return GitStatusResponse(
                git_installed=True,
                initialized=False,
                is_clean=True
            )

        # 1. Get current branch
        code, branch_out, _ = run_git_command(repo_path, ["branch", "--show-current"])
        branch = branch_out if code == 0 and branch_out else None

        # Check detached HEAD
        is_detached = False
        if not branch:
            code_head, head_sym, _ = run_git_command(repo_path, ["symbolic-ref", "-q", "HEAD"])
            if code_head != 0:
                is_detached = True
                branch = "DETACHED_HEAD"

        # 2. Get HEAD commit
        code_rev, head_rev, _ = run_git_command(repo_path, ["rev-parse", "--short", "HEAD"])
        head_commit = head_rev if code_rev == 0 else None

        # 3. Get file changes via status --porcelain
        code_stat, stat_out, _ = run_git_command(repo_path, ["status", "--porcelain"])
        changes: List[GitFileChange] = []
        if code_stat == 0 and stat_out:
            for line in stat_out.splitlines():
                if len(line) < 3:
                    continue
                index_st = line[0]
                work_st = line[1]
                file_rel = line[3:].strip()
                # Handle renamed files like "old -> new"
                if " -> " in file_rel:
                    file_rel = file_rel.split(" -> ")[1].strip()

                is_staged = index_st in ("M", "A", "D", "R", "C")
                st = "modified"
                if index_st == "?" or work_st == "?":
                    st = "untracked"
                elif index_st == "A" or work_st == "A":
                    st = "added"
                elif index_st == "D" or work_st == "D":
                    st = "deleted"
                elif index_st == "U" or work_st == "U":
                    st = "conflicted"

                # Check secret risk
                risk, reason = scan_file_for_secret_risk(repo_path / file_rel, file_rel)
                changes.append(GitFileChange(
                    path=file_rel,
                    status=st,
                    is_staged=is_staged,
                    has_secret_risk=risk,
                    risk_reason=reason
                ))

        # 4. Get remotes
        remotes: List[RemoteConfig] = []
        code_rem, rem_out, _ = run_git_command(repo_path, ["remote", "-v"])
        if code_rem == 0 and rem_out:
            seen_remotes: Dict[str, Dict[str, str]] = {}
            for line in rem_out.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    name, url, typ = parts[0], parts[1], parts[2].strip("()")
                    if name not in seen_remotes:
                        seen_remotes[name] = {"fetch": "", "push": ""}
                    if typ == "fetch":
                        seen_remotes[name]["fetch"] = redact_url_credentials(url)
                    elif typ == "push":
                        seen_remotes[name]["push"] = redact_url_credentials(url)
            for rname, rurls in seen_remotes.items():
                remotes.append(RemoteConfig(
                    name=rname,
                    fetch_url=rurls.get("fetch") or rurls.get("push") or "",
                    push_url=rurls.get("push") or rurls.get("fetch") or ""
                ))

        # 5. Check tracking status (ahead / behind)
        ahead = 0
        behind = 0
        diverged = False
        if branch and not is_detached:
            code_track, track_out, _ = run_git_command(repo_path, ["rev-list", "--left-right", "--count", f"{branch}...@{{u}}"])
            if code_track == 0 and track_out:
                parts = track_out.split()
                if len(parts) == 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
                    diverged = ahead > 0 and behind > 0

        return GitStatusResponse(
            git_installed=True,
            initialized=True,
            branch=branch,
            head_commit=head_commit,
            is_clean=len(changes) == 0,
            is_detached=is_detached,
            changes=changes,
            remotes=remotes,
            ahead_count=ahead,
            behind_count=behind,
            diverged=diverged
        )

    @staticmethod
    def init_repo(project: Project, default_branch: str = "main") -> GitStatusResponse:
        """Initializes a new Git repository in the generated project."""
        repo_path = resolve_and_validate_project_repo(project)
        git_dir = repo_path / ".git"
        if git_dir.exists():
            return GitService.get_status(project)

        # Run git init -b <branch>
        code, out, err = run_git_command(repo_path, ["init", "-b", default_branch])
        if code != 0:
            # Fallback for older git versions without -b flag
            code2, _, err2 = run_git_command(repo_path, ["init"])
            if code2 != 0:
                raise GitExecutionError(f"Failed to initialize Git repository: {err or err2}")
            run_git_command(repo_path, ["checkout", "-b", default_branch])

        # Ensure sensible local project .gitignore exists
        gitignore_path = repo_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(
                ".venv/\n__pycache__/\n*.pyc\n.env\n.env.local\nnode_modules/\ndist/\n.rogers/\n",
                encoding="utf-8"
            )

        return GitService.get_status(project)

    @staticmethod
    def get_diff(project: Project, max_bytes: int = MAX_DIFF_BYTES) -> GitDiffResponse:
        """Retrieves a bounded git diff of unstaged and staged changes."""
        repo_path = resolve_and_validate_project_repo(project)
        # Combine staged and unstaged diff
        code, out, _ = run_git_command(repo_path, ["diff", "HEAD"])
        if code != 0 or not out:
            # If no HEAD commit yet, diff cached or empty
            code_c, out_c, _ = run_git_command(repo_path, ["diff", "--cached"])
            out = out_c if code_c == 0 else ""

        truncated = False
        if len(out.encode("utf-8")) > max_bytes:
            out = out[:max_bytes] + "\n\n... [DIFF TRUNCATED FOR SAFETY] ..."
            truncated = True

        file_count = len(re.findall(r"^diff --git ", out, re.MULTILINE))
        return GitDiffResponse(diff=out, truncated=truncated, file_count=file_count)

    @staticmethod
    def commit_approved_changes(project: Project, message: str, approved_files: List[str]) -> GitCommitResponse:
        """
        Stages ONLY explicitly approved files and creates a Git commit.
        Strictly blocks secrets and credentials.
        """
        repo_path = resolve_and_validate_project_repo(project)
        clean_msg = message.strip()
        if not clean_msg:
            raise GitSecurityError("Commit message cannot be empty.")

        # 1. Inspect each approved file for path safety and secret risk
        staged_files: List[str] = []
        for rel in approved_files:
            file_path = (repo_path / rel).resolve()
            # Verify file is inside project
            try:
                file_path.relative_to(repo_path)
            except ValueError:
                raise GitSecurityError(f"Path traversal detected in file '{rel}'.")

            risk, reason = scan_file_for_secret_risk(file_path, rel)
            if risk:
                raise GitSecurityError(f"Commit blocked: {reason}")

            staged_files.append(rel)

        # 2. Stage explicitly approved files
        # Only reset index if HEAD exists (on fresh/unborn branches, git reset errors)
        head_check, _, _ = run_git_command(repo_path, ["rev-parse", "-q", "--verify", "HEAD"])
        if head_check == 0:
            run_git_command(repo_path, ["reset"])

        for rel in staged_files:
            # Normalize path for git command
            normalized_rel = rel.replace("\\", "/")
            code_add, _, err_add = run_git_command(repo_path, ["add", normalized_rel])
            if code_add != 0:
                raise GitExecutionError(f"Failed to stage file '{rel}': {err_add}")

        # 3. Create commit
        # Set dummy user if not configured locally to prevent commit failure
        run_git_command(repo_path, ["config", "--local", "user.name", "ROGERS Mission Control"])
        run_git_command(repo_path, ["config", "--local", "user.email", "rogers@missioncontrol.local"])

        code_com, com_out, com_err = run_git_command(repo_path, ["commit", "-m", clean_msg])
        if code_com != 0:
            raise GitExecutionError(f"Git commit failed: {com_err or com_out}")

        # 4. Get created commit hash & branch
        _, hash_out, _ = run_git_command(repo_path, ["rev-parse", "HEAD"])
        _, br_out, _ = run_git_command(repo_path, ["branch", "--show-current"])

        commit_hash = hash_out[:8] if hash_out else "unknown"

        # Record publishing history in project
        entry = PublishingHistoryEntry(
            id=str(uuid.uuid4()),
            project_id=project.id,
            commit_hash=commit_hash,
            commit_message=clean_msg,
            branch=br_out or "main",
            remote_name=None,
            files_committed=staged_files,
            verification_status="verified" if (project.blueprint and any(t.status == "verified" for t in project.blueprint.development_tasks)) else "unverified",
            push_status="committed_local",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        project.publishing_history.insert(0, entry)

        return GitCommitResponse(
            success=True,
            commit_hash=commit_hash,
            branch=br_out or "main",
            files_committed=staged_files,
            message=f"Successfully created commit {commit_hash}"
        )

    @staticmethod
    def add_remote(project: Project, name: str, url: str) -> RemoteConfig:
        """Adds or updates a remote alias for the project repository."""
        repo_path = resolve_and_validate_project_repo(project)
        clean_name = name.strip()
        clean_url = url.strip()

        # Reject local paths or malicious protocols
        if not (clean_url.startswith("https://") or clean_url.startswith("git@") or clean_url.startswith("ssh://")):
            raise GitSecurityError("Remote URL must use HTTPS or SSH protocol.")

        # Check if remote already exists
        code, rem_list, _ = run_git_command(repo_path, ["remote"])
        if clean_name in rem_list.split():
            run_git_command(repo_path, ["remote", "set-url", clean_name, clean_url])
        else:
            code_add, _, err_add = run_git_command(repo_path, ["remote", "add", clean_name, clean_url])
            if code_add != 0:
                raise GitExecutionError(f"Failed to add remote: {err_add}")

        return RemoteConfig(
            name=clean_name,
            fetch_url=redact_url_credentials(clean_url),
            push_url=redact_url_credentials(clean_url)
        )

    @staticmethod
    def push_to_remote(project: Project, remote_name: str = "origin", branch_name: Optional[str] = None, auto_publish: bool = False) -> GitPushResponse:
        """
        Pushes verified commits to a configured Git remote.
        Strictly enforces the verification gate: unverified code cannot be published.
        """
        repo_path = resolve_and_validate_project_repo(project)

        # Gate 1: Verification gate check
        verified_tasks = 0
        if project.blueprint and project.blueprint.development_tasks:
            verified_tasks = sum(1 for t in project.blueprint.development_tasks if t.status == "verified")
            failed_tasks = sum(1 for t in project.blueprint.development_tasks if t.status == "failed")
            if failed_tasks > 0:
                raise GitSecurityError("Publishing blocked: Project contains failed development tasks.")

        if verified_tasks == 0:
            raise GitSecurityError("Publishing blocked: Project must have at least one verified task before pushing.")

        # Gate 2: Branch resolution & detached HEAD check
        _, cur_br, _ = run_git_command(repo_path, ["branch", "--show-current"])
        target_branch = branch_name or cur_br
        if not target_branch:
            raise GitSecurityError("Publishing blocked: Cannot push from detached HEAD.")

        # Gate 3: Check remote exists
        code_rem, remotes_out, _ = run_git_command(repo_path, ["remote"])
        if remote_name not in remotes_out.split():
            raise GitSecurityError(f"Remote '{remote_name}' is not configured.")

        # Gate 4: Push to remote safely without force
        _, head_commit, _ = run_git_command(repo_path, ["rev-parse", "--short", "HEAD"])
        code_push, push_out, push_err = run_git_command(repo_path, ["push", remote_name, f"{target_branch}:{target_branch}"], timeout=45.0)

        # Sanitize push output (redact URLs and credentials)
        clean_err = redact_url_credentials(push_err)
        clean_out = redact_url_credentials(push_out)

        if code_push != 0:
            # Record failed push in history (local commit preserved!)
            entry = PublishingHistoryEntry(
                id=str(uuid.uuid4()),
                project_id=project.id,
                commit_hash=head_commit,
                commit_message=f"Push to {remote_name}/{target_branch}",
                branch=target_branch,
                remote_name=remote_name,
                files_committed=[],
                verification_status="verified",
                push_status="push_failed",
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_detail=clean_err or "Push rejected by remote."
            )
            project.publishing_history.insert(0, entry)

            return GitPushResponse(
                success=False,
                remote_name=remote_name,
                branch_name=target_branch,
                commit_hash=head_commit,
                message="Push failed. Local commit was preserved.",
                error_detail=clean_err or "Remote rejected push."
            )

        # Success
        entry = PublishingHistoryEntry(
            id=str(uuid.uuid4()),
            project_id=project.id,
            commit_hash=head_commit,
            commit_message=f"Pushed to {remote_name}/{target_branch}",
            branch=target_branch,
            remote_name=remote_name,
            files_committed=[],
            verification_status="verified",
            push_status="pushed",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        project.publishing_history.insert(0, entry)

        return GitPushResponse(
            success=True,
            remote_name=remote_name,
            branch_name=target_branch,
            commit_hash=head_commit,
            message=f"Successfully pushed {head_commit} to {remote_name}/{target_branch}"
        )
