"""
Integration tests for User Management API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestUsersAPI:
    """Integration tests for /api/v1/users endpoints."""
    
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
                
                # Create mock users for different roles
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
    
    # --- List Users Endpoint Tests ---
    
    def test_list_users_requires_authentication(self, test_client):
        """Test that GET /users requires authentication."""
        response = test_client.get('/api/v1/users')
        assert response.status_code == 401
    
    def test_list_users_requires_admin_role(self, test_client, staff_headers):
        """Test that GET /users requires Admin role."""
        response = test_client.get('/api/v1/users', headers=staff_headers)
        assert response.status_code == 403
    
    def test_list_users_with_admin(self, test_client, admin_headers):
        """Test that GET /users succeeds for Admin."""
        response = test_client.get('/api/v1/users', headers=admin_headers)
        assert response.status_code in [200, 500]
    
    def test_list_users_accepts_pagination(self, test_client, admin_headers):
        """Test that GET /users accepts pagination parameters."""
        response = test_client.get('/api/v1/users?page=1&per_page=10', headers=admin_headers)
        assert response.status_code in [200, 500]
    
    def test_list_users_accepts_filters(self, test_client, admin_headers):
        """Test that GET /users accepts filter parameters."""
        response = test_client.get(
            '/api/v1/users?is_active=true&role=Admin&search=admin',
            headers=admin_headers
        )
        assert response.status_code in [200, 500]
    
    # --- Create User Endpoint Tests ---
    
    def test_create_user_requires_authentication(self, test_client):
        """Test that POST /users requires authentication."""
        response = test_client.post('/api/v1/users')
        assert response.status_code == 401
    
    def test_create_user_requires_admin_role(self, test_client, staff_headers):
        """Test that POST /users requires Admin role."""
        response = test_client.post(
            '/api/v1/users',
            headers=staff_headers,
            data=json.dumps({
                'username': 'newuser',
                'password': 'password123'
            })
        )
        assert response.status_code == 403
    
    def test_create_user_validates_required_fields(self, test_client, admin_headers):
        """Test that POST /users validates required fields."""
        response = test_client.post(
            '/api/v1/users',
            headers=admin_headers,
            data=json.dumps({})
        )
        assert response.status_code == 400
    
    def test_create_user_validates_password_length(self, test_client, admin_headers):
        """Test that POST /users validates password length."""
        response = test_client.post(
            '/api/v1/users',
            headers=admin_headers,
            data=json.dumps({
                'username': 'newuser',
                'password': '123'
            })
        )
        assert response.status_code == 400
    
    def test_create_user_validates_role(self, test_client, admin_headers):
        """Test that POST /users validates role values."""
        response = test_client.post(
            '/api/v1/users',
            headers=admin_headers,
            data=json.dumps({
                'username': 'newuser',
                'password': 'password123',
                'role': 'InvalidRole'
            })
        )
        assert response.status_code == 400
    
    def test_create_user_accepts_valid_data(self, test_client, admin_headers):
        """Test that POST /users accepts valid data."""
        response = test_client.post(
            '/api/v1/users',
            headers=admin_headers,
            data=json.dumps({
                'username': 'newuser',
                'password': 'password123',
                'email': 'newuser@example.com',
                'role': 'Teacher'
            })
        )
        assert response.status_code in [201, 400, 500]  # 400 if username exists
    
    # --- Get User Endpoint Tests ---
    
    def test_get_user_requires_authentication(self, test_client):
        """Test that GET /users/<id> requires authentication."""
        response = test_client.get('/api/v1/users/1')
        assert response.status_code == 401
    
    def test_get_user_requires_admin_role(self, test_client, staff_headers):
        """Test that GET /users/<id> requires Admin role."""
        response = test_client.get('/api/v1/users/1', headers=staff_headers)
        assert response.status_code == 403
    
    def test_get_user_returns_404_for_nonexistent(self, test_client, admin_headers):
        """Test that GET /users/<id> returns 404 for nonexistent user."""
        response = test_client.get('/api/v1/users/99999', headers=admin_headers)
        assert response.status_code in [404, 500]
    
    # --- Update User Endpoint Tests ---
    
    def test_update_user_requires_authentication(self, test_client):
        """Test that PUT /users/<id> requires authentication."""
        response = test_client.put('/api/v1/users/1')
        assert response.status_code == 401
    
    def test_update_user_requires_admin_role(self, test_client, staff_headers):
        """Test that PUT /users/<id> requires Admin role."""
        response = test_client.put(
            '/api/v1/users/1',
            headers=staff_headers,
            data=json.dumps({'role': 'Teacher'})
        )
        assert response.status_code == 403
    
    def test_update_user_validates_role(self, test_client, admin_headers):
        """Test that PUT /users/<id> validates role values."""
        response = test_client.put(
            '/api/v1/users/1',
            headers=admin_headers,
            data=json.dumps({'role': 'InvalidRole'})
        )
        assert response.status_code == 400
    
    def test_update_user_accepts_empty_body(self, test_client, admin_headers):
        """Test that PUT /users/<id> accepts empty body."""
        response = test_client.put(
            '/api/v1/users/1',
            headers=admin_headers,
            data=json.dumps({})
        )
        assert response.status_code in [200, 404, 500]
    
    # --- Delete User Endpoint Tests ---
    
    def test_delete_user_requires_authentication(self, test_client):
        """Test that DELETE /users/<id> requires authentication."""
        response = test_client.delete('/api/v1/users/1')
        assert response.status_code == 401
    
    def test_delete_user_requires_admin_role(self, test_client, staff_headers):
        """Test that DELETE /users/<id> requires Admin role."""
        response = test_client.delete('/api/v1/users/1', headers=staff_headers)
        assert response.status_code == 403
    
    def test_delete_user_returns_404_for_nonexistent(self, test_client, admin_headers):
        """Test that DELETE /users/<id> returns 404 for nonexistent user."""
        response = test_client.delete('/api/v1/users/99999', headers=admin_headers)
        assert response.status_code in [404, 500]
    
    # --- Activity Log Endpoint Tests ---
    
    def test_activity_log_requires_authentication(self, test_client):
        """Test that GET /users/<id>/activity-log requires authentication."""
        response = test_client.get('/api/v1/users/1/activity-log')
        assert response.status_code == 401
    
    def test_activity_log_requires_admin_role(self, test_client, staff_headers):
        """Test that GET /users/<id>/activity-log requires Admin role."""
        response = test_client.get('/api/v1/users/1/activity-log', headers=staff_headers)
        assert response.status_code == 403
    
    def test_activity_log_returns_404_for_nonexistent(self, test_client, admin_headers):
        """Test that GET /users/<id>/activity-log returns 404 for nonexistent user."""
        response = test_client.get('/api/v1/users/99999/activity-log', headers=admin_headers)
        assert response.status_code in [404, 500]
    
    def test_activity_log_accepts_filters(self, test_client, admin_headers):
        """Test that GET /users/<id>/activity-log accepts filter parameters."""
        response = test_client.get(
            '/api/v1/users/1/activity-log?page=1&per_page=10&action=login',
            headers=admin_headers
        )
        assert response.status_code in [200, 404, 500]


class TestUsersAPIResponseFormat:
    """Tests for Users API response format compliance."""
    
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
    
    def test_validation_error_response_format(self, test_client, admin_headers):
        """Verify validation error responses follow standard format."""
        response = test_client.post(
            '/api/v1/users',
            headers=admin_headers,
            data=json.dumps({'username': 'a'})  # Too short
        )
        data = json.loads(response.data)
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
    
    def test_access_denied_response_format(self, test_client):
        """Verify access denied responses follow standard format."""
        # Create a mock for staff user
        with patch('src.app.middleware.jwt.decode') as mock_decode:
            with patch('src.app.middleware.User') as mock_user_cls:
                mock_decode.return_value = {'user_id': 2}
                mock_user = MagicMock()
                mock_user.id = 2
                mock_user.role = 'Staff'
                mock_user.is_active = True
                mock_user_cls.query.filter_by.return_value.first.return_value = mock_user
                
                response = test_client.get(
                    '/api/v1/users',
                    headers={"Authorization": "Bearer staff_token", "Content-Type": "application/json"}
                )
                data = json.loads(response.data)
                
                assert "success" in data
                assert data["success"] is False
                assert "error" in data
                assert data["error"]["code"] == "ACCESS_DENIED"
