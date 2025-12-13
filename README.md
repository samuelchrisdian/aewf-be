# AEWF Backend Service (Flask)

Backend service for the **Attendance Early Warning Framework (AEWF)** system. Built with **Flask**, **PostgreSQL**, and **scikit-learn**, this service handles data processing, machine learning model training, and provides APIs for the frontend dashboard.

## 📋 Features

- **Master Data Management (MDM)**: APIs to manage Student and Teacher data.
- **Data Pipeline**: 
  - Import and validate master data (Excel/CSV).
  - Clean and import raw attendance logs.
- **Machine Learning**: 
  - Train prediction models based on historical attendance data.
  - Integration with `scikit-learn` for model persistence.
- **Early Warning System (EWS)**: 
  - Real-time risk assessment engine.
  - Hybrid rule-based and ML-based risk scoring.
- **Modular Architecture**: 
  - Built using Flask Blueprints and Application Factory pattern.
  - Separation of concerns: API, Services, Repositories, Domain, ML, EWS.

## 📂 Directory Structure

```
be-flask/
├── src/
│   ├── api/v1/         # API Routes (Blueprints)
│   ├── app/            # App factory, config, extensions
│   ├── db/             # Database migrations
│   ├── domain/         # Database Models (SQLAlchemy)
│   ├── ews/            # Early Warning System Logic
│   ├── ml/             # Machine Learning (Training & Preprocessing)
│   ├── repositories/   # Database Access Layer
│   └── services/       # Business Logic Layer
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

### `attendance_records`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Index | Unique Record ID |
| `student_nis` | String | FK (`students.nis`), Index | Student ID |
| `date` | Date | Not Null | Date of attendance |
| `status` | String | Not Null | Status (Present, Absent, Late) |

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- PostgreSQL installed and running

### Step 1: Clone the Repository
```bash
git clone <repository_url>
cd be-flask
```

### Step 2: Create a Virtual Environment
It is recommended to use a virtual environment.
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
2. Open `.env` and update the `DATABASE_URL` with your PostgreSQL credentials:
   ```ini
   DATABASE_URL=postgresql://username:password@localhost:5432/aewf_db
   ```
   *Note: Ensure the database `aewf_db` exists or is created before running.*

### Step 5: Initialize Database
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

### Master Data
- `POST /api/v1/students` - Add a new student.
- `GET /api/v1/students/<nis>` - Get student details.
- `GET /api/v1/teachers/<teacher_id>/students` - Get list of students for a specific teacher.

### Data Pipeline
- `POST /api/v1/master/import` - Upload Master Data file (`.xlsx`).
- `POST /api/v1/attendance/import` - Upload Attendance Log file (`.csv`).

### Machine Learning & EWS
- `POST /api/v1/models/train` - Trigger ML model training.
- `GET /api/v1/risk/<nis>` - Get risk assessment status for a student.

## 🧪 Testing

To run the tests:
```bash
pytest
```
