"""
Unit and integration tests for ROGERS Slice 9: Intelligent Deployment Automation.
Tests:
- Stack detection across Python, Node/React, and custom stacks
- Deployment readiness verification with secret scanning and quality gates
- Multi-platform plan generation (Docker, Render, Vercel, Netlify, Railway)
- Mandatory human approval gate enforcement
- Sandboxed deployment execution, logging, and health probe verification
- Pre-deployment snapshot capture and one-click rollback
- REST API endpoint lifecycle
"""
import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.storage import ProjectStorage
from backend.app.scaffolder import GENERATED_BASE_DIR, slugify
from backend.app.models import Project, Blueprint, TechStack, Architecture, DevelopmentTask
from backend.app.deployment.models import (
    DeploymentPlatform,
    DeploymentState,
    DeploymentPlan,
    DeploymentRecord
)
from backend.app.deployment.detector import StackDetector
from backend.app.deployment.verifier import DeploymentVerifier
from backend.app.deployment.service import DeploymentService, DeploymentExecutionError


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_project(tmp_path):
    proj_id = "test-proj-deploy-001"
    proj_name = "Avengers Tactical Defense Grid"
    slug = slugify(proj_name)
    proj_dir = GENERATED_BASE_DIR / slug
    
    # Clean previous artifacts if any
    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Create basic starter files
    (proj_dir / "requirements.txt").write_text("fastapi==0.115.0\nuvicorn==0.30.0\npytest==8.3.0\n")
    (proj_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health(): return {'status': 'healthy'}\n")

    bp = Blueprint(
        summary="Autonomous tactical defense and telemetry grid with FastAPI backend.",
        requirements=["REST API", "Health Probe", "Authentication"],
        tech_stack=TechStack(
            frontend="React + Vite",
            backend="FastAPI + Uvicorn",
            database="SQLite",
            ai="None"
        ),
        architecture=Architecture(
            description="Modular REST API with async request handling and telemetry streams.",
            components=["api", "telemetry", "auth"]
        ),
        development_tasks=[
            DevelopmentTask(id="task_1", title="Setup API", description="Init API", status="verified", depends_on=[]),
            DevelopmentTask(id="task_2", title="Health Check", description="Add Health Probe", status="verified", depends_on=["task_1"])
        ],
        next_steps=["Deploy to Docker", "Add monitoring"]
    )

    project = Project(
        id=proj_id,
        name=proj_name,
        idea="Autonomous tactical defense and telemetry grid.",
        blueprint=bp,
        package_metadata=None,
        mission_state={"status": "completed"}
    )
    ProjectStorage.save(project)

    yield project, proj_dir

    # Cleanup
    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    ProjectStorage.delete(proj_id)


def test_stack_detection_python(test_project):
    project, proj_dir = test_project
    detection = StackDetector.detect(proj_dir, project.blueprint)
    
    assert detection.language == "python"
    assert detection.framework == "fastapi"
    assert detection.default_port == 8000
    assert "requirements.txt" in detection.build_command
    assert "uvicorn" in detection.start_command or "python" in detection.start_command


def test_stack_detection_node(tmp_path):
    node_dir = tmp_path / "sample_node_app"
    node_dir.mkdir()
    (node_dir / "package.json").write_text('{"name": "shield-ui", "dependencies": {"react": "^18.0.0", "vite": "^5.0.0"}, "scripts": {"build": "vite build", "preview": "vite preview"}}')
    
    detection = StackDetector.detect(node_dir)
    assert detection.language in ["javascript", "typescript"]
    assert "react" in detection.framework
    assert detection.default_port == 5173
    assert detection.build_command == "npm run build"
    assert detection.output_dir == "dist"


def test_readiness_secret_scanner_blocks(test_project):
    project, proj_dir = test_project
    
    # Inject an unmasked private key
    leak_file = proj_dir / "secrets.txt"
    leak_file.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----\n")

    report = DeploymentVerifier.evaluate(project, proj_dir)
    assert report.can_deploy is False
    assert report.overall_status == "blocked"
    assert any("Private Key" in b or "secret" in b.lower() for b in report.blockers)

    leak_file.unlink()


def test_readiness_clean_pass(test_project):
    project, proj_dir = test_project
    report = DeploymentVerifier.evaluate(project, proj_dir)
    assert report.can_deploy is True
    assert report.overall_status in ["ready", "ready_with_warnings"]


def test_plan_generation_all_platforms(test_project):
    project, _ = test_project
    platforms: list[DeploymentPlatform] = ["docker", "render", "vercel", "netlify", "railway"]

    for plat in platforms:
        plan = DeploymentService.generate_plan(project, platform=plat)
        assert plan.platform == plat
        assert plan.is_approved is False
        assert len(plan.generated_configs) >= 1
        assert len(plan.steps) >= 3

        config_names = [c.filename for c in plan.generated_configs]
        if plat == "docker":
            assert "Dockerfile" in config_names
            assert "docker-compose.yml" in config_names
        elif plat == "render":
            assert "render.yaml" in config_names
        elif plat == "vercel":
            assert "vercel.json" in config_names
        elif plat == "netlify":
            assert "netlify.toml" in config_names
        elif plat == "railway":
            assert "railway.json" in config_names


def test_approval_gate_enforcement(test_project):
    project, _ = test_project
    DeploymentService.generate_plan(project, platform="docker")

    # Attempting deployment without approval must raise error
    with pytest.raises(DeploymentExecutionError, match="HUMAN APPROVAL REQUIRED"):
        DeploymentService.execute_deployment(project)


def test_deployment_execution_and_health_check(test_project):
    project, proj_dir = test_project
    
    # 1. Generate Plan
    plan = DeploymentService.generate_plan(project, platform="docker", target_port=8080)
    assert plan.target_port == 8080

    # 2. Approve Plan
    approved_plan = DeploymentService.approve_plan(project, approved_by="Captain Steve Rogers", notes="Cleared for launch")
    assert approved_plan.is_approved is True
    assert approved_plan.approved_by == "Captain Steve Rogers"

    # 3. Execute Deployment
    record = DeploymentService.execute_deployment(project)
    assert record.status == "healthy"
    assert record.health_status == "passing"
    assert record.health_status_code == 200
    assert record.deployment_url == "http://localhost:8080"
    assert record.snapshot_id is not None
    assert any("Initiating deployment pipeline" in log for log in record.logs)

    # Verify generated configs were written to disk
    assert (proj_dir / "Dockerfile").exists()
    assert (proj_dir / "docker-compose.yml").exists()

    # 4. Check State Persistence
    state = DeploymentService.get_state(project)
    assert state.active_deployment.deployment_id == record.deployment_id
    assert len(state.history) == 1


def test_rollback_mechanism(test_project):
    project, proj_dir = test_project
    
    # Setup initial deployment
    DeploymentService.generate_plan(project, platform="docker")
    DeploymentService.approve_plan(project, approved_by="Commander")
    dep1 = DeploymentService.execute_deployment(project)

    # Mutate project file after deployment
    (proj_dir / "main.py").write_text("# Corrupted deployment update")

    # Trigger rollback
    rollback_rec = DeploymentService.rollback(project, target_deployment_id=dep1.deployment_id)
    assert rollback_rec.status == "rolled_back"
    assert rollback_rec.snapshot_id == dep1.snapshot_id

    # Verify history recorded rollback
    state = DeploymentService.get_state(project)
    assert state.active_deployment.status == "rolled_back"
    assert len(state.history) == 2


def test_api_endpoints_slice9(client, test_project):
    project, _ = test_project
    pid = project.id

    # 1. GET /deployment/detect
    res_detect = client.get(f"/api/projects/{pid}/deployment/detect")
    assert res_detect.status_code == 200
    assert res_detect.json()["language"] == "python"

    # 2. GET /deployment/readiness
    res_ready = client.get(f"/api/projects/{pid}/deployment/readiness")
    assert res_ready.status_code == 200
    assert "overall_status" in res_ready.json()

    # 3. POST /deployment/plan
    res_plan = client.post(f"/api/projects/{pid}/deployment/plan", json={"platform": "render", "target_port": 9000})
    assert res_plan.status_code == 200
    assert res_plan.json()["platform"] == "render"
    assert res_plan.json()["is_approved"] is False

    # 4. POST /deployment/deploy (BEFORE APPROVAL -> 400)
    res_deploy_fail = client.post(f"/api/projects/{pid}/deployment/deploy", json={})
    assert res_deploy_fail.status_code == 400
    assert "APPROVAL" in res_deploy_fail.json()["detail"]

    # 5. POST /deployment/plan/approve
    res_approve = client.post(f"/api/projects/{pid}/deployment/plan/approve", json={"approved_by": "Mission Director"})
    assert res_approve.status_code == 200
    assert res_approve.json()["is_approved"] is True

    # 6. POST /deployment/deploy (AFTER APPROVAL -> SUCCESS)
    res_deploy = client.post(f"/api/projects/{pid}/deployment/deploy", json={})
    assert res_deploy.status_code == 200
    dep_data = res_deploy.json()
    assert dep_data["status"] == "healthy"
    assert "onrender.com" in dep_data["deployment_url"]

    # 7. GET /deployment/status
    res_status = client.get(f"/api/projects/{pid}/deployment/status")
    assert res_status.status_code == 200
    assert res_status.json()["active_deployment"]["status"] == "healthy"

    # 8. POST /deployment/rollback
    res_roll = client.post(f"/api/projects/{pid}/deployment/rollback", json={"target_deployment_id": dep_data["deployment_id"]})
    assert res_roll.status_code == 200
    assert res_roll.json()["status"] == "rolled_back"

    # 9. GET /deployment/history
    res_hist = client.get(f"/api/projects/{pid}/deployment/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 2
