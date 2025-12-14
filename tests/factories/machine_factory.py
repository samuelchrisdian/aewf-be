"""
Test factory for Machine and MachineUser entities.
"""
from faker import Faker
from src.domain.models import Machine, MachineUser
from src.app.extensions import db

fake = Faker()


class MachineFactory:
    """Factory for creating Machine test instances."""
    
    @staticmethod
    def create(
        machine_code: str = None,
        location: str = None,
        status: str = 'active',
        commit: bool = True
    ) -> Machine:
        """
        Create a Machine instance.
        
        Args:
            machine_code: Machine code (generated if not provided)
            location: Machine location
            status: Machine status
            commit: Whether to commit to database
            
        Returns:
            Machine instance
        """
        machine = Machine(
            machine_code=machine_code or f"FP-{fake.random_number(digits=3)}",
            location=location or fake.address()[:50],
            status=status
        )
        
        db.session.add(machine)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        
        return machine
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> list:
        """Create multiple Machine instances."""
        machines = []
        for i in range(count):
            code = f"FP-{str(i + 1).zfill(3)}"
            machine = MachineFactory.create(machine_code=code, commit=False, **kwargs)
            machines.append(machine)
        db.session.commit()
        return machines


class MachineUserFactory:
    """Factory for creating MachineUser test instances."""
    
    @staticmethod
    def create(
        machine: Machine = None,
        machine_user_id: str = None,
        machine_user_name: str = None,
        department: str = None,
        commit: bool = True
    ) -> MachineUser:
        """
        Create a MachineUser instance.
        
        Args:
            machine: Parent Machine instance
            machine_user_id: User ID on the machine
            machine_user_name: User name on the machine
            department: Department
            commit: Whether to commit to database
            
        Returns:
            MachineUser instance
        """
        if machine is None:
            machine = MachineFactory.create(commit=False)
        
        user = MachineUser(
            machine_id=machine.id,
            machine_user_id=machine_user_id or str(fake.random_number(digits=4)),
            machine_user_name=machine_user_name or fake.name(),
            department=department or fake.company()[:50]
        )
        
        db.session.add(user)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        
        return user
    
    @staticmethod
    def create_batch(count: int, machine: Machine = None, **kwargs) -> list:
        """Create multiple MachineUser instances."""
        if machine is None:
            machine = MachineFactory.create(commit=False)
        
        users = []
        for i in range(count):
            user = MachineUserFactory.create(machine=machine, commit=False, **kwargs)
            users.append(user)
        db.session.commit()
        return users
