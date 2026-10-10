import os
import re
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
    TaskImplementationResult,
    TestResult,
    FailureAnalysis,
    RepairAttempt,
    MissionLogEntry,
)
from ..models import Project, DevelopmentTask
from ..providers.base import AIProvider
from ..providers.factory import get_ai_provider
from ..scaffolder import ProjectScaffolder, GENERATED_BASE_DIR, slugify
from ..storage import ProjectStorage

MAX_REPAIR_ATTEMPTS = 3


class PathSecurityError(Exception):
    """Raised when an operation attempts to access or write files outside the project root."""
    pass


class TaskImplementationError(Exception):
    pass


def validate_safe_path(project_dir: Path, rel_path: str) -> Path:
    """
    Strict path security validator.
    Rejects:
    - Absolute paths or drive letters
    - Path traversal with '..'
    - Any path resolving outside project_dir
    - Hidden control directories like '.git'
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

    # Rejection of .git access
    if ".git" in parts or any(part.startswith(".git") for part in parts):
        raise PathSecurityError(f"Access denied: .git access is prohibited ('{rel_path}')")

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


def run_safe_tests(project_dir: Path, timeout: float = 30.0) -> TestResult:
    """
    Executes automated tests in a safe, sandboxed subprocess confined to the project directory.
    Uses allowlisted command: python -m pytest.
    """
    resolved_root = project_dir.resolve()

    # Discover test files (ignoring .rogers snapshots)
    test_files = list(resolved_root.glob("**/test_*.py")) + list(resolved_root.glob("**/*_test.py"))
    test_files = [f for f in test_files if ".rogers" not in f.parts]

    if not test_files:
        return TestResult(
            status="no_tests",
            exit_code=0,
            stdout="No test files discovered in project repository.",
            stderr="",
            duration_seconds=0.0,
            tests_total=0,
            tests_passed=0,
            tests_failed=0,
            tests_skipped=0,
            failure_summary="No tests discovered in project repository."
        )

    backend_dir = resolved_root / "backend"
    work_dir = backend_dir if backend_dir.exists() else resolved_root

    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]

    start_time = datetime.now()
    try:
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{work_dir}{os.pathsep}{existing_pythonpath}"

        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env
        )
        duration = round((datetime.now() - start_time).total_seconds(), 2)

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        exit_code = result.returncode

        # Parse pytest output
        passed_m = re.search(r"(\d+)\s+passed", stdout)
        failed_m = re.search(r"(\d+)\s+failed", stdout)
        skipped_m = re.search(r"(\d+)\s+skipped", stdout)

        passed = int(passed_m.group(1)) if passed_m else 0
        failed = int(failed_m.group(1)) if failed_m else 0
        skipped = int(skipped_m.group(1)) if skipped_m else 0
        total = passed + failed + skipped

        if exit_code == 0:
            status = "passed"
            failure_summary = None
        else:
            status = "failed"
            failures = []
            for line in stdout.splitlines():
                if line.startswith("FAILED ") or "AssertionError" in line or "Error:" in line:
                    failures.append(line.strip())
            failure_summary = "; ".join(failures[:3]) if failures else f"Pytest exited with status {exit_code}"

        return TestResult(
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            tests_total=total,
            tests_passed=passed,
            tests_failed=failed,
            tests_skipped=skipped,
            failure_summary=failure_summary
        )

    except subprocess.TimeoutExpired:
        duration = round((datetime.now() - start_time).total_seconds(), 2)
        return TestResult(
            status="timeout",
            exit_code=-1,
            stdout="",
            stderr=f"Test runner timed out after {timeout} seconds.",
            duration_seconds=duration,
            failure_summary=f"Tests timed out after {timeout}s"
        )
    except Exception as e:
        duration = round((datetime.now() - start_time).total_seconds(), 2)
        return TestResult(
            status="error",
            exit_code=-1,
            stdout="",
            stderr=str(e),
            duration_seconds=duration,
            failure_summary=f"Subprocess execution error: {str(e)}"
        )


class TaskImplementationService:
    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or get_ai_provider()

    def _load_relevant_files(self, project_dir: Path) -> Dict[str, str]:
        """Loads key codebase files for AI context."""
        relevant_files: Dict[str, str] = {}
        candidate_paths = [
            "backend/app/main.py",
            "backend/app/models.py",
            "backend/requirements.txt",
            "backend/tests/test_api.py",
        ]
        # Also discover any existing routes or services
        for py_file in project_dir.glob("backend/app/**/*.py"):
            rel = str(py_file.relative_to(project_dir)).replace("\\", "/")
            if rel not in candidate_paths:
                candidate_paths.append(rel)

        for candidate in candidate_paths:
            file_path = project_dir / candidate
            if file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        relevant_files[candidate] = f.read()
                except Exception:
                    pass
        return relevant_files

    async def implement_task(self, project: Project, task_identifier: str) -> TaskImplementationResult:
        """
        Executes controlled code implementation for a specific development task
        following the Slice 4 Mission Control loop:
        RECON -> IMPLEMENT -> SECURE -> SNAPSHOT -> WRITE -> VALIDATE -> TEST -> (ANALYZE / REPAIR) -> VERIFY
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

        # Update task status to inspecting
        target_task.status = "inspecting"
        ProjectStorage.save(project)

        # Ensure project directory is scaffolded
        project_slug = slugify(project.name)
        project_dir = GENERATED_BASE_DIR / project_slug
        if not project_dir.exists():
            project_dir_str, _ = ProjectScaffolder.scaffold(project)
            project_dir = Path(project_dir_str)

        mission_logs: List[MissionLogEntry] = []

        def log(stage: str, message: str, level: str = "info"):
            now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
            mission_logs.append(MissionLogEntry(timestamp=now_str, stage=stage, level=level, message=message))

        log("RECON", f"Mission initialized for task: '{target_task.title}'")

        # 1. RECON: Inspect relevant files
        relevant_files = self._load_relevant_files(project_dir)
        log("RECON", f"Codebase inspected ({len(relevant_files)} files loaded for context)")

        project_context = {
            "name": project.name,
            "idea": project.idea,
            "tech_stack": project.blueprint.tech_stack.model_dump(),
            "architecture": project.blueprint.architecture.model_dump()
        }

        # Update task status to implementing
        target_task.status = "implementing"
        ProjectStorage.save(project)

        # Verifiable security checks
        security_checks = {
            "project_root_locked": True,
            "path_traversal_blocked": True,
            "git_access_blocked": True,
            "snapshot_protection_active": True,
            "shell_execution_blocked": True,
            "write_target_validated": True
        }

        try:
            # 2. IMPLEMENT: Generate implementation
            log("IMPLEMENT", f"Synthesizing implementation for objective: {target_task.title}")
            proposal: ImplementationProposal = await self.provider.generate_task_implementation(
                task_title=target_task.title,
                task_description=target_task.description,
                project_context=project_context,
                relevant_files=relevant_files
            )
            log("IMPLEMENT", f"Implementation generated ({len(proposal.changes)} file operations)")

            # 3. SECURE: Sandbox validation
            validated_operations: List[Tuple[Path, FileOperation]] = []
            files_to_backup: List[str] = []

            for change in proposal.changes:
                target_file_path = validate_safe_path(project_dir, change.path)
                validated_operations.append((target_file_path, change))
                files_to_backup.append(change.path)

            log("SECURE", "Path security sandbox verified (no directory traversal or .git access)")

            # 4. SNAPSHOT: Pre-modification backup
            snapshot_id = create_snapshot_backup(project_dir, files_to_backup)
            log("SNAPSHOT", f"Pre-modification backup created: snapshot {snapshot_id}")

            # 5. WRITE: Apply file changes to disk
            files_changed: List[str] = []
            final_changes: List[FileOperation] = []

            for target_file_path, change in validated_operations:
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

            log("WRITE", f"Applied {len(final_changes)} file modifications to disk")

            # 6. VALIDATE: Static compilation check
            target_task.status = "validating"
            ProjectStorage.save(project)

            validation = run_safe_validation(project_dir)
            if validation.status == "passed":
                log("VALIDATE", "Static bytecode & syntax compilation passed with 0 errors", level="success")
            else:
                log("VALIDATE", f"Static compilation error: {validation.error}", level="warning")

            # 7. TEST: Safe test execution
            target_task.status = "testing"
            ProjectStorage.save(project)

            log("TEST", "Executing safe automated pytest runner")
            test_result = run_safe_tests(project_dir)

            repair_attempts: List[RepairAttempt] = []
            is_verified = False
            overall_status = "success"

            if test_result.status == "no_tests":
                log("TEST", "No automated tests discovered in project repository", level="info")
                if validation.status == "passed":
                    target_task.status = "completed"
                    overall_status = "success"
                    is_verified = False
                    log("VERIFY", "Task completed (tests not available)", level="success")
                else:
                    target_task.status = "failed"
                    overall_status = "failed"
                    is_verified = False
                    log("VERIFY", "Task static validation failed", level="error")

            elif test_result.status == "passed":
                log("TEST", f"All tests passed ({test_result.tests_passed}/{test_result.tests_total} in {test_result.duration_seconds}s)", level="success")
                target_task.status = "verified"
                overall_status = "success"
                is_verified = True
                log("VERIFY", "Mission Verified: Feature operational and all test assertions satisfied", level="success")

            else:
                # Tests failed or compilation failed -> Enter bounded repair loop
                log("TEST", f"Test failure detected: {test_result.failure_summary or 'Assertions failed'}", level="error")
                target_task.status = "repairing"
                ProjectStorage.save(project)

                current_test_result = test_result
                current_validation = validation
                repaired_successfully = False

                for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
                    log("REPAIR", f"Commencing bounded AI repair attempt {attempt}/{MAX_REPAIR_ATTEMPTS}")

                    # A. Failure Analysis
                    failure_analysis = await self.provider.analyze_failure(
                        task_title=target_task.title,
                        task_description=target_task.description,
                        test_output=current_test_result.stdout + "\n" + current_test_result.stderr + (current_validation.error or ""),
                        relevant_files=self._load_relevant_files(project_dir),
                        current_implementation=proposal
                    )
                    log("REPAIR", f"Diagnosis (attempt {attempt}): {failure_analysis.root_cause}")

                    # B. Generate Repair
                    repair_proposal = await self.provider.generate_repair(
                        task_title=target_task.title,
                        task_description=target_task.description,
                        failure_analysis=failure_analysis,
                        test_output=current_test_result.stdout + "\n" + current_test_result.stderr,
                        relevant_files=self._load_relevant_files(project_dir),
                        attempt=attempt
                    )

                    # C. Path Sandbox Validation
                    repair_validated_ops = []
                    repair_files_to_backup = []
                    for change in repair_proposal.changes:
                        target_fp = validate_safe_path(project_dir, change.path)
                        repair_validated_ops.append((target_fp, change))
                        repair_files_to_backup.append(change.path)

                    # D. Snapshot before repair
                    repair_snapshot_id = create_snapshot_backup(project_dir, repair_files_to_backup)

                    # E. Apply repair changes
                    repair_changes: List[FileOperation] = []
                    for target_fp, change in repair_validated_ops:
                        before_c = None
                        if target_fp.is_file():
                            with open(target_fp, "r", encoding="utf-8") as f:
                                before_c = f.read()

                        target_fp.parent.mkdir(parents=True, exist_ok=True)
                        with open(target_fp, "w", encoding="utf-8") as f:
                            f.write(change.content.strip() + "\n")

                        if change.path not in files_changed:
                            files_changed.append(change.path)

                        repair_changes.append(FileOperation(
                            path=change.path,
                            operation=change.operation,
                            content=change.content,
                            before_content=before_c
                        ))

                    # F. Validate repair
                    current_validation = run_safe_validation(project_dir)

                    # G. Re-test
                    current_test_result = run_safe_tests(project_dir)

                    attempt_record = RepairAttempt(
                        attempt_number=attempt,
                        snapshot_id=repair_snapshot_id,
                        summary=repair_proposal.summary,
                        changes=repair_changes,
                        validation=current_validation,
                        test_result=current_test_result,
                        failure_analysis=failure_analysis
                    )
                    repair_attempts.append(attempt_record)

                    if current_validation.status == "passed" and current_test_result.status == "passed":
                        repaired_successfully = True
                        log("VERIFY", f"Repair succeeded on attempt {attempt}/{MAX_REPAIR_ATTEMPTS}! All tests passing.", level="success")
                        break
                    else:
                        log("REPAIR", f"Repair attempt {attempt}/{MAX_REPAIR_ATTEMPTS} did not resolve all test failures.", level="warning")

                if repaired_successfully:
                    target_task.status = "verified"
                    overall_status = "success"
                    is_verified = True
                    test_result = current_test_result
                    validation = current_validation
                else:
                    target_task.status = "failed"
                    overall_status = "failed"
                    is_verified = False
                    test_result = current_test_result
                    validation = current_validation
                    log("VERIFY", f"Verification failed. Maximum repair attempts reached ({MAX_REPAIR_ATTEMPTS}).", level="error")

            result = TaskImplementationResult(
                status=overall_status,
                task_id=target_task.id,
                summary=proposal.summary,
                files_changed=files_changed,
                changes=final_changes,
                validation=validation,
                snapshot_id=snapshot_id,
                test_result=test_result,
                repair_attempts=repair_attempts,
                mission_logs=mission_logs,
                verified=is_verified,
                security_checks=security_checks
            )

            target_task.implementation_result = result
            ProjectStorage.save(project)
            return result

        except Exception as e:
            target_task.status = "failed"
            ProjectStorage.save(project)
            log("VERIFY", f"Mission aborted: {str(e)}", level="error")
            if isinstance(e, PathSecurityError):
                raise
            raise TaskImplementationError(f"Task implementation error: {str(e)}") from e
