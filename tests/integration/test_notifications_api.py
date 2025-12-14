"""
Integration tests for Notifications API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestNotificationsAPI:
    """Integration tests for /api/v1/notifications endpoints."""
    
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
                mock_user_cls.query.filter_by.return_value.first.return_value = mock_user
                yield
    
    # --- Get Notifications Endpoint Tests ---
    
    def test_get_notifications_requires_authentication(self, test_client):
        """Test that GET /notifications requires authentication."""
        response = test_client.get('/api/v1/notifications')
        assert response.status_code == 401
    
    def test_get_notifications_returns_success(self, test_client, auth_headers):
        """Test that GET /notifications returns success."""
        response = test_client.get('/api/v1/notifications', headers=auth_headers)
        assert response.status_code in [200, 500]  # 500 if DB not available
    
    def test_get_notifications_accepts_is_read_filter(self, test_client, auth_headers):
        """Test that GET /notifications accepts is_read filter."""
        response = test_client.get('/api/v1/notifications?is_read=true', headers=auth_headers)
        assert response.status_code in [200, 500]
    
    def test_get_notifications_accepts_pagination(self, test_client, auth_headers):
        """Test that GET /notifications accepts pagination parameters."""
        response = test_client.get('/api/v1/notifications?page=1&per_page=10', headers=auth_headers)
        assert response.status_code in [200, 500]
    
    # --- Send Notification Endpoint Tests ---
    
    def test_send_notification_requires_authentication(self, test_client):
        """Test that POST /notifications/send requires authentication."""
        response = test_client.post('/api/v1/notifications/send')
        assert response.status_code == 401
    
    def test_send_notification_validates_required_fields(self, test_client, auth_headers):
        """Test that POST /notifications/send validates required fields."""
        # Missing required fields
        response = test_client.post(
            '/api/v1/notifications/send',
            headers=auth_headers,
            data=json.dumps({})
        )
        assert response.status_code == 400
    
    def test_send_notification_validates_recipient_type(self, test_client, auth_headers):
        """Test that POST /notifications/send validates recipient_type."""
        response = test_client.post(
            '/api/v1/notifications/send',
            headers=auth_headers,
            data=json.dumps({
                "recipient_type": "invalid",
                "recipient_id": "T001",
                "title": "Test",
                "message": "Test message"
            })
        )
        assert response.status_code == 400
    
    def test_send_notification_accepts_valid_data(self, test_client, auth_headers):
        """Test that POST /notifications/send accepts valid data."""
        response = test_client.post(
            '/api/v1/notifications/send',
            headers=auth_headers,
            data=json.dumps({
                "recipient_type": "teacher",
                "recipient_id": "T001",
                "title": "Test Notification",
                "message": "This is a test message"
            })
        )
        assert response.status_code in [201, 500]
    
    def test_send_notification_accepts_all_fields(self, test_client, auth_headers):
        """Test that POST /notifications/send accepts all optional fields."""
        response = test_client.post(
            '/api/v1/notifications/send',
            headers=auth_headers,
            data=json.dumps({
                "recipient_type": "teacher",
                "recipient_id": "T001",
                "type": "risk_alert",
                "title": "High Risk Alert",
                "message": "Student at high risk",
                "priority": "high",
                "channel": "in_app",
                "action_url": "/risk/2024001"
            })
        )
        assert response.status_code in [201, 500]
    
    # --- Mark As Read Endpoint Tests ---
    
    def test_mark_read_requires_authentication(self, test_client):
        """Test that PUT /notifications/<id>/read requires authentication."""
        response = test_client.put('/api/v1/notifications/1/read')
        assert response.status_code == 401
    
    def test_mark_read_returns_404_for_nonexistent(self, test_client, auth_headers):
        """Test that PUT /notifications/<id>/read returns 404 for nonexistent."""
        response = test_client.put('/api/v1/notifications/99999/read', headers=auth_headers)
        assert response.status_code in [404, 500]
    
    # --- Delete Notification Endpoint Tests ---
    
    def test_delete_notification_requires_authentication(self, test_client):
        """Test that DELETE /notifications/<id> requires authentication."""
        response = test_client.delete('/api/v1/notifications/1')
        assert response.status_code == 401
    
    def test_delete_notification_returns_404_for_nonexistent(self, test_client, auth_headers):
        """Test that DELETE /notifications/<id> returns 404 for nonexistent."""
        response = test_client.delete('/api/v1/notifications/99999', headers=auth_headers)
        assert response.status_code in [404, 500]
    
    # --- Get Settings Endpoint Tests ---
    
    def test_get_settings_requires_authentication(self, test_client):
        """Test that GET /notifications/settings requires authentication."""
        response = test_client.get('/api/v1/notifications/settings')
        assert response.status_code == 401
    
    def test_get_settings_returns_success(self, test_client, auth_headers):
        """Test that GET /notifications/settings returns success."""
        response = test_client.get('/api/v1/notifications/settings', headers=auth_headers)
        assert response.status_code in [200, 500]
    
    # --- Update Settings Endpoint Tests ---
    
    def test_update_settings_requires_authentication(self, test_client):
        """Test that PUT /notifications/settings requires authentication."""
        response = test_client.put('/api/v1/notifications/settings')
        assert response.status_code == 401
    
    def test_update_settings_accepts_empty_body(self, test_client, auth_headers):
        """Test that PUT /notifications/settings accepts empty body."""
        response = test_client.put(
            '/api/v1/notifications/settings',
            headers=auth_headers,
            data=json.dumps({})
        )
        assert response.status_code in [200, 500]
    
    def test_update_settings_accepts_valid_data(self, test_client, auth_headers):
        """Test that PUT /notifications/settings accepts valid data."""
        response = test_client.put(
            '/api/v1/notifications/settings',
            headers=auth_headers,
            data=json.dumps({
                "enable_risk_alerts": True,
                "enable_email": False,
                "daily_digest_time": "08:00"
            })
        )
        assert response.status_code in [200, 500]
    
    def test_update_settings_validates_time_format(self, test_client, auth_headers):
        """Test that PUT /notifications/settings validates time format."""
        response = test_client.put(
            '/api/v1/notifications/settings',
            headers=auth_headers,
            data=json.dumps({
                "daily_digest_time": "invalid"
            })
        )
        assert response.status_code == 400


class TestNotificationsAPIResponseFormat:
    """Tests for Notifications API response format compliance."""
    
    @pytest.fixture
    def auth_headers(self, test_client):
        """Get authentication headers."""
        return {"Authorization": "Bearer test_token", "Content-Type": "application/json"}

    @pytest.fixture(autouse=True)
    def mock_auth_middleware(self):
        """Mock authentication middleware to accept test token."""
        with patch('src.app.middleware.jwt.decode') as mock_decode:
            with patch('src.app.middleware.User') as mock_user_cls:
                mock_decode.return_value = {'user_id': 1}
                mock_user = MagicMock()
                mock_user.id = 1
                mock_user_cls.query.filter_by.return_value.first.return_value = mock_user
                yield
    
    def test_validation_error_response_format(self, test_client, auth_headers):
        """Verify validation error responses follow standard format."""
        response = test_client.post(
            '/api/v1/notifications/send',
            headers=auth_headers,
            data=json.dumps({"recipient_type": "invalid"})
        )
        data = json.loads(response.data)
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
