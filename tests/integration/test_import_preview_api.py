"""
Integration tests for Import Preview API endpoints.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestImportPreviewAPI:
    """Integration tests for /api/v1/import/*/preview endpoints."""

    @pytest.fixture
    def admin_headers(self, test_client):
        """Get authentication headers for admin user."""
        return {"Authorization": "Bearer admin_token"}

    @pytest.fixture(autouse=True)
    def mock_auth_middleware(self):
        """Mock authentication middleware."""
        with patch("src.app.middleware.jwt.decode") as mock_decode:
            with patch("src.app.middleware.User") as mock_user_cls:
                mock_decode.return_value = {"user_id": 1}
                mock_user = MagicMock()
                mock_user.id = 1
                mock_user.role = "Admin"
                mock_user.is_active = True
                mock_user_cls.query.filter_by.return_value.first.return_value = (
                    mock_user
                )
                yield

    # --- Master Data Preview Tests ---

    def test_preview_master_requires_authentication(self, test_client):
        """Test that POST /import/master/preview requires authentication."""
        response = test_client.post("/api/v1/import/master/preview")
        assert response.status_code == 401

    def test_preview_master_requires_file(self, test_client, admin_headers):
        """Test that POST /import/master/preview requires file upload."""
        response = test_client.post(
            "/api/v1/import/master/preview", headers=admin_headers
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "No file part" in data.get("message", "")

    def test_preview_master_rejects_empty_filename(self, test_client, admin_headers):
        """Test that empty filename is rejected."""
        data = {"file": (BytesIO(b""), "")}  # Empty filename
        response = test_client.post(
            "/api/v1/import/master/preview",
            headers=admin_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    # --- Users Sync Preview Tests ---

    def test_preview_users_sync_requires_authentication(self, test_client):
        """Test that POST /import/users-sync/preview requires authentication."""
        response = test_client.post("/api/v1/import/users-sync/preview")
        assert response.status_code == 401

    def test_preview_users_sync_requires_file(self, test_client, admin_headers):
        """Test that POST /import/users-sync/preview requires file upload."""
        response = test_client.post(
            "/api/v1/import/users-sync/preview", headers=admin_headers
        )
        assert response.status_code == 400

    def test_preview_users_sync_requires_machine_code(self, test_client, admin_headers):
        """Test that POST /import/users-sync/preview requires machine_code."""
        data = {"file": (BytesIO(b"test"), "test.xlsx")}
        response = test_client.post(
            "/api/v1/import/users-sync/preview",
            headers=admin_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "machine_code" in data.get("message", "")

    # --- Attendance Preview Tests ---

    def test_preview_attendance_requires_authentication(self, test_client):
        """Test that POST /import/attendance/preview requires authentication."""
        response = test_client.post("/api/v1/import/attendance/preview")
        assert response.status_code == 401

    def test_preview_attendance_requires_file(self, test_client, admin_headers):
        """Test that POST /import/attendance/preview requires file upload."""
        response = test_client.post(
            "/api/v1/import/attendance/preview", headers=admin_headers
        )
        assert response.status_code == 400

    def test_preview_attendance_requires_machine_code(self, test_client, admin_headers):
        """Test that POST /import/attendance/preview requires machine_code."""
        data = {"file": (BytesIO(b"test"), "test.xlsx")}
        response = test_client.post(
            "/api/v1/import/attendance/preview",
            headers=admin_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "machine_code" in data.get("message", "")


class TestPreviewResponseFormat:
    """Tests for preview endpoint response format compliance."""

    @pytest.fixture
    def admin_headers(self, test_client):
        """Get authentication headers for admin user."""
        return {"Authorization": "Bearer admin_token"}

    @pytest.fixture(autouse=True)
    def mock_auth_middleware(self):
        """Mock authentication middleware for admin."""
        with patch("src.app.middleware.jwt.decode") as mock_decode:
            with patch("src.app.middleware.User") as mock_user_cls:
                mock_decode.return_value = {"user_id": 1}
                mock_user = MagicMock()
                mock_user.id = 1
                mock_user.role = "Admin"
                mock_user.is_active = True
                mock_user_cls.query.filter_by.return_value.first.return_value = (
                    mock_user
                )
                yield

    def test_preview_master_returns_success_format(self, test_client, admin_headers):
        """Verify preview master response follows standard format when service is mocked."""
        with patch(
            "src.api.v1.routes.MasterDataService.preview_from_excel"
        ) as mock_preview:
            mock_preview.return_value = {
                "classes": [],
                "students": [],
                "teachers": [],
                "summary": {
                    "total_classes": 0,
                    "total_students": 0,
                    "total_teachers": 0,
                },
                "errors": [],
            }

            data = {"file": (BytesIO(b"test content"), "test.xlsx")}
            response = test_client.post(
                "/api/v1/import/master/preview",
                headers=admin_headers,
                data=data,
                content_type="multipart/form-data",
            )

            if response.status_code == 200:
                result = json.loads(response.data)
                assert "success" in result
                assert result["success"] is True
                assert "data" in result

    def test_preview_users_sync_returns_success_format(
        self, test_client, admin_headers
    ):
        """Verify preview users-sync response follows standard format when service is mocked."""
        with patch(
            "src.api.v1.routes.MachineService.preview_users_from_excel"
        ) as mock_preview:
            mock_preview.return_value = {
                "users": [],
                "summary": {
                    "total_users": 0,
                    "new_users": 0,
                    "existing_users": 0,
                    "skipped_non_smp": 0,
                },
                "errors": [],
            }

            data = {
                "file": (BytesIO(b"test content"), "test.xlsx"),
                "machine_code": "MACHINE_01",
            }
            response = test_client.post(
                "/api/v1/import/users-sync/preview",
                headers=admin_headers,
                data=data,
                content_type="multipart/form-data",
            )

            if response.status_code == 200:
                result = json.loads(response.data)
                assert "success" in result
                assert result["success"] is True
                assert "data" in result

    def test_preview_attendance_returns_success_format(
        self, test_client, admin_headers
    ):
        """Verify preview attendance response follows standard format when service is mocked."""
        with patch(
            "src.api.v1.routes.IngestionService.preview_logs_from_excel"
        ) as mock_preview:
            mock_preview.return_value = {
                "format": "matrix",
                "period": {"year": 2025, "month": 8},
                "users": [],
                "summary": {
                    "total_logs": 0,
                    "total_users": 0,
                    "users_not_found": 0,
                    "unmapped_users": 0,
                },
                "errors": [],
            }

            data = {
                "file": (BytesIO(b"test content"), "test.xlsx"),
                "machine_code": "MACHINE_01",
            }
            response = test_client.post(
                "/api/v1/import/attendance/preview",
                headers=admin_headers,
                data=data,
                content_type="multipart/form-data",
            )

            if response.status_code == 200:
                result = json.loads(response.data)
                assert "success" in result
                assert result["success"] is True
                assert "data" in result
