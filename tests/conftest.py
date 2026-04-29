"""Pytest configuration and fixtures"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_url():
    """Sample URL for testing"""
    return "https://example.com"


@pytest.fixture
def verify_request_data():
    """Sample verification request data"""
    return {
        "url": "https://example.com/article",
        "options": {
            "async_mode": False,
            "timeout_seconds": 60,
        }
    }
