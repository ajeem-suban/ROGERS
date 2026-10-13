from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..models import Project, DevelopmentTask
from ..storage import ProjectStorage
from ..scaffolder import GENERATED_BASE_DIR, slugify
from ..implementation.service import (
    TaskImplementationService,
    TaskImplementationError,
    PathSecurityError
)
from .models import (
    MissionState,
    MissionStatus,
    ExecutionPlan,
    TaskProgressItem,
    MissionExecutionReport
)
from .graph import DependencyGraph

logger = logging.getLogger("rogers.mission")

# Concurrency locks and cancel/pause events per project
_PROJECT_LOCKS: Dict[str, asyncio.Lock] = {}
_ACTIVE_TASKS: Dict[str, asyncio.Task] = {}
_PAUSE_FLAGS: Dict[str, bool] = {}
_CANCEL_FLAGS: Dict[str, bool] = {}


def _get_project_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _PROJECT_LOCKS:
        _PROJECT_LOCKS[project_id] = asyncio.Lock()
    return _PROJECT_LOCKS[project_id]


class MissionOrchestratorError(Exception):
    pass


class MissionOrchestrator:
    """
    Slice 7 Mission Orchestrator:
    Controls dependency-aware, sequential multi-task project execution.
    Provides starting, pausing, resuming, cancelling, and state recovery.
    """

    @staticmethod
    def get_execution_plan(project: Project) -> ExecutionPlan:
        """Previews and validates the task dependency DAG."""
        if not project.blueprint or not project.blueprint.development_tasks:
            return ExecutionPlan(
                project_id=project.id,
                project_name=project.name,
                is_valid=False,
                total_tasks=0,
                execution_order=[],
                tasks=[],
                validation_errors=["Project has no blueprint or development tasks to execute."]
            )

        # Ensure every task has an ID
        tasks = project.blueprint.development_tasks
        for i, t in enumerate(tasks):
            if not t.id:
                clean_title = slugify(t.title).replace("-", "_")[:30]
                t.id = f"task_{i+1}_{clean_title}"

        return DependencyGraph.validate_and_plan(project.id, project.name, tasks)

    @staticmethod
    def get_mission_state(project: Project) -> MissionState:
        """Retrieves or restores active/persisted mission state."""
        if project.mission_state:
            try:
                state = MissionState.model_validate(project.mission_state)
                # Reconcile if marked running but no active in-memory task
                if state.status == "running" and project.id not in _ACTIVE_TASKS:
                    # Interrupted or server restarted
                    state.status = "paused"
                    state.error_message = "Execution was interrupted (server restart or boundary pause)."
                    project.mission_state = state.model_dump()
                    ProjectStorage.save(project)
                return state
            except Exception as e:
                logger.warning(f"Error parsing persisted mission state: {e}")

        # Initialize default READY state
        plan = MissionOrchestrator.get_execution_plan(project)
        progress_map: Dict[str, TaskProgressItem] = {}
        completed: List[str] = []

        if project.blueprint and project.blueprint.development_tasks:
            for t in project.blueprint.development_tasks:
                if not t.id:
                    continue
                is_ver = t.status == "verified"
                if is_ver:
                    completed.append(t.id)

                progress_map[t.id] = TaskProgressItem(
                    task_id=t.id,
                    title=t.title,
                    status=t.status,
                    depends_on=t.depends_on or [],
                    verified=is_ver,
                    snapshot_id=t.implementation_result.snapshot_id if t.implementation_result else None,
                    tests_passed=t.implementation_result.test_result.tests_passed if (t.implementation_result and t.implementation_result.test_result) else 0,
                    tests_total=t.implementation_result.test_result.tests_total if (t.implementation_result and t.implementation_result.test_result) else 0,
                    repair_attempts_count=len(t.implementation_result.repair_attempts) if (t.implementation_result and t.implementation_result.repair_attempts) else 0
                )

        state = MissionState(
            project_id=project.id,
            status="ready",
            execution_order=plan.execution_order,
            completed_task_ids=completed,
            tasks_progress=progress_map,
            started_at=None,
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        project.mission_state = state.model_dump()
        ProjectStorage.save(project)
        return state

    @staticmethod
    async def start_mission(project_id: str) -> MissionState:
        """Validates approval and initiates multi-task mission execution."""
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MissionOrchestratorError(f"Project '{project_id}' not found.")

        plan = MissionOrchestrator.get_execution_plan(project)
        if not plan.is_valid:
            errors_str = "; ".join(plan.validation_errors)
            raise MissionOrchestratorError(f"Cannot start mission: Roadmap has invalid dependencies: {errors_str}")

        lock = _get_project_lock(project_id)
        if lock.locked() or project_id in _ACTIVE_TASKS:
            raise MissionOrchestratorError("Mission is already currently running. Duplicate execution prevented.")

        state = MissionOrchestrator.get_mission_state(project)
        if state.status == "running":
            raise MissionOrchestratorError("Mission is already marked running.")

        # Reset flags
        _PAUSE_FLAGS[project_id] = False
        _CANCEL_FLAGS[project_id] = False

        state.status = "running"
        state.error_message = None
        state.started_at = state.started_at or datetime.now(timezone.utc).isoformat()
        state.updated_at = datetime.now(timezone.utc).isoformat()
        project.mission_state = state.model_dump()
        ProjectStorage.save(project)

        # Launch background runner task
        loop = asyncio.get_running_loop()
        task = loop.create_task(MissionOrchestrator._execute_mission_loop(project_id))
        _ACTIVE_TASKS[project_id] = task

        return state

    @staticmethod
    async def pause_mission(project_id: str) -> MissionState:
        """Signals execution loop to safely pause at next task boundary."""
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MissionOrchestratorError(f"Project '{project_id}' not found.")

        state = MissionOrchestrator.get_mission_state(project)
        if state.status != "running":
            raise MissionOrchestratorError(f"Cannot pause mission with status '{state.status}'.")

        _PAUSE_FLAGS[project_id] = True
        state.status = "paused"
        state.updated_at = datetime.now(timezone.utc).isoformat()
        project.mission_state = state.model_dump()
        ProjectStorage.save(project)
        return state

    @staticmethod
    async def resume_mission(project_id: str) -> MissionState:
        """Resumes a paused or blocked mission from its last completed checkpoint."""
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MissionOrchestratorError(f"Project '{project_id}' not found.")

        state = MissionOrchestrator.get_mission_state(project)
        if state.status not in ("paused", "blocked", "failed", "ready"):
            raise MissionOrchestratorError(f"Cannot resume mission with status '{state.status}'.")

        # Reset pause/cancel flags and run
        _PAUSE_FLAGS[project_id] = False
        _CANCEL_FLAGS[project_id] = False

        lock = _get_project_lock(project_id)
        if lock.locked() or project_id in _ACTIVE_TASKS:
            raise MissionOrchestratorError("Mission worker is already active.")

        state.status = "running"
        state.error_message = None
        state.updated_at = datetime.now(timezone.utc).isoformat()
        project.mission_state = state.model_dump()
        ProjectStorage.save(project)

        loop = asyncio.get_running_loop()
        task = loop.create_task(MissionOrchestrator._execute_mission_loop(project_id))
        _ACTIVE_TASKS[project_id] = task

        return state

    @staticmethod
    async def cancel_mission(project_id: str) -> MissionState:
        """Cancels active mission execution safely."""
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MissionOrchestratorError(f"Project '{project_id}' not found.")

        _CANCEL_FLAGS[project_id] = True
        state = MissionOrchestrator.get_mission_state(project)
        state.status = "cancelled"
        state.error_message = "Mission cancelled by user."
        state.updated_at = datetime.now(timezone.utc).isoformat()
        project.mission_state = state.model_dump()
        ProjectStorage.save(project)

        # Cancel active task if running
        active_task = _ACTIVE_TASKS.get(project_id)
        if active_task and not active_task.done():
            active_task.cancel()
        _ACTIVE_TASKS.pop(project_id, None)

        return state

    @staticmethod
    async def _execute_mission_loop(project_id: str) -> None:
        """
        Internal sequential execution engine:
        Iterates through tasks in topological dependency order.
        Verifies each task before advancing.
        Safely pauses on failure or user request.
        """
        lock = _get_project_lock(project_id)
        async with lock:
            try:
                impl_service = TaskImplementationService()

                while True:
                    # 1. Reload project state from storage
                    project = ProjectStorage.get_by_id(project_id)
                    if not project or not project.blueprint:
                        break

                    state = MissionState.model_validate(project.mission_state or {})

                    # Check cancel or pause requests at boundary
                    if _CANCEL_FLAGS.get(project_id, False) or state.status == "cancelled":
                        state.status = "cancelled"
                        state.updated_at = datetime.now(timezone.utc).isoformat()
                        project.mission_state = state.model_dump()
                        ProjectStorage.save(project)
                        break

                    if _PAUSE_FLAGS.get(project_id, False) or state.status == "paused":
                        state.status = "paused"
                        state.updated_at = datetime.now(timezone.utc).isoformat()
                        project.mission_state = state.model_dump()
                        ProjectStorage.save(project)
                        break

                    # 2. Reconcile verified tasks
                    completed_set: Set[str] = set()
                    failed_set: Set[str] = set()
                    for t in project.blueprint.development_tasks:
                        if not t.id:
                            continue
                        if t.status == "verified":
                            completed_set.add(t.id)
                        elif t.status == "failed":
                            failed_set.add(t.id)

                    state.completed_task_ids = list(completed_set)
                    state.failed_task_ids = list(failed_set)

                    # 3. Determine next eligible and blocked tasks
                    eligible, blocked_info = DependencyGraph.get_eligible_tasks(
                        project.blueprint.development_tasks,
                        completed_set,
                        failed_set
                    )

                    # Update blocked task IDs in state
                    blocked_ids = [b[0].id for b in blocked_info if b[0].id]
                    state.blocked_task_ids = blocked_ids

                    # Check completion criteria
                    total_count = len(project.blueprint.development_tasks)
                    if len(completed_set) == total_count:
                        state.status = "completed"
                        state.current_task_id = None
                        state.current_task_title = None
                        state.completed_at = datetime.now(timezone.utc).isoformat()
                        state.updated_at = datetime.now(timezone.utc).isoformat()
                        project.mission_state = state.model_dump()
                        ProjectStorage.save(project)
                        logger.info(f"Mission for project '{project_id}' completed successfully!")
                        break

                    # If no eligible tasks remain
                    if not eligible:
                        if blocked_ids or failed_set:
                            state.status = "blocked" if not failed_set else "failed"
                            state.error_message = (
                                f"Mission halted: {len(failed_set)} tasks failed, "
                                f"{len(blocked_ids)} tasks blocked by dependencies."
                            )
                        else:
                            state.status = "completed"
                            state.completed_at = datetime.now(timezone.utc).isoformat()

                        state.current_task_id = None
                        state.current_task_title = None
                        state.updated_at = datetime.now(timezone.utc).isoformat()
                        project.mission_state = state.model_dump()
                        ProjectStorage.save(project)
                        break

                    # 4. Pick next eligible task (order by execution_order)
                    order_map = {tid: idx for idx, tid in enumerate(state.execution_order)}
                    eligible.sort(key=lambda t: order_map.get(t.id or "", 999))
                    next_task = eligible[0]
                    task_id = next_task.id or ""

                    # Set current executing task
                    state.current_task_id = task_id
                    state.current_task_title = next_task.title
                    state.updated_at = datetime.now(timezone.utc).isoformat()
                    project.mission_state = state.model_dump()
                    ProjectStorage.save(project)

                    logger.info(f"Mission [{project.name}]: Executing task '{next_task.title}' ({task_id})")

                    # 5. Execute task with Slice 4 implementation & bounded repair pipeline
                    try:
                        result = await impl_service.implement_task(project, task_id)
                        
                        # Reload project to get latest task changes & snapshot
                        project = ProjectStorage.get_by_id(project_id) or project
                        target_t = next((t for t in (project.blueprint.development_tasks if project.blueprint else []) if t.id == task_id), None)
                        
                        is_verified = (target_t.status == "verified") if target_t else False
                        
                        # Update task progress entry
                        state.tasks_progress[task_id] = TaskProgressItem(
                            task_id=task_id,
                            title=next_task.title,
                            status="verified" if is_verified else "failed",
                            depends_on=next_task.depends_on or [],
                            verified=is_verified,
                            snapshot_id=result.snapshot_id,
                            tests_passed=result.test_result.tests_passed if result.test_result else 0,
                            tests_total=result.test_result.tests_total if result.test_result else 0,
                            repair_attempts_count=len(result.repair_attempts) if result.repair_attempts else 0,
                            error_message=None if is_verified else (result.summary or "Validation/Test failed")
                        )

                        if is_verified:
                            if task_id not in state.completed_task_ids:
                                state.completed_task_ids.append(task_id)
                        else:
                            if task_id not in state.failed_task_ids:
                                state.failed_task_ids.append(task_id)
                            # Bounded repair exhausted -> Halt mission safely
                            state.status = "failed"
                            state.error_message = f"Task '{next_task.title}' failed verification after maximum repair attempts."
                            state.updated_at = datetime.now(timezone.utc).isoformat()
                            project.mission_state = state.model_dump()
                            ProjectStorage.save(project)
                            break

                    except Exception as e:
                        logger.error(f"Task '{task_id}' raised error: {e}", exc_info=True)
                        if task_id not in state.failed_task_ids:
                            state.failed_task_ids.append(task_id)
                        state.status = "failed"
                        state.error_message = f"Task '{next_task.title}' encountered fatal error: {str(e)}"
                        state.updated_at = datetime.now(timezone.utc).isoformat()
                        project.mission_state = state.model_dump()
                        ProjectStorage.save(project)
                        break

                    # Save updated progress
                    state.updated_at = datetime.now(timezone.utc).isoformat()
                    project.mission_state = state.model_dump()
                    ProjectStorage.save(project)

            except asyncio.CancelledError:
                logger.info(f"Mission execution loop for project '{project_id}' cancelled.")
            except Exception as e:
                logger.error(f"Unhandled error in mission loop: {e}", exc_info=True)
            finally:
                _ACTIVE_TASKS.pop(project_id, None)

    @staticmethod
    def get_mission_report(project: Project) -> MissionExecutionReport:
        """Generates comprehensive final mission execution report."""
        state = MissionOrchestrator.get_mission_state(project)
        tasks = project.blueprint.development_tasks if project.blueprint else []

        items: List[TaskProgressItem] = []
        for t in tasks:
            if not t.id:
                continue
            prog = state.tasks_progress.get(t.id)
            if prog:
                items.append(prog)
            else:
                items.append(TaskProgressItem(
                    task_id=t.id,
                    title=t.title,
                    status=t.status,
                    depends_on=t.depends_on or [],
                    verified=t.status == "verified",
                    snapshot_id=t.implementation_result.snapshot_id if t.implementation_result else None
                ))

        # Calculate duration
        duration = 0.0
        if state.started_at:
            try:
                start_dt = datetime.fromisoformat(state.started_at)
                end_dt = datetime.fromisoformat(state.completed_at) if state.completed_at else datetime.now(timezone.utc)
                duration = round((end_dt - start_dt).total_seconds(), 2)
            except Exception:
                pass

        summary_msg = (
            f"Mission {state.status.upper()}: {len(state.completed_task_ids)}/{len(tasks)} tasks verified. "
            f"Failed: {len(state.failed_task_ids)}, Blocked: {len(state.blocked_task_ids)}."
        )

        return MissionExecutionReport(
            project_id=project.id,
            project_name=project.name,
            status=state.status,
            total_tasks=len(tasks),
            completed_count=len(state.completed_task_ids),
            failed_count=len(state.failed_task_ids),
            blocked_count=len(state.blocked_task_ids),
            skipped_count=len(state.skipped_task_ids),
            duration_seconds=duration,
            tasks=items,
            started_at=state.started_at,
            completed_at=state.completed_at,
            summary=summary_msg
        )
