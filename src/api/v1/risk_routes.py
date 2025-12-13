from flask import jsonify
from . import v1_bp
from src.ews.engine import assess_risk
import logging

logger = logging.getLogger(__name__)

@v1_bp.route('/risk/<nis>', methods=['GET'])
def get_student_risk(nis):
    result = assess_risk(nis)
    return jsonify({
        "success": True,
        "data": {
            "nis": nis,
            "risk_assessment": result
        }
    })

# Placeholder for bulk risk (Phase 3 feature request in plan)
@v1_bp.route('/risk', methods=['GET'])
def get_bulk_risk():
    return jsonify({"success": False, "error": "Not implemented yet (Phase 3)"}), 501
