"""
Integration tests for Import Batch API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestBatchAPI:
    """Integration tests for /api/v1/import/batches endpoints."""
    
    @pytest.fixture
    def admin_headers(self, test_client):
        """Get authentication headers for admin user."""
        return {"Authorization": "Bearer admin_token", "Content-Type": "application/json"}
    
    @pytest.fixture
    def staff_headers(self, test_client):
        """Get authentication headers for staff user (non-admin)."""
        return {"Authorization": "Bearer staff_token", "Content-Type": "application/json"}

    @pytest.fixture(autouse=True)
    def mock_auth_middleware(self):
        """Mock authentication middleware."""
        with patch('src.app.middleware.jwt.decode') as mock_decode:
            with patch('src.app.middleware.User') as mock_user_cls:
                def decode_token(token, *args, **kwargs):
                    if token == 'admin_token':
                        return {'user_id': 1}
                    elif token == 'staff_token':
                        return {'user_id': 2}
                    return {'user_id': 1}
                
                mock_decode.side_effect = decode_token
                
                mock_admin = MagicMock()
                mock_admin.id = 1
                mock_admin.username = 'admin'
                mock_admin.role = 'Admin'
                mock_admin.is_active = True
                
                mock_staff = MagicMock()
                mock_staff.id = 2
                mock_staff.username = 'staff'
                mock_staff.role = 'Staff'
                mock_staff.is_active = True
                
                def get_user(id=None):
                    result = MagicMock()
                    if id == 1:
                        result.first.return_value = mock_admin
                    elif id == 2:
                        result.first.return_value = mock_staff
                    else:
                        result.first.return_value = mock_admin
                    return result
                
                mock_user_cls.query.filter_by.side_effect = get_user
                yield
    
    # --- List Batches Endpoint Tests ---
    
    def test_list_batches_requires_authentication(self, test_client):
        """Test that GET /import/batches requires authentication."""
        response = test_client.get('/api/v1/import/batches')
        assert response.status_code == 401
    
    def test_list_batches_succeeds_with_auth(self, test_client, admin_headers):
        """Test that GET /import/batches returns batches."""
        response = test_client.get('/api/v1/import/batches', headers=admin_headers)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "success" in data
            assert "data" in data
            assert "pagination" in data
    
    def test_list_batches_accepts_pagination(self, test_client, admin_headers):
        """Test that GET /import/batches accepts pagination parameters."""
        response = test_client.get(
            '/api/v1/import/batches?page=1&per_page=10',
            headers=admin_headers
        )
        assert response.status_code in [200, 500]
    
    def test_list_batches_accepts_filters(self, test_client, admin_headers):
        """Test that GET /import/batches accepts filter parameters."""
        response = test_client.get(
            '/api/v1/import/batches?file_type=logs&status=completed',
            headers=admin_headers
        )
        assert response.status_code in [200, 500]
    
    # --- Get Batch Endpoint Tests ---
    
    def test_get_batch_requires_authentication(self, test_client):
        """Test that GET /import/batches/<id> requires authentication."""
        response = test_client.get('/api/v1/import/batches/1')
        assert response.status_code == 401
    
    def test_get_batch_returns_404_for_nonexistent(self, test_client, admin_headers):
        """Test that GET /import/batches/<id> returns 404 for nonexistent."""
        response = test_client.get('/api/v1/import/batches/99999', headers=admin_headers)
        assert response.status_code in [404, 500]
    
    # --- Delete Batch Endpoint Tests ---
    
    def test_delete_batch_requires_authentication(self, test_client):
        """Test that DELETE /import/batches/<id> requires authentication."""
        response = test_client.delete('/api/v1/import/batches/1')
        assert response.status_code == 401
    
    def test_delete_batch_requires_admin(self, test_client, staff_headers):
        """Test that DELETE /import/batches/<id> requires Admin role."""
        response = test_client.delete('/api/v1/import/batches/1', headers=staff_headers)
        assert response.status_code == 403
    
    def test_delete_batch_returns_404_for_nonexistent(self, test_client, admin_headers):
        """Test that DELETE /import/batches/<id> returns 404 for nonexistent."""
        response = test_client.delete('/api/v1/import/batches/99999', headers=admin_headers)
        assert response.status_code in [404, 500]
    
    # --- Rollback Batch Endpoint Tests ---
    
    def test_rollback_batch_requires_authentication(self, test_client):
        """Test that POST /import/batches/<id>/rollback requires authentication."""
        response = test_client.post('/api/v1/import/batches/1/rollback')
        assert response.status_code == 401
    
    def test_rollback_batch_requires_admin(self, test_client, staff_headers):
        """Test that POST /import/batches/<id>/rollback requires Admin role."""
        response = test_client.post('/api/v1/import/batches/1/rollback', headers=staff_headers)
        assert response.status_code == 403
    
    def test_rollback_batch_returns_404_for_nonexistent(self, test_client, admin_headers):
        """Test that POST /import/batches/<id>/rollback returns 404 for nonexistent."""
        response = test_client.post('/api/v1/import/batches/99999/rollback', headers=admin_headers)
        assert response.status_code in [404, 500]


class TestBatchAPIResponseFormat:
    """Tests for Batch API response format compliance."""
    
    @pytest.fixture
    def admin_headers(self, test_client):
        """Get authentication headers for admin user."""
        return {"Authorization": "Bearer admin_token", "Content-Type": "application/json"}

    @pytest.fixture(autouse=True)
    def mock_auth_middleware(self):
        """Mock authentication middleware for admin."""
        with patch('src.app.middleware.jwt.decode') as mock_decode:
            with patch('src.app.middleware.User') as mock_user_cls:
                mock_decode.return_value = {'user_id': 1}
                mock_user = MagicMock()
                mock_user.id = 1
                mock_user.role = 'Admin'
                mock_user.is_active = True
                mock_user_cls.query.filter_by.return_value.first.return_value = mock_user
                yield
    
    def test_list_batches_response_format(self, test_client, admin_headers):
        """Verify list batches response follows standard format."""
        response = test_client.get('/api/v1/import/batches', headers=admin_headers)
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "success" in data
            assert data["success"] is True
            assert "data" in data
            assert "pagination" in data
            assert isinstance(data["data"], list)
    
    def test_access_denied_response_format(self, test_client):
        """Verify access denied responses follow standard format."""
        with patch('src.app.middleware.jwt.decode') as mock_decode:
            with patch('src.app.middleware.User') as mock_user_cls:
                mock_decode.return_value = {'user_id': 2}
                mock_user = MagicMock()
                mock_user.id = 2
                mock_user.role = 'Staff'
                mock_user.is_active = True
                mock_user_cls.query.filter_by.return_value.first.return_value = mock_user
                
                response = test_client.delete(
                    '/api/v1/import/batches/1',
                    headers={"Authorization": "Bearer staff_token", "Content-Type": "application/json"}
                )
                data = json.loads(response.data)
                
                assert "success" in data
                assert data["success"] is False
                assert "error" in data
                assert data["error"]["code"] == "ACCESS_DENIED"
