import os
import tempfile
import pytest
from app import app

@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test"
    import app as app_module
    app_module.DATABASE = db_path
    with app.test_client() as client:
        yield client
    os.unlink(db_path)

def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"MediTrack" in response.data

def test_add_and_list_medicine(client):
    response = client.post("/medicines/add", data={
        "name": "Paracetamol", "batch_number": "PCM-001",
        "category": "Tablet", "quantity": "50", "unit_price": "2.5",
        "expiry_date": "2030-12-31", "supplier": "ABC Pharma"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Paracetamol" in response.data

def test_health_endpoint(client):
    assert client.get("/health").json == {"status": "ok"}
