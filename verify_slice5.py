"""
ROGERS Slice 5 Verification Script: Mission Control & End-to-End Delivery
Verifies:
1. End-to-end integration: Inception -> Blueprint -> Scaffolding -> Task Implementation -> Test Verification -> Secure Packaging -> Download -> Final Mission Report.
2. Packaging verification gates: Strictly blocks unverified or failed projects.
3. Secret and artifact sanitization: Excludes .env secrets, .git, .venv, .rogers, and caches.
4. Embedded verification report: Injects VERIFICATION_REPORT.md into root of delivery archive.
5. Cryptographic artifact integrity: Computes and validates SHA-256 checksum.
6. Package streaming download endpoint.
7. Truthful Final Mission Report generation.
"""
import sys
import zipfile
import hashlib
from pathlib import Path
import httpx

BASE_URL = "http://127.0.0.1:8000"


def get_client():
    try:
        r = httpx.get(f"{BASE_URL}/api/health", timeout=1.0)
        if r.status_code == 200:
            print("[INFO] Testing against running live server at http://127.0.0.1:8000")
            return httpx.Client(base_url=BASE_URL, timeout=40.0)
    except Exception:
        pass

    print("[INFO] Live server not detected; using FastAPI TestClient in-memory runner.")
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)


def verify_slice5():
    client = get_client()

    print("\n========================================================")
    print(" ROGERS SLICE 5 -- MISSION CONTROL & DELIVERY VERIFICATION")
    print("========================================================")

    # --- 1. Testing API Health ---
    print("\n--- 1. Testing API Health ---")
    health = client.get("/api/health")
    assert health.status_code == 200, f"Health check failed: {health.text}"
    health_data = health.json()
    print(f"[OK] Health: {health_data['service']} ({health_data['version']})")

    # --- 2. Project Creation & Blueprint ---
    print("\n--- 2. Project Creation & Blueprint ---")
    create_res = client.post(
        "/api/projects",
        json={
            "name": "Shield Tactical Command Platform",
            "idea": "An enterprise mission control platform with distributed telemetry ingest, automated self-healing diagnostics, and verifiable delivery packaging."
        }
    )
    assert create_res.status_code == 201, f"Failed to create project: {create_res.text}"
    project = create_res.json()
    project_id = project["id"]
    print(f"[OK] Project created: ID={project_id}, Name='{project['name']}'")

    bp_res = client.post(f"/api/projects/{project_id}/blueprint")
    assert bp_res.status_code == 200
    blueprint = bp_res.json()["blueprint"]
    tasks = blueprint["development_tasks"]
    print(f"[OK] Blueprint ready with {len(tasks)} tasks.")

    # --- 3. Scaffolding Generation ---
    print("\n--- 3. Scaffolding Generation ---")
    scaffold_res = client.post(f"/api/projects/{project_id}/scaffold")
    assert scaffold_res.status_code == 200, f"Scaffold failed: {scaffold_res.text}"
    scaffold_data = scaffold_res.json()
    project_dir = Path(scaffold_data["project_dir"])
    print(f"[OK] Project scaffolded at: {project_dir} ({len(scaffold_data['files_created'])} files)")

    # --- 4. Packaging Gate: Verify Blocking on Unverified Project ---
    print("\n--- 4. Packaging Gate: Verifying Unverified Project is Blocked ---")
    early_pkg_res = client.post(f"/api/projects/{project_id}/package")
    assert early_pkg_res.status_code == 400, "Packaging should have been blocked for unverified project!"
    print(f"[OK] Packaging gate enforced: {early_pkg_res.json()['detail']}")

    # --- 5. Implement & Verify Task ---
    print("\n--- 5. Task Implementation & Test Verification ---")
    target_task = tasks[0]
    task_id = target_task["id"]
    print(f"[INFO] Implementing task: '{target_task['title']}' ({task_id})")

    impl_res = client.post(f"/api/projects/{project_id}/tasks/{task_id}/implement")
    assert impl_res.status_code == 200, f"Implementation failed: {impl_res.text}"
    impl_data = impl_res.json()

    assert impl_data["status"] == "success"
    assert impl_data["verified"] is True
    print(f"[OK] Task implementation status: {impl_data['status']}")
    print(f"[OK] Task automated test verification: {impl_data['verified']}")
    print(f"[OK] Tests passed: {impl_data['test_result']['tests_passed']}/{impl_data['test_result']['tests_total']}")

    # Confirm updated project task status in blueprint
    refreshed_project = client.get(f"/api/projects/{project_id}").json()
    refreshed_tasks = refreshed_project["blueprint"]["development_tasks"]
    assert refreshed_tasks[0]["status"] == "verified"
    print(f"[OK] Project blueprint task status transitioned to 'verified'")

    # --- 6. Infiltrate Simulated Secrets and Caches to Test Sanitization ---
    print("\n--- 6. Injecting Simulated Secrets and Caches to Test Sanitization ---")
    # Secret .env
    (project_dir / ".env").write_text("DATABASE_PASSWORD=classified_production_root_password_12345", encoding="utf-8")
    # Virtual environment
    (project_dir / ".venv").mkdir(exist_ok=True)
    (project_dir / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin/python", encoding="utf-8")
    # Git directory
    (project_dir / ".git").mkdir(exist_ok=True)
    (project_dir / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
    # Pycache
    (project_dir / "backend" / "__pycache__").mkdir(exist_ok=True)
    (project_dir / "backend" / "__pycache__" / "temp.cpython-311.pyc").write_bytes(b"PYC")
    print("[OK] Simulated .env, .venv, .git, and __pycache__ injected into project root.")

    # --- 7. Secure Packaging Execution ---
    print("\n--- 7. Secure Packaging Execution ---")
    pkg_res = client.post(f"/api/projects/{project_id}/package")
    assert pkg_res.status_code == 200, f"Packaging failed: {pkg_res.text}"
    pkg_meta = pkg_res.json()

    print(f"[OK] Package filename: {pkg_meta['package_filename']}")
    print(f"[OK] Package size: {pkg_meta['package_size_bytes']} bytes ({(pkg_meta['package_size_bytes'] / 1024):.1f} KB)")
    print(f"[OK] Files included: {pkg_meta['files_count']}")
    print(f"[OK] SHA-256 Checksum: {pkg_meta['sha256_checksum']}")
    print(f"[OK] Verification Status: {pkg_meta['verification_status']}")

    pkg_file = Path(pkg_meta["package_path"])
    assert pkg_file.exists(), "Package archive file does not exist on disk!"

    # Verify SHA-256 integrity
    hasher = hashlib.sha256()
    with open(pkg_file, "rb") as f:
        hasher.update(f.read())
    assert hasher.hexdigest() == pkg_meta["sha256_checksum"]
    print("[OK] Cryptographic SHA-256 checksum verified against physical archive.")

    # --- 8. Archive Inspection & Secret Exclusion ---
    print("\n--- 8. Inspecting Archive Contents & Exclusion Defense ---")
    with zipfile.ZipFile(pkg_file, "r") as zf:
        namelist = zf.namelist()

        # Report check
        assert "VERIFICATION_REPORT.md" in namelist, "VERIFICATION_REPORT.md must be included in archive root!"
        report_content = zf.read("VERIFICATION_REPORT.md").decode("utf-8")
        assert "ROGERS MISSION VERIFICATION REPORT" in report_content
        assert "DEFENSE ARCHITECTURE & SECURITY AUDIT" in report_content
        print("[OK] Embedded VERIFICATION_REPORT.md verified in archive root.")

        # Preserved templates
        assert ".env.example" in namelist
        assert "README.md" in namelist
        assert "backend/requirements.txt" in namelist
        print("[OK] Project structure and templates (.env.example, README.md) preserved.")

        # Sanitization check
        assert ".env" not in namelist, "CRITICAL LEAK: .env secret found in delivery package!"
        assert not any(n.startswith(".git") for n in namelist), "CRITICAL LEAK: .git metadata found in delivery package!"
        assert not any(n.startswith(".venv") for n in namelist), "CRITICAL LEAK: .venv found in delivery package!"
        assert not any(n.startswith(".rogers") for n in namelist), "CRITICAL LEAK: .rogers snapshots found in delivery package!"
        assert not any("__pycache__" in n for n in namelist), "CRITICAL LEAK: __pycache__ found in delivery package!"
        assert not any(n.endswith(".pyc") for n in namelist), "CRITICAL LEAK: .pyc cache found in delivery package!"
        print("[OK] Zero secrets, zero virtual environments, zero git internals, zero caches in package.")

    # --- 9. Package Download Endpoint ---
    print("\n--- 9. Testing Package Streaming Download Endpoint ---")
    download_res = client.get(f"/api/projects/{project_id}/package/download")
    assert download_res.status_code == 200, f"Download failed: {download_res.text}"
    assert download_res.headers["content-type"] == "application/zip"
    assert len(download_res.content) == pkg_meta["package_size_bytes"]
    print(f"[OK] Package successfully streamed ({len(download_res.content)} bytes, content-type: {download_res.headers['content-type']})")

    # --- 10. Final Mission Report Telemetry ---
    print("\n--- 10. Testing Final Mission Report Telemetry ---")
    report_res = client.get(f"/api/projects/{project_id}/mission-report")
    assert report_res.status_code == 200, f"Mission report failed: {report_res.text}"
    report_data = report_res.json()

    assert report_data["project_id"] == project_id
    assert report_data["project_name"] == project["name"]
    assert report_data["tagline"] == "I CAN DO THIS ALL DAY."

    v_sum = report_data["verification_summary"]
    assert v_sum["status"] == "verified"
    assert v_sum["verified_tasks"] >= 1
    assert v_sum["pass_rate_percent"] == 100.0
    print(f"[OK] Mission report verification summary: {v_sum['verified_tasks']} task(s) verified, {v_sum['pass_rate_percent']}% pass rate")

    sec = report_data["security_audit"]
    assert sec["project_root_locked"] is True
    assert sec["path_traversal_blocked"] is True
    assert sec["git_access_blocked"] is True
    assert sec["snapshot_protection_active"] is True
    assert sec["shell_execution_blocked"] is True
    assert sec["write_target_validated"] is True
    print(f"[OK] Verifiable defense audit: All 6 security checks confirmed active.")

    assert report_data["package_metadata"] is not None
    assert report_data["package_metadata"]["sha256_checksum"] == pkg_meta["sha256_checksum"]
    print(f"[OK] Package metadata linked to mission report.")

    print("\n========================================================")
    print(" *** ALL SLICE 5 VERIFICATIONS PASSED SUCCESSFULLY! ***")
    print("========================================================\n")


if __name__ == "__main__":
    verify_slice5()
