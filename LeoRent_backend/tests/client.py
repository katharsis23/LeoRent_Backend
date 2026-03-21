from fastapi.testclient import TestClient
from src.leorent_backend.main import app


client = TestClient(app)


# TODO: Add cleanup function to delete test data after tests
