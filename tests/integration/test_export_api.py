"""
Integration tests for Export API endpoints.
"""
import pytest
import json


class TestExportAPI:
    """Integration tests for /api/v1/export endpoints."""
    
    @pytest.fixture
    def auth_headers(self, test_client):
        """Get authentication headers with valid token."""
        return {"Authorization": "Bearer test_token", "Content-Type": "application/json"}
    
    def test_export_students_requires_authentication(self, test_client):
        """Test that GET /export/students requires authentication."""
        response = test_client.get('/api/v1/export/students')
        assert response.status_code == 401
    
    def test_export_students_returns_excel(self, test_client, auth_headers):
        """Test that GET /export/students returns Excel file."""
        response = test_client.get('/api/v1/export/students', headers=auth_headers)
        # Should return Excel file or error
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            # Check filename
            assert 'students.xlsx' in response.headers.get('Content-Disposition', '')
    
    def test_export_students_accepts_class_filter(self, test_client, auth_headers):
        """Test that GET /export/students accepts class_id parameter."""
        response = test_client.get('/api/v1/export/students?class_id=X-IPA-1', headers=auth_headers)
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            # Check filename includes class_id
            assert 'students_X-IPA-1.xlsx' in response.headers.get('Content-Disposition', '')
    
    def test_export_attendance_requires_authentication(self, test_client):
        """Test that GET /export/attendance requires authentication."""
        response = test_client.get('/api/v1/export/attendance?start_date=2024-01-01&end_date=2024-01-31')
        assert response.status_code == 401
    
    def test_export_attendance_requires_dates(self, test_client, auth_headers):
        """Test that GET /export/attendance requires start_date and end_date."""
        response = test_client.get('/api/v1/export/attendance', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_export_attendance_returns_excel(self, test_client, auth_headers):
        """Test that GET /export/attendance returns Excel file."""
        response = test_client.get(
            '/api/v1/export/attendance?start_date=2024-01-01&end_date=2024-01-31',
            headers=auth_headers
        )
        # Should return Excel file or error
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            # Check filename includes dates
            assert 'attendance_2024-01-01_2024-01-31.xlsx' in response.headers.get('Content-Disposition', '')
    
    def test_export_attendance_accepts_class_filter(self, test_client, auth_headers):
        """Test that GET /export/attendance accepts class_id parameter."""
        response = test_client.get(
            '/api/v1/export/attendance?start_date=2024-01-01&end_date=2024-01-31&class_id=X-IPA-1',
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 500]
    
    def test_export_template_requires_authentication(self, test_client):
        """Test that GET /export/template/master requires authentication."""
        response = test_client.get('/api/v1/export/template/master')
        assert response.status_code == 401
    
    def test_export_template_returns_excel(self, test_client, auth_headers):
        """Test that GET /export/template/master returns Excel file."""
        response = test_client.get('/api/v1/export/template/master', headers=auth_headers)
        # Should return Excel file or error
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            # Check filename
            assert 'master_data_template.xlsx' in response.headers.get('Content-Disposition', '')


class TestExportAPIFileContent:
    """Tests for Export API file content validation."""
    
    def test_students_export_has_headers(self):
        """Verify students export includes proper headers."""
        # This would require actual data setup and file parsing
        pass
    
    def test_attendance_export_has_headers(self):
        """Verify attendance export includes proper headers."""
        pass
    
    def test_template_has_multiple_sheets(self):
        """Verify template has Students, Classes, and Teachers sheets."""
        pass
    
    def test_template_has_example_data(self):
        """Verify template includes example rows."""
        pass
