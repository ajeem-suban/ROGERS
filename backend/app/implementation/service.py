import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import (
    FileOperation,
    ImplementationProposal,
    ValidationResult,
    TaskImplementationResult
)
from ..models import Project, DevelopmentTask
from ..providers.base import AIProvider
from ..providers.factory import get_ai_provider
from ..scaffolder import ProjectScaffolder, GENERATED_BASE_DIR, slugify
from ..storage import ProjectStorage


class PathSecurityError(Exception):
    """Raised when an operation attempts to access or write files outside the project root."""
    pass


class TaskImplementationError(Exception):
    pass


def validate_safe_path(project_dir: Path, rel_path: str) -> Path:
    """
    Strict path security validator.
    Rejects:
    - Absolute paths
    - Path traversal with '..'
    - Any path resolving outside project_dir
    """
    clean_path = rel_path.strip().replace("\\", "/")

    if not clean_path:
        raise PathSecurityError("Target path cannot be empty.")

    # Rejection of absolute paths or drive letters
    if clean_path.startswith("/") or ":" in clean_path or clean_path.startswith("\\"):
        raise PathSecurityError(f"Access denied: absolute paths not permitted ('{rel_path}')")

    # Rejection of parent directory traversal
    parts = clean_path.split("/")
    if ".." in parts:
        raise PathSecurityError(f"Access denied: path traversal with '..' is prohibited ('{rel_path}')")

    target_full = (project_dir / clean_path).resolve()
    resolved_root = project_dir.resolve()

    try:
        # Must be relative to project root
        target_full.relative_to(resolved_root)
    except ValueError:
        raise PathSecurityError(f"Access denied: path '{rel_path}' escapes project root '{resolved_root}'")

    return target_full


def create_snapshot_backup(project_dir: Path, files_to_backup: List[str]) -> str:
    """
    Creates a pre-modification snapshot of affected files in .rogers/snapshots/<timestamp>.
    """
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    snapshot_dir = project_dir / ".rogers" / "snapshots" / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    for rel_path in files_to_backup:
        source_path = project_dir / rel_path
        if source_path.is_file():
            backup_target = snapshot_dir / rel_path
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, backup_target)

    return snapshot_id


def restore_snapshot(project_dir: Path, snapshot_id: str) -> bool:
    """Restores backed-up files from a previous snapshot."""
    snapshot_dir = project_dir / ".rogers" / "snapshots" / snapshot_id
    if not snapshot_dir.exists():
        return False

    for backup_file in snapshot_dir.rglob("*"):
        if backup_file.is_file():
            rel = backup_file.relative_to(snapshot_dir)
            target = project_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, target)

    return True


def run_safe_validation(project_dir: Path) -> ValidationResult:
    """
    Runs an allowlisted syntax & compilation validation check on the project.
    Never accepts arbitrary shell commands from the LLM.
    """
    backend_dir = project_dir / "backend"
    if not backend_dir.exists():
        return ValidationResult(
            status="passed",
            command="check_exists",
            output="Project directory verified."
        )

    # Allowlisted safe command: compileall verifies Python syntax and bytecode compilation
    cmd = [sys.executable, "-m", "compileall", "-q", str(backend_dir)]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )

        if result.returncode == 0:
            return ValidationResult(
                status="passed",
                command="python -m compileall",
                output="Python bytecode compilation and syntax validation passed with 0 errors."
            )
        else:
            return ValidationResult(
                status="failed",
                command="python -m compileall",
                output=result.stdout,
                error=result.stderr or "Compilation check failed."
            )
    except Exception as e:
        return ValidationResult(
            status="failed",
            command="python -m compileall",
            output="",
            error=str(e)
        )


class TaskImplementationService:
    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or get_ai_provider()

    async def implement_task(self, project: Project, task_identifier: str) -> TaskImplementationResult:
        """
        Executes controlled code implementation for a specific development task.
        """
        if not project.blueprint or not project.blueprint.development_tasks:
            raise TaskImplementationError("Project has no development tasks to implement.")

        # Locate the targeted task by ID, title, or index
        target_task: Optional[DevelopmentTask] = None
        for i, t in enumerate(project.blueprint.development_tasks):
            if not t.id:
                t.id = f"task_{i+1}_{slugify(t.title)}"
            if t.id == task_identifier or str(i) == task_identifier or t.title.lower() == task_identifier.lower():
                target_task = t
                break

        if not target_task:
            raise TaskImplementationError(f"Task '{task_identifier}' not found in project development tasks.")

        # Update task status to implementing
        target_task.status = "implementing"
        ProjectStorage.save(project)

        # Ensure project directory is scaffolded
        project_slug = slugify(project.name)
        project_dir = GENERATED_BASE_DIR / project_slug
        if not project_dir.exists():
            project_dir_str, _ = ProjectScaffolder.scaffold(project)
            project_dir = Path(project_dir_str)

        # Inspect relevant files
        relevant_files: Dict[str, str] = {}
        for candidate in ["backend/app/main.py", "backend/app/models.py", "backend/requirements.txt"]:
            file_path = project_dir / candidate
            if file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        relevant_files[candidate] = f.read()
                except Exception:
                    pass

        project_context = {
            "name": project.name,
            "idea": project.idea,
            "tech_stack": project.blueprint.tech_stack.model_dump(),
            "architecture": project.blueprint.architecture.model_dump()
        }

        try:
            # 1. Ask AI Provider for structured implementation proposal
            proposal: ImplementationProposal = await self.provider.generate_task_implementation(
                task_title=target_task.title,
                task_description=target_task.description,
                project_context=project_context,
                relevant_files=relevant_files
            )

            # 2. Strict Path Validation for all proposed file changes
            validated_operations: List[Tuple[Path, FileOperation]] = []
            files_to_backup: List[str] = []

            for change in proposal.changes:
                target_file_path = validate_safe_path(project_dir, change.path)
                validated_operations.append((target_file_path, change))
                files_to_backup.append(change.path)

            # 3. Create Pre-Modification Snapshot Backup
            snapshot_id = create_snapshot_backup(project_dir, files_to_backup)

            # 4. Apply Changes to Disk
            files_changed: List[str] = []
            final_changes: List[FileOperation] = []

            for target_file_path, change in validated_operations:
                # Capture before_content if modifying
                before_content = None
                if target_file_path.is_file():
                    with open(target_file_path, "r", encoding="utf-8") as f:
                        before_content = f.read()

                target_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_file_path, "w", encoding="utf-8") as f:
                    f.write(change.content.strip() + "\n")

                files_changed.append(change.path)
                final_changes.append(FileOperation(
                    path=change.path,
                    operation=change.operation,
                    content=change.content,
                    before_content=before_content
                ))

            # 5. Run Safe Code Validation
            validation = run_safe_validation(project_dir)

            if validation.status == "passed":
                target_task.status = "completed"
                overall_status = "success"
            else:
                target_task.status = "failed"
                overall_status = "failed"

            result = TaskImplementationResult(
                status=overall_status,
                task_id=target_task.id,
                summary=proposal.summary,
                files_changed=files_changed,
                changes=final_changes,
                validation=validation,
                snapshot_id=snapshot_id
            )

            target_task.implementation_result = result
            ProjectStorage.save(project)
            return result

        except Exception as e:
            target_task.status = "failed"
            ProjectStorage.save(project)
            if isinstance(e, PathSecurityError):
                raise
            raise TaskImplementationError(f"Task implementation error: {str(e)}") from e
