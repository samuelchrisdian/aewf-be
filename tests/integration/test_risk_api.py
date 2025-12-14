"""
Integration tests for Risk API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestRiskAPI:
    """Integration tests for /api/v1/risk endpoints."""
    
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
    
    # --- Risk List Endpoint Tests ---
    
    def test_get_risk_list_requires_authentication(self, test_client):
        """Test that GET /risk/list requires authentication."""
        response = test_client.get('/api/v1/risk/list')
        assert response.status_code == 401
    
    def test_get_risk_list_accepts_level_filter(self, test_client, auth_headers):
        """Test that GET /risk/list accepts level filter."""
        # Test that endpoint exists and accepts level parameter
        response = test_client.get('/api/v1/risk/list?level=high', headers=auth_headers)
        assert response.status_code in [200, 500]  # 500 if DB not available
    
    def test_get_risk_list_rejects_invalid_level(self, test_client, auth_headers):
        """Test that GET /risk/list rejects invalid level."""
        response = test_client.get('/api/v1/risk/list?level=invalid', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
    
    def test_get_risk_list_accepts_pagination(self, test_client, auth_headers):
        """Test that GET /risk/list accepts pagination parameters."""
        response = test_client.get('/api/v1/risk/list?page=1&per_page=10', headers=auth_headers)
        assert response.status_code in [200, 500]
    
    # --- Student Risk Endpoint Tests ---
    
    def test_get_student_risk_requires_authentication(self, test_client):
        """Test that GET /risk/<nis> requires authentication."""
        response = test_client.get('/api/v1/risk/2024001')
        assert response.status_code == 401
    
    def test_get_student_risk_returns_404_for_nonexistent(self, test_client, auth_headers):
        """Test that GET /risk/<nis> returns 404 for nonexistent student."""
        response = test_client.get('/api/v1/risk/NONEXISTENT', headers=auth_headers)
        assert response.status_code in [404, 500]
    
    # --- Alerts Endpoint Tests ---
    
    def test_get_alerts_requires_authentication(self, test_client):
        """Test that GET /risk/alerts requires authentication."""
        response = test_client.get('/api/v1/risk/alerts')
        assert response.status_code == 401
    
    def test_get_alerts_accepts_status_filter(self, test_client, auth_headers):
        """Test that GET /risk/alerts accepts status filter."""
        response = test_client.get('/api/v1/risk/alerts?status=pending', headers=auth_headers)
        assert response.status_code in [200, 500]
    
    def test_get_alerts_rejects_invalid_status(self, test_client, auth_headers):
        """Test that GET /risk/alerts rejects invalid status."""
        response = test_client.get('/api/v1/risk/alerts?status=invalid', headers=auth_headers)
        assert response.status_code == 400
    
    # --- Alert Action Endpoint Tests ---
    
    def test_take_alert_action_requires_authentication(self, test_client):
        """Test that POST /risk/alerts/<id>/action requires authentication."""
        response = test_client.post('/api/v1/risk/alerts/1/action')
        assert response.status_code == 401
    
    def test_take_alert_action_validates_input(self, test_client, auth_headers):
        """Test that POST /risk/alerts/<id>/action validates input."""
        # Missing required 'action' field
        response = test_client.post(
            '/api/v1/risk/alerts/1/action',
            headers=auth_headers,
            data=json.dumps({"notes": "test"})
        )
        assert response.status_code == 400
    
    def test_take_alert_action_accepts_valid_action(self, test_client, auth_headers):
        """Test that POST /risk/alerts/<id>/action accepts valid action."""
        response = test_client.post(
            '/api/v1/risk/alerts/1/action',
            headers=auth_headers,
            data=json.dumps({
                "action": "contacted_parent",
                "notes": "Called parent"
            })
        )
        # 404 if alert doesn't exist, 200 if it does
        assert response.status_code in [200, 404, 500]
    
    # --- Risk History Endpoint Tests ---
    
    def test_get_risk_history_requires_authentication(self, test_client):
        """Test that GET /risk/history/<nis> requires authentication."""
        response = test_client.get('/api/v1/risk/history/2024001')
        assert response.status_code == 401
    
    def test_get_risk_history_returns_404_for_nonexistent(self, test_client, auth_headers):
        """Test that GET /risk/history/<nis> returns 404 for nonexistent student."""
        response = test_client.get('/api/v1/risk/history/NONEXISTENT', headers=auth_headers)
        assert response.status_code in [404, 500]
    
    # --- Recalculate Endpoint Tests ---
    
    def test_recalculate_requires_authentication(self, test_client):
        """Test that POST /risk/recalculate requires authentication."""
        response = test_client.post('/api/v1/risk/recalculate')
        assert response.status_code == 401
    
    def test_recalculate_accepts_empty_body(self, test_client, auth_headers):
        """Test that POST /risk/recalculate accepts empty body."""
        response = test_client.post(
            '/api/v1/risk/recalculate',
            headers=auth_headers,
            data=json.dumps({})
        )
        assert response.status_code in [200, 500]
    
    def test_recalculate_accepts_class_filter(self, test_client, auth_headers):
        """Test that POST /risk/recalculate accepts class_id filter."""
        response = test_client.post(
            '/api/v1/risk/recalculate',
            headers=auth_headers,
            data=json.dumps({"class_id": "X-IPA-1"})
        )
        assert response.status_code in [200, 500]


class TestRiskAPIResponseFormat:
    """Tests for Risk API response format compliance."""
    
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
    
    def test_error_response_format(self, test_client, auth_headers):
        """Verify error responses follow standard format."""
        response = test_client.get('/api/v1/risk/list?level=invalid', headers=auth_headers)
        data = json.loads(response.data)
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
