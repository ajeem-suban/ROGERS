from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_health():
    """Verify system health endpoint returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_api_info():
    """Verify info endpoint returns project identity."""
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Fleet Route Optimization Platform"
