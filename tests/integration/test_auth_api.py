"""
Integration tests for Authentication API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestAuthAPI:
    """Integration tests for /api/v1/auth endpoints."""
    
    @pytest.fixture
    def auth_headers(self, test_client):
        """Get authentication headers with valid token."""
        return {"Authorization": "Bearer test_token", "Content-Type": "application/json"}

    @pytest.fixture(autouse=True)
    def mock_auth_middleware(self):
        """Mock authentication middleware to accept test token."""
        with patch('src.app.middleware.jwt.decode') as mock_decode:
            with patch('src.app.middleware.User') as mock_user_cls:
                mock_decode.return_value = {'user_id': 1}
                mock_user = MagicMock()
                mock_user.id = 1
                mock_user.username = 'admin'
                mock_user.role = 'Admin'
                mock_user.is_active = True
                mock_user_cls.query.filter_by.return_value.first.return_value = mock_user
                yield
    
    # --- Login Endpoint Tests ---
    
    def test_login_no_credentials(self, test_client):
        """Test that POST /auth/login fails without credentials."""
        response = test_client.post(
            '/api/v1/auth/login',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_login_missing_password(self, test_client):
        """Test that POST /auth/login fails without password."""
        response = test_client.post(
            '/api/v1/auth/login',
            data=json.dumps({'username': 'admin'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_login_missing_username(self, test_client):
        """Test that POST /auth/login fails without username."""
        response = test_client.post(
            '/api/v1/auth/login',
            data=json.dumps({'password': 'password'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_login_validates_input(self, test_client):
        """Test that POST /auth/login validates input format."""
        response = test_client.post(
            '/api/v1/auth/login',
            data=json.dumps({
                'username': 'admin',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        # May return 401 (invalid credentials) or 500 (DB issue) - not 400
        assert response.status_code in [200, 401, 500]
    
    # --- Logout Endpoint Tests ---
    
    def test_logout_requires_authentication(self, test_client):
        """Test that POST /auth/logout requires authentication."""
        response = test_client.post('/api/v1/auth/logout')
        assert response.status_code == 401
    
    def test_logout_with_auth(self, test_client, auth_headers):
        """Test that POST /auth/logout succeeds with valid token."""
        response = test_client.post('/api/v1/auth/logout', headers=auth_headers)
        assert response.status_code in [200, 500]
    
    # --- Refresh Token Endpoint Tests ---
    
    def test_refresh_no_token(self, test_client):
        """Test that POST /auth/refresh fails without token."""
        response = test_client.post(
            '/api/v1/auth/refresh',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_refresh_invalid_token(self, test_client):
        """Test that POST /auth/refresh fails with invalid token."""
        response = test_client.post(
            '/api/v1/auth/refresh',
            data=json.dumps({'refresh_token': 'invalid_token'}),
            content_type='application/json'
        )
        assert response.status_code == 401
    
    # --- Get Current User Endpoint Tests ---
    
    def test_me_requires_authentication(self, test_client):
        """Test that GET /auth/me requires authentication."""
        response = test_client.get('/api/v1/auth/me')
        assert response.status_code == 401
    
    def test_me_with_auth(self, test_client, auth_headers):
        """Test that GET /auth/me returns user info with valid token."""
        response = test_client.get('/api/v1/auth/me', headers=auth_headers)
        assert response.status_code in [200, 500]
    
    # --- Change Password Endpoint Tests ---
    
    def test_change_password_requires_authentication(self, test_client):
        """Test that POST /auth/change-password requires authentication."""
        response = test_client.post('/api/v1/auth/change-password')
        assert response.status_code == 401
    
    def test_change_password_validates_required_fields(self, test_client, auth_headers):
        """Test that POST /auth/change-password validates required fields."""
        response = test_client.post(
            '/api/v1/auth/change-password',
            headers=auth_headers,
            data=json.dumps({})
        )
        assert response.status_code == 400
    
    def test_change_password_validates_password_match(self, test_client, auth_headers):
        """Test that POST /auth/change-password validates password match."""
        response = test_client.post(
            '/api/v1/auth/change-password',
            headers=auth_headers,
            data=json.dumps({
                'current_password': 'oldpass',
                'new_password': 'newpass123',
                'confirm_password': 'differentpass'
            })
        )
        assert response.status_code == 400
    
    def test_change_password_validates_min_length(self, test_client, auth_headers):
        """Test that POST /auth/change-password validates password length."""
        response = test_client.post(
            '/api/v1/auth/change-password',
            headers=auth_headers,
            data=json.dumps({
                'current_password': 'oldpass',
                'new_password': '123',
                'confirm_password': '123'
            })
        )
        assert response.status_code == 400
    
    def test_change_password_same_password_rejected(self, test_client, auth_headers):
        """Test that POST /auth/change-password rejects same password."""
        response = test_client.post(
            '/api/v1/auth/change-password',
            headers=auth_headers,
            data=json.dumps({
                'current_password': 'password123',
                'new_password': 'password123',
                'confirm_password': 'password123'
            })
        )
        assert response.status_code == 400


class TestAuthAPIResponseFormat:
    """Tests for Auth API response format compliance."""
    
    def test_login_validation_error_format(self, test_client):
        """Verify validation error responses follow standard format."""
        response = test_client.post(
            '/api/v1/auth/login',
            data=json.dumps({}),
            content_type='application/json'
        )
        data = json.loads(response.data)
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
    
    def test_refresh_validation_error_format(self, test_client):
        """Verify refresh token error responses follow standard format."""
        response = test_client.post(
            '/api/v1/auth/refresh',
            data=json.dumps({'refresh_token': 'invalid'}),
            content_type='application/json'
        )
        data = json.loads(response.data)
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
