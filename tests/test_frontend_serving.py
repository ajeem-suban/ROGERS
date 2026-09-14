import pytest
from httpx import AsyncClient, ASGITransport
import importlib
import backend.app.main


@pytest.mark.asyncio
async def test_spa_and_static_serving():
    # Reload main module now that dist exists
    importlib.reload(backend.app.main)
    app = backend.app.main.app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Root SPA HTML
        res = await ac.get("/")
        assert res.status_code == 200
        assert "ROGERS — AI Project Orchestrator" in res.text
        assert "root" in res.text

        # 2. Health check still works
        health = await ac.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"
