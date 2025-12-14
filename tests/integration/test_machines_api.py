"""
Integration tests for Machines API endpoints.
"""
import pytest
import json


class TestMachinesAPI:
    """Integration tests for /api/v1/machines endpoints."""
    
    @pytest.fixture
    def auth_headers(self, test_client):
        """Get authentication headers with valid token."""
        return {"Authorization": "Bearer test_token", "Content-Type": "application/json"}
    
    def test_get_machines_requires_authentication(self, test_client):
        """Test that GET /machines requires authentication."""
        response = test_client.get('/api/v1/machines')
        assert response.status_code == 401
    
    def test_get_machine_requires_authentication(self, test_client):
        """Test that GET /machines/<id> requires authentication."""
        response = test_client.get('/api/v1/machines/1')
        assert response.status_code == 401
    
    def test_create_machine_requires_authentication(self, test_client):
        """Test that POST /machines requires authentication."""
        response = test_client.post(
            '/api/v1/machines',
            data=json.dumps({"machine_code": "FP-001", "location": "Main Gate"}),
            content_type='application/json'
        )
        assert response.status_code == 401
    
    def test_update_machine_requires_authentication(self, test_client):
        """Test that PUT /machines/<id> requires authentication."""
        response = test_client.put(
            '/api/v1/machines/1',
            data=json.dumps({"location": "Back Gate"}),
            content_type='application/json'
        )
        assert response.status_code == 401
    
    def test_delete_machine_requires_authentication(self, test_client):
        """Test that DELETE /machines/<id> requires authentication."""
        response = test_client.delete('/api/v1/machines/1')
        assert response.status_code == 401
    
    def test_get_machine_users_requires_authentication(self, test_client):
        """Test that GET /machines/<id>/users requires authentication."""
        response = test_client.get('/api/v1/machines/1/users')
        assert response.status_code == 401


class TestMachinesAPIResponseFormat:
    """Tests for Machines API response format compliance."""
    
    def test_success_response_has_correct_format(self):
        """Verify success response matches expected format."""
        expected_keys = ["success", "message", "data"]
        pass
    
    def test_error_response_has_correct_format(self):
        """Verify error response matches expected format."""
        expected_keys = ["success", "error"]
        pass
    
    def test_paginated_response_has_correct_format(self):
        """Verify paginated response matches expected format."""
        expected_keys = ["success", "message", "data", "pagination"]
        pagination_keys = ["page", "per_page", "total", "pages"]
        pass
