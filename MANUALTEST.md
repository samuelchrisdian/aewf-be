# AEWF Backend API - Manual Testing Guide

This document provides a detailed reference for manually testing the Attendance Early Warning Framework (AEWF) API. It includes complete request payloads and expected JSON responses for every endpoint to verify the full application flow.

## 🛠 Setup & Authentication

**Base URL**: `http://localhost:5000/api/v1`

**Authentication**:
All endpoints (except health check) require a JWT Bearer Token.
1.  Run `python generate_auth_token.py` to get a token.
2.  **Header**: `Authorization: Bearer <TOKEN>`

---

## 1. 🏥 System Health

### Check Server Status
*   **Method**: `GET`
*   **URL**: `http://localhost:5000/health`
*   **Response**:
    ```json
    {
        "status": "ok"
    }
    ```

---

## 2. 🏫 Master Data Management

Follow this order to ensure foreign key dependencies are met.

### 2.1 Teachers
**Scenario**: Register a new homeroom teacher.

*   **Endpoint**: `POST /teachers`
*   **Request Body**:
    ```json
    {
        "teacher_id": "T-001",
        "name": "Sarah Connor",
        "role": "Wali Kelas",
        "phone": "08123456789"
    }
    ```
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Teacher created successfully",
        "data": {
            "teacher_id": "T-001",
            "name": "Sarah Connor",
            "role": "Wali Kelas"
        }
    }
    ```

### 2.2 Classes
**Scenario**: Create a class and assign the teacher created above.

*   **Endpoint**: `POST /classes`
*   **Request Body**:
    ```json
    {
        "class_id": "XII-IPA-A",
        "class_name": "Grade 12 Science A",
        "wali_kelas_id": "T-001"
    }
    ```
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Class created successfully",
        "data": {
            "class_id": "XII-IPA-A",
            "class_name": "Grade 12 Science A",
            "wali_kelas_id": "T-001"
        }
    }
    ```

### 2.3 Students
**Scenario**: Register a student into the class.

*   **Endpoint**: `POST /students`
*   **Request Body**:
    ```json
    {
        "nis": "2024001",
        "name": "John Doe",
        "class_id": "XII-IPA-A",
        "parent_phone": "0811998877",
        "is_active": true
    }
    ```
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Student created successfully",
        "data": {
            "nis": "2024001",
            "name": "John Doe",
            "class_id": "XII-IPA-A",
            "is_active": true
        }
    }
    ```

### 2.4 Get Student Details
*   **Endpoint**: `GET /students/2024001`
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Student retrieved successfully",
        "data": {
            "nis": "2024001",
            "name": "John Doe",
            "class_name": "Grade 12 Science A",
            "attendance_summary": {
                "present": 0,
                "absent": 0,
                "late": 0
            }
        }
    }
    ```

---

## 3. 🖨 Machine Management

### 3.1 Register Machine
*   **Endpoint**: `POST /machines`
*   **Request Body**:
    ```json
    {
        "machine_code": "BIO-LAB-01",
        "location": "Biology Lab Entrance",
        "status": "active"
    }
    ```
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Machine created successfully",
        "data": {
            "id": 1,
            "machine_code": "BIO-LAB-01",
            "location": "Biology Lab Entrance"
        }
    }
    ```

### 3.2 List Machines
*   **Endpoint**: `GET /machines`
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Machines retrieved successfully",
        "data": [
            {
                "id": 1,
                "machine_code": "BIO-LAB-01",
                "status": "active",
                "user_count": 0
            }
        ],
        "pagination": { ... }
    }
    ```

---

## 4. 📥 Data Import & Sync

### 4.1 Import Master Data
**Scenario**: Bulk upload students/teachers via Excel.

*   **Endpoint**: `POST /import/master`
*   **Body (form-data)**:
    *   `file`: select `master_template.xlsx`
*   **Response**:
    ```json
    {
        "success": true,
        "data": {
            "students_imported": 50,
            "teachers_imported": 5,
            "classes_imported": 2
        }
    }
    ```

### 4.2 Sync Machine Users
**Scenario**: Upload user list export from various machines.

*   **Endpoint**: `POST /import/users-sync`
*   **Body (form-data)**:
    *   `file`: select `user_export.xls`
    *   `machine_code`: `BIO-LAB-01`
*   **Response**:
    ```json
    {
        "success": true,
        "data": {
            "machine_code": "BIO-LAB-01",
            "users_synced": 10,
            "new_users": 2
        }
    }
    ```

---

## 5. 🔍 Fuzzy Mapping
**Scenario**: Map a raw machine user (ID: 101, Name: "Jhn Dae") to Student "John Doe" (2024001).

### 5.1 Run Auto-Mapping
*   **Endpoint**: `POST /mapping/process`
*   **Request Body**:
    ```json
    {
        "threshold": 85
    }
    ```
*   **Response**:
    ```json
    {
        "success": true,
        "data": {
            "matches_found": 1,
            "auto_verified": 0
        }
    }
    ```

### 5.2 Get Suggestions
*   **Endpoint**: `GET /mapping/suggestions`
*   **Response**:
    ```json
    {
        "success": true,
        "data": [
            {
                "mapping_id": 12,
                "machine_user_name": "Jhn Dae",
                "suggested_student_name": "John Doe",
                "confidence_score": 88
            }
        ]
    }
    ```

### 5.3 Verify Mapping
*   **Endpoint**: `POST /mapping/verify`
*   **Request Body**:
    ```json
    {
        "mapping_id": 12,
        "status": "verified"
    }
    ```
*   **Response**:
    ```json
    { "success": true }
    ```

---

## 6. 📅 Attendance Log Processing

### 6.1 Import Attendance Log
**Scenario**: Upload daily attendance logs.

*   **Endpoint**: `POST /import/attendance`
*   **Body (form-data)**:
    *   `file`: select `attendance_log.csv`
    *   `machine_code`: `BIO-LAB-01`
*   **Response**:
    ```json
    {
        "success": true,
        "data": {
            "processed_count": 100,
            "matched_students": 95
        }
    }
    ```

### 6.2 Manual Attendance Entry
**Scenario**: Student forgot to scan, teacher adds manually.

*   **Endpoint**: `POST /attendance/manual`
*   **Request Body**:
    ```json
    {
        "student_nis": "2024001",
        "attendance_date": "2024-12-14",
        "status": "Present",
        "notes": "Forgot ID card"
    }
    ```
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Attendance recorded successfully",
        "data": {
            "id": 505,
            "status": "Present",
            "date": "2024-12-14"
        }
    }
    ```

### 6.3 Get Daily Attendance
*   **Endpoint**: `GET /attendance/daily`
*   **Query**: `?date=2024-12-14`
*   **Response**:
    ```json
    {
        "status": "success",
        "data": [
            {
                "student_name": "John Doe",
                "nis": "2024001",
                "check_in": "07:05:00",
                "check_out": "15:00:00",
                "status": "Present"
            }
        ],
        "pagination": { "total": 1, "pages": 1, ... }
    }
    ```

---

## 7. 🚨 Risk & EWS (Early Warning System)

### 7.1 Calculate Risk
**Scenario**: Trigger background risk calculation.

*   **Endpoint**: `POST /risk/recalculate`
*   **Request Body**: `{}` (Empty for all, or `{"class_id": "XII-IPA-A"}`)
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Risk recalculation completed",
        "data": {
            "processed": 50,
            "high_risk_count": 2
        }
    }
    ```

### 7.2 Get Risk List
*   **Endpoint**: `GET /risk/list`
*   **Query**: `?level=high`
*   **Response**:
    ```json
    {
        "status": "success",
        "data": [
            {
                "nis": "2024001",
                "name": "John Doe",
                "risk_score": 85,
                "risk_level": "High",
                "factors": {
                    "attendance_rate": 60.5,
                    "consecutive_absences": 4
                }
            }
        ]
    }
    ```

---

## 8. 📊 Dashboard & Analytics

### 8.1 Dashboard Stats
*   **Endpoint**: `GET /dashboard/stats`
*   **Response**:
    ```json
    {
        "status": "success",
        "data": {
            "overview": {
                "total_students": 150,
                "total_teachers": 10,
                "total_classes": 6
            },
            "today_attendance": {
                "present": 140,
                "absent": 5,
                "late": 5
            },
            "risk_summary": {
                "high": 3,
                "medium": 12,
                "low": 135
            }
        }
    }
    ```

### 8.2 Student Analytics Patterns
*   **Endpoint**: `GET /analytics/student-patterns/2024001`
*   **Response**:
    ```json
    {
        "status": "success",
        "data": {
            "summary": { "attendance_rate": 88.5 },
            "weekly_breakdown": { "Mon": 90, "Tue": 100, ... },
            "trend": "decreasing"
        }
    }
    ```

---

## 9. 🤖 ML Model Management

### 9.1 Retrain Models
*   **Endpoint**: `POST /models/retrain`
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Model retraining completed successfully",
        "data": {
            "models_updated": ["logistic_regression", "decision_tree"]
        }
    }
    ```

### 9.2 Model Info
*   **Endpoint**: `GET /models/info`
*   **Response**:
    ```json
    {
        "status": "success",
        "data": {
            "logistic_regression": {
                "status": "available",
                "version": "1.0",
                "accuracy": 0.89
            }
        }
    }
    ```
