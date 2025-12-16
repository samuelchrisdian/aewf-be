"""
AEWF Database Seeders Package

Provides tools for generating realistic test data for end-to-end testing.

Note: Imports are lazy to avoid loading models before environment is configured.
Use explicit imports when needed, e.g.:
    from src.seeders.master_seeder import MasterSeeder
"""

# Lazy imports - only expose names but don't import until accessed
def __getattr__(name):
    if name == 'BaseSeeder':
        from .base_seeder import BaseSeeder
        return BaseSeeder
    elif name == 'MasterSeeder':
        from .master_seeder import MasterSeeder
        return MasterSeeder
    elif name == 'MachineSeeder':
        from .machine_seeder import MachineSeeder
        return MachineSeeder
    elif name == 'AttendanceSeeder':
        from .attendance_seeder import AttendanceSeeder
        return AttendanceSeeder
    elif name == 'MappingSeeder':
        from .mapping_seeder import MappingSeeder
        return MappingSeeder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'BaseSeeder',
    'MasterSeeder',
    'MachineSeeder',
    'AttendanceSeeder',
    'MappingSeeder',
]
