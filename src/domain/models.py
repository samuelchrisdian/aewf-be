from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Boolean, BigInteger, JSON
from sqlalchemy.orm import relationship
from src.app.extensions import db
import datetime

# --- Auth Domain ---
class User(db.Model):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# --- Master Data (School) ---
class Teacher(db.Model):
    __tablename__ = "teachers"

    teacher_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, default="Teacher") # e.g., "Wali Kelas", "Guru Mapel"

    # Relationships
    classes = relationship("Class", back_populates="wali_kelas")

class Class(db.Model):
    __tablename__ = "classes"

    class_id = Column(String, primary_key=True, index=True)
    class_name = Column(String, nullable=False)
    wali_kelas_id = Column(String, ForeignKey("teachers.teacher_id"), nullable=True)

    # Relationships
    students = relationship("Student", back_populates="student_class")
    wali_kelas = relationship("Teacher", back_populates="classes")

class Student(db.Model):
    __tablename__ = "students"

    nis = Column(String, primary_key=True, index=True) # No Induk Sekolah
    name = Column(String, nullable=False)
    class_id = Column(String, ForeignKey("classes.class_id"))
    parent_phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    student_class = relationship("Class", back_populates="students")
    attendance_daily = relationship("AttendanceDaily", back_populates="student")
    machine_mappings = relationship("StudentMachineMap", back_populates="student")

# --- Machine Domain ---
class Machine(db.Model):
    __tablename__ = "machines"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    machine_code = Column(String, unique=True, nullable=False, index=True)
    location = Column(String, nullable=True)
    status = Column(String, default='active')  # 'active' or 'inactive'
    last_sync = Column(DateTime, nullable=True)  # Last sync timestamp

    # Relationships
    users = relationship("MachineUser", back_populates="machine")

class MachineUser(db.Model):
    __tablename__ = "machine_users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    machine_id = Column(BigInteger, ForeignKey("machines.id"), nullable=False)
    machine_user_id = Column(String, nullable=False) # ID on the machine e.g. "195"
    machine_user_name = Column(String, nullable=True) # Name on machine e.g. "Shem"
    department = Column(String, nullable=True)

    # Unique constraint for machine_id + machine_user_id
    # (Assuming SQLAlchemy handles logic, but explicit constraint is good practice)
    # __table_args__ = (db.UniqueConstraint('machine_id', 'machine_user_id', name='_machine_user_uc'),)

    # Relationships
    machine = relationship("Machine", back_populates="users")
    student_map = relationship("StudentMachineMap", back_populates="machine_user", uselist=False)
    raw_logs = relationship("AttendanceRawLog", back_populates="machine_user")

# --- Mapping Layer ---
class StudentMachineMap(db.Model):
    __tablename__ = "student_machine_maps"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    machine_user_id_fk = Column(BigInteger, ForeignKey("machine_users.id"), unique=True, nullable=False)
    student_nis = Column(String, ForeignKey("students.nis"), nullable=True)
    status = Column(String, default='suggested') # 'suggested', 'verified', 'disabled'
    confidence_score = Column(Integer, default=0) # 0-100
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)

    # Relationships
    machine_user = relationship("MachineUser", back_populates="student_map")
    student = relationship("Student", back_populates="machine_mappings")

# --- Transactional ---
class ImportBatch(db.Model):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False) # 'master', 'users', 'logs'
    status = Column(String, default='processing') # 'processing', 'completed', 'failed'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    records_processed = Column(Integer, default=0)
    error_log = Column(JSON, nullable=True)

    # Relationships
    raw_logs = relationship("AttendanceRawLog", back_populates="batch")

class AttendanceRawLog(db.Model):
    __tablename__ = "attendance_raw_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    machine_user_id_fk = Column(BigInteger, ForeignKey("machine_users.id"), nullable=False)
    event_time = Column(DateTime, nullable=False)
    raw_data = Column(JSON, nullable=True)

    # Relationships
    batch = relationship("ImportBatch", back_populates="raw_logs")
    machine_user = relationship("MachineUser", back_populates="raw_logs")

class AttendanceDaily(db.Model):
    __tablename__ = "attendance_daily"

    id = Column(Integer, primary_key=True, index=True)
    student_nis = Column(String, ForeignKey("students.nis"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)  # Present, Absent, Late, Sick, Permission
    notes = Column(String, nullable=True)  # Notes/reason for manual entries
    recorded_by = Column(String, ForeignKey("teachers.teacher_id"), nullable=True)  # Who recorded manually
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="attendance_daily")
    recorder = relationship("Teacher", foreign_keys=[recorded_by])

# --- Risk Management (EWS) ---
class RiskAlert(db.Model):
    """Alerts generated for at-risk students."""
    __tablename__ = "risk_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    student_nis = Column(String, ForeignKey("students.nis"), nullable=False, index=True)
    alert_type = Column(String, nullable=False)  # 'high_risk', 'medium_risk', 'consecutive_absence'
    message = Column(String, nullable=False)
    status = Column(String, default='pending')  # 'pending', 'acknowledged', 'resolved'
    assigned_to = Column(String, ForeignKey("teachers.teacher_id"), nullable=True)
    action_taken = Column(String, nullable=True)  # 'contacted_parent', 'scheduled_meeting', etc.
    action_notes = Column(String, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("Student", backref="alerts")
    assignee = relationship("Teacher", foreign_keys=[assigned_to])


class RiskHistory(db.Model):
    """Historical risk scores for students."""
    __tablename__ = "risk_history"
    
    id = Column(Integer, primary_key=True, index=True)
    student_nis = Column(String, ForeignKey("students.nis"), nullable=False, index=True)
    risk_level = Column(String, nullable=False)  # 'high', 'medium', 'low'
    risk_score = Column(Integer, nullable=False)  # 0-100
    factors = Column(JSON, nullable=True)  # Stores factors like attendance_rate, consecutive_absences, etc.
    calculated_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    student = relationship("Student", backref="risk_history")


# --- Notifications Domain ---
class Notification(db.Model):
    """In-app notifications for teachers and parents."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_type = Column(String, nullable=False)  # 'teacher' or 'parent'
    recipient_id = Column(String, nullable=False, index=True)  # teacher_id or parent phone
    type = Column(String, nullable=False)  # 'risk_alert', 'attendance', 'custom'
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    priority = Column(String, default='normal')  # 'high', 'normal', 'low'
    channel = Column(String, default='in_app')  # 'in_app', 'email', 'sms'
    is_read = Column(Boolean, default=False)
    action_url = Column(String, nullable=True)  # Optional deep link
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    read_at = Column(DateTime, nullable=True)


class NotificationSettings(db.Model):
    """User notification preferences."""
    __tablename__ = "notification_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    enable_risk_alerts = Column(Boolean, default=True)
    enable_attendance = Column(Boolean, default=True)
    enable_email = Column(Boolean, default=True)
    enable_sms = Column(Boolean, default=False)
    daily_digest_time = Column(String, default='07:00')  # HH:MM format
    
    # Relationships
    user = relationship("User", backref="notification_settings")
