"""
Machine repository for database operations.
Handles all direct database interactions for Machine and MachineUser models.
"""
from typing import Optional, List, Tuple
from sqlalchemy import or_, func
from src.domain.models import Machine, MachineUser, StudentMachineMap
from src.app.extensions import db


class MachineRepository:
    """Repository class for Machine entity database operations."""
    
    def get_by_id(self, machine_id: int) -> Optional[Machine]:
        """
        Get a machine by ID.
        
        Args:
            machine_id: Machine ID
            
        Returns:
            Machine or None if not found
        """
        return db.session.query(Machine).filter(Machine.id == machine_id).first()
    
    def get_by_machine_code(self, machine_code: str) -> Optional[Machine]:
        """
        Get a machine by machine_code.
        
        Args:
            machine_code: Unique machine code
            
        Returns:
            Machine or None if not found
        """
        return db.session.query(Machine).filter(Machine.machine_code == machine_code).first()
    
    def exists(self, machine_code: str) -> bool:
        """
        Check if a machine with given code exists.
        
        Args:
            machine_code: Machine code
            
        Returns:
            bool: True if exists
        """
        return db.session.query(
            db.session.query(Machine).filter(Machine.machine_code == machine_code).exists()
        ).scalar()
    
    def get_all(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        order: str = 'asc'
    ):
        """
        Get query for all machines with optional filters.
        
        Args:
            status: Filter by status (active/inactive)
            search: Search by machine_code or location
            sort_by: Field to sort by (machine_code, location)
            order: Sort order ('asc' or 'desc')
            
        Returns:
            SQLAlchemy query object (not executed)
        """
        query = db.session.query(Machine)
        
        # Apply filters
        if status:
            query = query.filter(Machine.status == status)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Machine.machine_code.ilike(search_pattern),
                    Machine.location.ilike(search_pattern)
                )
            )
        
        # Apply sorting
        if sort_by:
            sort_column = getattr(Machine, sort_by, None)
            if sort_column is not None:
                if order.lower() == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
        else:
            # Default sort by machine_code
            query = query.order_by(Machine.machine_code.asc())
        
        return query
    
    def create(self, machine_data: dict) -> Machine:
        """
        Create a new machine.
        
        Args:
            machine_data: Dictionary with machine fields
            
        Returns:
            Created Machine instance
        """
        machine = Machine(**machine_data)
        db.session.add(machine)
        db.session.commit()
        return machine
    
    def update(self, machine_id: int, update_data: dict) -> Optional[Machine]:
        """
        Update an existing machine.
        
        Args:
            machine_id: Machine ID
            update_data: Dictionary with fields to update
            
        Returns:
            Updated Machine or None if not found
        """
        machine = self.get_by_id(machine_id)
        if not machine:
            return None
        
        for key, value in update_data.items():
            if hasattr(machine, key):
                setattr(machine, key, value)
        
        db.session.commit()
        return machine
    
    def delete(self, machine_id: int) -> bool:
        """
        Delete a machine.
        
        Args:
            machine_id: Machine ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        machine = self.get_by_id(machine_id)
        if not machine:
            return False
        
        db.session.delete(machine)
        db.session.commit()
        return True
    
    def get_user_count(self, machine_id: int) -> int:
        """
        Count users for a machine.
        
        Args:
            machine_id: Machine ID
            
        Returns:
            int: Number of users
        """
        return db.session.query(func.count(MachineUser.id)).filter(
            MachineUser.machine_id == machine_id
        ).scalar() or 0
    
    def get_users(
        self,
        machine_id: int,
        search: Optional[str] = None,
        mapped_only: Optional[bool] = None
    ):
        """
        Get query for users of a machine.
        
        Args:
            machine_id: Machine ID
            search: Search by user name
            mapped_only: If True, only mapped users; if False, only unmapped
            
        Returns:
            SQLAlchemy query object
        """
        query = db.session.query(MachineUser).filter(
            MachineUser.machine_id == machine_id
        )
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    MachineUser.machine_user_name.ilike(search_pattern),
                    MachineUser.machine_user_id.ilike(search_pattern)
                )
            )
        
        if mapped_only is not None:
            # Subquery for mapped user IDs
            mapped_ids = db.session.query(StudentMachineMap.machine_user_id_fk).subquery()
            if mapped_only:
                query = query.filter(MachineUser.id.in_(mapped_ids))
            else:
                query = query.filter(MachineUser.id.notin_(mapped_ids))
        
        query = query.order_by(MachineUser.machine_user_name.asc())
        return query
    
    def has_users(self, machine_id: int) -> bool:
        """
        Check if a machine has any users.
        
        Args:
            machine_id: Machine ID
            
        Returns:
            bool: True if has users
        """
        return self.get_user_count(machine_id) > 0


# Singleton instance
machine_repository = MachineRepository()
