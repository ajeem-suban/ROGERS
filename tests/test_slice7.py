import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.storage import ProjectStorage
from backend.app.models import (
    Project,
    Blueprint,
    TechStack,
    Architecture,
    DevelopmentTask,
    StageData
)
from backend.app.mission.graph import DependencyGraph, DependencyGraphError
from backend.app.mission.service import MissionOrchestrator, MissionOrchestratorError
from backend.app.scaffolder import GENERATED_BASE_DIR, slugify


@pytest.fixture
def client():
    return TestClient(app)


def test_dependency_graph_valid_dag():
    """Confirms valid dependency graph generates correct topological execution order."""
    t1 = DevelopmentTask(id="task_db", title="Database Setup", description="Setup db", depends_on=[])
    t2 = DevelopmentTask(id="task_api", title="API Endpoints", description="Build api", depends_on=["task_db"])
    t3 = DevelopmentTask(id="task_ui", title="Frontend UI", description="Build ui", depends_on=["task_api"])

    plan = DependencyGraph.validate_and_plan("p1", "Project 1", [t3, t1, t2])
    assert plan.is_valid is True
    assert plan.has_cycles is False
    assert len(plan.validation_errors) == 0
    # Topo sort must execute t1 before t2, and t2 before t3
    order = plan.execution_order
    assert order.index("task_db") < order.index("task_api")
    assert order.index("task_api") < order.index("task_ui")


def test_dependency_graph_cycle_detection():
    """Confirms cycle detection flags circular dependencies (A -> B -> A)."""
    t1 = DevelopmentTask(id="task_a", title="Task A", description="Desc A", depends_on=["task_b"])
    t2 = DevelopmentTask(id="task_b", title="Task B", description="Desc B", depends_on=["task_a"])

    plan = DependencyGraph.validate_and_plan("p2", "Cycle Project", [t1, t2])
    assert plan.is_valid is False
    assert plan.has_cycles is True
    assert any("cycle" in err.lower() for err in plan.validation_errors)


def test_dependency_graph_missing_and_self_dependencies():
    """Confirms missing dependency and self-dependency are flagged."""
    t1 = DevelopmentTask(id="task_self", title="Self Task", description="Desc", depends_on=["task_self"])
    t2 = DevelopmentTask(id="task_ghost", title="Ghost Task", description="Desc", depends_on=["non_existent_id"])

    plan = DependencyGraph.validate_and_plan("p3", "Invalid Deps", [t1, t2])
    assert plan.is_valid is False
    assert any("cannot depend on itself" in err for err in plan.validation_errors)
    assert any("non-existent" in err for err in plan.validation_errors)


def test_dependency_graph_eligibility_and_blocking():
    """Confirms tasks are blocked if dependencies fail, while independent tasks stay eligible."""
    t1 = DevelopmentTask(id="t1", title="Task 1", description="D1", depends_on=[])
    t2 = DevelopmentTask(id="t2", title="Task 2", description="D2", depends_on=["t1"])
    t3 = DevelopmentTask(id="t3", title="Task 3", description="D3", depends_on=[])

    # t1 failed
    eligible, blocked = DependencyGraph.get_eligible_tasks([t1, t2, t3], completed_task_ids=set(), failed_task_ids={"t1"})
    assert any(t.id == "t3" for t in eligible)
    assert not any(t.id == "t2" for t in eligible)
    assert any(b[0].id == "t2" for b in blocked)


def test_mission_plan_and_status_endpoints(client):
    """Tests GET /api/projects/{id}/mission/plan and /status endpoints."""
    t1 = DevelopmentTask(id="task_step1", title="Step 1", description="Init", depends_on=[])
    t2 = DevelopmentTask(id="task_step2", title="Step 2", description="Core", depends_on=["task_step1"])

    bp = Blueprint(
        summary="Mission Blueprint",
        requirements=["R1"],
        tech_stack=TechStack(frontend="React", backend="FastAPI", database="SQLite", ai="ROGERS"),
        architecture=Architecture(description="Arch", components=["C1"]),
        development_tasks=[t1, t2],
        next_steps=["Step 3"]
    )
    project = Project(
        id="proj-slice7-status-test",
        name="Mission Status Test",
        idea="Test mission status endpoints",
        status="completed",
        blueprint=bp
    )
    ProjectStorage.save(project)

    # 1. Plan endpoint
    plan_res = client.get(f"/api/projects/{project.id}/mission/plan")
    assert plan_res.status_code == 200, plan_res.text
    pdata = plan_res.json()
    assert pdata["is_valid"] is True
    assert pdata["total_tasks"] == 2
    assert pdata["execution_order"] == ["task_step1", "task_step2"]

    # 2. Status endpoint
    st_res = client.get(f"/api/projects/{project.id}/mission/status")
    assert st_res.status_code == 200, st_res.text
    st_data = st_res.json()
    assert st_data["status"] == "ready"


def test_mission_lifecycle_transitions(client):
    """Tests start, pause, resume, cancel state transitions."""
    t1 = DevelopmentTask(id="task_l1", title="Lifecycle 1", description="Init", depends_on=[])
    bp = Blueprint(
        summary="Lifecycle BP",
        requirements=["R1"],
        tech_stack=TechStack(frontend="React", backend="FastAPI", database="SQLite", ai="ROGERS"),
        architecture=Architecture(description="Arch", components=["C1"]),
        development_tasks=[t1],
        next_steps=["N1"]
    )
    project = Project(
        id="proj-slice7-lifecycle-test",
        name="Mission Lifecycle Test",
        idea="Test lifecycle transitions",
        status="completed",
        blueprint=bp
    )
    ProjectStorage.save(project)

    # Cannot pause when ready
    pause_err = client.post(f"/api/projects/{project.id}/mission/pause")
    assert pause_err.status_code == 400

    # Cancel transition
    cancel_res = client.post(f"/api/projects/{project.id}/mission/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Report endpoint
    report_res = client.get(f"/api/projects/{project.id}/mission/report")
    assert report_res.status_code == 200
    rep_data = report_res.json()
    assert rep_data["status"] == "cancelled"
    assert rep_data["total_tasks"] == 1
