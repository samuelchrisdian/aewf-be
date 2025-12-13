# AEWF Backend Service (Flask)

Backend service for the **Attendance Early Warning Framework (AEWF)** system. Built with **Flask**, **PostgreSQL**, and **scikit-learn**, this service handles data processing, machine learning model training, and provides APIs for the frontend dashboard.

## 📋 Features

- **Master Data Management (MDM)**:
  - Manage Students, Teachers, and Class data.
  - Bulk import from Excel templates.
- **Machine & User Synchronization**:
  - Sync user data from attendance machines.
  - **Fuzzy Mapping Engine**: Automatically map raw machine users to registered students with fuzzy logic and confidence scoring.
  - Verification workflow for ambiguous mappings.
- **Data Ingestion Pipeline**:
  - Import raw attendance logs from multiple machine types.
  - Automatic cleaning and processing of daily attendance.
- **Early Warning System (EWS)**:
  - Real-time risk assessment engine (Planned).
  - Hybrid rule-based and ML-based risk scoring (Planned).
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
│   └── services/       # Business Logic & Orchestration
├── tests/              # Unit and integration tests
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
| `password_hash` | String | Not Null | Hashed Password |
| `role` | String | Nullable | User Role (Admin, etc) |
| `created_at` | DateTime | Nullable | Creation Timestamp |

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
| `status` | String | Not Null | Final Status (Present, Absent, Late) |

### `import_batches`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK | Unique Batch ID |
| `filename` | String | Not Null | Imported Filename |
| `file_type` | String | Not Null | Type (MASTER, ATTENDANCE) |
| `status` | String | Nullable | Processing Status |
| `records_processed`| Integer | Nullable | Number of records handled |
| `error_log` | JSON | Nullable | Log of processing errors |

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

### 📥 Data Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/import/master` | Upload Master Data Excel (Students, Classes, Teachers). |
| `POST` | `/import/users-sync` | Upload Machine User export to sync machine users. Params: `machine_code` |
| `POST` | `/import/attendance` | Upload Attendance Logs CSV/Excel. Params: `machine_code` |

### 🔍 Fuzzy Mapping
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/mapping/process` | Run auto-mapping engine between Machine Users and Students. Body: `{"threshold": 90}` |
| `GET` | `/mapping/suggestions` | Get list of mapping suggestions requiring manual verification. |
| `POST` | `/mapping/verify` | Verify or reject a mapping suggestion. Body: `{"mapping_id": 1, "status": "verified"}` |

## 🧪 Testing

To run the test suite:
```bash
pytest
```
