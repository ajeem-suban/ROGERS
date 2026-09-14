import pytest
import os
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_multi_stage_progression_and_human_modification():
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
        project = create_res.json()
        project_id = project["id"]
        assert len(project["stages"]) == 5
        assert project["stages"]["research"]["status"] == "pending"

        # 2. Run Stage 1: Research
        s1_res = await ac.post(f"/api/projects/{project_id}/stages/research/run")
        assert s1_res.status_code == 200
        s1 = s1_res.json()
        assert s1["status"] == "waiting_approval"
        assert "summary" in s1["output"]

        # 3. Approve Stage 1
        appr1_res = await ac.post(f"/api/projects/{project_id}/stages/research/approve")
        assert appr1_res.status_code == 200
        assert appr1_res.json()["status"] == "approved"

        # 4. Run Stage 2: Requirements with user guidance
        s2_res = await ac.post(
            f"/api/projects/{project_id}/stages/requirements/run",
            json={"guidance": "Must support offline batch processing of 10,000 documents"}
        )
        assert s2_res.status_code == 200
        s2 = s2_res.json()
        assert any("offline batch processing" in r for r in s2["output"]["functional_requirements"])
        await ac.post(f"/api/projects/{project_id}/stages/requirements/approve")

        # 5. Run Stage 3: Tech Stack & Human Modification
        s_stack_res = await ac.post(f"/api/projects/{project_id}/stages/tech_stack/run")
        assert s_stack_res.status_code == 200

        # Human changes database to SQLite 3
        modify_res = await ac.post(
            f"/api/projects/{project_id}/stages/tech_stack/modify",
            json={
                "modifications": {
                    "database": "SQLite 3 with vector extension (Local Edge)",
                    "backend": "FastAPI + Python 3.12"
                }
            }
        )
        assert modify_res.status_code == 200
        assert modify_res.json()["status"] == "modified"
        assert modify_res.json()["output"]["database"] == "SQLite 3 with vector extension (Local Edge)"
        await ac.post(f"/api/projects/{project_id}/stages/tech_stack/approve")

        # 6. Run Stage 4: Architecture - Context propagation check!
        arch_res = await ac.post(f"/api/projects/{project_id}/stages/architecture/run")
        assert arch_res.status_code == 200
        arch_output = arch_res.json()["output"]
        # Downstream stage should reflect SQLite modification instead of PostgreSQL!
        assert "sqlite" in arch_output["description"].lower()
        await ac.post(f"/api/projects/{project_id}/stages/architecture/approve")

        # 7. Run Stage 5: Development
        dev_res = await ac.post(f"/api/projects/{project_id}/stages/development/run")
        assert dev_res.status_code == 200
        await ac.post(f"/api/projects/{project_id}/stages/development/approve")

        # 8. Check project completed and blueprint synced
        proj_res = await ac.get(f"/api/projects/{project_id}")
        assert proj_res.status_code == 200
        proj_data = proj_res.json()
        assert proj_data["status"] == "completed"
        assert proj_data["blueprint"] is not None
        assert "SQLite" in proj_data["blueprint"]["tech_stack"]["database"]


@pytest.mark.asyncio
async def test_scaffolding_generator_physical_files():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create and run-all
        create_res = await ac.post(
            "/api/projects",
            json={
                "name": "Fleet Route Optimization Platform",
                "idea": "Real-time GPS routing and battery optimization service for electric delivery vans."
            }
        )
        project_id = create_res.json()["id"]
        run_res = await ac.post(f"/api/projects/{project_id}/run-all")
        assert run_res.status_code == 200

        # Trigger scaffolding
        scaffold_res = await ac.post(f"/api/projects/{project_id}/scaffold")
        assert scaffold_res.status_code == 200
        scaffold_data = scaffold_res.json()
        
        project_dir = Path(scaffold_data["project_dir"])
        assert project_dir.exists()

        # Verify key physical files
        assert (project_dir / "README.md").exists()
        assert (project_dir / "docker-compose.yml").exists()
        assert (project_dir / "backend" / "app" / "main.py").exists()
        assert (project_dir / "backend" / "requirements.txt").exists()
        assert (project_dir / "frontend" / "package.json").exists()
        assert (project_dir / "docs" / "ARCHITECTURE.md").exists()
        assert (project_dir / "docs" / "BLUEPRINT.md").exists()

        # Read README.md content to verify domain-specific text
        content = (project_dir / "README.md").read_text(encoding="utf-8")
        assert "Fleet Route Optimization Platform" in content
