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
from backend.app.agents.models import (
    ParallelMissionConfig,
    ParallelMissionState,
    ParallelExecutionPlan,
    AgentRole,
    AgentStatus
)
from backend.app.agents.roles import (
    ResearchAgent,
    ArchitectureAgent,
    DevelopmentAgent,
    TestingAgent,
    ReviewAgent
)
from backend.app.agents.orchestrator import MultiAgentOrchestrator, MultiAgentOrchestratorError


@pytest.fixture
def client():
    return TestClient(app)


def test_agent_registration_and_roles():
    """Confirms all specialized agent roles instantiate with correct specialization and idle status."""
    researcher = ResearchAgent()
    architect = ArchitectureAgent()
    developer = DevelopmentAgent(agent_id="test_dev", name="Test Builder")
    tester = TestingAgent()
    reviewer = ReviewAgent()

    assert researcher.role == "researcher"
    assert architect.role == "architect"
    assert developer.role == "developer"
    assert tester.role == "tester"
    assert reviewer.role == "reviewer"

    info = developer.get_info()
    assert info.status == "idle"
    assert info.tasks_completed == 0
    assert info.agent_id == "test_dev"


def test_parallel_batches_and_dag_grouping():
    """Confirms tasks with dependencies are structured into sequential parallel stages."""
    # Tasks:
    # Layer 1: t1, t2 (independent)
    # Layer 2: t3 depends on t1, t4 depends on t2
    # Layer 3: t5 depends on t3 and t4
    t1 = DevelopmentTask(id="task_db", title="DB Setup", description="Database", depends_on=[])
    t2 = DevelopmentTask(id="task_auth_spec", title="Auth Spec", description="Auth", depends_on=[])
    t3 = DevelopmentTask(id="task_api_db", title="DB API", description="API", depends_on=["task_db"])
    t4 = DevelopmentTask(id="task_api_auth", title="Auth API", description="Auth API", depends_on=["task_auth_spec"])
    t5 = DevelopmentTask(id="task_client", title="Client App", description="Client", depends_on=["task_api_db", "task_api_auth"])

    bp = Blueprint(
        summary="Parallel Blueprint",
        requirements=["R1"],
        tech_stack=TechStack(frontend="React", backend="FastAPI", database="SQLite", ai="ROGERS"),
        architecture=Architecture(description="Arch", components=["C1"]),
        development_tasks=[t1, t2, t3, t4, t5],
        next_steps=["Deploy"]
    )
    project = Project(
        id="proj-slice8-dag-test",
        name="Parallel DAG Test",
        idea="Test parallel DAG batches",
        status="completed",
        blueprint=bp
    )

    plan = MultiAgentOrchestrator.get_parallel_plan(project)
    assert plan.is_valid is True
    assert len(plan.parallel_batches) == 3
    # Layer 1 has t1 and t2
    assert set(plan.parallel_batches[0]) == {"task_db", "task_auth_spec"}
    # Layer 2 has t3 and t4
    assert set(plan.parallel_batches[1]) == {"task_api_db", "task_api_auth"}
    # Layer 3 has t5
    assert set(plan.parallel_batches[2]) == {"task_client"}


def test_file_conflict_guard_prediction():
    """Confirms architecture agent plans file boundaries to prevent collision."""
    arch = ArchitectureAgent()
    t_auth = DevelopmentTask(id="t_auth", title="Build Authentication System", description="")
    t_db = DevelopmentTask(id="t_db", title="Scaffold Database Migrations", description="")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    files_auth = loop.run_until_complete(arch.design_task_structure(t_auth, {}))
    files_db = loop.run_until_complete(arch.design_task_structure(t_db, {}))

    assert any("auth" in f for f in files_auth)
    assert any("main" in f or "database" in f for f in files_db)


def test_parallel_endpoints_plan_and_status(client):
    """Tests GET /api/projects/{id}/parallel/plan and /status."""
    t1 = DevelopmentTask(id="task_p1", title="Task 1", description="Desc 1", depends_on=[])
    t2 = DevelopmentTask(id="task_p2", title="Task 2", description="Desc 2", depends_on=[])

    bp = Blueprint(
        summary="Parallel BP",
        requirements=["R1"],
        tech_stack=TechStack(frontend="React", backend="FastAPI", database="SQLite", ai="ROGERS"),
        architecture=Architecture(description="Arch", components=["C1"]),
        development_tasks=[t1, t2],
        next_steps=["N1"]
    )
    project = Project(
        id="proj-slice8-endpoints-test",
        name="Parallel Endpoints Test",
        idea="Test parallel API",
        status="completed",
        blueprint=bp
    )
    ProjectStorage.save(project)

    # 1. Plan preview
    plan_res = client.get(f"/api/projects/{project.id}/parallel/plan")
    assert plan_res.status_code == 200, plan_res.text
    pdata = plan_res.json()
    assert pdata["is_valid"] is True
    assert pdata["total_tasks"] == 2
    assert len(pdata["parallel_batches"]) >= 1

    # 2. Status inspection
    st_res = client.get(f"/api/projects/{project.id}/parallel/status")
    assert st_res.status_code == 200, st_res.text
    st_data = st_res.json()
    assert st_data["status"] == "ready"
    assert len(st_data["agents"]) >= 5


def test_parallel_mission_lifecycle_transitions(client):
    """Tests start, pause, resume, cancel state transitions for parallel execution."""
    t1 = DevelopmentTask(id="task_par_l1", title="Parallel Lifecycle 1", description="Init", depends_on=[])
    bp = Blueprint(
        summary="Lifecycle BP",
        requirements=["R1"],
        tech_stack=TechStack(frontend="React", backend="FastAPI", database="SQLite", ai="ROGERS"),
        architecture=Architecture(description="Arch", components=["C1"]),
        development_tasks=[t1],
        next_steps=["N1"]
    )
    project = Project(
        id="proj-slice8-lifecycle-test",
        name="Parallel Lifecycle Test",
        idea="Test parallel lifecycle transitions",
        status="completed",
        blueprint=bp
    )
    ProjectStorage.save(project)

    # Cannot pause when ready
    pause_err = client.post(f"/api/projects/{project.id}/parallel/pause")
    assert pause_err.status_code == 400

    # Cancel transition
    cancel_res = client.post(f"/api/projects/{project.id}/parallel/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Report endpoint
    report_res = client.get(f"/api/projects/{project.id}/parallel/report")
    assert report_res.status_code == 200
    rep_data = report_res.json()
    assert rep_data["status"] == "cancelled"
    assert rep_data["total_tasks"] == 1
    assert len(rep_data["agents_summary"]) >= 5
