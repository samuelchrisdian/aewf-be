from flask import Blueprint

v1_bp = Blueprint('v1', __name__)

from . import students_routes, teachers_routes, master_routes, risk_routes, attendance_routes, ml_routes
