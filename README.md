# AEWF Backend Service (Flask)

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
| `factors` | JSON | Nullable | Contributing factors |
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
| `GET` | `/students` | Get list of students (filter by class, active status, search). |
| `POST` | `/students` | Create a new student. |
| `GET` | `/students/<nis>` | Get student details. |
| `PUT` | `/students/<nis>` | Update student details. |
| `DELETE` | `/students/<nis>` | Soft delete student. |
| `GET` | `/teachers` | Get list of teachers. |
| `POST` | `/teachers` | Create a new teacher. |
| `GET` | `/teachers/<id>` | Get teacher details. |
| `PUT` | `/teachers/<id>` | Update teacher details. |
| `DELETE` | `/teachers/<id>` | Delete teacher (if not assigned to class). |
| `GET` | `/classes` | Get list of classes. |
| `POST` | `/classes` | Create a new class. |
| `GET` | `/classes/<id>` | Get class details. |
| `PUT` | `/classes/<id>` | Update class details. |
| `DELETE` | `/classes/<id>` | Delete class (if empty). |

### 📥 Data Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/import/master` | Upload Master Data Excel (Students, Classes, Teachers). |
| `POST` | `/import/users-sync` | Upload Machine User export to sync machine users. Params: `machine_code` |
| `POST` | `/import/attendance` | Upload Attendance Logs CSV/Excel. Params: `machine_code` |

### 🖨️ Machine Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/machines` | List machines (filter by status, search). |
| `POST` | `/machines` | Create a new machine. |
| `GET` | `/machines/<id>` | Get machine details. |
| `PUT` | `/machines/<id>` | Update machine details. |
| `DELETE` | `/machines/<id>` | Delete machine. |
| `GET` | `/machines/<id>/users` | List users on a specific machine. |

### 🔍 Fuzzy Mapping
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/mapping/unmapped` | List unmapped machine users with suggestions. |
| `POST` | `/mapping/bulk-verify` | Bulk verify or reject mappings. |
| `GET` | `/mapping/stats` | Get mapping statistics. |
| `GET` | `/mapping/<id>` | Get mapping details. |
| `DELETE` | `/mapping/<id>` | Delete a mapping. |
| `POST` | `/mapping/process` | Run auto-mapping engine (Legacy). |
| `GET` | `/mapping/suggestions` | Get list of mapping suggestions (Legacy). |
| `POST` | `/mapping/verify` | Verify or reject a mapping suggestion (Legacy). |

### 📅 Attendance Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/attendance/daily` | Get daily attendance list with filters (date, class, status). |
| `GET` | `/attendance/student/<nis>` | Get attendance history for a specific student. |
| `POST` | `/attendance/manual` | Create a manual attendance entry. Body: `{"student_nis": "...", "status": "Sick", ...}` |
| `PUT` | `/attendance/<id>` | Update an attendance record. |
| `GET` | `/attendance/summary` | Get aggregated attendance summary/analytics. |

### 📊 Dashboard & Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard/stats` | Get complete dashboard statistics (overview, today's attendance, monthly stats, risk summary). |
| `GET` | `/analytics/trends` | Get attendance trend data for charts. Query: `?period=weekly\|monthly&start_date=&end_date=` |
| `GET` | `/analytics/class-comparison` | Get class-by-class attendance comparison. Query: `?period=YYYY-MM` |
| `GET` | `/analytics/student-patterns/<nis>` | Get individual student attendance patterns (summary, trend, weekly patterns). |

### 🚨 Risk Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/risk/list` | List at-risk students (filter by level, class). |
| `GET` | `/risk/<nis>` | Get detailed risk profile for a student. |
| `GET` | `/risk/alerts` | Get risk alerts (filter by status). |
| `POST` | `/risk/alerts/<id>/action` | Take action on an alert (update status). |
| `GET` | `/risk/history/<nis>` | Get historical risk scores. |
| `POST` | `/risk/recalculate` | Trigger batch risk recalculation. |

### 🤖 ML Model Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/models/info` | Get installed ML models info. |
| `GET` | `/models/performance` | Get recent model performance metrics. |
| `POST` | `/models/retrain` | Trigger retraining of ML models. |

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

This project implements a novel **Early Warning System (EWS)** using Machine Learning to predict student drop-out risks based on attendance patterns.

### 📊 Success Criteria (Thesis Targets)
| Metric | Target | Achieved |
|--------|--------|----------|
| Recall (At-Risk) | ≥ 0.70 | ✅ 0.89 |
| F1-Score | ≥ 0.65 | ✅ 0.94 |
| AUC-ROC | ≥ 0.75 | ✅ 1.00 |
| API Response | < 3 sec | ✅ <100ms |

### 1. Feature Engineering (`src/ml/preprocessing.py`)
The system automatically extracts **11 features** from daily attendance logs:

| Feature | Description |
|---------|-------------|
| `absent_count` | Total absences (recorded + **inferred**) |
| `late_count` | Count of 'Late' check-ins |
| `present_count` | Count of 'Present' check-ins |
| `permission_count` | Count of 'Permission' status |
| `sick_count` | Count of 'Sick' status |
| `total_days` | Expected school days |
| `absent_ratio` | Absence rate (0.0-1.0) |
| `late_ratio` | Late rate (0.0-1.0) |
| `attendance_ratio` | Presence rate (0.0-1.0) |
| `trend_score` | 7-day trend (-1 to +1) |
| `is_rule_triggered` | Rule-based override flag |

#### 🔑 Inferred Absences (Key Feature)
Students without attendance records for certain days are treated as **absent**:
```
Expected School Days = MAX(recorded_days across all students)
Inferred Absents = Expected - Recorded Days
Total Absent = Recorded Absent + Inferred Absent
```

### 2. Model Training (`src/ml/training.py`)
- **Algorithm**: Logistic Regression with `class_weight='balanced'`
- **Imbalance Handling**: SMOTE (Synthetic Minority Over-sampling)
- **Threshold Tuning**: Automatic threshold reduction (0.50 → 0.30) if Recall < 0.70
- **Output**: `models/ews_model.pkl` + `models/model_metadata.json`

### 3. Hybrid Risk Prediction (`src/services/ml_service.py`)
The system uses a **hybrid approach** combining rules and ML:

```
┌─────────────────────────────────────────────────────────┐
│                   PREDICTION FLOW                       │
├─────────────────────────────────────────────────────────┤
│ 1. Engineer features (with inferred absences)          │
│ 2. RULE CHECK: absent_ratio > 15% OR absent_count > 5? │
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

For detailed ML documentation, see [ML_FLOW_GUIDE.md](./ML_FLOW_GUIDE.md).

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
