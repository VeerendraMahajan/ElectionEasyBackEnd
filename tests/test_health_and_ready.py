import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Verify /health returns 200 OK and application metadata."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_ready_check_endpoint(client: AsyncClient):
    """Verify /ready probe responds with service status."""
    response = await client.get("/ready")
    # Response code depends on database engine state
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "database" in data
    # Sensitive connection strings or internal errors must NEVER be leaked in JSON
    assert "password" not in str(data).lower()
    assert "secret" not in str(data).lower()
