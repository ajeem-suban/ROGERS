import pytest
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
from backend.app.git.service import (
    is_git_installed,
    scan_file_for_secret_risk,
    redact_url_credentials,
    resolve_and_validate_project_repo,
    GitSecurityError,
    GitService,
    ROGERS_ROOT,
)


import os
import stat
import shutil

@pytest.fixture
def client():
    return TestClient(app)


def _safe_clean_dir(path: Path):
    if not path.exists():
        return
    def remove_readonly(func, p, _):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass
    shutil.rmtree(path, onexc=remove_readonly)


@pytest.fixture(autouse=True)
def cleanup_test_repos():
    # Clean before and after
    repos_to_clean = [
        GENERATED_BASE_DIR / "git-lifecycle-flow-test",
        GENERATED_BASE_DIR / "unverified-push-gate-test",
        GENERATED_BASE_DIR / "git-defense-test-project",
    ]
    for r in repos_to_clean:
        _safe_clean_dir(r)
    yield
    for r in repos_to_clean:
        _safe_clean_dir(r)


def create_slice6_test_project(name: str = "Git Defense Test Project", is_verified: bool = True) -> Project:
    project_id = f"test-slice6-{slugify(name)}"
    task = DevelopmentTask(
        id="task_git_health",
        title="Git Health Telemetry",
        description="Verify Git telemetry and publishing pipeline",
        priority="high",
        status="verified" if is_verified else "pending"
    )

    if is_verified:
        task.implementation_result = TaskImplementationResult(
            status="verified",
            task_id="task_git_health",
            summary="Verified implementation",
            files_changed=["backend/app/main.py"],
            changes=[],
            validation=ValidationResult(status="passed", command="compileall", output="OK"),
            test_result=TestResult(status="passed", tests_total=2, tests_passed=2, tests_failed=0),
            verified=True
        )

    bp = Blueprint(
        summary="A secure git integration test project.",
        requirements=["Requirement 1: Git Integration"],
        tech_stack=TechStack(frontend="React", backend="FastAPI", database="SQLite", ai="ROGERS"),
        architecture=Architecture(description="Git architecture", components=["API"]),
        development_tasks=[task],
        next_steps=["Publish to remote"]
    )

    project = Project(
        id=project_id,
        name=name,
        idea="Git test idea",
        status="completed",
        stages={"research": StageData(name="research", label="Research", status="approved")},
        blueprint=bp
    )
    ProjectStorage.save(project)

    # Physical directory
    proj_dir = GENERATED_BASE_DIR / slugify(name)
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "backend").mkdir(parents=True, exist_ok=True)
    (proj_dir / "backend" / "main.py").write_text("print('hello world')", encoding="utf-8")
    (proj_dir / "README.md").write_text(f"# {name}", encoding="utf-8")
    return project


def test_git_cli_detected():
    """Confirms Git CLI executable is properly detected on host system."""
    assert is_git_installed() is True


def test_url_credential_redaction():
    """Confirms sensitive usernames and tokens are redacted from remote URLs."""
    url1 = "https://user:ghp_secrettoken1234567890@github.com/org/repo.git"
    assert redact_url_credentials(url1) == "https://***@github.com/org/repo.git"

    url2 = "https://ghp_pat1234567890@github.com/org/repo.git"
    assert redact_url_credentials(url2) == "https://***@github.com/org/repo.git"

    url3 = "git@github.com:org/repo.git"
    assert redact_url_credentials(url3) == "git@github.com:org/repo.git"


def test_secret_scanner_blocks_env_and_private_keys(tmp_path):
    """Confirms secret scanning flags .env files and embedded private keys."""
    # .env exact match
    env_file = tmp_path / ".env"
    env_file.write_text("DB_PASS=secret", encoding="utf-8")
    risk, reason = scan_file_for_secret_risk(env_file, ".env")
    assert risk is True
    assert "sensitive configuration file" in reason

    # .env.example allowed
    example_file = tmp_path / ".env.example"
    example_file.write_text("DB_PASS=template", encoding="utf-8")
    risk, _ = scan_file_for_secret_risk(example_file, ".env.example")
    assert risk is False

    # Embedded RSA private key
    key_file = tmp_path / "server.key"
    key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...", encoding="utf-8")
    risk, reason = scan_file_for_secret_risk(key_file, "server.key")
    assert risk is True
    assert "credential" in reason.lower() or "private" in reason.lower()


def test_rogers_source_directory_protected():
    """Guarantees Git operations cannot target ROGERS root repository."""
    rogers_project = Project(
        id="rogers-core-protection-test",
        name="../..",  # Path traversal attempt
        idea="Exploit attempt",
        status="created"
    )
    with pytest.raises(GitSecurityError):
        resolve_and_validate_project_repo(rogers_project)


def test_git_init_status_diff_and_commit_flow(client):
    """
    End-to-end unit test:
    1. Initialize repo
    2. Check status and detect changes
    3. Stage only approved files
    4. Create commit and verify audit entry
    """
    project = create_slice6_test_project(name="Git Lifecycle Flow Test", is_verified=True)

    # 1. Init
    init_res = client.post(f"/api/projects/{project.id}/git/init")
    assert init_res.status_code == 200, init_res.text
    status_data = init_res.json()
    assert status_data["initialized"] is True
    assert status_data["branch"] == "main"

    # 2. Status inspection
    st_res = client.get(f"/api/projects/{project.id}/git/status")
    assert st_res.status_code == 200
    st_data = st_res.json()
    assert len(st_data["changes"]) > 0

    # 3. Diff inspection
    diff_res = client.get(f"/api/projects/{project.id}/git/diff")
    assert diff_res.status_code == 200

    # 4. Attempt commit with secret-bearing file -> must be blocked
    proj_dir = GENERATED_BASE_DIR / slugify(project.name)
    (proj_dir / ".env").write_text("SUPER_SECRET=classified", encoding="utf-8")

    blocked_commit = client.post(
        f"/api/projects/{project.id}/git/commit",
        json={"message": "feat: leak secret", "approved_files": [".env"]}
    )
    assert blocked_commit.status_code == 400
    assert "sensitive" in blocked_commit.json()["detail"].lower() or "blocked" in blocked_commit.json()["detail"].lower()

    # 5. Commit approved safe files
    approved = ["README.md", "backend/main.py"]
    commit_res = client.post(
        f"/api/projects/{project.id}/git/commit",
        json={"message": "feat: initial verified commit", "approved_files": approved}
    )
    assert commit_res.status_code == 200, commit_res.text
    c_data = commit_res.json()
    assert c_data["success"] is True
    assert c_data["commit_hash"] is not None

    # Verify publishing history audit
    hist_res = client.get(f"/api/projects/{project.id}/git/publishing-history")
    assert hist_res.status_code == 200
    entries = hist_res.json()
    assert len(entries) >= 1
    assert entries[0]["commit_hash"] == c_data["commit_hash"]


def test_push_gate_blocks_unverified_project(client):
    """Guarantees push operation is strictly blocked if project has no verified tasks."""
    project = create_slice6_test_project(name="Unverified Push Gate Test", is_verified=False)

    # Init repo & commit locally
    client.post(f"/api/projects/{project.id}/git/init")
    client.post(
        f"/api/projects/{project.id}/git/commit",
        json={"message": "test: unverified commit", "approved_files": ["README.md"]}
    )
    # Configure remote
    client.post(
        f"/api/projects/{project.id}/git/remote",
        json={"name": "origin", "url": "https://github.com/mock-org/mock-repo.git"}
    )

    # Push must be blocked by verification gate
    push_res = client.post(f"/api/projects/{project.id}/git/push")
    assert push_res.status_code == 400
    assert "Publishing blocked" in push_res.json()["detail"]
