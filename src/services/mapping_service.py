"""
Mapping service for business logic operations.
Handles auto-mapping, verification, and mapping statistics.
"""
from thefuzz import fuzz
from typing import Optional, Tuple, List
from src.app.extensions import db
from src.domain.models import MachineUser, Student, StudentMachineMap, User
from src.repositories.mapping_repo import mapping_repository
from src.schemas.mapping_schema import bulk_verify_request_schema
from src.utils.pagination import paginate_query
import datetime
import logging

logger = logging.getLogger(__name__)


class MappingService:
    """Service class for Mapping business logic."""
    
    def __init__(self):
        self.repository = mapping_repository
    
    def get_unmapped_users(
        self,
        page: int = 1,
        per_page: int = 20,
        machine_id: Optional[int] = None,
        include_suggestions: bool = True,
        max_suggestions: int = 3
    ) -> dict:
        """
        Get paginated list of unmapped machine users with optional suggestions.
        
        Args:
            page: Page number
            per_page: Items per page
            machine_id: Filter by machine ID
            include_suggestions: Whether to include suggested matches
            max_suggestions: Maximum number of suggestions per user
            
        Returns:
            dict: Paginated unmapped users with suggestions
        """
        query = self.repository.get_unmapped_users(machine_id=machine_id)
        result = paginate_query(query, page, per_page)
        
        # Get active students for fuzzy matching if suggestions requested
        students = []
        if include_suggestions:
            students = db.session.query(Student).filter_by(is_active=True).all()
        
        # Serialize unmapped users
        users_data = []
        for user in result["data"]:
            user_data = self._serialize_unmapped_user(user, students, max_suggestions)
            users_data.append(user_data)
        
        result["data"] = users_data
        return result
    
    def get_mapping_stats(self) -> dict:
        """
        Get mapping statistics.
        
        Returns:
            dict: Mapping statistics
        """
        return self.repository.get_stats()
    
    def bulk_verify_mappings(
        self,
        data: dict,
        admin_user_id: int
    ) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Bulk verify/reject mappings.
        
        Args:
            data: Request data with mappings array
            admin_user_id: ID of admin performing verification
            
        Returns:
            Tuple of (result, errors)
        """
        # Validate input
        errors = bulk_verify_request_schema.validate(data)
        if errors:
            return None, errors
        
        # Get admin username
        admin = User.query.get(admin_user_id)
        admin_name = admin.username if admin else "Unknown"
        
        # Process bulk updates
        validated_data = bulk_verify_request_schema.load(data)
        results = self.repository.bulk_update_status(
            updates=validated_data["mappings"],
            admin_username=admin_name
        )
        
        return results, None
    
    def delete_mapping(self, mapping_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a mapping.
        
        Args:
            mapping_id: Mapping ID
            
        Returns:
            Tuple of (success, error_message)
        """
        mapping = self.repository.get_by_id(mapping_id)
        if not mapping:
            return False, "Mapping not found"
        
        self.repository.delete(mapping_id)
        return True, None
    
    def get_mapping(self, mapping_id: int) -> Tuple[Optional[dict], Optional[str]]:
        """
        Get a single mapping by ID.
        
        Args:
            mapping_id: Mapping ID
            
        Returns:
            Tuple of (mapping_data, error_message)
        """
        mapping = self.repository.get_by_id(mapping_id)
        if not mapping:
            return None, "Mapping not found"
        
        return self._serialize_mapping(mapping), None
    
    def _serialize_unmapped_user(
        self,
        user: MachineUser,
        students: List[Student],
        max_suggestions: int = 3
    ) -> dict:
        """Serialize unmapped user with suggestions."""
        data = {
            "machine_user": {
                "id": user.id,
                "machine_user_id": user.machine_user_id,
                "machine_user_name": user.machine_user_name,
                "machine_code": user.machine.machine_code if user.machine else None
            },
            "suggested_matches": []
        }
        
        if students and user.machine_user_name:
            # Find best matches
            matches = []
            for student in students:
                score = fuzz.token_sort_ratio(user.machine_user_name, student.name)
                if score >= 50:  # Minimum threshold for suggestions
                    matches.append({
                        "student": {
                            "nis": student.nis,
                            "name": student.name,
                            "class_id": student.class_id
                        },
                        "confidence_score": score
                    })
            
            # Sort by score and take top N
            matches.sort(key=lambda x: x["confidence_score"], reverse=True)
            data["suggested_matches"] = matches[:max_suggestions]
        
        return data
    
    def _serialize_mapping(self, mapping: StudentMachineMap) -> dict:
        """Serialize a mapping object."""
        return {
            "id": mapping.id,
            "machine_user": {
                "id": mapping.machine_user.id,
                "machine_user_id": mapping.machine_user.machine_user_id,
                "machine_user_name": mapping.machine_user.machine_user_name,
                "machine_code": mapping.machine_user.machine.machine_code if mapping.machine_user.machine else None
            },
            "student": {
                "nis": mapping.student.nis,
                "name": mapping.student.name,
                "class_id": mapping.student.class_id
            } if mapping.student else None,
            "status": mapping.status,
            "confidence_score": mapping.confidence_score,
            "verified_at": mapping.verified_at.isoformat() if mapping.verified_at else None,
            "verified_by": mapping.verified_by
        }
    
    # --- Legacy static methods for backward compatibility ---
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
            # 1. Find unmapped users
            mapped_ids = db.session.query(StudentMachineMap.machine_user_id_fk).subquery()
            unmapped_users = db.session.query(MachineUser).filter(
                MachineUser.id.notin_(mapped_ids)
            ).all()
            
            results['unmapped_users'] = len(unmapped_users)
            
            if not unmapped_users:
                return results
            
            # 2. Get all active students
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
                
                for student in students:
                    score = fuzz.token_sort_ratio(m_user.machine_user_name, student.name)
                    if score > best_score:
                        best_score = score
                        best_student = student
                
                if best_score >= confidence_threshold and best_student:
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
                db.session.delete(mapping)
                db.session.commit()
                return True
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error verifying mapping {mapping_id}: {e}")
            return False


# Singleton instance
mapping_service = MappingService()
