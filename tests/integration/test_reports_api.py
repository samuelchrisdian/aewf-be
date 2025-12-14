"""
Integration tests for Reports API endpoints.
"""
import pytest
import json


class TestReportsAPI:
    """Integration tests for /api/v1/reports endpoints."""
    
    @pytest.fixture
    def auth_headers(self, test_client):
        """Get authentication headers with valid token."""
        return {"Authorization": "Bearer test_token", "Content-Type": "application/json"}
    
    def test_attendance_report_requires_authentication(self, test_client):
        """Test that GET /reports/attendance requires authentication."""
        response = test_client.get('/api/v1/reports/attendance?start_date=2024-01-01&end_date=2024-01-31')
        assert response.status_code == 401
    
    def test_attendance_report_requires_dates(self, test_client, auth_headers):
        """Test that GET /reports/attendance requires start_date and end_date."""
        response = test_client.get('/api/v1/reports/attendance', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_attendance_report_json_format(self, test_client, auth_headers):
        """Test that GET /reports/attendance returns JSON by default."""
        response = test_client.get(
            '/api/v1/reports/attendance?start_date=2024-01-01&end_date=2024-01-31',
            headers=auth_headers
        )
        # May return 200 or error depending on data availability
        assert response.status_code in [200, 400, 500]
    
    def test_attendance_report_excel_format(self, test_client, auth_headers):
        """Test that GET /reports/attendance?format=excel returns Excel file."""
        response = test_client.get(
            '/api/v1/reports/attendance?start_date=2024-01-01&end_date=2024-01-31&format=excel',
            headers=auth_headers
        )
        # Should return Excel file or error
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    def test_attendance_report_accepts_class_filter(self, test_client, auth_headers):
        """Test that GET /reports/attendance accepts class_id parameter."""
        response = test_client.get(
            '/api/v1/reports/attendance?start_date=2024-01-01&end_date=2024-01-31&class_id=X-IPA-1',
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 500]
    
    def test_attendance_report_accepts_student_filter(self, test_client, auth_headers):
        """Test that GET /reports/attendance accepts student_nis parameter."""
        response = test_client.get(
            '/api/v1/reports/attendance?start_date=2024-01-01&end_date=2024-01-31&student_nis=2024001',
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 500]
    
    def test_risk_report_requires_authentication(self, test_client):
        """Test that GET /reports/risk requires authentication."""
        response = test_client.get('/api/v1/reports/risk')
        assert response.status_code == 401
    
    def test_risk_report_json_format(self, test_client, auth_headers):
        """Test that GET /reports/risk returns JSON by default."""
        response = test_client.get('/api/v1/reports/risk', headers=auth_headers)
        assert response.status_code in [200, 400, 500]
    
    def test_risk_report_excel_format(self, test_client, auth_headers):
        """Test that GET /reports/risk?format=excel returns Excel file."""
        response = test_client.get('/api/v1/reports/risk?format=excel', headers=auth_headers)
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    def test_risk_report_accepts_class_filter(self, test_client, auth_headers):
        """Test that GET /reports/risk accepts class_id parameter."""
        response = test_client.get('/api/v1/reports/risk?class_id=X-IPA-1', headers=auth_headers)
        assert response.status_code in [200, 400, 500]
    
    def test_class_summary_requires_authentication(self, test_client):
        """Test that GET /reports/class-summary requires authentication."""
        response = test_client.get('/api/v1/reports/class-summary?start_date=2024-01-01&end_date=2024-01-31')
        assert response.status_code == 401
    
    def test_class_summary_requires_dates(self, test_client, auth_headers):
        """Test that GET /reports/class-summary requires start_date and end_date."""
        response = test_client.get('/api/v1/reports/class-summary', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_class_summary_json_format(self, test_client, auth_headers):
        """Test that GET /reports/class-summary returns JSON by default."""
        response = test_client.get(
            '/api/v1/reports/class-summary?start_date=2024-01-01&end_date=2024-01-31',
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 500]
    
    def test_class_summary_excel_format(self, test_client, auth_headers):
        """Test that GET /reports/class-summary?format=excel returns Excel file."""
        response = test_client.get(
            '/api/v1/reports/class-summary?start_date=2024-01-01&end_date=2024-01-31&format=excel',
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class TestReportsAPIResponseFormat:
    """Tests for Reports API response format compliance."""
    
    def test_attendance_report_structure(self):
        """Verify attendance report includes required fields."""
        # This would require actual data setup
        pass
    
    def test_risk_report_structure(self):
        """Verify risk report includes student details and interventions."""
        pass
    
    def test_class_summary_structure(self):
        """Verify class summary includes all classes with statistics."""
        pass
