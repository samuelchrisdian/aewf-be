"""
Base Seeder - Abstract base class for all seeders.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseSeeder(ABC):
    """
    Abstract base class for database seeders.
    
    All seeders should inherit from this class and implement
    the clear_data() and seed() methods.
    """
    
    def __init__(self, db_session):
        """
        Initialize the seeder with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    @abstractmethod
    def clear_data(self) -> int:
        """
        Clear/truncate related tables.
        
        Returns:
            Number of records deleted
        """
        pass
    
    @abstractmethod
    def seed(self) -> Dict[str, Any]:
        """
        Insert seed data into the database.
        
        Returns:
            Dictionary with counts of records created
        """
        pass
    
    def run(self, clear_first: bool = True) -> Dict[str, Any]:
        """
        Orchestrator method to run the seeder.
        
        Args:
            clear_first: If True, clear existing data before seeding
            
        Returns:
            Dictionary with results including cleared and created counts
        """
        result = {
            'cleared': 0,
            'created': {}
        }
        
        if clear_first:
            result['cleared'] = self.clear_data()
        
        result['created'] = self.seed()
        
        return result
