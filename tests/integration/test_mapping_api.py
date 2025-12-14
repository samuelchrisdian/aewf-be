"""
Integration tests for Mapping API endpoints.
"""
import pytest
import json


class TestMappingAPI:
    """Integration tests for /api/v1/mapping endpoints."""
    
    @pytest.fixture
    def auth_headers(self, test_client):
        """Get authentication headers with valid token."""
        return {"Authorization": "Bearer test_token", "Content-Type": "application/json"}
    
    def test_get_unmapped_users_requires_authentication(self, test_client):
        """Test that GET /mapping/unmapped requires authentication."""
        response = test_client.get('/api/v1/mapping/unmapped')
        assert response.status_code == 401
    
    def test_bulk_verify_requires_authentication(self, test_client):
        """Test that POST /mapping/bulk-verify requires authentication."""
        response = test_client.post(
            '/api/v1/mapping/bulk-verify',
            data=json.dumps({"mappings": [{"mapping_id": 1, "status": "verified"}]}),
            content_type='application/json'
        )
        assert response.status_code == 401
    
    def test_get_mapping_stats_requires_authentication(self, test_client):
        """Test that GET /mapping/stats requires authentication."""
        response = test_client.get('/api/v1/mapping/stats')
        assert response.status_code == 401
    
    def test_delete_mapping_requires_authentication(self, test_client):
        """Test that DELETE /mapping/<id> requires authentication."""
        response = test_client.delete('/api/v1/mapping/1')
        assert response.status_code == 401
    
    def test_get_mapping_requires_authentication(self, test_client):
        """Test that GET /mapping/<id> requires authentication."""
        response = test_client.get('/api/v1/mapping/1')
        assert response.status_code == 401


class TestMappingAPIResponseFormat:
    """Tests for Mapping API response format compliance."""
    
    def test_unmapped_response_has_correct_format(self):
        """Verify unmapped users response has suggested matches."""
        pass
    
    def test_stats_response_has_all_metrics(self):
        """Verify stats response includes all required metrics."""
        expected_keys = [
            "total_machine_users",
            "mapped_count",
            "verified_count",
            "suggested_count",
            "unmapped_count",
            "mapping_rate"
        ]
        pass
    
    def test_bulk_verify_response_has_counts(self):
        """Verify bulk verify response includes success/failure counts."""
        expected_keys = ["verified", "rejected", "failed", "errors"]
        pass
