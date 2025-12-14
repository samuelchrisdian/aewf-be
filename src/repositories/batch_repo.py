"""
Import batch repository for database operations.
"""
import datetime
from sqlalchemy import desc
from src.app.extensions import db
from src.domain.models import ImportBatch, AttendanceRawLog


class BatchRepository:
    """Repository for import batch database operations."""
    
    @staticmethod
    def get_all(page=1, per_page=20, file_type=None, status=None):
        """
        Get all import batches with optional filters and pagination.
        
        Args:
            page: Page number
            per_page: Items per page
            file_type: Filter by file type (master, users, logs)
            status: Filter by status (processing, completed, failed)
            
        Returns:
            Tuple of (batches list, pagination dict)
        """
        query = ImportBatch.query
        
        if file_type:
            query = query.filter(ImportBatch.file_type == file_type)
        
        if status:
            query = query.filter(ImportBatch.status == status)
        
        # Order by created_at descending (newest first)
        query = query.order_by(desc(ImportBatch.created_at))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        batches = query.offset((page - 1) * per_page).limit(per_page).all()
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
        
        return batches, pagination
    
    @staticmethod
    def get_by_id(batch_id):
        """Get a batch by ID with related log count."""
        return ImportBatch.query.get(batch_id)
    
    @staticmethod
    def get_log_count(batch_id):
        """Get count of raw logs for a batch."""
        return AttendanceRawLog.query.filter_by(batch_id=batch_id).count()
    
    @staticmethod
    def delete(batch_id):
        """
        Delete a batch and its associated raw logs.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Tuple of (success, deleted_logs_count, error_message)
        """
        batch = ImportBatch.query.get(batch_id)
        if not batch:
            return False, 0, "Batch not found"
        
        try:
            # Delete associated raw logs first
            log_count = AttendanceRawLog.query.filter_by(batch_id=batch_id).delete()
            
            # Delete the batch
            db.session.delete(batch)
            db.session.commit()
            
            return True, log_count, None
        except Exception as e:
            db.session.rollback()
            return False, 0, str(e)
    
    @staticmethod
    def rollback(batch_id):
        """
        Rollback a batch by deleting its raw logs and marking as rolled back.
        Does NOT affect processed daily attendance records.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Tuple of (success, deleted_logs_count, error_message)
        """
        batch = ImportBatch.query.get(batch_id)
        if not batch:
            return False, 0, "Batch not found"
        
        if batch.status == 'rolled_back':
            return False, 0, "Batch already rolled back"
        
        try:
            # Delete associated raw logs
            log_count = AttendanceRawLog.query.filter_by(batch_id=batch_id).delete()
            
            # Update batch status
            batch.status = 'rolled_back'
            batch.error_log = batch.error_log or []
            if isinstance(batch.error_log, list):
                batch.error_log.append(f"Rolled back at {datetime.datetime.utcnow().isoformat()}")
            
            db.session.commit()
            
            return True, log_count, None
        except Exception as e:
            db.session.rollback()
            return False, 0, str(e)


# Singleton instance
batch_repo = BatchRepository()
