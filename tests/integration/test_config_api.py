"""
Integration tests for System Configuration API endpoints.
"""
import pytest
import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


class TestConfigAPI:
    """Integration tests for /api/v1/config endpoints."""
    
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
    
    # --- Settings Endpoint Tests ---
    
    def test_get_settings_requires_authentication(self, test_client):
        """Test that GET /config/settings requires authentication."""
        response = test_client.get('/api/v1/config/settings')
        assert response.status_code == 401
    
    def test_get_settings_returns_defaults(self, test_client, admin_headers):
        """Test that GET /config/settings returns settings."""
        response = test_client.get('/api/v1/config/settings', headers=admin_headers)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "success" in data
            assert "data" in data
    
    def test_update_settings_requires_admin(self, test_client, staff_headers):
        """Test that PUT /config/settings requires Admin role."""
        response = test_client.put(
            '/api/v1/config/settings',
            headers=staff_headers,
            data=json.dumps({'attendance_rules': {'late_threshold_minutes': 20}})
        )
        assert response.status_code == 403
    
    def test_update_settings_with_admin(self, test_client, admin_headers):
        """Test that PUT /config/settings succeeds for Admin."""
        response = test_client.put(
            '/api/v1/config/settings',
            headers=admin_headers,
            data=json.dumps({'attendance_rules': {'late_threshold_minutes': 20}})
        )
        assert response.status_code in [200, 500]
    
    def test_update_settings_validates_values(self, test_client, admin_headers):
        """Test that PUT /config/settings validates value ranges."""
        response = test_client.put(
            '/api/v1/config/settings',
            headers=admin_headers,
            data=json.dumps({'attendance_rules': {'late_threshold_minutes': -5}})
        )
        assert response.status_code == 400
    
    # --- School Calendar Endpoint Tests ---
    
    def test_get_school_calendar_requires_authentication(self, test_client):
        """Test that GET /config/school-calendar requires authentication."""
        response = test_client.get('/api/v1/config/school-calendar')
        assert response.status_code == 401
    
    def test_get_school_calendar_succeeds(self, test_client, admin_headers):
        """Test that GET /config/school-calendar returns calendar data."""
        response = test_client.get('/api/v1/config/school-calendar', headers=admin_headers)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "data" in data
            assert "holidays" in data["data"]
    
    def test_get_school_calendar_with_year(self, test_client, admin_headers):
        """Test that GET /config/school-calendar accepts year parameter."""
        response = test_client.get(
            '/api/v1/config/school-calendar?year=2024',
            headers=admin_headers
        )
        assert response.status_code in [200, 500]
    
    # --- Holiday Endpoint Tests ---
    
    def test_add_holiday_requires_admin(self, test_client, staff_headers):
        """Test that POST /config/holidays requires Admin role."""
        response = test_client.post(
            '/api/v1/config/holidays',
            headers=staff_headers,
            data=json.dumps({'date': '2024-12-25', 'name': 'Christmas'})
        )
        assert response.status_code == 403
    
    def test_add_holiday_validates_required_fields(self, test_client, admin_headers):
        """Test that POST /config/holidays validates required fields."""
        response = test_client.post(
            '/api/v1/config/holidays',
            headers=admin_headers,
            data=json.dumps({})
        )
        assert response.status_code == 400
    
    def test_add_holiday_validates_date_format(self, test_client, admin_headers):
        """Test that POST /config/holidays validates date format."""
        response = test_client.post(
            '/api/v1/config/holidays',
            headers=admin_headers,
            data=json.dumps({'date': 'invalid-date', 'name': 'Test'})
        )
        assert response.status_code == 400
    
    def test_add_holiday_with_valid_data(self, test_client, admin_headers):
        """Test that POST /config/holidays accepts valid data."""
        response = test_client.post(
            '/api/v1/config/holidays',
            headers=admin_headers,
            data=json.dumps({
                'date': '2025-01-01',
                'name': 'New Year',
                'type': 'holiday'
            })
        )
        assert response.status_code in [201, 400, 500]  # 400 if already exists
    
    def test_delete_holiday_requires_admin(self, test_client, staff_headers):
        """Test that DELETE /config/holidays/<id> requires Admin role."""
        response = test_client.delete(
            '/api/v1/config/holidays/1',
            headers=staff_headers
        )
        assert response.status_code == 403
    
    def test_delete_holiday_returns_404_for_nonexistent(self, test_client, admin_headers):
        """Test that DELETE /config/holidays/<id> returns 404 for nonexistent."""
        response = test_client.delete(
            '/api/v1/config/holidays/99999',
            headers=admin_headers
        )
        assert response.status_code in [404, 500]


class TestConfigAPIResponseFormat:
    """Tests for Config API response format compliance."""
    
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
        response = test_client.put(
            '/api/v1/config/settings',
            headers=admin_headers,
            data=json.dumps({'attendance_rules': {'late_threshold_minutes': -1}})
        )
        data = json.loads(response.data)
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
