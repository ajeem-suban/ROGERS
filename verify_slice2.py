import httpx
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def get_client():
    try:
        r = httpx.get(f"{BASE_URL}/api/health", timeout=1.0)
        if r.status_code == 200:
            print("[INFO] Testing against running live server at http://127.0.0.1:8000")
            return httpx.Client(base_url=BASE_URL, timeout=30.0)
    except Exception:
        pass
    print("[INFO] Live server not detected; using FastAPI TestClient in-memory runner.")
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)

def verify_slice2():
    client = get_client()

    print("\n--- 1. Testing API Health ---")
    health = client.get("/api/health")
    assert health.status_code == 200
    print(f"[OK] Health: {health.json()}")

    print("\n--- 2. Testing Project Creation with Multi-Stage Initialization ---")
    create_res = client.post(
        "/api/projects",
        json={
            "name": "Tamil AI Document Intelligence",
            "idea": "Build an AI system that allows users to upload Tamil documents, extract text using OCR, search the documents using RAG, and ask questions about the uploaded content."
        }
    )
    assert create_res.status_code == 201
    project = create_res.json()
    project_id = project["id"]
    assert len(project["stages"]) == 5
    print(f"[OK] Project created: ID={project_id}, Stages={list(project['stages'].keys())}")

    print("\n--- 3. Running Stage 1 (Research) & Human Approval ---")
    s1 = client.post(f"/api/projects/{project_id}/stages/research/run").json()
    assert s1["status"] == "waiting_approval"
    print(f"[OK] Research completed: {s1['output']['summary'][:80]}...")
    client.post(f"/api/projects/{project_id}/stages/research/approve")
    print("[OK] Stage 1 Approved.")

    print("\n--- 4. Running Stage 2 (Requirements) with User Guidance ---")
    s2 = client.post(
        f"/api/projects/{project_id}/stages/requirements/run",
        json={"guidance": "High security requirement: zero data retention on third-party servers"}
    ).json()
    assert s2["status"] == "waiting_approval"
    assert any("zero data retention" in r for r in s2["output"]["functional_requirements"])
    print(f"[OK] Requirements generated with custom guidance incorporated.")
    client.post(f"/api/projects/{project_id}/stages/requirements/approve")

    print("\n--- 5. Running Stage 3 (Tech Stack) & Submitting Human Modification ---")
    s3 = client.post(f"/api/projects/{project_id}/stages/tech_stack/run").json()
    # Modify database to SQLite Edge
    mod_res = client.post(
        f"/api/projects/{project_id}/stages/tech_stack/modify",
        json={
            "modifications": {
                "database": "SQLite 3 with vector extensions (Local Edge)",
                "backend": "FastAPI + Python 3.12"
            }
        }
    )
    assert mod_res.status_code == 200
    print("[OK] Tech Stack modified by human to SQLite Edge.")
    client.post(f"/api/projects/{project_id}/stages/tech_stack/approve")

    print("\n--- 6. Running Stage 4 (Architecture) - Context Propagation Check ---")
    s4 = client.post(f"/api/projects/{project_id}/stages/architecture/run").json()
    assert "sqlite" in s4["output"]["description"].lower()
    print("[OK] Downstream Architecture successfully reflects SQLite modification!")
    client.post(f"/api/projects/{project_id}/stages/architecture/approve")

    print("\n--- 7. Running Stage 5 (Development Roadmap) ---")
    s5 = client.post(f"/api/projects/{project_id}/stages/development/run").json()
    client.post(f"/api/projects/{project_id}/stages/development/approve")
    print("[OK] Development stage finished and approved.")

    print("\n--- 8. Verifying Final Blueprint Synchronization ---")
    fresh_proj = client.get(f"/api/projects/{project_id}").json()
    assert fresh_proj["status"] == "completed"
    assert fresh_proj["blueprint"] is not None
    assert "SQLite" in fresh_proj["blueprint"]["tech_stack"]["database"]
    print(f"[OK] Full blueprint assembled with: Database = {fresh_proj['blueprint']['tech_stack']['database']}")

    print("\n--- 9. Testing Physical Scaffolding Generation ---")
    scaffold_res = client.post(f"/api/projects/{project_id}/scaffold")
    assert scaffold_res.status_code == 200
    scaffold_data = scaffold_res.json()
    proj_dir = Path(scaffold_data["project_dir"])
    assert proj_dir.exists()
    assert (proj_dir / "README.md").exists()
    assert (proj_dir / "docker-compose.yml").exists()
    assert (proj_dir / "backend" / "app" / "main.py").exists()
    assert (proj_dir / "frontend" / "package.json").exists()
    assert (proj_dir / "docs" / "ARCHITECTURE.md").exists()
    print(f"[OK] Project scaffolding written to: {proj_dir}")
    print(f"[OK] Files generated: {len(scaffold_data['files_created'])} files.")

    print("\n========================================================")
    print(" ALL SLICE 2 VERIFICATIONS PASSED SUCCESSFULLY! ")
    print("========================================================\n")

if __name__ == "__main__":
    verify_slice2()
