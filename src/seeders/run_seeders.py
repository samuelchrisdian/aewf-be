"""
CLI Entry Point for AEWF Database Seeders.

Usage:
    python -m src.seeders.run_seeders seed-all --clear
    python -m src.seeders.run_seeders seed-master
    python -m src.seeders.run_seeders seed-machine
    python -m src.seeders.run_seeders seed-attendance
    python -m src.seeders.run_seeders seed-mapping
    python -m src.seeders.run_seeders generate-excel
"""
import click
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables BEFORE importing Flask app
from dotenv import load_dotenv
load_dotenv()

# Verify DATABASE_URL is set
db_url = os.environ.get('DATABASE_URL')
if db_url:
    click.echo(f'📦 Using database: {db_url.split("@")[-1] if "@" in db_url else db_url}')
else:
    click.echo('⚠️  WARNING: DATABASE_URL not set, using SQLite fallback!')

from src.app import create_app
from src.app.extensions import db


@click.group()
def cli():
    """AEWF Database Seeder - Generate realistic test data."""
    pass


@cli.command('seed-all')
@click.option('--clear', is_flag=True, help='Clear existing data before seeding')
def seed_all(clear):
    """Run all seeders in correct order."""
    app = create_app()
    with app.app_context():
        from src.seeders.master_seeder import MasterSeeder
        from src.seeders.machine_seeder import MachineSeeder
        from src.seeders.attendance_seeder import AttendanceSeeder
        from src.seeders.mapping_seeder import MappingSeeder
        
        if clear:
            click.echo('🗑️  Clearing all existing data (reverse FK order)...')
            # Clear in reverse order: mapping -> attendance -> machine -> master
            mapping = MappingSeeder(db.session)
            mapping.clear_data()
            
            attendance = AttendanceSeeder(db.session)
            attendance.clear_data()
            
            machine = MachineSeeder(db.session)
            machine.clear_data()
            
            master = MasterSeeder(db.session)
            master.clear_data()
            click.echo('   ✓ All tables cleared')
        
        click.echo('\n1️⃣  Seeding master data (Teachers, Classes, Students)...')
        master = MasterSeeder(db.session)
        master_result = master.run(clear_first=False)  # Already cleared above
        click.echo(f'   ✓ Created: {master_result["created"]}')
        
        click.echo('\n2️⃣  Seeding machines and users...')
        machine = MachineSeeder(db.session)
        machine_result = machine.run(clear_first=False)
        click.echo(f'   ✓ Created: {machine_result["created"]}')
        
        click.echo('\n3️⃣  Seeding attendance raw logs...')
        attendance = AttendanceSeeder(db.session)
        attendance_result = attendance.run(clear_first=False)
        click.echo(f'   ✓ Created: {attendance_result["created"]}')
        
        click.echo('\n4️⃣  Seeding mapping suggestions...')
        mapping = MappingSeeder(db.session)
        mapping_result = mapping.run(clear_first=False)
        click.echo(f'   ✓ Created: {mapping_result["created"]}')
        
        click.echo('\n✅ All seeding completed successfully!')
        click.echo('\n📊 Summary:')
        click.echo(f'   Teachers: {master_result["created"].get("teachers", 0)}')
        click.echo(f'   Classes: {master_result["created"].get("classes", 0)}')
        click.echo(f'   Students: {master_result["created"].get("students", 0)}')
        click.echo(f'   Machines: {machine_result["created"].get("machines", 0)}')
        click.echo(f'   Machine Users: {machine_result["created"].get("machine_users", 0)}')
        click.echo(f'   Import Batches: {attendance_result["created"].get("batches", 0)}')
        click.echo(f'   Raw Logs: {attendance_result["created"].get("logs", 0)}')
        click.echo(f'   Mappings: {mapping_result["created"].get("total", 0)}')


@cli.command('seed-master')
@click.option('--clear', is_flag=True, help='Clear existing data before seeding')
def seed_master(clear):
    """Seed only master data (Teachers, Classes, Students)."""
    app = create_app()
    with app.app_context():
        from src.seeders.master_seeder import MasterSeeder
        
        click.echo('📚 Seeding master data...')
        seeder = MasterSeeder(db.session)
        result = seeder.run(clear_first=clear)
        click.echo(f'✅ Created: {result["created"]}')


@cli.command('seed-machine')
@click.option('--clear', is_flag=True, help='Clear existing data before seeding')
def seed_machine(clear):
    """Seed only machines and machine users."""
    app = create_app()
    with app.app_context():
        from src.seeders.machine_seeder import MachineSeeder
        
        click.echo('🖥️  Seeding machines and users...')
        seeder = MachineSeeder(db.session)
        result = seeder.run(clear_first=clear)
        click.echo(f'✅ Created: {result["created"]}')


@cli.command('seed-attendance')
@click.option('--clear', is_flag=True, help='Clear existing data before seeding')
def seed_attendance(clear):
    """Seed only attendance raw logs."""
    app = create_app()
    with app.app_context():
        from src.seeders.attendance_seeder import AttendanceSeeder
        
        click.echo('📋 Seeding attendance logs...')
        seeder = AttendanceSeeder(db.session)
        result = seeder.run(clear_first=clear)
        click.echo(f'✅ Created: {result["created"]}')


@cli.command('seed-mapping')
@click.option('--clear', is_flag=True, help='Clear existing data before seeding')
def seed_mapping(clear):
    """Seed only mapping suggestions."""
    app = create_app()
    with app.app_context():
        from src.seeders.mapping_seeder import MappingSeeder
        
        click.echo('🔗 Seeding mapping suggestions...')
        seeder = MappingSeeder(db.session)
        result = seeder.run(clear_first=clear)
        click.echo(f'✅ Created: {result["created"]}')


@cli.command('generate-excel')
@click.option('--output-dir', default='tests/datasets', help='Output directory for Excel files')
def generate_excel(output_dir):
    """Generate Excel test files for import testing."""
    app = create_app()
    with app.app_context():
        from src.seeders.excel_generator import ExcelGenerator
        
        click.echo(f'📁 Generating Excel files to {output_dir}...')
        generator = ExcelGenerator(db.session, output_dir)
        result = generator.generate_all()
        click.echo(f'✅ Generated files: {result}')


if __name__ == '__main__':
    cli()
