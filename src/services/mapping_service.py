from thefuzz import fuzz
from src.app.extensions import db
from src.domain.models import MachineUser, Student, StudentMachineMap, User
import datetime
import logging

logger = logging.getLogger(__name__)

class MappingService:
    @staticmethod
    def run_auto_mapping(confidence_threshold: int = 90) -> dict:
        """
        Runs fuzzy matching to suggest mappings for unmapped machine users.
        """
        results = {
            'unmapped_users': 0,
            'suggestions_created': 0,
            'errors': []
        }
        
        try:
            # 1. Find unmapped users (LEFT JOIN check or NOT EXISTS)
            # SQLAlchemy: MachineUser not in StudentMachineMap.machine_user_id_fk
            mapped_ids = db.session.query(StudentMachineMap.machine_user_id_fk).subquery()
            unmapped_users = db.session.query(MachineUser).filter(
                MachineUser.id.notin_(mapped_ids)
            ).all()
            
            results['unmapped_users'] = len(unmapped_users)
            
            if not unmapped_users:
                return results
            
            # 2. Get all active students
            # Optimization: Load name and nis into memory to avoid N+1
            students = db.session.query(Student).filter_by(is_active=True).all()
            if not students:
                results['errors'].append("No active students found to map against.")
                return results

            # 3. Fuzzy match
            for m_user in unmapped_users:
                if not m_user.machine_user_name:
                    continue
                
                best_score = 0
                best_student = None
                
                # Check exact match first? (Optional but good for speed)
                
                for student in students:
                    # Token sort ratio handles "Name Surname" vs "Surname Name"
                    score = fuzz.token_sort_ratio(m_user.machine_user_name, student.name)
                    if score > best_score:
                        best_score = score
                        best_student = student
                
                if best_score >= confidence_threshold and best_student:
                    # Create Suggestion
                    mapping = StudentMachineMap(
                        machine_user_id_fk=m_user.id,
                        student_nis=best_student.nis,
                        status='suggested',
                        confidence_score=best_score
                    )
                    db.session.add(mapping)
                    results['suggestions_created'] += 1
            
            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_mapping_suggestions() -> list:
        """
        Returns list of suggested mappings for frontend verification.
        """
        suggestions = db.session.query(StudentMachineMap).filter_by(status='suggested').all()
        output = []
        for s in suggestions:
            output.append({
                'mapping_id': s.id,
                'machine_user': {
                    'id': s.machine_user.id,
                    'name': s.machine_user.machine_user_name,
                    'machine_id': s.machine_user.machine_user_id
                },
                'suggested_student': {
                    'nis': s.student.nis,
                    'name': s.student.name,
                    'class': s.student.class_id
                },
                'confidence_score': s.confidence_score
            })
        return output

    @staticmethod
    def verify_mapping(mapping_id: int, admin_user_id: int, status: str = 'verified') -> bool:
        """
        Verifies or Rejects a mapping.
        """
        try:
            mapping = StudentMachineMap.query.get(mapping_id)
            if not mapping:
                return False
            
            admin = User.query.get(admin_user_id)
            admin_name = admin.username if admin else "Unknown"

            if status == 'verified':
                mapping.status = 'verified'
                mapping.verified_at = datetime.datetime.utcnow()
                mapping.verified_by = admin_name
            elif status == 'rejected':
                 # Hard delete or set status to rejected?
                 # If rejected, we might want to allow re-mapping later.
                 # For now, let's delete so it can be re-mapped manually or by algorithm if logic changes
                 db.session.delete(mapping)
                 db.session.commit()
                 return True
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error verifying mapping {mapping_id}: {e}")
            return False
