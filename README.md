# AEWF Backend Service (Flask)

> **API Version:** 1.0 | **ML Version:** v2.1 | **Last Updated:** 2026-01-09

Backend service for the **Attendance Early Warning Framework (AEWF)** system. Built with **Flask**, **PostgreSQL**, and **scikit-learn**, this service handles data processing, machine learning model training, and provides APIs for the frontend dashboard.

## 📋 Features

- **Master Data Management (MDM)**:
  - Manage Students, Teachers, and Class data.
  - Bulk import from Excel templates.
- **Machine & User Synchronization**:
  - Sync user data from attendance machines.
  - **Machine Management**: Full CRUD support for fingerprint machines and user tracking.
  - **Fuzzy Mapping Engine**: Automatically map raw machine users to registered students with fuzzy logic and confidence scoring.
  - **Enhanced Mapping Dashboard**: Bulk verification, statistics, and manual mapping management.
- **Data Ingestion Pipeline**:
  - Import raw attendance logs from multiple machine types.
  - Automatic cleaning and processing of daily attendance.
- **Early Warning System (EWS)**:
  - Real-time risk assessment engine.
  - Hybrid rule-based and ML-based risk scoring.
  - Automated alert generation (`risk_alerts`) and history tracking (`risk_history`).
- **Notifications System**:
  - In-app notification center for teachers and parents.
  - Multi-channel support (In-App, Email, SMS).
  - User-configurable notification settings per teacher.
- **Authentication & User Management**:
  - JWT-based authentication with access and refresh tokens.
  - Role-based access control (Admin, Teacher, Staff).
  - Password hashing with bcrypt.
  - Activity logging for audit trails.
- **System Configuration**:
  - Configurable attendance rules (late threshold, grace period, school hours).
  - Risk assessment thresholds and notification settings.
  - School calendar and holiday management.
  - Import batch management with rollback support.
- **Architecture**:
  - Modular Flask Blueprint design.
  - SQLAlchemy ORM with PostgreSQL.
  - Application Factory pattern.

## 📂 Directory Structure

```
be-flask/
├── migrations/         # Database migration scripts (Alembic)
├── src/
│   ├── api/
│   │   └── v1/         # API Routes & Controllers
│   ├── app/            # App setup, config, extensions
│   ├── domain/         # SQLAlchemy Database Models
│   ├── ews/            # Early Warning System Logic
│   ├── ml/             # Machine Learning Modules
│   ├── repositories/   # Data Access Layer
│   ├── seeders/        # Database Seeders (Test Data Generation)
│   ├── schemas/        # Marshmallow Schemas
│   ├── services/       # Business Logic & Orchestration
│   └── utils/          # Utility functions
├── tests/
│   ├── datasets/       # Generated Excel test files
│   ├── factories/      # Test data factories
│   ├── integration/    # Integration tests
│   └── unit/           # Unit tests
├── .env.example        # Environment variables template
├── app.py              # Application entry point
└── requirements.txt    # Python dependencies
```

## 🗄️ Database Schema

### `classes`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `class_id` | String | PK, Index | Unique Class ID |
| `class_name` | String | Not Null | Name of the Class |
| `wali_kelas_id` | String | FK (`teachers.teacher_id`) | ID of the homeroom teacher |

### `teachers`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `teacher_id` | String | PK, Index | Unique Teacher ID |
| `name` | String | Not Null | Teacher Name |
| `role` | String | Default: 'Teacher' | Role (e.g., Wali Kelas) |

### `students`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `nis` | String | PK, Index | Student ID Number |
| `name` | String | Not Null | Student Name |
| `class_id` | String | FK (`classes.class_id`) | Class ID |
| `parent_phone` | String | Nullable | Parent's Phone Number |
| `is_active` | Boolean | Default: True | Student Active Status |

### `users` (System Users)
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique User ID |
| `username` | String | Unique, Not Null | Username for login |
| `password_hash` | String | Not Null | Hashed Password (bcrypt) |
| `email` | String | Nullable | User Email |
| `role` | String | Default: Admin | User Role (Admin, Teacher, Staff) |
| `is_active` | Boolean | Default: True | Account Active Status |
| `last_login` | DateTime | Nullable | Last Login Timestamp |
| `refresh_token` | String | Nullable | JWT Refresh Token |
| `created_at` | DateTime | Nullable | Creation Timestamp |
| `updated_at` | DateTime | Nullable | Last Update Timestamp |

### `activity_logs` (Audit Trail)
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique Log ID |
| `user_id` | Integer | FK (`users.id`) | User who performed action |
| `action` | String | Not Null | Action type (login, logout, etc.) |
| `resource_type` | String | Nullable | Type of resource affected |
| `resource_id` | String | Nullable | ID of affected resource |
| `details` | JSON | Nullable | Additional context |
| `ip_address` | String | Nullable | Client IP Address |
| `user_agent` | String | Nullable | Client User Agent |
| `created_at` | DateTime | Not Null | Timestamp |

### `machines`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigInteger | PK | Unique ID |
| `machine_code` | String | Unique, Not Null | Hardware Machine Code |
| `location` | String | Nullable | Machine Location |

### `machine_users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigInteger | PK | Unique ID |
| `machine_id` | BigInteger | FK (`machines.id`) | Reference to Machine |
| `machine_user_id` | String | Not Null | ID registered in the Machine |
| `machine_user_name`| String | Nullable | Name registered in Machine |
| `department` | String | Nullable | Department info |

### `student_machine_maps` (Fuzzy Mapping)
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigInteger | PK | Unique ID |
| `machine_user_id_fk`| BigInteger | FK, Unique | Reference to Machine User |
| `student_nis` | String | FK (`students.nis`) | Mapped Student |
| `status` | String | Nullable | Mapping Status |
| `confidence_score` | Integer | Nullable | Confidence Score (0-100) |
| `verified_at` | DateTime | Nullable | Verification Time |
| `verified_by` | String | Nullable | Verifying User |

### `attendance_raw_logs`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigInteger | PK | Unique ID |
| `batch_id` | Integer | FK (`import_batches.id`) | Import Batch Reference |
| `machine_user_id_fk`| BigInteger | FK (`machine_users.id`) | Reference to Mapped User |
| `event_time` | DateTime | Not Null | Time of attendance event |
| `raw_data` | JSON | Nullable | Original raw data payload |

### `attendance_daily`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique Record ID |
| `student_nis` | String | FK (`students.nis`), Index | Student ID |
| `attendance_date` | Date | Not Null | Date of attendance |
| `check_in` | DateTime | Nullable | First Check-in Time |
| `check_out` | DateTime | Nullable | Last Check-out Time |
| `status` | String | Not Null | Final Status (Present, Absent, Late, Sick, Permission) |
| `notes` | String | Nullable | Manual entry notes |
| `recorded_by` | String | FK (`teachers.teacher_id`) | Teacher who recorded the entry |

### `import_batches`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK | Unique Batch ID |
| `filename` | String | Not Null | Imported Filename |
| `file_type` | String | Not Null | Type (MASTER, ATTENDANCE) |
| `status` | String | Nullable | Processing Status |
| `records_processed`| Integer | Nullable | Number of records handled |
| `error_log` | JSON | Nullable | Log of processing errors |

### `risk_alerts`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique Alert ID |
| `student_nis` | String | FK (`students.nis`) | Student ID |
| `alert_type` | String | Not Null | Type (High Risk, etc) |
| `message` | String | Not Null | Alert Message |
| `status` | String | Default: pending | Status (pending, acknowledged, resolved) |
| `assigned_to` | String | FK (`teachers.teacher_id`) | Teacher assigned |
| `action_taken` | String | Nullable | Action taken |
| `follow_up_date`| Date | Nullable | Scheduled follow-up |

### `risk_history`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK | Unique ID |
| `student_nis` | String | FK (`students.nis`) | Student ID |
| `risk_level` | String | Not Null | Risk Level (High, Medium, Low) |
| `risk_score` | Integer | Not Null | Score (0-100) |
| `factors` | JSON | Nullable | Contributing factors (includes `explanation_text`) |
| `calculated_at`| DateTime | Not Null | Calculation time |

### `notifications`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique Notification ID |
| `recipient_type` | String | Not Null | 'teacher' or 'parent' |
| `recipient_id` | String | Index | Teacher ID or Parent Phone |
| `type` | String | Not Null | Type (risk_alert, attendance, etc) |
| `title` | String | Not Null | Title |
| `message` | String | Not Null | Body content |
| `priority` | String | Default: normal | High, Normal, Low |
| `is_read` | Boolean | Default: False | Read status |

### `notification_settings`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique Settings ID |
| `user_id` | Integer | FK (`users.id`), Unique | User/Teacher ID |
| `enable_risk_alerts`| Boolean | Default: True | Toggle risk alerts |
| `enable_attendance` | Boolean | Default: True | Toggle attendance alerts |
| `daily_digest_time` | String | Default: 07:00 | Preferred digest time |

### `system_config` (Settings)
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `key` | String | PK | Setting key name |
| `value` | JSON | Not Null | Setting value (JSON) |
| `category` | String | Not Null, Index | Category (attendance, risk, notification) |
| `description` | String | Nullable | Setting description |
| `updated_at` | DateTime | Nullable | Last update timestamp |
| `updated_by` | Integer | FK (`users.id`) | User who updated |

### `school_holidays`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique Holiday ID |
| `date` | Date | Unique, Index | Holiday date |
| `name` | String | Not Null | Holiday name |
| `type` | String | Default: holiday | Type (holiday, break, event) |
| `created_at` | DateTime | Default: now | Creation timestamp |
| `created_by` | Integer | FK (`users.id`) | User who created |

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12+

### Step 1: Clone the Repository
```bash
git clone <repository_url>
cd be-flask
```

### Step 2: Create a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Environment Configuration
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   # On Windows Command Prompt: copy .env.example .env
   ```
2. Update `.env` with your PostgreSQL credentials:
   ```ini
   DATABASE_URL=postgresql://username:password@localhost:5432/aewf_db
   ```
   *Note: Ensure the database `aewf_db` exists or is created before running.*

### Step 5: Initialize Database
Run the following to apply existing migrations:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## ▶️ Running the Application

Start the Flask development server:
```bash
python app.py
```
The server will start at `http://localhost:5000`.

## 📡 API Endpoints (v1)

All endpoints are prefixed with `/api/v1` and require authentication token (Header: `Authorization: <token>`).

### 🏫 Master Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/students` | Get list of students. Query: `?page=1&per_page=20&class_id=&is_active=true\|false&search=&sort_by=name\|nis\|class_id&order=asc\|desc` |
| `POST` | `/students` | Create a new student. Body: `{"nis": "...", "name": "...", "class_id": "...", "parent_phone": "...", "is_active": true}` |
| `GET` | `/students/<nis>` | Get student details with attendance summary. |
| `PUT` | `/students/<nis>` | Update student details. |
| `DELETE` | `/students/<nis>` | Soft delete student (set is_active=false). |
| `GET` | `/teachers` | Get list of teachers. Query: `?role=Wali Kelas` |
| `POST` | `/teachers` | Create a new teacher. Body: `{"teacher_id": "...", "name": "...", "role": "...", "phone": "..."}` |
| `GET` | `/teachers/<id>` | Get teacher details with managed classes. |
| `PUT` | `/teachers/<id>` | Update teacher details. |
| `DELETE` | `/teachers/<id>` | Delete teacher (if not assigned to class). |
| `GET` | `/classes` | Get list of classes with student count. |
| `POST` | `/classes` | Create a new class. Body: `{"class_id": "...", "class_name": "...", "wali_kelas_id": "..."}` |
| `GET` | `/classes/<id>` | Get class details with wali kelas and stats. |
| `PUT` | `/classes/<id>` | Update class details. |
| `DELETE` | `/classes/<id>` | Delete class (if empty). |

### 📥 Data Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/import/master` | Upload Master Data Excel (Students, Classes, Teachers). |
| `POST` | `/import/master/preview` | Preview Master Data Excel before import. Returns classes, students, teachers with status (new/exists). |
| `POST` | `/import/users-sync` | Upload Machine User export to sync machine users. Params: `machine_code` |
| `POST` | `/import/users-sync/preview` | Preview Machine Users before sync. Params: `machine_code`. Returns users with status (new/exists). |
| `POST` | `/import/attendance` | Upload Attendance Logs CSV/Excel. Params: `machine_code` |
| `POST` | `/import/attendance/preview` | Preview Attendance Logs before import. Params: `machine_code`. Returns format, period, users, log counts. |


### 🖨️ Machine Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/machines` | List machines. Query: `?page=1&per_page=20&status=active\|inactive&search=&sort_by=machine_code\|location&order=asc\|desc` |
| `POST` | `/machines` | Create a new machine. Body: `{"machine_code": "...", "location": "...", "status": "active\|inactive"}` |
| `GET` | `/machines/<id>` | Get machine details with user count. |
| `PUT` | `/machines/<id>` | Update machine details. Body: `{"location": "...", "status": "..."}` |
| `DELETE` | `/machines/<id>` | Delete machine. |
| `GET` | `/machines/<id>/users` | List users on a machine. Query: `?page=1&per_page=20&search=&mapped=true\|false` |
| `DELETE` | `/machines/<id>/users/<user_id>` | Delete a machine user. |

### 🔍 Fuzzy Mapping
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/mapping/unmapped` | List unmapped machine users. Query: `?page=1&per_page=20&machine_id=&include_suggestions=true\|false` |
| `GET` | `/mapping/unmapped-students` | List students without any mapping. Query: `?page=1&per_page=20&class_id=&search=&is_active=true\|false` |
| `GET` | `/mapping/list` | Get all mappings. Query: `?page=1&per_page=20&status=verified\|suggested\|rejected&machine_id=&class_id=&search=` |
| `POST` | `/mapping/manual` | Create a single manual mapping. Body: `{"machine_user_id": 123, "student_nis": "2024001", "status": "verified"}` |
| `POST` | `/mapping/bulk-create` | Create multiple mappings at once. Body: `{"mappings": [{"machine_user_id": 123, "student_nis": "2024001"}, ...]}` |
| `POST` | `/mapping/bulk-verify` | Bulk verify/reject mappings. Body: `{"mappings": [{"mapping_id": 1, "status": "verified"}, ...]}` |
| `GET` | `/mapping/stats` | Get mapping statistics (total, mapped, verified, suggested counts). |
| `GET` | `/mapping/<id>` | Get mapping details. |
| `DELETE` | `/mapping/<id>` | Delete a mapping. |
| `DELETE` | `/mapping/student/<nis>` | Remove mapping for a student (unmap). |
| `POST` | `/mapping/process` | Run auto-mapping engine (Legacy). |
| `GET` | `/mapping/suggestions` | Get list of mapping suggestions (Legacy). |
| `POST` | `/mapping/verify` | Verify or reject a mapping suggestion (Legacy). |

### 📅 Attendance Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/attendance/daily` | Get daily attendance list. Query: `?date=YYYY-MM-DD&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&class_id=&status=Present\|Absent\|Late\|Sick\|Permission&page=1&per_page=20&paginate=true\|false` |
| `GET` | `/attendance/student/<nis>` | Get attendance history for a specific student. Query: `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&month=YYYY-MM` |
| `POST` | `/attendance/manual` | Create a manual attendance entry. Body: `{"student_nis": "...", "attendance_date": "YYYY-MM-DD", "status": "Sick\|Permission\|..."}` |
| `PUT` | `/attendance/<id>` | Update an attendance record. Body: `{"status": "...", "check_in": "...", "check_out": "...", "notes": "..."}` |
| `GET` | `/attendance/summary` | Get aggregated attendance summary with daily breakdown. Query: `?class_id=&period=YYYY-MM&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` |

### 📊 Dashboard & Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard/stats` | Get complete dashboard statistics. Returns: overview (entity counts), today_attendance, this_month (monthly stats), risk_summary. *Note: Admin sees all data, Teacher sees only their classes.* |
| `GET` | `/analytics/trends` | Get attendance trend data for charts. Query: `?period=weekly\|monthly&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`. *Role-based filtering applies.* |
| `GET` | `/analytics/class-comparison` | Get class-by-class attendance comparison. Query: `?period=YYYY-MM`. *Role-based filtering applies.* |
| `GET` | `/analytics/student-patterns/<nis>` | Get individual student attendance patterns (summary, weekly analysis, trend direction, consecutive absences). |

### 🚨 Risk Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/risk/list` | List at-risk students. Query: `?level=high\|medium\|low&class_id=&page=1&per_page=20` |
| `GET` | `/risk/<nis>` | Get detailed risk profile for a student (ML prediction, factors, recommendations). |
| `GET` | `/risk/alerts` | Get risk alerts. Query: `?status=pending\|acknowledged\|resolved&class_id=&page=1&per_page=20` |
| `GET` | `/risk/alerts/actioned` | Get actioned alerts (acknowledged/resolved). Query: `?class_id=&action_type=&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&page=1&per_page=20` |
| `POST` | `/risk/alerts/<id>/action` | Take action on an alert. Body: `{"action": "...", "notes": "...", "follow_up_date": "YYYY-MM-DD", "status": "acknowledged\|resolved"}` |
| `GET` | `/risk/history/<nis>` | Get historical risk scores for a student. |
| `POST` | `/risk/recalculate` | Trigger batch risk recalculation. Body: `{"class_id": "...", "student_nis": "..."}` (optional filters) |

### 🤖 ML Model Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/models/info` | Get installed ML models info (model type, version, training date). |
| `GET` | `/models/performance` | Get model performance metrics (recall, F1, AUC-ROC, threshold, feature importance). |
| `POST` | `/models/retrain` | Trigger retraining of ML models. |
| `POST` | `/models/train` | Alias for `/models/retrain`. |
| `GET` | `/models/predict/<nis>` | Get ML risk prediction for a specific student (tier, probability, factors). |
| `GET` | `/models/features` | Get feature importance from the trained model (coefficient weights). |

### 📄 Reports & Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/reports/attendance` | Generate attendance report. Query: `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&format=json\|excel&class_id=&student_nis=` |
| `GET` | `/reports/risk` | Generate risk report with at-risk students. Query: `?format=json\|excel&class_id=` |
| `GET` | `/reports/class-summary` | Generate class summary report. Query: `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&format=json\|excel` |
| `GET` | `/export/students` | Export students to Excel file. Query: `?class_id=` (optional) |
| `GET` | `/export/attendance` | Export attendance records to Excel. Query: `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&class_id=` (optional) |
| `GET` | `/export/template/master` | Download master data import template (Excel with Students, Classes, Teachers sheets). |

### 🔔 Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/notifications` | List notifications. Query: `?is_read=true\|false`, `?page=1` |
| `POST` | `/notifications/send` | Send a new notification content. |
| `PUT` | `/notifications/<id>/read` | Mark a notification as read. |
| `DELETE` | `/notifications/<id>` | Delete a notification. |
| `GET` | `/notifications/settings` | Get user notification preferences. |
| `PUT` | `/notifications/settings` | Update notification preferences. |

### 🔐 Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | User login. Returns access token and refresh token. |
| `POST` | `/auth/logout` | User logout. Invalidates refresh token. |
| `POST` | `/auth/refresh` | Refresh access token using refresh token. |
| `GET` | `/auth/me` | Get current authenticated user info. |
| `POST` | `/auth/change-password` | Change user password. |

### 👥 User Management (Admin Only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users` | List all users. Query: `?is_active=true\|false`, `?role=Admin\|Teacher\|Staff`, `?search=` |
| `POST` | `/users` | Create a new user. Body: `{"username": "...", "password": "...", "role": "...", "email": "..."}` |
| `GET` | `/users/<id>` | Get user details. |
| `PUT` | `/users/<id>` | Update user details. |
| `DELETE` | `/users/<id>` | Soft delete user (sets is_active=false). |
| `GET` | `/users/<id>/activity-log` | Get user activity log. Query: `?action=login\|logout\|password_change` |

### ⚙️ System Configuration (Admin Only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/config/settings` | Get all system settings (attendance rules, risk thresholds, notification settings). |
| `PUT` | `/config/settings` | Update system settings. Body: `{"attendance_rules": {...}, "risk_thresholds": {...}}` |
| `GET` | `/config/school-calendar` | Get school calendar with holidays. Query: `?year=2024` |
| `POST` | `/config/holidays` | Add a school holiday. Body: `{"date": "YYYY-MM-DD", "name": "...", "type": "holiday\|break\|event"}` |
| `DELETE` | `/config/holidays/<id>` | Remove a school holiday. |

### 📦 Import Batch Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/import/batches` | List import batches. Query: `?file_type=logs\|master\|users`, `?status=completed\|failed` |
| `GET` | `/import/batches/<id>` | Get batch details with error logs. |
| `DELETE` | `/import/batches/<id>` | Delete batch and raw logs. (Admin only) |
| `POST` | `/import/batches/<id>/rollback` | Rollback batch - delete raw logs. (Admin only) |

## 🧪 Testing

To run the test suite:
```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

---

## 🧠 Machine Learning Architecture

This project implements a **scientifically rigorous Early Warning System (EWS)** using Machine Learning to predict student dropout risks based on attendance patterns, with proper validation methodology to prevent data leakage and overfitting.

### 📊 Success Criteria (Thesis Targets)
| Metric | Target | Status |
|--------|--------|--------|
| Recall (At-Risk) | ≥ 0.70 | ✅ Meets target |
| F1-Score | ≥ 0.65 | ✅ Meets target |
| AUC-ROC | ≥ 0.75 | ✅ Meets target |
| API Response | < 3 sec | ✅ <100ms |

> **Model Version v3**: Proper validation methodology (Train/Val/Test 60/20/20) + no target leakage (removed direct label-defining features).

### 1. Feature Engineering (`src/ml/preprocessing.py`)

The system automatically extracts **10 behavioral features** from daily attendance logs, **excluding features that directly define the label** to prevent target leakage:

| Feature | Description | Used in Model |
|---------|-------------|---------------|
| `late_count` | Count of 'Late' check-ins | ✅ Yes |
| `present_count` | Count of 'Present' check-ins | ✅ Yes |
| `permission_count` | Count of 'Permission' status | ✅ Yes |
| `sick_count` | Count of 'Sick' status | ✅ Yes |
| `total_days` | **Global active days** (days with ≥50% students) | ✅ Yes |
| `attendance_ratio` | Presence rate (0.0-1.0) | ✅ Yes |
| `trend_score` | 7-day trend (-1 to +1) | ✅ Yes |
| `is_rule_triggered` | Rule-based override flag | ✅ Yes |
| `recording_completeness` | Recorded days / Expected days (0.0-1.0) | ✅ Yes |
| `longest_gap_days` | Max consecutive active days without record | ✅ Yes |
| `absent_count` | Total explicit absences | ❌ Excluded (target leakage) |
| `absent_ratio` | Absence rate (0.0-1.0) | ❌ Excluded (target leakage) |
| `late_ratio` | Late rate (0.0-1.0) | ❌ Excluded (target leakage) |

> **Rationale**: Features like `absent_ratio` and `absent_count` directly define the at-risk label (e.g., label = `absent_ratio > 0.15`), causing the model to simply memorize the rule instead of learning patterns. We use derivative behavioral signals instead.

#### 🔑 Temporal Cutoff Support
The preprocessing function supports `cutoff_date` parameter for temporal split validation:
```python
features = engineer_features_from_df(df, cutoff_date='2024-10-01')
# Only uses records BEFORE cutoff_date to prevent temporal leakage
```

### 2. Model Training & Validation (`src/ml/training.py`)

#### Validation Methodology

| Aspect | Implementation | Purpose |
|--------|----------------|---------|
| **Split Strategy** | GroupShuffleSplit 60/20/20 by `student_nis` | Prevent same student in train/test (no data leakage) |
| **CV Method** | StratifiedGroupKFold (3-fold) or GroupKFold fallback | Robust performance estimation with stratified class distribution |
| **Threshold Tuning** | On validation/OOF predictions | Protect test set from contamination |
| **SMOTE Placement** | Training folds only | Preserve real-world class distribution in validation |
| **Test Isolation** | Single evaluation, frozen threshold | Unbiased final metrics |
| **Uncertainty Reporting** | Bootstrap 95% CI (1000 iterations) | Account for small sample size (n~89) |

#### Training Pipeline

```
┌────────────────────────────────────────────────────────────┐
│                   TRAINING PIPELINE (v3)                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. Load & Engineer Features (10 features, no leakage)    │
│  2. Create Labels (late_count>3 OR attendance_ratio<0.85) │
│  3. GroupShuffleSplit: Train│Val│Test (60/20/20)          │
│     └── by student_nis (no student in both train & test)  │
│                                                            │
│  4. StratifiedGroupKFold CV on Train+Val (3 folds)        │
│     ├── For each fold:                                     │
│     │   ├── SMOTE on train_fold only                       │
│     │   ├── Train Logistic Regression                      │
│     │   └── Predict on val_fold (OOF)                      │
│     └── Collect all OOF predictions                        │
│                                                            │
│  5. Tune Threshold on OOF (maximize F1, Recall ≥ 0.70)    │
│     └── Range: 0.30 - 0.70, step 0.05                     │
│                                                            │
│  6. Train Final Model on Train+Val                        │
│     └── With frozen threshold from step 5                 │
│                                                            │
│  7. Evaluate on Test Set (ONE TIME, isolated)             │
│     ├── Apply frozen threshold                            │
│     └── Bootstrap 95% CI (1000 iterations)                │
│                                                            │
│  8. Save: ews_model.pkl, explainer_tree.pkl, metadata     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### Algorithms
- **Primary Model**: Logistic Regression (`class_weight='balanced'`, max_iter=1000)
- **Explainer Model**: Decision Tree (max_depth=4) for interpretability
- **Imbalance Handling**: SMOTE with fallback to RandomOverSampler
- **Class Weighting**: Balanced to handle minority class

#### Model Outputs

| File | Location | Contents |
|------|----------|----------|
| `ews_model.pkl` | `models/` | Trained Logistic Regression (pickle) |
| `ews_explainer_tree.pkl` | `models/` | Decision Tree for explainability |
| `model_metadata.json` | `models/` | CV metrics (mean±std), test metrics (with 95% CI), threshold, feature importance |

**Example Metadata:**
```json
{
  "model_version": "v3",
  "split_method": "grouped",
  "threshold": 0.45,
  "threshold_source": "validation_oof",
  "features_excluded": ["absent_ratio", "absent_count", "late_ratio"],
  "cv_metrics": {
    "recall_mean": 0.85,
    "recall_std": 0.05,
    "f1_mean": 0.78,
    "f1_std": 0.04
  },
  "test_metrics": {
    "recall": 0.88,
    "f1": 0.82,
    "precision": 0.77,
    "bootstrap_ci": {
      "recall": [0.75, 0.95],
      "f1": [0.68, 0.91]
    }
  }
}
```

### 3. Hybrid Risk Prediction (`src/services/ml_service.py`)
The system uses a **hybrid approach** combining rules and ML:

```
┌─────────────────────────────────────────────────────────┐
│                   PREDICTION FLOW                       │
├─────────────────────────────────────────────────────────┤
│ 1. Engineer features (derivative signals only)         │
│ 2. RULE CHECK: is_rule_triggered flag?                 │
│    ├── YES → 🔴 RED (Rule Override)                    │
│    └── NO  → Continue to ML                            │
│ 3. ML CHECK: model.predict_proba()                     │
│    ├── prob > 0.70 → 🔴 RED                            │
│    ├── prob > 0.40 → 🟡 YELLOW                         │
│    └── else        → 🟢 GREEN                          │
└─────────────────────────────────────────────────────────┘
```

### 4. Risk Tiers
| Tier | Color | Threshold | Recommended Action |
|------|-------|-----------|-------------------|
| RED | 🔴 | Prob > 0.70 or Rule Triggered | Contact parent immediately |
| YELLOW | 🟡 | Prob 0.40 - 0.70 | Close monitoring for 2 weeks |
| GREEN | 🟢 | Prob < 0.40 | Regular monitoring |

### 5. Explainability (`src/ml/interpretation.py`)
The system generates **Indonesian natural language explanations** for teachers:

```
Faktor Utama Risiko (Berdasarkan Bobot):
- Total Ketidakhadiran tergolong tinggi (6 hari).
- Tren Kehadiran memburuk dalam 7 hari terakhir.

Logika Deteksi (Aturan):
- Keterlambatan > 3 kali
- Tren Kehadiran (Mingguan) ≤ -0.50
```

**How it works:**
- Analyzes Logistic Regression coefficients to identify top 3 contributing factors
- Extracts Decision Tree decision path to show IF-THEN rules
- Translates technical feature names to readable Indonesian
- **Saved to `risk_history.factors` JSON** for historical tracking

### 6. Limitations

The following limitations are transparently disclosed for academic rigor:

1. **Small Sample Size**: Dataset contains ~90 students from one school, limiting statistical power. Test set contains only 18 students (5 at-risk), resulting in **wide bootstrap confidence intervals**. For example, test F1-Score: 0.77 (95% CI: [0.40, 1.00]) with 60% range indicates metrics may vary considerably with new data.

2. **Test Set Uncertainty**: Perfect test recall (1.00) achieved on small test set (n=5 at-risk students) with FN=0. While bootstrap resampling confirms this result is stable within current data, **metrics may not generalize** to larger cohorts or schools with different risk distributions.

3. **Threshold Selection Constraints**: Model trained with target Recall ≥ 0.70 as primary constraint. Optimal threshold (0.50) balances precision and recall, but audit showed previous threshold (0.30) was overly aggressive (69% more false positives without benefit). For details, see [ML_VALIDATION_AUDIT_REPORT.md](./ML_VALIDATION_AUDIT_REPORT.md).

4. **Feature Reliance**: Model shows strong reliance on behavioral count features (`late_count`, `present_count`, `total_days`). While ablation studies confirm no single-feature dependency, the large separation between at-risk (mean late_count=4.7) and normal students (mean late_count=1.0) enables high accuracy but may not generalize to schools with different attendance cultures.

5. **Generalization Scope**: Model trained on single-school data. External validation needed before deployment to other schools with different attendance patterns, student demographics, or institutional policies.

6. **Label Definition**: At-risk labels are derived from attendance thresholds (e.g., `late_count > 3`, `attendance_ratio < 0.85`), not actual dropout outcomes. Model learns to predict threshold-based risk, not confirmed dropout events.

7. **Feature Aggregation**: Current features aggregate entire attendance history per student. For production deployment, time-windowed features (e.g., "last 30 days") would better support continuous monitoring and early detection.

8. **Class Imbalance**: Minority class (at-risk students) comprises ~31% of dataset. SMOTE is applied to training data only during cross-validation. Real-world deployment may encounter varying class distributions requiring model recalibration.

For detailed ML validation audit findings, see [ML_VALIDATION_AUDIT_REPORT.md](./ML_VALIDATION_AUDIT_REPORT.md).  
For ML methodology documentation, see [ML_FLOW_GUIDE.md](./ML_FLOW_GUIDE.md).

---

## 🌱 Database Seeders

The project includes a comprehensive test data seeder package for generating realistic test data for end-to-end testing.

### Seeder Package Structure

```
src/seeders/
├── __init__.py           # Package exports
├── base_seeder.py        # Abstract base class
├── master_seeder.py      # Teachers, Classes, Students
├── machine_seeder.py     # Machine, MachineUsers
├── attendance_seeder.py  # ImportBatch, AttendanceRawLog
├── mapping_seeder.py     # StudentMachineMap suggestions
├── excel_generator.py    # Excel file generation
└── run_seeders.py        # Click CLI entry point
```

### CLI Commands

```bash
# Show all available commands
py -m src.seeders.run_seeders --help

# Run all seeders (recommended: clear existing data first)
py -m src.seeders.run_seeders seed-all --clear

# Individual seeders
py -m src.seeders.run_seeders seed-master      # Teachers, Classes, Students
py -m src.seeders.run_seeders seed-machine     # Machine and MachineUsers
py -m src.seeders.run_seeders seed-attendance  # Attendance logs (14 days)
py -m src.seeders.run_seeders seed-mapping     # Mapping suggestions

# Generate Excel test files
py -m src.seeders.run_seeders generate-excel
```

### Generated Test Data

After running `seed-all`, the database will contain:

| Table               | Records | Details                             |
|---------------------|---------|-------------------------------------|
| `teachers`          | 5       | 3 wali kelas + 2 subject teachers   |
| `classes`           | 3       | 9A, 9B, 9C                          |
| `students`          | 30      | 10 per class (NIS 2024001-2024030)  |
| `machines`          | 1       | MAIN_GATE                           |
| `machine_users`     | 40      | 20 perfect + 10 typo + 10 unmapped  |
| `import_batches`    | ~10     | One per weekday (last 14 days)      |
| `attendance_raw_logs` | ~600  | Realistic check-in/out patterns     |
| `student_machine_maps` | 30   | 20 verified + 10 suggested          |

### Machine User Categories

The seeder creates three categories of machine users for testing fuzzy mapping:

1. **Perfect Matches (20 users)**: Exact name matches with students
2. **Typo/Variations (10 users)**: Intentional typos for fuzzy matching testing
   - Example: "Graciela Putri" → "Graciella Putri"
3. **Unmapped Users (10 users)**: Staff/guests that should remain unmapped

### Attendance Patterns

The seeder generates realistic attendance patterns:
- **90%** check-in on-time (07:15 - 07:45)
- **10%** check-in late (07:45 - 08:30)
- **5%** completely absent
- **85%** check-out recorded
- Staff users have random scan times throughout the day
