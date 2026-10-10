import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.implementation.models import TestResult, FailureAnalysis
from backend.app.implementation.service import (
    validate_safe_path,
    run_safe_validation,
    run_safe_tests,
    create_snapshot_backup,
    restore_snapshot,
    TaskImplementationService,
    PathSecurityError,
    MAX_REPAIR_ATTEMPTS
)
from backend.app.providers.builtin_provider import BuiltinProvider


def test_sandbox_security_git_and_traversal_blocking(tmp_path):
    project_dir = tmp_path / "sandbox_test"
    project_dir.mkdir()

    # Normal valid path
    valid = validate_safe_path(project_dir, "backend/app/main.py")
    assert valid == (project_dir / "backend" / "app" / "main.py").resolve()

    # .git access blocked
    with pytest.raises(PathSecurityError, match=r"\.git access is prohibited"):
        validate_safe_path(project_dir, ".git/config")

    with pytest.raises(PathSecurityError, match=r"\.git access is prohibited"):
        validate_safe_path(project_dir, "backend/.git/HEAD")

    # Directory traversal blocked
    with pytest.raises(PathSecurityError, match=r"path traversal"):
        validate_safe_path(project_dir, "../outside.py")

    # Absolute path blocked
    with pytest.raises(PathSecurityError, match=r"absolute paths not permitted"):
        validate_safe_path(project_dir, "/etc/passwd")


def test_safe_test_runner_no_tests(tmp_path):
    empty_proj = tmp_path / "empty_proj"
    empty_proj.mkdir()
    res = run_safe_tests(empty_proj)
    assert res.status == "no_tests"
    assert res.tests_total == 0
    assert "No test files discovered" in res.stdout


def test_safe_test_runner_pass_and_fail(tmp_path):
    test_proj = tmp_path / "test_proj"
    backend_dir = test_proj / "backend"
    tests_dir = backend_dir / "tests"
    tests_dir.mkdir(parents=True)

    # Passing test
    (tests_dir / "test_pass.py").write_text("def test_ok(): assert 1 == 1\n", encoding="utf-8")
    res_pass = run_safe_tests(test_proj)
    assert res_pass.status == "passed"
    assert res_pass.tests_passed >= 1
    assert res_pass.exit_code == 0

    # Failing test
    (tests_dir / "test_fail.py").write_text("def test_bad(): assert 1 == 2\n", encoding="utf-8")
    res_fail = run_safe_tests(test_proj)
    assert res_fail.status == "failed"
    assert res_fail.tests_failed >= 1
    assert res_fail.exit_code != 0
    assert res_fail.failure_summary is not None


@pytest.mark.asyncio
async def test_failure_analysis_and_repair_provider():
    provider = BuiltinProvider()
    failing_output = "FAILED backend/tests/test_api.py::test_api_health - assert response.status_code == 200 (got 404)"
    relevant_files = {
        "backend/app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "backend/app/routes/health.py": "# health router\n"
    }

    # 1. Analyze failure
    analysis = await provider.analyze_failure(
        task_title="Add Health Check Endpoint",
        task_description="Implement health endpoint",
        test_output=failing_output,
        relevant_files=relevant_files
    )
    assert isinstance(analysis, FailureAnalysis)
    assert "404" in analysis.root_cause or "route" in analysis.root_cause.lower()
    assert analysis.confidence >= 0.8
    assert len(analysis.affected_files) > 0

    # 2. Generate repair
    repair = await provider.generate_repair(
        task_title="Add Health Check Endpoint",
        task_description="Implement health endpoint",
        failure_analysis=analysis,
        test_output=failing_output,
        relevant_files=relevant_files,
        attempt=1
    )
    assert len(repair.changes) > 0
    assert any("main" in c.path or "health" in c.path for c in repair.changes)


@pytest.mark.asyncio
async def test_end_to_end_slice4_verification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create project
        create_res = await ac.post(
            "/api/projects",
            json={
                "name": "Mission Defense Telemetry",
                "idea": "Tactical telemetry and diagnostic intelligence system for monitoring mission hardware."
            }
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # Run pipeline
        run_res = await ac.post(f"/api/projects/{project_id}/run-all")
        assert run_res.status_code == 200

        # Scaffold project (includes backend/tests starter test suite)
        scaffold_res = await ac.post(f"/api/projects/{project_id}/scaffold")
        assert scaffold_res.status_code == 200

        # Find task to implement
        proj_data = (await ac.get(f"/api/projects/{project_id}")).json()
        tasks = proj_data["blueprint"]["development_tasks"]
        target_task = tasks[0]
        task_id = target_task["id"]

        # Implement task with full test and verification loop
        impl_res = await ac.post(f"/api/projects/{project_id}/tasks/{task_id}/implement")
        assert impl_res.status_code == 200
        impl_data = impl_res.json()

        # Check Slice 4 enriched result
        assert impl_data["status"] == "success"
        assert impl_data["verified"] is True
        assert impl_data["test_result"] is not None
        assert impl_data["test_result"]["status"] == "passed"
        assert impl_data["test_result"]["tests_passed"] > 0
        assert len(impl_data["mission_logs"]) >= 5
        assert impl_data["security_checks"]["project_root_locked"] is True
        assert impl_data["security_checks"]["git_access_blocked"] is True

        # Verify task state in blueprint is verified
        proj_after = (await ac.get(f"/api/projects/{project_id}")).json()
        updated_task = next(t for t in proj_after["blueprint"]["development_tasks"] if t["id"] == task_id)
        assert updated_task["status"] == "verified"
