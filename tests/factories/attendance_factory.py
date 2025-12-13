"""
Attendance factory for test data generation.
"""
import factory
from datetime import date, datetime, timedelta
from src.domain.models import AttendanceDaily
from src.app.extensions import db


class AttendanceFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for generating AttendanceDaily test data."""
    
    class Meta:
        model = AttendanceDaily
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n + 1)
    student_nis = factory.LazyAttribute(lambda o: "2024001")
    attendance_date = factory.LazyFunction(date.today)
    check_in = factory.LazyFunction(lambda: datetime.now().replace(hour=7, minute=30))
    check_out = factory.LazyFunction(lambda: datetime.now().replace(hour=14, minute=0))
    status = "Present"
    notes = None
    recorded_by = None


class AbsentAttendanceFactory(AttendanceFactory):
    """Factory for generating absent attendance records."""
    status = "Absent"
    check_in = None
    check_out = None


class LateAttendanceFactory(AttendanceFactory):
    """Factory for generating late attendance records."""
    status = "Late"
    check_in = factory.LazyFunction(lambda: datetime.now().replace(hour=8, minute=15))


class SickAttendanceFactory(AttendanceFactory):
    """Factory for generating sick attendance records."""
    status = "Sick"
    check_in = None
    check_out = None
    notes = factory.Faker("sentence")


class ManualAttendanceFactory(AttendanceFactory):
    """Factory for generating manual attendance entries."""
    recorded_by = factory.LazyAttribute(lambda o: "T001")
    notes = factory.Faker("sentence")
