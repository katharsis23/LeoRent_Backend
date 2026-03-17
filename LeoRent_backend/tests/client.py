from fastapi.testclient import TestClient
from src.leorent_backend.main import app


client = TestClient(app)
