"""
Import batch service for business logic.
"""
import datetime
from src.repositories.batch_repo import batch_repo


class BatchService:
    """Service for import batch management business logic."""
    
    @staticmethod
    def list_batches(page=1, per_page=20, file_type=None, status=None):
        """
        Get list of import batches with pagination.
        
        Args:
            page: Page number
            per_page: Items per page
            file_type: Filter by type
            status: Filter by status
            
        Returns:
            Tuple of (batches_list, pagination)
        """
        batches, pagination = batch_repo.get_all(
            page=page,
            per_page=per_page,
            file_type=file_type,
            status=status
        )
        
        # Serialize batches
        data = []
        for batch in batches:
            data.append({
                'id': batch.id,
                'filename': batch.filename,
                'file_type': batch.file_type,
                'status': batch.status,
                'records_processed': batch.records_processed or 0,
                'created_at': batch.created_at.isoformat() if batch.created_at else None,
                'has_errors': bool(batch.error_log)
            })
        
        return data, pagination
    
    @staticmethod
    def get_batch(batch_id):
        """
        Get batch details.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Tuple of (batch_data, error_message)
        """
        batch = batch_repo.get_by_id(batch_id)
        if not batch:
            return None, "Batch not found"
        
        log_count = batch_repo.get_log_count(batch_id)
        
        return {
            'id': batch.id,
            'filename': batch.filename,
            'file_type': batch.file_type,
            'status': batch.status,
            'records_processed': batch.records_processed or 0,
            'raw_logs_count': log_count,
            'created_at': batch.created_at.isoformat() if batch.created_at else None,
            'error_log': batch.error_log
        }, None
    
    @staticmethod
    def delete_batch(batch_id):
        """
        Delete a batch and its raw logs.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Tuple of (success, deleted_count, error_message)
        """
        success, deleted_count, error = batch_repo.delete(batch_id)
        return success, deleted_count, error
    
    @staticmethod
    def rollback_batch(batch_id):
        """
        Rollback a batch - delete raw logs and mark as rolled back.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Tuple of (success, deleted_count, error_message)
        """
        success, deleted_count, error = batch_repo.rollback(batch_id)
        return success, deleted_count, error


# Singleton instance
batch_service = BatchService()
