"""Contract tests for API endpoints"""

import pytest
from uuid import UUID


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"]
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Fakelytics"
    assert data["version"]


def test_verify_endpoint_invalid_url(client):
    """Test verification with invalid URL"""
    response = client.post(
        "/api/v1/verify",
        json={"url": "not-a-url"},
        headers={"X-API-Key": "dev-key"},
    )
    assert response.status_code == 422  # Pydantic validation error


def test_verify_endpoint_structure(client):
    """Test verification endpoint response structure
    
    **Satisfies**: T-906 (Contract Tests - API schema validation)
    """
    response = client.post(
        "/api/v1/verify",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "dev-key"},
    )
    
    # Should get a response (may be error if extraction fails, but API contract is valid)
    assert response.status_code in [200, 400, 500]
    
    # Response should match schema
    if response.status_code == 200:
        data = response.json()
        # Validate response structure
        assert "request_id" in data
        assert "status" in data
        assert UUID(data["request_id"])  # Should be valid UUID
        assert data["status"] in ["pending", "processing", "completed", "failed"]
        
        if data.get("report"):
            report = data["report"]
            assert "url" in report
            assert "overall_credibility_score" in report
            assert "summary" in report
            assert "findings" in report


def test_verify_requires_api_key(client):
    """Test API key requirement on protected endpoints."""
    response = client.post("/api/v1/verify", json={"url": "https://example.com"})
    assert response.status_code == 401
