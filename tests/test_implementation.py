import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.implementation.service import (
    validate_safe_path, 
    PathSecurityError, 
    create_snapshot_backup, 
    restore_snapshot,
    run_safe_validation
)


def test_path_security_sandbox(tmp_path):
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    # 1. Valid safe path
    safe_target = validate_safe_path(project_dir, "backend/app/routes/health.py")
    assert safe_target == (project_dir / "backend/app/routes/health.py").resolve()

    # 2. Reject absolute path
    with pytest.raises(PathSecurityError):
        validate_safe_path(project_dir, "C:/Windows/System32/calc.exe")

    with pytest.raises(PathSecurityError):
        validate_safe_path(project_dir, "/etc/passwd")

    # 3. Reject path traversal
    with pytest.raises(PathSecurityError):
        validate_safe_path(project_dir, "../outside.py")

    with pytest.raises(PathSecurityError):
        validate_safe_path(project_dir, "backend/../../outside.py")


def test_snapshot_backup_and_restore(tmp_path):
    project_dir = tmp_path / "project_alpha"
    project_dir.mkdir()

    test_file = project_dir / "app.py"
    test_file.write_text("original content", encoding="utf-8")

    # Backup
    snapshot_id = create_snapshot_backup(project_dir, ["app.py"])
    assert snapshot_id is not None
    assert (project_dir / ".rogers" / "snapshots" / snapshot_id / "app.py").exists()

    # Modify file
    test_file.write_text("corrupted content", encoding="utf-8")
    assert test_file.read_text(encoding="utf-8") == "corrupted content"

    # Restore
    restored = restore_snapshot(project_dir, snapshot_id)
    assert restored is True
    assert test_file.read_text(encoding="utf-8") == "original content"


def test_safe_validation_runner(tmp_path):
    project_dir = tmp_path / "val_project"
    backend_dir = project_dir / "backend"
    backend_dir.mkdir(parents=True)

    # Valid python
    (backend_dir / "valid.py").write_text("x = 10\nprint(x)", encoding="utf-8")
    res = run_safe_validation(project_dir)
    assert res.status == "passed"

    # Invalid syntax
    (backend_dir / "invalid.py").write_text("def broken(: x = 1", encoding="utf-8")
    res2 = run_safe_validation(project_dir)
    assert res2.status == "failed"


@pytest.mark.asyncio
async def test_end_to_end_task_implementation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create project
        create_res = await ac.post(
            "/api/projects",
            json={
                "name": "Health Probe Microservice",
                "idea": "A lightweight microservice providing system diagnostics and uptime health checks."
            }
        )
        assert create_res.status_code == 201
        project = create_res.json()
        project_id = project["id"]

        # 2. Run pipeline
        run_res = await ac.post(f"/api/projects/{project_id}/run-all")
        assert run_res.status_code == 200

        # 3. Scaffold project
        scaffold_res = await ac.post(f"/api/projects/{project_id}/scaffold")
        assert scaffold_res.status_code == 200

        # 4. Find task to implement
        fresh_proj = (await ac.get(f"/api/projects/{project_id}")).json()
        tasks = fresh_proj["blueprint"]["development_tasks"]
        assert len(tasks) > 0
        target_task = tasks[0]
        task_id = target_task["id"]

        # 5. Execute Task Implementation
        impl_res = await ac.post(f"/api/projects/{project_id}/tasks/{task_id}/implement")
        assert impl_res.status_code == 200
        impl_data = impl_res.json()

        assert impl_data["status"] == "success"
        assert impl_data["task_id"] == task_id
        assert len(impl_data["files_changed"]) > 0
        assert impl_data["validation"]["status"] == "passed"
        assert impl_data["snapshot_id"] is not None

        # 6. Verify task status updated in project storage
        proj_after = (await ac.get(f"/api/projects/{project_id}")).json()
        task_after = next(t for t in proj_after["blueprint"]["development_tasks"] if t["id"] == task_id)
        assert task_after["status"] == "completed"
        assert task_after["implementation_result"] is not None

        # 7. Test task restore endpoint
        restore_res = await ac.post(f"/api/projects/{project_id}/tasks/{task_id}/restore")
        assert restore_res.status_code == 200
        assert restore_res.json()["status"] == "restored"

        proj_restored = (await ac.get(f"/api/projects/{project_id}")).json()
        task_restored = next(t for t in proj_restored["blueprint"]["development_tasks"] if t["id"] == task_id)
        assert task_restored["status"] == "pending"
        assert task_restored["implementation_result"] is None
