import pytest
import zipfile
import hashlib
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
from backend.app.implementation.models import TaskImplementationResult, TestResult, ValidationResult
from backend.app.scaffolder import GENERATED_BASE_DIR, slugify
from backend.app.delivery.service import DIST_PACKAGES_DIR


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def cleanup_projects():
    yield
    # Cleanup any created test projects from memory/storage
    # and generated directories if necessary
    pass


def create_mock_project(
    name: str = "Mission Packaging Defense Test",
    scaffold: bool = True,
    task_status: str = "verified"
) -> Project:
    project_id = f"test-slice5-{slugify(name)}"
    
    task = DevelopmentTask(
        id="task_core_health",
        title="Core Health Monitoring Endpoint",
        description="Provide real-time mission status health probe",
        priority="high",
        status=task_status
    )

    if task_status == "verified":
        task.implementation_result = TaskImplementationResult(
            status="verified",
            task_id="task_core_health",
            summary="Implemented and verified health monitoring endpoint",
            files_changed=["backend/app/main.py", "backend/tests/test_api.py"],
            changes=[],
            validation=ValidationResult(
                status="passed",
                command="python -m compileall .",
                output="Compilation succeeded"
            ),
            test_result=TestResult(
                status="passed",
                exit_code=0,
                duration_seconds=0.85,
                tests_total=4,
                tests_passed=4,
                tests_failed=0,
                tests_skipped=0
            ),
            verified=True,
            security_checks={
                "project_root_locked": True,
                "path_traversal_blocked": True,
                "git_access_blocked": True,
                "snapshot_protection_active": True,
                "shell_execution_blocked": True,
                "write_target_validated": True
            }
        )
    elif task_status == "failed":
        task.implementation_result = TaskImplementationResult(
            status="failed",
            task_id="task_core_health",
            summary="Implementation failed unit tests",
            files_changed=["backend/app/main.py"],
            changes=[],
            validation=ValidationResult(
                status="passed",
                command="python -m compileall .",
                output="Compilation succeeded"
            ),
            test_result=TestResult(
                status="failed",
                exit_code=1,
                duration_seconds=1.2,
                tests_total=4,
                tests_passed=2,
                tests_failed=2,
                tests_skipped=0,
                failure_summary="AssertionError: Status code 500 != 200"
            ),
            verified=False
        )

    blueprint = Blueprint(
        summary="A secure tactical mission control microservice.",
        requirements=["Requirement 1: Health Probe", "Requirement 2: Defense Check"],
        tech_stack=TechStack(
            frontend="React + Tailwind CSS",
            backend="FastAPI Python 3.11+",
            database="PostgreSQL + Redis",
            ai="ROGERS Autonomous Agent"
        ),
        architecture=Architecture(
            description="Mission-critical distributed telemetry pipeline",
            components=["API Gateway", "Health Probe Engine", "Telemetry Ingestion"]
        ),
        development_tasks=[task],
        next_steps=["Deploy to secure cluster", "Configure production TLS certificates"]
    )

    project = Project(
        id=project_id,
        name=name,
        idea="A secure mission command platform requiring full end-to-end delivery verification.",
        status="completed",
        stages={
            "research": StageData(name="research", label="Research", status="approved"),
            "requirements": StageData(name="requirements", label="Requirements", status="approved"),
            "architecture": StageData(name="architecture", label="Architecture", status="approved"),
            "tech_stack": StageData(name="tech_stack", label="Tech Stack", status="approved"),
            "development": StageData(name="development", label="Development", status="approved")
        },
        blueprint=blueprint
    )

    ProjectStorage.save(project)

    if scaffold:
        # Create physical directory
        proj_dir = GENERATED_BASE_DIR / slugify(name)
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "backend").mkdir(parents=True, exist_ok=True)
        (proj_dir / "backend" / "requirements.txt").write_text("fastapi\nuvicorn\npytest\n", encoding="utf-8")
        (proj_dir / ".env.example").write_text("APP_ENV=production\nSECRET_KEY=template\n", encoding="utf-8")
        (proj_dir / "README.md").write_text(f"# {name}\nProduction ready.\n", encoding="utf-8")

    return project


def test_packaging_gate_blocks_unscaffolded_project(client):
    """Packaging must fail with 400 Bad Request if project has not been physically scaffolded."""
    project = create_mock_project(
        name="Unscaffolded Defense Test",
        scaffold=False,
        task_status="verified"
    )

    res = client.post(f"/api/projects/{project.id}/package")
    assert res.status_code == 400
    assert "You must scaffold the project before packaging" in res.json()["detail"]


def test_packaging_gate_blocks_unverified_project(client):
    """Packaging must fail with 400 Bad Request if no development task has been verified."""
    project = create_mock_project(
        name="Unverified Defense Test",
        scaffold=True,
        task_status="pending"
    )

    res = client.post(f"/api/projects/{project.id}/package")
    assert res.status_code == 400
    assert "no verified or completed development tasks" in res.json()["detail"]


def test_packaging_gate_blocks_failed_project(client):
    """Packaging must fail with 400 Bad Request if any development task failed."""
    project = create_mock_project(
        name="Failed Tasks Defense Test",
        scaffold=True,
        task_status="failed"
    )

    res = client.post(f"/api/projects/{project.id}/package")
    assert res.status_code == 400
    assert "failed task(s)" in res.json()["detail"]


def test_successful_packaging_and_secret_exclusion(client):
    """
    Confirms clean packaging:
    1. Produces valid zip archive.
    2. Excludes .env secrets, .git, .venv, and __pycache__.
    3. Injects VERIFICATION_REPORT.md.
    4. Computes valid SHA-256 integrity checksum.
    """
    project = create_mock_project(
        name="Verified Stealth Platform",
        scaffold=True,
        task_status="verified"
    )
    proj_dir = GENERATED_BASE_DIR / slugify(project.name)

    # Infiltrate simulated secrets, virtual environments, and caches
    (proj_dir / ".env").write_text("SUPER_SECRET_TOKEN=tactical_classified_key_12345", encoding="utf-8")
    (proj_dir / ".git").mkdir(exist_ok=True)
    (proj_dir / ".git" / "config").write_text("[core]\nrepositoryformatversion = 0", encoding="utf-8")
    (proj_dir / ".venv").mkdir(exist_ok=True)
    (proj_dir / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin/python", encoding="utf-8")
    (proj_dir / "backend" / "__pycache__").mkdir(exist_ok=True)
    (proj_dir / "backend" / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"PYCBYTECODE")
    (proj_dir / ".rogers" / "snapshots" / "snap_1").mkdir(parents=True, exist_ok=True)
    (proj_dir / ".rogers" / "snapshots" / "snap_1" / "backup.py").write_text("old code", encoding="utf-8")

    # Call package endpoint
    res = client.post(f"/api/projects/{project.id}/package")
    assert res.status_code == 200, res.text
    meta = res.json()

    assert meta["project_id"] == project.id
    assert meta["verification_status"] == "verified"
    assert meta["package_filename"].endswith(".zip")
    assert meta["package_size_bytes"] > 0
    assert len(meta["sha256_checksum"]) == 64

    # Validate package physical file
    pkg_file = Path(meta["package_path"])
    assert pkg_file.exists()

    # Re-verify SHA256 matches actual file
    hasher = hashlib.sha256()
    with open(pkg_file, "rb") as f:
        hasher.update(f.read())
    assert hasher.hexdigest() == meta["sha256_checksum"]

    # Open zip and inspect contained entries
    with zipfile.ZipFile(pkg_file, "r") as zf:
        namelist = zf.namelist()

        # Embedded verification report must exist
        assert "VERIFICATION_REPORT.md" in namelist
        report_text = zf.read("VERIFICATION_REPORT.md").decode("utf-8")
        assert "ROGERS MISSION VERIFICATION REPORT" in report_text
        assert "DEFENSE ARCHITECTURE & SECURITY AUDIT" in report_text
        assert "100.0%" in report_text  # 4/4 tests passed

        # Template files must be preserved
        assert ".env.example" in namelist
        assert "backend/requirements.txt" in namelist
        assert "README.md" in namelist

        # Critical exclusions: NO SECRETS, NO VENV, NO GIT, NO PYCACHE, NO SNAPSHOTS
        assert ".env" not in namelist
        assert not any(n.startswith(".git") for n in namelist)
        assert not any(n.startswith(".venv") for n in namelist)
        assert not any(n.startswith(".rogers") for n in namelist)
        assert not any("__pycache__" in n for n in namelist)
        assert not any(n.endswith(".pyc") for n in namelist)


def test_download_package_endpoint(client):
    """Validates streaming download of the generated zip archive."""
    project = create_mock_project(
        name="Download Stream Verification",
        scaffold=True,
        task_status="verified"
    )

    # First attempt download before packaging -> 404
    no_pkg_res = client.get(f"/api/projects/{project.id}/package/download")
    assert no_pkg_res.status_code == 404

    # Package the project
    pkg_res = client.post(f"/api/projects/{project.id}/package")
    assert pkg_res.status_code == 200

    # Download
    download_res = client.get(f"/api/projects/{project.id}/package/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/zip"
    assert len(download_res.content) == pkg_res.json()["package_size_bytes"]


def test_mission_report_endpoint(client):
    """Validates truthful mission report synthesis."""
    project = create_mock_project(
        name="Tactical Mission Report Dossier",
        scaffold=True,
        task_status="verified"
    )

    # Create package so metadata is included
    pkg_res = client.post(f"/api/projects/{project.id}/package")
    assert pkg_res.status_code == 200

    report_res = client.get(f"/api/projects/{project.id}/mission-report")
    assert report_res.status_code == 200
    report = report_res.json()

    assert report["project_id"] == project.id
    assert report["project_name"] == project.name
    assert report["tagline"] == "I CAN DO THIS ALL DAY."

    # Verification metrics
    verif = report["verification_summary"]
    assert verif["status"] == "verified"
    assert verif["verified_tasks"] == 1
    assert verif["tests_passed"] == 4
    assert verif["pass_rate_percent"] == 100.0

    # Defense security audit
    audit = report["security_audit"]
    assert audit["project_root_locked"] is True
    assert audit["path_traversal_blocked"] is True
    assert audit["git_access_blocked"] is True

    # Package metadata linked
    assert report["package_metadata"] is not None
    assert report["package_metadata"]["sha256_checksum"] == pkg_res.json()["sha256_checksum"]
    assert len(report["recommended_next_steps"]) > 0
