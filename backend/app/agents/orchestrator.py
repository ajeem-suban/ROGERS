from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..models import Project, DevelopmentTask
from ..storage import ProjectStorage
from ..scaffolder import GENERATED_BASE_DIR, slugify
from ..implementation.service import TaskImplementationService, PathSecurityError, TaskImplementationError
from ..mission.graph import DependencyGraph
from .models import (
    ParallelMissionConfig,
    ParallelMissionState,
    ParallelExecutionPlan,
    ParallelPlanItem,
    ParallelMissionReport,
    AgentInfo,
    AgentLogEntry
)
from .roles import (
    ResearchAgent,
    ArchitectureAgent,
    DevelopmentAgent,
    TestingAgent,
    ReviewAgent
)

logger = logging.getLogger("rogers.agents.orchestrator")

_PARALLEL_LOCKS: Dict[str, asyncio.Lock] = {}
_ACTIVE_PARALLEL_TASKS: Dict[str, asyncio.Task] = {}
_PARALLEL_PAUSE_FLAGS: Dict[str, bool] = {}
_PARALLEL_CANCEL_FLAGS: Dict[str, bool] = {}


def _get_parallel_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _PARALLEL_LOCKS:
        _PARALLEL_LOCKS[project_id] = asyncio.Lock()
    return _PARALLEL_LOCKS[project_id]


class MultiAgentOrchestratorError(Exception):
    pass


class MultiAgentOrchestrator:
    """
    Slice 8: Multi-Agent Parallel Execution Orchestrator.
    Manages parallel task distribution across specialized AI agents.
    Enforces configurable concurrency limits, dependency ordering,
    and file-conflict locks.
    """

    @staticmethod
    def get_parallel_plan(project: Project) -> ParallelExecutionPlan:
        """Computes dependency DAG, assigns agent roles, and groups tasks into parallel batches."""
        if not project.blueprint or not project.blueprint.development_tasks:
            return ParallelExecutionPlan(
                project_id=project.id,
                project_name=project.name,
                is_valid=False,
                total_tasks=0,
                parallel_batches=[],
                tasks=[],
                validation_errors=["Project has no blueprint or tasks for parallel execution."]
            )

        tasks = project.blueprint.development_tasks
        for i, t in enumerate(tasks):
            if not t.id:
                clean_title = slugify(t.title).replace("-", "_")[:30]
                t.id = f"task_{i+1}_{clean_title}"

        # 1. Validate DAG using Slice 7 DependencyGraph
        plan = DependencyGraph.validate_and_plan(project.id, project.name, tasks)
        if not plan.is_valid:
            return ParallelExecutionPlan(
                project_id=project.id,
                project_name=project.name,
                is_valid=False,
                total_tasks=len(tasks),
                parallel_batches=[],
                tasks=[],
                validation_errors=plan.validation_errors
            )

        # 2. Compute parallel stages/batches (layer by layer in DAG)
        task_map = {t.id: t for t in tasks if t.id}
        in_degree = {t.id: len(t.depends_on or []) for t in tasks if t.id}
        completed_layers: Set[str] = set()
        batches: List[List[str]] = []
        remaining = set(task_map.keys())

        while remaining:
            # Current batch consists of tasks whose dependencies are all in completed_layers
            current_batch = [
                tid for tid in remaining
                if all(dep in completed_layers for dep in (task_map[tid].depends_on or []))
            ]
            if not current_batch:
                # Break to prevent infinite loop on abnormal cycles
                break
            batches.append(current_batch)
            completed_layers.update(current_batch)
            remaining.difference_update(current_batch)

        # 3. Build ParallelPlanItems
        arch_agent = ArchitectureAgent()
        plan_items: List[ParallelPlanItem] = []
        for stage_idx, batch in enumerate(batches):
            for tid in batch:
                t = task_map[tid]
                plan_items.append(ParallelPlanItem(
                    task_id=tid,
                    title=t.title,
                    priority=t.priority,
                    depends_on=t.depends_on or [],
                    stage_index=stage_idx + 1,
                    assigned_role="developer",
                    estimated_files=[]
                ))

        return ParallelExecutionPlan(
            project_id=project.id,
            project_name=project.name,
            is_valid=True,
            total_tasks=len(tasks),
            parallel_batches=batches,
            tasks=plan_items,
            validation_errors=[]
        )

    @staticmethod
    def get_state(project: Project) -> ParallelMissionState:
        """Retrieves or initializes active parallel mission state."""
        raw_state = (project.mission_state or {}).get("parallel_execution")
        if raw_state:
            try:
                state = ParallelMissionState.model_validate(raw_state)
                # Reconcile if running but no active in-memory task
                if state.status == "running" and project.id not in _ACTIVE_PARALLEL_TASKS:
                    state.status = "paused"
                    state.error_message = "Parallel execution was interrupted (server restart or boundary pause)."
                return state
            except Exception as e:
                logger.warning(f"Error parsing parallel mission state: {e}")

        # Initialize default roster of specialized agents
        researcher = ResearchAgent()
        architect = ArchitectureAgent()
        dev1 = DevelopmentAgent(agent_id="agent_dev_alpha", name="War Machine Alpha")
        dev2 = DevelopmentAgent(agent_id="agent_dev_beta", name="Iron Patriot Beta")
        dev3 = DevelopmentAgent(agent_id="agent_dev_gamma", name="Hulkbuster Gamma")
        tester = TestingAgent()
        reviewer = ReviewAgent()

        agents = [
            researcher.get_info(),
            architect.get_info(),
            dev1.get_info(),
            dev2.get_info(),
            dev3.get_info(),
            tester.get_info(),
            reviewer.get_info()
        ]

        plan = MultiAgentOrchestrator.get_parallel_plan(project)
        state = ParallelMissionState(
            project_id=project.id,
            status="ready",
            config=ParallelMissionConfig(max_concurrent_agents=3),
            agents=agents,
            file_locks={},
            running_task_ids=[],
            completed_task_ids=[t.id for t in (project.blueprint.development_tasks if project.blueprint else []) if t.status == "verified" and t.id],
            failed_task_ids=[t.id for t in (project.blueprint.development_tasks if project.blueprint else []) if t.status == "failed" and t.id],
            blocked_task_ids=[],
            parallel_batches=plan.parallel_batches,
            logs=[
                AgentLogEntry(
                    timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
                    agent_id="agent_reviewer_01",
                    role="reviewer",
                    message="Multi-Agent Command Roster initialized and ready for parallel mission engagement."
                )
            ]
        )
        return state

    @staticmethod
    def _save_state(project: Project, state: ParallelMissionState) -> None:
        state.updated_at = datetime.now(timezone.utc).isoformat()
        current_m = project.mission_state or {}
        current_m["parallel_execution"] = state.model_dump()
        project.mission_state = current_m
        ProjectStorage.save(project)

    @staticmethod
    async def start_parallel_mission(project_id: str, max_concurrent_agents: int = 3) -> ParallelMissionState:
        """Starts multi-agent parallel mission execution."""
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MultiAgentOrchestratorError(f"Project '{project_id}' not found.")

        plan = MultiAgentOrchestrator.get_parallel_plan(project)
        if not plan.is_valid:
            errors = "; ".join(plan.validation_errors)
            raise MultiAgentOrchestratorError(f"Cannot start parallel mission: {errors}")

        lock = _get_parallel_lock(project_id)
        if lock.locked() or project_id in _ACTIVE_PARALLEL_TASKS:
            raise MultiAgentOrchestratorError("Parallel mission is already currently active.")

        state = MultiAgentOrchestrator.get_state(project)
        if state.status == "running":
            raise MultiAgentOrchestratorError("Parallel mission is already marked running.")

        _PARALLEL_PAUSE_FLAGS[project_id] = False
        _PARALLEL_CANCEL_FLAGS[project_id] = False

        state.status = "running"
        state.config.max_concurrent_agents = max(1, min(5, max_concurrent_agents))
        state.error_message = None
        state.started_at = state.started_at or datetime.now(timezone.utc).isoformat()
        state.logs.append(AgentLogEntry(
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            agent_id="agent_reviewer_01",
            role="reviewer",
            message=f"Engaging parallel execution with max concurrency = {state.config.max_concurrent_agents}."
        ))

        MultiAgentOrchestrator._save_state(project, state)

        loop = asyncio.get_running_loop()
        task = loop.create_task(MultiAgentOrchestrator._execute_parallel_loop(project_id))
        _ACTIVE_PARALLEL_TASKS[project_id] = task

        return state

    @staticmethod
    async def pause_parallel_mission(project_id: str) -> ParallelMissionState:
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MultiAgentOrchestratorError(f"Project '{project_id}' not found.")

        state = MultiAgentOrchestrator.get_state(project)
        if state.status != "running":
            raise MultiAgentOrchestratorError(f"Cannot pause mission with status '{state.status}'.")

        _PARALLEL_PAUSE_FLAGS[project_id] = True
        state.status = "paused"
        state.logs.append(AgentLogEntry(
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            agent_id="agent_reviewer_01",
            role="reviewer",
            message="Pause command issued. Agents will halt safely at next task boundary."
        ))
        MultiAgentOrchestrator._save_state(project, state)
        return state

    @staticmethod
    async def resume_parallel_mission(project_id: str) -> ParallelMissionState:
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MultiAgentOrchestratorError(f"Project '{project_id}' not found.")

        state = MultiAgentOrchestrator.get_state(project)
        if state.status not in ("paused", "blocked", "failed", "ready"):
            raise MultiAgentOrchestratorError(f"Cannot resume mission with status '{state.status}'.")

        _PARALLEL_PAUSE_FLAGS[project_id] = False
        _PARALLEL_CANCEL_FLAGS[project_id] = False

        lock = _get_parallel_lock(project_id)
        if lock.locked() or project_id in _ACTIVE_PARALLEL_TASKS:
            raise MultiAgentOrchestratorError("Parallel mission is already active.")

        state.status = "running"
        state.error_message = None
        state.logs.append(AgentLogEntry(
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            agent_id="agent_reviewer_01",
            role="reviewer",
            message="Resuming parallel mission execution."
        ))
        MultiAgentOrchestrator._save_state(project, state)

        loop = asyncio.get_running_loop()
        task = loop.create_task(MultiAgentOrchestrator._execute_parallel_loop(project_id))
        _ACTIVE_PARALLEL_TASKS[project_id] = task

        return state

    @staticmethod
    async def cancel_parallel_mission(project_id: str) -> ParallelMissionState:
        project = ProjectStorage.get_by_id(project_id)
        if not project:
            raise MultiAgentOrchestratorError(f"Project '{project_id}' not found.")

        _PARALLEL_CANCEL_FLAGS[project_id] = True
        state = MultiAgentOrchestrator.get_state(project)
        state.status = "cancelled"
        state.file_locks.clear()
        state.running_task_ids.clear()
        state.logs.append(AgentLogEntry(
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            agent_id="agent_reviewer_01",
            role="reviewer",
            message="Mission cancelled. Parallel agents stood down."
        ))
        MultiAgentOrchestrator._save_state(project, state)

        active_t = _ACTIVE_PARALLEL_TASKS.get(project_id)
        if active_t and not active_t.done():
            active_t.cancel()
        _ACTIVE_PARALLEL_TASKS.pop(project_id, None)

        return state

    @staticmethod
    async def _execute_parallel_loop(project_id: str) -> None:
        """
        Main parallel task execution coordinator:
        Launches concurrent tasks within the configured semaphore limit.
        Guarantees no simultaneous conflicting writes to identical files.
        """
        lock = _get_parallel_lock(project_id)
        async with lock:
            try:
                # Specialized agent instances
                researcher = ResearchAgent()
                architect = ArchitectureAgent()
                testers = TestingAgent()
                reviewers = ReviewAgent()
                dev_pool = [
                    DevelopmentAgent(agent_id="agent_dev_alpha", name="War Machine Alpha"),
                    DevelopmentAgent(agent_id="agent_dev_beta", name="Iron Patriot Beta"),
                    DevelopmentAgent(agent_id="agent_dev_gamma", name="Hulkbuster Gamma")
                ]

                impl_service = TaskImplementationService()

                while True:
                    project = ProjectStorage.get_by_id(project_id)
                    if not project or not project.blueprint:
                        break

                    state = MultiAgentOrchestrator.get_state(project)

                    # Check pause / cancel flags
                    if _PARALLEL_CANCEL_FLAGS.get(project_id, False) or state.status == "cancelled":
                        state.status = "cancelled"
                        MultiAgentOrchestrator._save_state(project, state)
                        break

                    if _PARALLEL_PAUSE_FLAGS.get(project_id, False) or state.status == "paused":
                        state.status = "paused"
                        MultiAgentOrchestrator._save_state(project, state)
                        break

                    # 1. Update verified/failed sets from project tasks
                    tasks = project.blueprint.development_tasks
                    completed_set = {t.id for t in tasks if t.status == "verified" and t.id}
                    failed_set = {t.id for t in tasks if t.status == "failed" and t.id}

                    state.completed_task_ids = list(completed_set)
                    state.failed_task_ids = list(failed_set)

                    # 2. Check total completion
                    if len(completed_set) == len(tasks):
                        state.status = "completed"
                        state.file_locks.clear()
                        state.completed_at = datetime.now(timezone.utc).isoformat()
                        state.logs.append(AgentLogEntry(
                            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
                            agent_id="agent_reviewer_01",
                            role="reviewer",
                            level="success",
                            message=f"All {len(tasks)} tasks verified! Multi-agent mission successfully completed."
                        ))
                        MultiAgentOrchestrator._save_state(project, state)
                        break

                    # 3. Determine candidate eligible tasks whose prerequisites passed
                    eligible_tasks, blocked_info = DependencyGraph.get_eligible_tasks(
                        tasks,
                        completed_set,
                        failed_set
                    )
                    state.blocked_task_ids = [b[0].id for b in blocked_info if b[0].id]

                    if not eligible_tasks:
                        if state.blocked_task_ids or failed_set:
                            state.status = "blocked" if not failed_set else "failed"
                            state.error_message = (
                                f"Parallel mission halted: {len(failed_set)} tasks failed, "
                                f"{len(state.blocked_task_ids)} tasks blocked by prerequisites."
                            )
                        else:
                            state.status = "completed"
                            state.completed_at = datetime.now(timezone.utc).isoformat()
                        MultiAgentOrchestrator._save_state(project, state)
                        break

                    # 4. Filter candidate tasks based on active file-locks (prevent conflicting file edits)
                    launch_candidates: List[DevelopmentTask] = []
                    current_locked_files = set(state.file_locks.keys())

                    for cand in eligible_tasks:
                        # Architecture agent predicts target files
                        cand_files = await architect.design_task_structure(cand, {})
                        # Check collision with already locked files or other candidates in this batch
                        if any(f in current_locked_files for f in cand_files):
                            # Conflict detected: defer to next iteration
                            continue
                        # Claim file locks
                        for f in cand_files:
                            current_locked_files.add(f)
                            state.file_locks[f] = cand.id or ""
                        launch_candidates.append(cand)
                        if len(launch_candidates) >= state.config.max_concurrent_agents:
                            break

                    if not launch_candidates:
                        # If candidates are deferred due to file locks, wait for currently running tasks to finish
                        await asyncio.sleep(0.5)
                        continue

                    # 5. Execute launch candidates concurrently
                    state.running_task_ids = [t.id for t in launch_candidates if t.id]
                    MultiAgentOrchestrator._save_state(project, state)

                    async def run_single_agent_task(dev_agent: DevelopmentAgent, task_obj: DevelopmentTask):
                        t_id = task_obj.id or ""
                        try:
                            # 1. Recon by Research Agent
                            await researcher.investigate_task(project, task_obj, {})

                            # 2. Assign Developer Agent
                            dev_agent.status = "busy"
                            dev_agent.current_task_id = t_id
                            dev_agent.current_task_title = task_obj.title
                            dev_agent.log(f"Implementing task '{task_obj.title}' in parallel stream")

                            # Run task implementation service with tests and repair
                            res = await impl_service.implement_task(project, t_id)

                            # 3. Quality & Security Review by Reviewer Agent
                            review_pass = await reviewers.review_implementation(task_obj, res.files_changed)
                            
                            # 4. Testing verification by Tester Agent
                            test_pass = await testers.verify_tests(task_obj, res.test_result or None, res.validation)

                            is_verified = (res.status in ("success", "verified")) and review_pass and test_pass

                            dev_agent.status = "idle"
                            dev_agent.current_task_id = None
                            dev_agent.current_task_title = None

                            return t_id, is_verified, None
                        except Exception as e:
                            logger.error(f"Parallel task '{t_id}' failed: {e}", exc_info=True)
                            dev_agent.status = "idle"
                            dev_agent.current_task_id = None
                            return t_id, False, str(e)

                    # Gather parallel tasks
                    agent_coros = []
                    for idx, task_obj in enumerate(launch_candidates):
                        assigned_dev = dev_pool[idx % len(dev_pool)]
                        agent_coros.append(run_single_agent_task(assigned_dev, task_obj))

                    results = await asyncio.gather(*agent_coros, return_exceptions=True)

                    # 6. Release file locks and process outcomes
                    for res_item in results:
                        if isinstance(res_item, tuple):
                            t_id, is_ver, err = res_item
                            # Remove file locks for this task
                            keys_to_del = [k for k, v in state.file_locks.items() if v == t_id]
                            for k in keys_to_del:
                                state.file_locks.pop(k, None)

                            if is_ver:
                                if t_id not in state.completed_task_ids:
                                    state.completed_task_ids.append(t_id)
                                state.logs.append(AgentLogEntry(
                                    timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                    agent_id="agent_reviewer_01",
                                    role="reviewer",
                                    task_id=t_id,
                                    level="success",
                                    message=f"Task '{t_id}' successfully completed and verified by agents."
                                ))
                            else:
                                if t_id not in state.failed_task_ids:
                                    state.failed_task_ids.append(t_id)
                                state.logs.append(AgentLogEntry(
                                    timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                    agent_id="agent_reviewer_01",
                                    role="reviewer",
                                    task_id=t_id,
                                    level="error",
                                    message=f"Task '{t_id}' failed agent verification: {err or 'Test/Review failure'}."
                                ))

                    state.running_task_ids.clear()
                    # Update live agents info in state
                    state.agents = [
                        researcher.get_info(),
                        architect.get_info(),
                        dev_pool[0].get_info(),
                        dev_pool[1].get_info(),
                        dev_pool[2].get_info(),
                        testers.get_info(),
                        reviewers.get_info()
                    ]
                    MultiAgentOrchestrator._save_state(project, state)

            except asyncio.CancelledError:
                logger.info(f"Parallel mission for project '{project_id}' cancelled.")
            except Exception as e:
                logger.error(f"Unhandled error in parallel mission loop: {e}", exc_info=True)
            finally:
                _ACTIVE_PARALLEL_TASKS.pop(project_id, None)

    @staticmethod
    def get_report(project: Project) -> ParallelMissionReport:
        """Generates comprehensive multi-agent parallel mission execution report."""
        state = MultiAgentOrchestrator.get_state(project)
        tasks = project.blueprint.development_tasks if project.blueprint else []

        duration = 0.0
        if state.started_at:
            try:
                start_dt = datetime.fromisoformat(state.started_at)
                end_dt = datetime.fromisoformat(state.completed_at) if state.completed_at else datetime.now(timezone.utc)
                duration = round((end_dt - start_dt).total_seconds(), 2)
            except Exception:
                pass

        summary_msg = (
            f"Multi-Agent Parallel Mission {state.status.upper()}: {len(state.completed_task_ids)}/{len(tasks)} verified. "
            f"Failed: {len(state.failed_task_ids)}, Blocked: {len(state.blocked_task_ids)}. "
            f"Concurrency Limit: {state.config.max_concurrent_agents} agents."
        )

        return ParallelMissionReport(
            project_id=project.id,
            project_name=project.name,
            status=state.status,
            total_tasks=len(tasks),
            completed_count=len(state.completed_task_ids),
            failed_count=len(state.failed_task_ids),
            blocked_count=len(state.blocked_task_ids),
            concurrent_limit=state.config.max_concurrent_agents,
            duration_seconds=duration,
            agents_summary=state.agents,
            summary=summary_msg,
            started_at=state.started_at,
            completed_at=state.completed_at
        )
