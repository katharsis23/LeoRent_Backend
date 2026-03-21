import pytest
from fastapi.testclient import TestClient
from src.leorent_backend.main import app
from src.leorent_backend.database_connector import get_db, AsyncSessionLocal, engine
import asyncio


@pytest.fixture(scope="function")
def client():
    """Test client with overridden DB dependency."""
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    
    # Clear the engine pool to avoid loop mismatch in next test
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(engine.dispose())
        else:
            loop.run_until_complete(engine.dispose())
    except Exception:
        # Fallback for complex loop scenarios
        pass
