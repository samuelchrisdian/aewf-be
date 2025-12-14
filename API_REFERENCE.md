# AEWF API Reference

## Project Overview
The **Attendance Early Warning Framework (AEWF)** API serves as the backend for a comprehensive system designed to monitor student attendance, identify at-risk students using Machine Learning, and manage school master data. It facilitates data ingestion from fingerprint machines, provides dashboards for teachers, and issues alerts for early intervention.

## Base URL
All API requests should be prefixed with the base URL.
**Default:** `http://localhost:5000`

## Authentication
The API uses **Bearer Token** authentication.
1. Obtain an access token by calling the **Login** endpoint.
2. Include the token in the `Authorization` header for all protected endpoints.

**Header Format:**
```
Authorization: Bearer <your_access_token>
```
*Most endpoints require authentication unless specified otherwise.*

---

## Response Format
### Success (200 OK)
```json
{
  "status": "success",
  "message": "Operation successful",
  "data": { ... }
}
```

### Error (4xx/5xx)
```json
{
  "status": "error",
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

---

## Endpoints

### 1. Authentication
Manage user sessions and credentials.

| Method | URL | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | User login | `username`, `password` |
| `POST` | `/api/v1/auth/logout` | User logout | - |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | `refresh_token` |
| `GET` | `/api/v1/auth/me` | Get current user info | - |
| `POST` | `/api/v1/auth/change-password` | Change password | `current_password`, `new_password`, `confirm_password` |

### 2. Dashboard
Aggregated statistics for the main view.

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/dashboard/stats` | Get overview stats (attendance, risk, counts) |

### 3. Students
Manage student master data.

| Method | URL | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/students` | List students | `page`, `per_page`, `class_id`, `search`, `sort_by` |
| `POST` | `/api/v1/students` | Create student | `nis`, `name`, `class_id` |
| `GET` | `/api/v1/students/<nis>` | Get student details | - |
| `PUT` | `/api/v1/students/<nis>` | Update student | `name`, `class_id`, `parent_phone` |
| `DELETE` | `/api/v1/students/<nis>` | Soft delete student | - |

### 4. Attendance
Manage daily attendance records.

| Method | URL | Description | Parameters/Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/attendance/daily` | Get daily records | `date`, `class_id`, `status` |
| `POST` | `/api/v1/attendance/manual` | Manual entry | `student_nis`, `date`, `status`, `notes` |
| `PUT` | `/api/v1/attendance/<id>` | Update record | `status`, `check_in`, `check_out` |
| `GET` | `/api/v1/attendance/student/<nis>` | Student history | `start_date`, `end_date`, `month` |
| `GET` | `/api/v1/attendance/summary` | Aggregate summary | `period`, `class_id` |

### 5. Risk Management (EWS)
Monitor at-risk students and alerts.

| Method | URL | Description | Parameters/Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/risk/list` | List at-risk students | `level`, `class_id` |
| `GET` | `/api/v1/risk/<nis>` | Student risk detail | - |
| `GET` | `/api/v1/risk/alerts` | Get risk alerts | `status`, `class_id` |
| `POST` | `/api/v1/risk/alerts/<id>/action` | Take action | `action`, `notes`, `status` |
| `GET` | `/api/v1/risk/history/<nis>` | Risk score history | - |
| `POST` | `/api/v1/risk/recalculate` | Trigger EWS engine | `class_id`, `student_nis` |

### 6. Machines
Manage fingerprint devices.

| Method | URL | Description | Parameters/Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/machines` | List machines | `status`, `search` |
| `POST` | `/api/v1/machines` | Register machine | `machine_code`, `location` |
| `GET` | `/api/v1/machines/<id>` | Get machine detail | - |
| `PUT` | `/api/v1/machines/<id>` | Update machine | `location`, `status` |
| `DELETE` | `/api/v1/machines/<id>` | Delete machine | - |
| `GET` | `/api/v1/machines/<id>/users` | Get machine users | `mapped` (bool), `search` |

### 7. User Mapping
Link machine users to students.

| Method | URL | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/mapping/unmapped` | Unmapped users | `machine_id`, `include_suggestions` |
| `POST` | `/api/v1/mapping/bulk-verify` | Verify mappings | `mappings` array |
| `GET` | `/api/v1/mapping/stats` | Mapping statistics | - |
| `DELETE` | `/api/v1/mapping/<id>` | Delete mapping | - |

### 8. Analytics
Advanced reporting and trends.

| Method | URL | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/analytics/trends` | Attendance trends | `period` (weekly/monthly) |
| `GET` | `/api/v1/analytics/class-comparison` | Class performance | `period` (YYYY-MM) |
| `GET` | `/api/v1/analytics/student-patterns/<nis>` | Individual patterns | - |

### 9. Reports
Generate downloadable reports.

| Method | URL | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/attendance` | Attendance report | `format` (json/excel), `start_date`, `end_date` |
| `GET` | `/api/v1/reports/risk` | Risk assessment | `format`, `class_id` |
| `GET` | `/api/v1/reports/class-summary` | Class summary | `start_date`, `end_date` |

### 10. Export
Data export utilities.

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/export/students` | Export student list (Excel) |
| `GET` | `/api/v1/export/attendance` | Export raw attendance (Excel) |
| `GET` | `/api/v1/export/template/master` | Get import template |

### 11. Classes
Manage school classes.

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/classes` | List classes |
| `POST` | `/api/v1/classes` | Create class |
| `GET` | `/api/v1/classes/<id>` | Get class details |
| `PUT` | `/api/v1/classes/<id>` | Update class |
| `DELETE` | `/api/v1/classes/<id>` | Delete class |

### 12. Teachers
Manage teacher data.

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/teachers` | List teachers |
| `POST` | `/api/v1/teachers` | Create teacher |
| `GET` | `/api/v1/teachers/<id>` | Get teacher details |
| `PUT` | `/api/v1/teachers/<id>` | Update teacher |
| `DELETE` | `/api/v1/teachers/<id>` | Delete teacher |

### 13. Users
System user administration (Admin only).

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/users` | List system users |
| `POST` | `/api/v1/users` | Create user |
| `GET` | `/api/v1/users/<id>` | Get user details |
| `PUT` | `/api/v1/users/<id>` | Update user |
| `DELETE` | `/api/v1/users/<id>` | Delete user |
| `GET` | `/api/v1/users/<id>/activity-log` | View user activity |

### 14. Notifications
In-app notifications.

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/notifications` | Get notifications |
| `POST` | `/api/v1/notifications/send` | Send new notification |
| `PUT` | `/api/v1/notifications/<id>/read` | Mark as read |
| `DELETE` | `/api/v1/notifications/<id>` | Delete notification |
| `GET` | `/api/v1/notifications/settings` | Get preferences |
| `PUT` | `/api/v1/notifications/settings` | Update preferences |

### 15. System Configuration
Global settings and calendar.

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/config/settings` | Get system settings |
| `PUT` | `/api/v1/config/settings` | Update settings (Admin) |
| `GET` | `/api/v1/config/school-calendar` | Get calendar/holidays |
| `POST` | `/api/v1/config/holidays` | Add holiday |
| `DELETE` | `/api/v1/config/holidays/<id>` | Remove holiday |

### 16. ML Models
Machine learning model management.

| Method | URL | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/models/info` | Get model status |
| `GET` | `/api/v1/models/performance` | Get accuracy metrics |
| `POST` | `/api/v1/models/retrain` | Trigger retraining |

---

## Example Usage

### Authenticate and Get Student List
```bash
# 1. Login to get token
TOKEN=$(curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin", "password":"password123"}' \
  | grep -o '"access_token": "[^"]*' | cut -d'"' -f4)

# 2. Get Students using the token
curl -X GET http://localhost:5000/api/v1/students \
  -H "Authorization: Bearer $TOKEN"
```
