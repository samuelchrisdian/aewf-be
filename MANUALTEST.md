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

---

## 10. 📄 Reports & Export

### 10.1 Attendance Report (JSON)
**Scenario**: Generate attendance report for a date range.

*   **Endpoint**: `GET /reports/attendance`
*   **Query**: `?start_date=2024-01-01&end_date=2024-01-31`
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Attendance report generated successfully",
        "data": {
            "report_type": "attendance",
            "period": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            },
            "statistics": {
                "total_school_days": 20,
                "average_attendance_rate": 94.5,
                "present_count": 662,
                "late_count": 28,
                "absent_count": 10
            },
            "daily_breakdown": [
                {
                    "date": "2024-01-15",
                    "present": 33,
                    "late": 2,
                    "absent": 0
                }
            ]
        }
    }
    ```

### 10.2 Attendance Report (Excel)
**Scenario**: Download attendance report as Excel file.

*   **Endpoint**: `GET /reports/attendance`
*   **Query**: `?start_date=2024-01-01&end_date=2024-01-31&format=excel`
*   **Response**: Excel file download (`attendance_report_2024-01-01_2024-01-31.xlsx`)

### 10.3 Risk Report
**Scenario**: Generate report of at-risk students.

*   **Endpoint**: `GET /reports/risk`
*   **Query**: `?class_id=XII-IPA-A` (optional)
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Risk report generated successfully",
        "data": {
            "report_type": "risk",
            "summary": {
                "total_at_risk": 5,
                "high_risk": 2,
                "medium_risk": 3,
                "low_risk": 0
            },
            "students": [
                {
                    "nis": "2024001",
                    "name": "John Doe",
                    "class_id": "XII-IPA-A",
                    "risk_level": "high",
                    "risk_score": 85.5,
                    "factors": {
                        "attendance_rate": 60.5,
                        "consecutive_absences": 4
                    }
                }
            ]
        }
    }
    ```

### 10.4 Class Summary Report
**Scenario**: Generate summary report for all classes.

*   **Endpoint**: `GET /reports/class-summary`
*   **Query**: `?start_date=2024-01-01&end_date=2024-01-31`
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Class summary report generated successfully",
        "data": {
            "report_type": "class_summary",
            "period": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            },
            "classes": [
                {
                    "class_id": "XII-IPA-A",
                    "class_name": "Grade 12 Science A",
                    "wali_kelas": {
                        "teacher_id": "T-001",
                        "name": "Sarah Connor"
                    },
                    "student_count": 35,
                    "attendance_statistics": {
                        "average_attendance_rate": 93.2
                    },
                    "at_risk_students": 3
                }
            ]
        }
    }
    ```

### 10.5 Export Students to Excel
**Scenario**: Download all students as Excel file.

*   **Endpoint**: `GET /export/students`
*   **Query**: `?class_id=XII-IPA-A` (optional filter)
*   **Response**: Excel file download (`students.xlsx` or `students_XII-IPA-A.xlsx`)
*   **File Contents**: 
    - Headers: NIS, Name, Class ID, Class Name, Parent Phone, Active
    - Formatted with colored headers and auto-sized columns

### 10.6 Export Attendance to Excel
**Scenario**: Download attendance records as Excel file.

*   **Endpoint**: `GET /export/attendance`
*   **Query**: `?start_date=2024-01-01&end_date=2024-01-31&class_id=XII-IPA-A` (class_id optional)
*   **Response**: Excel file download (`attendance_2024-01-01_2024-01-31.xlsx`)
*   **File Contents**:
    - Headers: Date, NIS, Student Name, Class, Status, Check In, Check Out, Notes
    - Date and time formatting applied

### 10.7 Download Master Data Template
**Scenario**: Get template for bulk import.

*   **Endpoint**: `GET /export/template/master`
*   **Response**: Excel file download (`master_data_template.xlsx`)
*   **File Contents**:
    - **Students sheet**: nis, name, class_id, parent_phone (with example row)
    - **Classes sheet**: class_id, class_name, wali_kelas_id (with example row)
    - **Teachers sheet**: teacher_id, name, phone, role (with example row)

---

## 11. 🔔 Notifications

### 11.1 List Notifications
*   **Endpoint**: `GET /notifications`
*   **Response**:
    ```json
    {
        "status": "success",
        "data": {
            "unread_count": 1,
            "notifications": [
                {
                    "id": 1,
                    "type": "risk_alert",
                    "title": "High Risk Alert",
                    "message": "Student John Doe is at high risk due to attendance.",
                    "priority": "high",
                    "is_read": false,
                    "created_at": "2024-12-14T10:00:00"
                }
            ]
        },
        "pagination": { ... }
    }
    ```

### 11.2 Send Notification
*   **Endpoint**: `POST /notifications/send`
*   **Request Body**:
    ```json
    {
        "recipient_type": "teacher",
        "recipient_id": "T-001",
        "title": "Meeting Reminder",
        "message": "Please attend the staff meeting at 3 PM.",
        "priority": "normal"
    }
    ```
*   **Response**: `201 Created` with notification details.

### 11.3 Mark as Read
*   **Endpoint**: `PUT /notifications/1/read`
*   **Response**:
    ```json
    {
        "status": "success",
        "message": "Notification marked as read"
    }
    ```

### 11.4 Get Notification Settings
*   **Endpoint**: `GET /notifications/settings`
*   **Response**:
    ```json
    {
        "status": "success",
        "data": {
            "user_id": 1,
            "enable_risk_alerts": true,
            "enable_attendance": true,
            "enable_email": true,
            "enable_sms": false,
            "daily_digest_time": "07:00"
        }
    }
    ```

### 11.5 Update Notification Settings
*   **Endpoint**: `PUT /notifications/settings`
*   **Request Body**:
    ```json
    {
        "enable_sms": true,
        "daily_digest_time": "08:00"
    }
    ```
*   **Response**: `200 OK` with updated settings.

---

## 12. 🔐 Authentication

### 12.1 Login
**Scenario**: User logs in with credentials.

*   **Endpoint**: `POST /auth/login`
*   **Request Body**:
    ```json
    {
        "username": "admin",
        "password": "password123"
    }
    ```
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Login successful",
        "data": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "Bearer",
            "expires_in": 3600,
            "user": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "Admin",
                "permissions": ["read", "write", "delete", "manage_users"]
            }
        }
    }
    ```

### 12.2 Get Current User
*   **Endpoint**: `GET /auth/me`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response**:
    ```json
    {
        "success": true,
        "message": "User retrieved successfully",
        "data": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "Admin",
            "is_active": true,
            "last_login": "2024-12-14T10:30:00",
            "permissions": ["read", "write", "delete", "manage_users"]
        }
    }
    ```

### 12.3 Refresh Token
**Scenario**: Access token expired, get new one using refresh token.

*   **Endpoint**: `POST /auth/refresh`
*   **Request Body**:
    ```json
    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Token refreshed successfully",
        "data": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "Bearer",
            "expires_in": 3600
        }
    }
    ```

### 12.4 Change Password
**Scenario**: User changes their password.

*   **Endpoint**: `POST /auth/change-password`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Request Body**:
    ```json
    {
        "current_password": "oldpassword",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123"
    }
    ```
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Password changed successfully"
    }
    ```

### 12.5 Logout
*   **Endpoint**: `POST /auth/logout`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Logout successful"
    }
    ```

---

## 13. 👥 User Management (Admin Only)

### 13.1 List Users
*   **Endpoint**: `GET /users`
*   **Headers**: `Authorization: Bearer <admin_token>`
*   **Query**: `?is_active=true&role=Admin&search=admin`
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Users retrieved successfully",
        "data": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "Admin",
                "is_active": true,
                "last_login": "2024-12-14T10:30:00",
                "created_at": "2024-01-01T00:00:00",
                "permissions": ["read", "write", "delete", "manage_users"]
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 1,
            "pages": 1
        }
    }
    ```

### 13.2 Create User
*   **Endpoint**: `POST /users`
*   **Headers**: `Authorization: Bearer <admin_token>`
*   **Request Body**:
    ```json
    {
        "username": "newteacher",
        "password": "password123",
        "email": "teacher@school.edu",
        "role": "Teacher"
    }
    ```
*   **Response**:
    ```json
    {
        "success": true,
        "message": "User created successfully",
        "data": {
            "id": 2,
            "username": "newteacher",
            "email": "teacher@school.edu",
            "role": "Teacher",
            "is_active": true,
            "permissions": ["read", "write"]
        }
    }
    ```

### 13.3 Get User by ID
*   **Endpoint**: `GET /users/2`
*   **Headers**: `Authorization: Bearer <admin_token>`
*   **Response**:
    ```json
    {
        "success": true,
        "message": "User retrieved successfully",
        "data": {
            "id": 2,
            "username": "newteacher",
            "email": "teacher@school.edu",
            "role": "Teacher",
            "is_active": true,
            "permissions": ["read", "write"]
        }
    }
    ```

### 13.4 Update User
*   **Endpoint**: `PUT /users/2`
*   **Headers**: `Authorization: Bearer <admin_token>`
*   **Request Body**:
    ```json
    {
        "role": "Admin",
        "email": "teacher-admin@school.edu"
    }
    ```
*   **Response**:
    ```json
    {
        "success": true,
        "message": "User updated successfully",
        "data": {
            "id": 2,
            "username": "newteacher",
            "role": "Admin",
            "email": "teacher-admin@school.edu"
        }
    }
    ```

### 13.5 Delete User (Soft Delete)
*   **Endpoint**: `DELETE /users/2`
*   **Headers**: `Authorization: Bearer <admin_token>`
*   **Response**:
    ```json
    {
        "success": true,
        "message": "User deleted successfully"
    }
    ```

### 13.6 Get User Activity Log
*   **Endpoint**: `GET /users/1/activity-log`
*   **Headers**: `Authorization: Bearer <admin_token>`
*   **Query**: `?action=login` (optional filter)
*   **Response**:
    ```json
    {
        "success": true,
        "message": "Activity log retrieved successfully",
        "data": [
            {
                "id": 1,
                "action": "login",
                "resource_type": null,
                "resource_id": null,
                "details": null,
                "ip_address": "127.0.0.1",
                "created_at": "2024-12-14T10:30:00"
            },
            {
                "id": 2,
                "action": "create_user",
                "resource_type": "user",
                "resource_id": "2",
                "details": {"username": "newteacher", "role": "Teacher"},
                "ip_address": "127.0.0.1",
                "created_at": "2024-12-14T10:35:00"
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 2,
            "pages": 1
        }
    }
    ```

### 13.7 Access Denied Example
**Scenario**: Non-admin user tries to access user management.

*   **Endpoint**: `GET /users`
*   **Headers**: `Authorization: Bearer <teacher_token>` (role=Teacher)
*   **Response**:
    ```json
    {
        "success": false,
        "error": {
            "code": "ACCESS_DENIED",
            "message": "Access denied. Required role: Admin"
        }
    }
    ```
