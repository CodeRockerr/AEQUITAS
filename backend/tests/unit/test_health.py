"""
AEQUITAS — Unit tests for the health endpoints.

Test naming convention: test_<what>_<expected_outcome>
e.g. test_health_returns_ok_status

Each test should:
  1. Arrange: set up any data/state needed
  2. Act:     call the thing being tested
  3. Assert:  verify the outcome

This is called the AAA pattern and is the standard in industry.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_returns_200(client: TestClient) -> None:
    """GET /health should return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


@pytest.mark.unit
def test_health_returns_ok_status(client: TestClient) -> None:
    """GET /health body should contain status: ok."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.unit
def test_health_returns_expected_fields(client: TestClient) -> None:
    """GET /health body should contain all required fields."""
    response = client.get("/health")
    data = response.json()

    # Every field in HealthResponse must be present
    assert "status" in data
    assert "env" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data


@pytest.mark.unit
def test_health_uptime_is_positive(client: TestClient) -> None:
    """Uptime should always be a positive number."""
    response = client.get("/health")
    data = response.json()
    assert data["uptime_seconds"] >= 0


@pytest.mark.unit
def test_health_ready_returns_200(client: TestClient) -> None:
    """GET /health/ready should return HTTP 200."""
    response = client.get("/health/ready")
    assert response.status_code == 200


@pytest.mark.unit
def test_health_ready_returns_ready_status(client: TestClient) -> None:
    """GET /health/ready should report all checks as ok."""
    response = client.get("/health/ready")
    data = response.json()

    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.unit
def test_docs_available_in_development(client: TestClient) -> None:
    """Swagger /docs should be accessible in development mode."""
    response = client.get("/docs")
    assert response.status_code == 200
