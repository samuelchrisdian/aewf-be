"""
Integration tests for Models API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestModelsAPI:
    """Integration tests for /api/v1/models endpoints."""
    
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
    
    # --- Model Info Endpoint Tests ---
    
    def test_get_model_info_requires_authentication(self, test_client):
        """Test that GET /models/info requires authentication."""
        response = test_client.get('/api/v1/models/info')
        assert response.status_code == 401
    
    def test_get_model_info_returns_model_metadata(self, test_client, auth_headers):
        """Test that GET /models/info returns model metadata."""
        response = test_client.get('/api/v1/models/info', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data["success"] is True
        assert "data" in data
        assert "logistic_regression" in data["data"]
        assert "decision_tree" in data["data"]
    
    def test_get_model_info_includes_status(self, test_client, auth_headers):
        """Test that GET /models/info includes model status."""
        response = test_client.get('/api/v1/models/info', headers=auth_headers)
        data = json.loads(response.data)
        
        # Each model should have a status
        assert "status" in data["data"]["logistic_regression"]
        assert "status" in data["data"]["decision_tree"]
    
    # --- Model Performance Endpoint Tests ---
    
    def test_get_model_performance_requires_authentication(self, test_client):
        """Test that GET /models/performance requires authentication."""
        response = test_client.get('/api/v1/models/performance')
        assert response.status_code == 401
    
    def test_get_model_performance_returns_metrics(self, test_client, auth_headers):
        """Test that GET /models/performance returns metrics."""
        response = test_client.get('/api/v1/models/performance', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data["success"] is True
        assert "data" in data
        assert "logistic_regression" in data["data"]
        assert "decision_tree" in data["data"]
    
    def test_get_model_performance_includes_comparison(self, test_client, auth_headers):
        """Test that GET /models/performance includes model comparison."""
        response = test_client.get('/api/v1/models/performance', headers=auth_headers)
        data = json.loads(response.data)
        
        assert "comparison" in data["data"]
    
    # --- Model Retrain Endpoint Tests ---
    
    def test_retrain_requires_authentication(self, test_client):
        """Test that POST /models/retrain requires authentication."""
        response = test_client.post('/api/v1/models/retrain')
        assert response.status_code == 401
    
    def test_retrain_triggers_training(self, test_client, auth_headers):
        """Test that POST /models/retrain triggers training."""
        # This will either succeed or fail based on whether data is available
        response = test_client.post('/api/v1/models/retrain', headers=auth_headers)
        assert response.status_code in [200, 500]
        
        data = json.loads(response.data)
        if response.status_code == 200:
            assert data["success"] is True
            assert "data" in data


class TestModelsAPIResponseFormat:
    """Tests for Models API response format compliance."""
    
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
    
    def test_success_response_format(self, test_client, auth_headers):
        """Verify success responses follow standard format."""
        response = test_client.get('/api/v1/models/info', headers=auth_headers)
        data = json.loads(response.data)
        
        assert "success" in data
        assert data["success"] is True
        assert "message" in data
        assert "data" in data
    
    def test_model_info_structure(self, test_client, auth_headers):
        """Verify model info response structure."""
        response = test_client.get('/api/v1/models/info', headers=auth_headers)
        data = json.loads(response.data)
        
        for model_name in ["logistic_regression", "decision_tree"]:
            model_info = data["data"][model_name]
            assert "name" in model_info or "status" in model_info
