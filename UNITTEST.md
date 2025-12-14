# Unit Testing Guide

This project uses **pytest** for automated testing. Tests are located in the `tests/` directory and are split into **Unit Tests** and **Integration Tests**.

## 🛠 Prerequisites

Ensure you have installed the development dependencies:

```bash
pip install -r requirements.txt
```
*(Pytest and plugins should be included in requirements.txt)*

## 🏃 Running Tests

### Run All Tests
To run the full test suite:
```bash
pytest
```

### Run with Detailed Output
To see which tests are passing/failing:
```bash
pytest -v
```

### Run Specific Test File
```bash
pytest tests/test_api_blackbox.py
```

### Run Specific Test Function
```bash
pytest tests/test_api_blackbox.py::test_create_student_flow
```

### View Print Statements
By default, pytest captures stdout. To see print statements during execution (useful for debugging):
```bash
pytest -s
```

---

## 📂 Test Structure

The `tests/` directory is organized as follows:

*   **`conftest.py`**: Contains **Fixtures** shared across tests.
    *   `test_client`: A Flask test client for making API requests.
    *   `db_session`: A database session that rolls back changes after each test (keeps DB clean).
*   **`unit/`**: Tests for individual functions/services (logic only, no DB or mocked DB).
*   **`integration/`**: Tests that involve the database and API endpoints working together.
*   **`factories/`**: Helper classes to generate dummy data for tests (e.g., `UserFactory`, `StudentFactory`).

## 📝 Writing New Tests

### Creating a New Test File
Create a file starting with `test_` in the appropriate directory (e.g., `tests/unit/test_my_service.py`).

### Example Integration Test
```python
def test_create_class(test_client):
    # Prepare data
    data = {"class_id": "XII-1", "class_name": "Grade 12 Class 1"}
    
    # Make Request (Assuming token bypass or mock in setup)
    # If auth is enforced, you may need to headers/mocking
    response = test_client.post('/api/v1/classes', json=data)
    
    # Assert
    assert response.status_code == 201
    assert response.json['class_id'] == "XII-1"
```

### Mocking vs Real DB
*   **Unit tests** should mock database calls to be fast.
*   **Integration tests** use the `db_session` fixture (or rely on `conftest` setup) to use a real (test) database but rollback transactions.

## ⚠️ Notes on Authentication in Tests
If your tests require authentication:
1.  Ensure your `conftest.py` configures the app correctly.
2.  You may need to mock the `token_required` decorator or generate a valid token in the test fixture to pass in headers.

---

## 📊 Test Coverage by Module

### Integration Tests
The following integration test files cover API endpoints:

*   **`test_students_api.py`**: Student CRUD operations
*   **`test_teachers_api.py`**: Teacher CRUD operations
*   **`test_classes_api.py`**: Class CRUD operations
*   **`test_attendance_api.py`**: Attendance management endpoints
*   **`test_machines_api.py`**: Machine management endpoints
*   **`test_mapping_api.py`**: Fuzzy mapping endpoints
*   **`test_dashboard_api.py`**: Dashboard statistics
*   **`test_analytics_api.py`**: Analytics and trends
*   **`test_risk_api.py`**: Risk management and alerts
*   **`test_models_api.py`**: ML model management
*   **`test_reports_api.py`**: Report generation (Phase 6)
*   **`test_export_api.py`**: Data export to Excel (Phase 6)
*   **`test_notifications_api.py`**: Notification system endpoints (Phase 7)
*   **`test_auth_api.py`**: Authentication endpoints (Phase 8)
*   **`test_users_api.py`**: User management endpoints (Phase 8)

### Running Specific Test Suites

**Run all integration tests:**
```bash
pytest tests/integration/ -v
```

**Run Phase 6 tests only:**
```bash
pytest tests/integration/test_reports_api.py tests/integration/test_export_api.py -v
```

**Run Phase 8 tests only:**
```bash
pytest tests/integration/test_auth_api.py tests/integration/test_users_api.py -v
```

**Run with coverage report:**
```bash
pytest --cov=src --cov-report=html
```
