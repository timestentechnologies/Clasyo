#!/usr/bin/env python
"""
Installation script for Multi-Tenant School Management System
"""
import os
import sys
import subprocess
from pathlib import Path


def print_step(step_number, message):
    """Print installation step"""
    print(f"\n{'='*60}")
    print(f"STEP {step_number}: {message}")
    print(f"{'='*60}\n")


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {description} failed")
        print(f"Error message: {e.stderr}")
        return False


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  Multi-Tenant School Management System - Installation      ║
    ║                                                              ║
    ║  This script will guide you through the installation        ║
    ║  process of the School Management System.                   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Check Python version
    print_step(1, "Checking Python Version")
    if sys.version_info < (3, 10):
        print("✗ Python 3.10 or higher is required!")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✓ Python version: {sys.version}")
    
    # Check if virtual environment is activated
    print_step(2, "Checking Virtual Environment")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ Virtual environment is active")
    else:
        print("⚠ Warning: No virtual environment detected!")
        print("It's recommended to use a virtual environment.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Installation cancelled.")
            sys.exit(0)
    
    # Install dependencies
    print_step(3, "Installing Python Dependencies")
    if not run_command("pip install -r requirements.txt", "Installing packages"):
        print("✗ Failed to install dependencies")
        sys.exit(1)
    
    # Check if .env file exists
    print_step(4, "Environment Configuration")
    if not os.path.exists('.env'):
        print("⚠ .env file not found!")
        print("Creating .env from .env.example...")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✓ .env file created")
            print("\n⚠ IMPORTANT: Please edit .env file with your actual configuration values!")
            print("Especially:")
            print("  - SECRET_KEY")
            print("  - Database credentials")
            print("  - Email settings")
            print("  - Payment gateway keys")
            
            response = input("\nHave you configured the .env file? (y/N): ")
            if response.lower() != 'y':
                print("\nPlease configure .env file and run this script again.")
                sys.exit(0)
        else:
            print("✗ .env.example not found!")
            sys.exit(1)
    else:
        print("✓ .env file found")
    
    # Check PostgreSQL connection
    print_step(5, "Database Configuration")
    print("Checking PostgreSQL connection...")
    
    from decouple import config
    db_name = config('DB_NAME', default='school_saas')
    db_user = config('DB_USER', default='postgres')
    db_host = config('DB_HOST', default='localhost')
    db_port = config('DB_PORT', default='5432')
    
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Host: {db_host}:{db_port}")
    
    print("\n⚠ Make sure PostgreSQL is running and the database exists!")
    response = input("Continue with database setup? (y/N): ")
    if response.lower() != 'y':
        print("Installation cancelled.")
        sys.exit(0)
    
    # Run migrations for shared schema
    print_step(6, "Running Database Migrations (Shared Schema)")
    if not run_command("python manage.py migrate_schemas --shared", "Migrating shared schema"):
        print("✗ Shared schema migration failed")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Create directories
    print_step(7, "Creating Required Directories")
    directories = ['media', 'staticfiles', 'backups', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    # Collect static files
    print_step(8, "Collecting Static Files")
    if not run_command("python manage.py collectstatic --noinput", "Collecting static files"):
        print("⚠ Static files collection failed (not critical)")
    
    # Create superuser
    print_step(9, "Creating Super Admin")
    print("\nYou will now create a super admin account.")
    print("This account will have full access to the system.")
    if not run_command("python manage.py createsuperuser", "Creating superuser"):
        print("⚠ Superuser creation skipped")
    
    # Create public tenant
    print_step(10, "Creating Public Tenant")
    print("\nCreating public schema for multi-tenancy...")
    # This would be done through Django admin or management command
    print("✓ You'll need to create the public tenant through Django admin")
    
    # Final instructions
    print_step(11, "Installation Complete!")
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              Installation Completed Successfully!           ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Next Steps:
    
    1. Start the development server:
       python manage.py runserver
    
    2. Start Redis server (in a new terminal):
       redis-server
    
    3. Start Celery worker (in a new terminal):
       celery -A school_saas worker -l info
    
    4. Start Celery beat (in a new terminal):
       celery -A school_saas beat -l info
    
    5. Access the system:
       Main Site: http://localhost:8000
       Admin Panel: http://localhost:8000/admin
    
    6. Create your first school:
       - Login to admin panel
       - Go to Tenants > Schools
       - Add a new school with domain
    
    Important Notes:
    - Make sure PostgreSQL is running
    - Make sure Redis is running for Celery tasks
    - Configure email settings in .env for email notifications
    - Configure payment gateway keys for subscriptions
    
    Documentation: README.md
    Support: support@schoolsaas.com
    
    Happy managing! 🎓
    """)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ An error occurred: {str(e)}")
        sys.exit(1)
