# Marshmallow schemas for request/response validation
from .student_schema import (
    StudentSchema,
    StudentCreateSchema,
    StudentUpdateSchema,
    AttendanceSummarySchema
)
from .class_schema import (
    ClassSchema,
    ClassCreateSchema,
    ClassUpdateSchema,
    ClassDetailSchema
)
from .teacher_schema import (
    TeacherSchema,
    TeacherCreateSchema,
    TeacherUpdateSchema
)
