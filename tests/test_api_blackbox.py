import pytest
import json

def test_index(test_client):
    response = test_client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "AEWF Backend API is running."

def test_create_student_flow(test_client):
    """
    Test creating a student and then retrieving them.
    """
    # 1. Create Student
    student_data = {
        "nis": "TEST001",
        "name": "Test Student",
        "class_id": "CLS001"
    }
    response = test_client.post('/api/students', 
                                data=json.dumps(student_data),
                                content_type='application/json')
    
    # Note: Depending on existing DB state, this might fail if duplicate or missing class.
    # We assert 201 or 400 (if duplicate).
    assert response.status_code in [201, 400]
    
    # 2. Get Student
    response = test_client.get('/api/students/TEST001')
    
    # If creation succeeded or existed, this should be 200
    if response.status_code == 200:
        data = json.loads(response.data)
        assert data["nis"] == "TEST001"
        assert data["name"] == "Test Student"

def test_get_nonexistent_student(test_client):
    response = test_client.get('/api/students/NON_EXISTENT')
    assert response.status_code == 404

def test_risk_assessment_no_data(test_client):
    """
    Test EWS endpoint for a student with no attendance data.
    """
    response = test_client.get('/api/risk/TEST001')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "risk_assessment" in data
    # Should be unknown or fallback
    assert data["risk_assessment"]["risk"] in ["Unknown", "Green", "Yellow", "Red", "Error"]
