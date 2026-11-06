from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_document_upload_success():
    files = {"file": ("test_sample.pdf", b"%PDF-1.4 test document content", "application/pdf")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "uploaded"
    assert data["filename"] == "test_sample.pdf"
