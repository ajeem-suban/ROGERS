from __future__ import annotations

from typing import Dict, List, Set, Tuple
from collections import deque
from ..models import DevelopmentTask
from .models import ExecutionPlan, TaskPlanItem


class DependencyGraphError(Exception):
    pass


class DependencyGraph:
    """
    Validates and resolves task dependency DAG for mission execution.
    Detects:
    1. Missing dependencies (reference to a non-existent task)
    2. Self-dependencies (a task depending on itself)
    3. Circular dependency cycles (A -> B -> A)
    4. Topological execution sequence
    """

    @staticmethod
    def validate_and_plan(project_id: str, project_name: str, tasks: List[DevelopmentTask]) -> ExecutionPlan:
        task_map: Dict[str, DevelopmentTask] = {}
        for t in tasks:
            task_id = t.id or f"task_{t.title}"
            task_map[task_id] = t

        missing_deps: Dict[str, List[str]] = {}
        errors: List[str] = []
        has_cycles = False
        execution_order: List[str] = []

        # 1. Check self-dependencies and missing dependencies
        for task_id, t in task_map.items():
            deps = t.depends_on or []
            missing_for_task: List[str] = []
            for dep in deps:
                if dep == task_id:
                    errors.append(f"Task '{t.title}' ({task_id}) cannot depend on itself.")
                elif dep not in task_map:
                    missing_for_task.append(dep)
                    errors.append(f"Task '{t.title}' ({task_id}) depends on non-existent task '{dep}'.")
            if missing_for_task:
                missing_deps[task_id] = missing_for_task

        # 2. Cycle detection and topological sorting via Kahn's algorithm
        # In-degree: number of prerequisite tasks each task has
        in_degree: Dict[str, int] = {tid: 0 for tid in task_map}
        adjacency: Dict[str, List[str]] = {tid: [] for tid in task_map}

        for task_id, t in task_map.items():
            valid_deps = [d for d in (t.depends_on or []) if d in task_map and d != task_id]
            in_degree[task_id] = len(valid_deps)
            for dep in valid_deps:
                adjacency[dep].append(task_id)

        # Queue nodes with in_degree == 0 (no prerequisites)
        # Preserve blueprint order as tie-breaker for deterministic sequence
        queue: deque[str] = deque([tid for tid in task_map if in_degree[tid] == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            execution_order.append(curr)
            visited_count += 1

            for neighbor in adjacency[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count < len(task_map):
            has_cycles = True
            errors.append("Circular dependency cycle detected in development roadmap.")

        is_valid = len(errors) == 0 and not has_cycles

        # Build plan items
        plan_items: List[TaskPlanItem] = []
        for idx, task_id in enumerate(execution_order if is_valid else list(task_map.keys())):
            t = task_map[task_id]
            plan_items.append(TaskPlanItem(
                task_id=task_id,
                title=t.title,
                priority=t.priority,
                depends_on=t.depends_on or [],
                state="pending",
                order_index=idx + 1,
                blocked_by=[]
            ))

        return ExecutionPlan(
            project_id=project_id,
            project_name=project_name,
            is_valid=is_valid,
            total_tasks=len(tasks),
            execution_order=execution_order if is_valid else [],
            tasks=plan_items,
            has_cycles=has_cycles,
            missing_dependencies=missing_deps,
            validation_errors=errors
        )

    @staticmethod
    def get_eligible_tasks(
        tasks: List[DevelopmentTask],
        completed_task_ids: Set[str],
        failed_task_ids: Set[str]
    ) -> Tuple[List[DevelopmentTask], List[Tuple[DevelopmentTask, List[str]]]]:
        """
        Determines:
        1. Eligible tasks (all dependencies in completed_task_ids and task not yet completed)
        2. Blocked tasks (at least one dependency failed or incomplete)
        """
        task_map = {t.id: t for t in tasks if t.id}
        eligible: List[DevelopmentTask] = []
        blocked: List[Tuple[DevelopmentTask, List[str]]] = []

        for t in tasks:
            if not t.id or t.id in completed_task_ids or t.id in failed_task_ids:
                continue

            deps = set(t.depends_on or [])
            failed_deps = [d for d in deps if d in failed_task_ids]
            unmet_deps = [d for d in deps if d not in completed_task_ids]

            if failed_deps or unmet_deps:
                blocked_reasons = failed_deps if failed_deps else unmet_deps
                blocked.append((t, blocked_reasons))
            else:
                eligible.append(t)

        return eligible, blocked
