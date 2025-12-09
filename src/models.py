from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Float
from sqlalchemy.orm import relationship
from src.db_config import Base
import datetime

class Class(Base):
    __tablename__ = "classes"

    class_id = Column(String, primary_key=True, index=True)
    class_name = Column(String, nullable=False)
    wali_kelas_id = Column(String, ForeignKey("teachers.teacher_id"), nullable=True)

    # Relationships
    students = relationship("Student", back_populates="student_class")
    wali_kelas = relationship("Teacher", back_populates="classes")

class Teacher(Base):
    __tablename__ = "teachers"

    teacher_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, default="Teacher") # e.g., "Wali Kelas", "Guru Mapel"

    # Relationships
    classes = relationship("Class", back_populates="wali_kelas")

class Student(Base):
    __tablename__ = "students"

    nis = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_id = Column(String, ForeignKey("classes.class_id"))

    # Relationships
    student_class = relationship("Class", back_populates="students")
    attendance_records = relationship("AttendanceRecord", back_populates="student")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    student_nis = Column(String, ForeignKey("students.nis"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False) # e.g., Present, Absent, Late
    
    # Additional features for ML can be stored here or computed
    # Simple storage of raw attendance
    
    student = relationship("Student", back_populates="attendance_records")
