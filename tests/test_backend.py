import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.storage import ProjectStorage


@pytest.fixture(autouse=True)
def clean_storage():
    # Setup / cleanup projects before tests
    yield


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_provider" in data


@pytest.mark.asyncio
async def test_create_project_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Empty name
        res = await ac.post("/api/projects", json={"name": "", "idea": "Some idea"})
        assert res.status_code == 422

        # Whitespace-only name
        res = await ac.post("/api/projects", json={"name": "   ", "idea": "Some idea"})
        assert res.status_code == 422

        # Empty idea
        res = await ac.post("/api/projects", json={"name": "Test Project", "idea": "   "})
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_complete_flow_tamil_ai_document_intelligence():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create project
        create_res = await ac.post(
            "/api/projects",
            json={
                "name": "Tamil AI Document Intelligence",
                "idea": "Build an AI system that allows users to upload Tamil documents, extract text using OCR, search the documents using RAG, and ask questions about the uploaded content."
            }
        )
        assert create_res.status_code == 201
        project_data = create_res.json()
        project_id = project_data["id"]
        assert project_data["name"] == "Tamil AI Document Intelligence"
        assert project_data["status"] == "created"

        # 2. Get project before blueprint
        get_res = await ac.get(f"/api/projects/{project_id}")
        assert get_res.status_code == 200
        assert get_res.json()["blueprint"] is None

        # 3. Generate blueprint
        bp_res = await ac.post(f"/api/projects/{project_id}/blueprint")
        assert bp_res.status_code == 200
        bp_data = bp_res.json()
        assert bp_data["project_id"] == project_id
        assert bp_data["status"] == "completed"

        blueprint = bp_data["blueprint"]
        # Verify structured blueprint fields
        assert "Tamil" in blueprint["summary"]
        assert len(blueprint["requirements"]) >= 3
        assert any("OCR" in req for req in blueprint["requirements"])
        assert any("RAG" in req or "vector" in req.lower() for req in blueprint["requirements"])

        # Tech stack
        assert "frontend" in blueprint["tech_stack"]
        assert "backend" in blueprint["tech_stack"]
        assert "database" in blueprint["tech_stack"]
        assert "ai" in blueprint["tech_stack"]
        assert "OCR" in blueprint["tech_stack"]["ai"] or "Tesseract" in blueprint["tech_stack"]["ai"]

        # Architecture
        assert len(blueprint["architecture"]["components"]) >= 3
        assert "description" in blueprint["architecture"]

        # Development tasks
        assert len(blueprint["development_tasks"]) >= 3
        for task in blueprint["development_tasks"]:
            assert "title" in task
            assert "description" in task
            assert task["priority"] in ["high", "medium", "low"]

        # Next steps
        assert len(blueprint["next_steps"]) >= 2

        # 4. Verify project persistence
        get_after = await ac.get(f"/api/projects/{project_id}")
        assert get_after.status_code == 200
        assert get_after.json()["status"] == "completed"
        assert get_after.json()["blueprint"] is not None


@pytest.mark.asyncio
async def test_unrelated_domain_fleet_optimization():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create unrelated project
        create_res = await ac.post(
            "/api/projects",
            json={
                "name": "Fleet Route Optimization Platform",
                "idea": "Real-time GPS routing and battery optimization service for electric delivery vans."
            }
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # Generate blueprint
        bp_res = await ac.post(f"/api/projects/{project_id}/blueprint")
        assert bp_res.status_code == 200
        bp = bp_res.json()["blueprint"]

        assert "fleet" in bp["summary"].lower() or "routing" in bp["summary"].lower()
        assert any("GPS" in req or "battery" in req.lower() or "telemetry" in req.lower() for req in bp["requirements"])
        assert len(bp["development_tasks"]) >= 3
