import os
import shutil
import sqlite3
import gzip
import logging
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from django.db import connections
from django.core.management import call_command
from django.core.exceptions import PermissionDenied

from superadmin.models import DatabaseBackup
from tenants.models import School
from tenants.services import register_tenant_connection, get_tenant_database_driver

logger = logging.getLogger(__name__)


def format_bytes(size_bytes: int) -> str:
    """Helper to format byte sizes into readable string"""
    if not size_bytes or size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 1)} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{round(size_bytes / (1024 * 1024), 2)} MB"
    else:
        return f"{round(size_bytes / (1024 * 1024 * 1024), 2)} GB"


def get_backup_directory(school: School = None) -> Path:
    """Returns the backup storage directory for master or a specific school tenant"""
    base_dir = Path(getattr(settings, 'BACKUP_ROOT', settings.BASE_DIR / 'backups'))
    if school:
        backup_dir = base_dir / 'tenants' / school.slug
    else:
        backup_dir = base_dir / 'master'
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_database_backup(db_alias: str = 'default', school: School = None, user=None) -> DatabaseBackup:
    """
    Creates a full snapshot backup of either the Master database ('default')
    or a dedicated school tenant database.
    
    Uses non-locking SQLite online backup API for SQLite engines, 
    and Django's multi-database dumpdata for other engines.
    """
    if school:
        db_alias = school.slug
        register_tenant_connection(db_alias)
        backup_type = 'tenant'
    else:
        db_alias = 'default'
        backup_type = 'master'

    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = get_backup_directory(school)
    
    db_config = settings.DATABASES.get(db_alias)
    if not db_config:
        raise ValueError(f"Database alias '{db_alias}' is not configured.")

    engine_str = db_config.get('ENGINE', '')
    engine = engine_str.split('.')[-1] if engine_str else 'unknown'

    dest_filename = f"backup_{db_alias}_{timestamp}.sqlite3" if 'sqlite' in engine else f"backup_{db_alias}_{timestamp}.json.gz"
    dest_path = backup_dir / dest_filename

    try:
        if 'sqlite' in engine:
            db_file = Path(db_config['NAME'])
            if not db_file.exists():
                raise FileNotFoundError(f"Database file {db_file} does not exist.")

            # Python's SQLite online backup API performs a non-locking, transactionally safe snapshot
            src_conn = sqlite3.connect(str(db_file))
            dest_conn = sqlite3.connect(str(dest_path))
            with dest_conn:
                src_conn.backup(dest_conn)
            dest_conn.close()
            src_conn.close()
        else:
            # Multi-database json dump compressed with gzip
            temp_json = backup_dir / f"temp_{db_alias}_{timestamp}.json"
            with open(temp_json, 'w', encoding='utf-8') as f:
                call_command('dumpdata', database=db_alias, indent=2, stdout=f)
            
            with open(temp_json, 'rb') as f_in, gzip.open(dest_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            
            if temp_json.exists():
                temp_json.unlink()

        file_size_bytes = dest_path.stat().st_size

        backup_record = DatabaseBackup.objects.using('default').create(
            school=school,
            db_alias=db_alias,
            backup_type=backup_type,
            file_name=dest_filename,
            file_path=str(dest_path),
            file_size_bytes=file_size_bytes,
            engine=engine,
            status='completed',
            created_by=user if user and getattr(user, 'is_authenticated', False) else None,
        )

        logger.info(f"[Backups] Successfully created {backup_type} backup '{dest_filename}' ({format_bytes(file_size_bytes)})")
        return backup_record

    except Exception as e:
        logger.error(f"[Backups] Failed to create {backup_type} backup for '{db_alias}': {e}")
        # Record failed attempt
        backup_record = DatabaseBackup.objects.using('default').create(
            school=school,
            db_alias=db_alias,
            backup_type=backup_type,
            file_name=dest_filename,
            file_path=str(dest_path) if dest_path.exists() else '',
            file_size_bytes=dest_path.stat().st_size if dest_path.exists() else 0,
            engine=engine,
            status='failed',
            error_message=str(e),
            created_by=user if user and getattr(user, 'is_authenticated', False) else None,
        )
        raise e


def get_database_info(db_alias: str = 'default', school: School = None) -> dict:
    """
    Returns statistics and metadata about the active database:
    - engine
    - size in bytes & display
    - table count
    - total backups & last backup
    """
    if school:
        db_alias = school.slug
        register_tenant_connection(db_alias)

    db_config = settings.DATABASES.get(db_alias, {})
    engine_str = db_config.get('ENGINE', '')
    engine = engine_str.split('.')[-1] if engine_str else 'unknown'
    db_name = db_config.get('NAME', '')

    size_bytes = 0
    if 'sqlite' in engine and db_name:
        p = Path(db_name)
        if p.exists():
            size_bytes = p.stat().st_size

    # Count tables
    table_count = 0
    try:
        conn = connections[db_alias]
        with conn.cursor() as cursor:
            tables = conn.introspection.table_names(cursor)
            table_count = len(tables)
    except Exception as e:
        logger.warning(f"Could not introspect tables for {db_alias}: {e}")

    # Query backups
    if school:
        backups_qs = DatabaseBackup.objects.using('default').filter(school=school)
    else:
        backups_qs = DatabaseBackup.objects.using('default').filter(backup_type='master')

    total_backups = backups_qs.filter(status='completed').count()
    last_backup = backups_qs.filter(status='completed').first()

    return {
        'db_alias': db_alias,
        'db_name': str(db_name),
        'engine': engine,
        'size_bytes': size_bytes,
        'size_display': format_bytes(size_bytes),
        'table_count': table_count,
        'total_backups': total_backups,
        'last_backup': last_backup,
    }


def get_all_tenant_databases_summary() -> list:
    """
    Returns summary statistics for all school tenant databases.
    Used by Super Admin to monitor all user tenant databases.
    """
    schools = School.objects.using('default').all().order_by('name')
    summary = []

    for school in schools:
        driver = get_tenant_database_driver()
        exists = driver.database_exists(school.slug)
        db_info = get_database_info(school=school) if exists else {
            'db_alias': school.slug,
            'db_name': f"{school.slug}.sqlite3",
            'engine': 'sqlite3',
            'size_bytes': 0,
            'size_display': '0 B',
            'table_count': 0,
            'total_backups': DatabaseBackup.objects.using('default').filter(school=school, status='completed').count(),
            'last_backup': DatabaseBackup.objects.using('default').filter(school=school, status='completed').first(),
        }
        summary.append({
            'school': school,
            'is_ready': exists,
            **db_info
        })

    return summary


def delete_database_backup(backup_id: int, school: School = None) -> bool:
    """
    Deletes a backup file and its database record.
    If `school` is provided, guarantees the backup belongs to that school (strict tenant isolation).
    """
    try:
        backup = DatabaseBackup.objects.using('default').get(pk=backup_id)
    except DatabaseBackup.DoesNotExist:
        return False

    if school is not None and backup.school != school:
        raise PermissionDenied("You do not have permission to delete this backup.")

    # Remove file from disk
    if backup.file_path and os.path.exists(backup.file_path):
        try:
            os.remove(backup.file_path)
            logger.info(f"[Backups] Removed file {backup.file_path}")
        except OSError as e:
            logger.warning(f"[Backups] Could not remove physical file {backup.file_path}: {e}")

    backup.delete(using='default')
    return True
