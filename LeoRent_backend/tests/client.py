from fastapi.testclient import TestClient
from leorent_backend.main import app


client = TestClient(app)
