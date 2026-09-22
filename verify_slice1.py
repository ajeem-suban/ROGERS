import httpx
import json

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

def run_verification():
    client = get_client()

    print("\n--- 1. Testing Frontend SPA Serving ---")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "ROGERS — AI Project Orchestrator" in res.text
    print("[OK] Frontend SPA HTML returned successfully.")

    print("\n--- 2. Testing API Health ---")
    res = client.get("/api/health")
    assert res.status_code == 200
    print(f"[OK] Health response: {res.json()}")

    print("\n--- 3. Testing Project Creation: Tamil AI Document Intelligence ---")
    payload = {
        "name": "Tamil AI Document Intelligence",
        "idea": "Build an AI system that allows users to upload Tamil documents, extract text using OCR, search the documents using RAG, and ask questions about the uploaded content."
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    project = res.json()
    project_id = project["id"]
    print(f"[OK] Project created: ID={project_id}, Status={project['status']}")

    print("\n--- 4. Testing Blueprint Orchestration ---")
    res = client.post(f"/api/projects/{project_id}/blueprint")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    bp_data = res.json()
    blueprint = bp_data["blueprint"]
    print(f"[OK] Blueprint generated successfully. Status={bp_data['status']}")
    print("\n[SUMMARY]:")
    print(blueprint["summary"])
    print("\n[REQUIREMENTS]:")
    for r in blueprint["requirements"][:4]:
        print(f"  * {r}")
    print("\n[TECH STACK]:")
    for k, v in blueprint["tech_stack"].items():
        print(f"  * {k.capitalize()}: {v}")
    print("\n[ARCHITECTURE]:")
    print(f"  Description: {blueprint['architecture']['description']}")
    print(f"  Components: {', '.join(blueprint['architecture']['components'])}")
    print("\n[DEVELOPMENT TASKS]:")
    for t in blueprint["development_tasks"][:3]:
        print(f"  * [{t['priority'].upper()}] {t['title']}: {t['description']}")
    print("\n[NEXT STEPS]:")
    for s in blueprint["next_steps"][:3]:
        print(f"  * {s}")

    print("\n--- 5. Testing Project Retrieval ---")
    res = client.get(f"/api/projects/{project_id}")
    assert res.status_code == 200
    retrieved = res.json()
    assert retrieved["status"] == "completed"
    assert retrieved["blueprint"] is not None
    print(f"[OK] Verified project persistence and retrieval from storage.")

    print("\n--- 6. Testing Unrelated Domain Project: Fleet Route Optimization ---")
    unrelated_payload = {
        "name": "Fleet Route Optimization Platform",
        "idea": "Real-time GPS routing and battery optimization service for electric delivery vans."
    }
    res2 = client.post("/api/projects", json=unrelated_payload)
    assert res2.status_code == 201
    p2_id = res2.json()["id"]

    res_bp2 = client.post(f"/api/projects/{p2_id}/blueprint")
    assert res_bp2.status_code == 200
    bp2 = res_bp2.json()["blueprint"]
    print(f"[OK] Second project blueprint generated.")
    print(f"  Summary: {bp2['summary']}")
    print(f"  Frontend: {bp2['tech_stack']['frontend']}")
    print(f"  Backend: {bp2['tech_stack']['backend']}")
    print(f"  Database: {bp2['tech_stack']['database']}")
    print(f"  AI: {bp2['tech_stack']['ai']}")

    print("\n========================================================")
    print(" ALL VERIFICATION CHECKS PASSED FOR ROGERS SLICE 1! ")
    print("========================================================\n")

if __name__ == "__main__":
    run_verification()
