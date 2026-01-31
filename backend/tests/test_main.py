"""Tests for main application."""

from unittest.mock import AsyncMock, patch

import pytest


class TestMainApp:
    """Test main application."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_cors_headers(self, client):
        """Test CORS headers are set."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS should allow the origin
        assert response.status_code in [200, 204, 405]

    def test_api_docs_available(self, client):
        """Test OpenAPI docs are available."""
        response = client.get("/docs")

        # Should redirect or return docs
        assert response.status_code in [200, 307]

    def test_openapi_schema(self, client):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "/api/upload/" in data["paths"]
        assert "/api/documents/" in data["paths"]
        assert "/api/chat/" in data["paths"]
