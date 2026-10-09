import logging
from django.db import connections
from django.apps import apps
from django.conf import settings
from .drivers import get_tenant_database_driver
from .school_sync import sync_tenant_school_record
from .tenant_ops import run_tenant_migrations

logger = logging.getLogger(__name__)


_checked_user_schemas = set()


def ensure_tenant_user_schema(db_alias: str) -> None:
    """Ensure that the local accounts_user table in tenant database has all necessary columns."""
    if db_alias in _checked_user_schemas or db_alias == 'default':
        return
    try:
        conn = connections[db_alias]
        with conn.cursor() as cursor:
            if conn.vendor == 'postgresql':
                cursor.execute("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'accounts_user';
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        ALTER TABLE accounts_user 
                        ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) DEFAULT 'email' NOT NULL;
                    """)
                _checked_user_schemas.add(db_alias)
            elif conn.vendor == 'sqlite':
                cursor.execute("PRAGMA table_info(accounts_user);")
                columns = [row[1] for row in cursor.fetchall()]
                if columns:
                    if 'auth_provider' not in columns:
                        cursor.execute("""
                            ALTER TABLE accounts_user 
                            ADD COLUMN auth_provider VARCHAR(20) DEFAULT 'email' NOT NULL;
                        """)
                    _checked_user_schemas.add(db_alias)
            else:
                _checked_user_schemas.add(db_alias)
    except Exception as e:
        logger.warning(f"[Tenants] Could not ensure user schema in {db_alias}: {e}")


def register_tenant_connection(db_alias: str) -> dict:
    """
    Dynamically register the tenant's database connection configuration 
    into django.conf.settings.DATABASES and django.db.connections if it is not already present.
    """
    if db_alias in settings.DATABASES:
        ensure_tenant_user_schema(db_alias)
        return settings.DATABASES[db_alias]

    driver = get_tenant_database_driver()
    config = driver.get_connection_config(db_alias)
    settings.DATABASES[db_alias] = config

    # Ensure connections handler is synced if it holds an active dictionary
    conn_databases = getattr(connections, 'databases', None)
    if isinstance(conn_databases, dict):
        conn_databases[db_alias] = config

    ensure_tenant_user_schema(db_alias)

    return config


def provision_school_database(school) -> bool:
    """
    Physically creates the dedicated database for the school (using school.slug),
    registers the connection, runs tenant schema migrations, and synchronizes the
    master School row into the tenant database (same primary key).

    Raises if database creation, migrations, or School sync fail.
    """
    db_alias = school.slug
    driver = get_tenant_database_driver()

    logger.info(f"[Tenants] Provisioning dedicated database for school '{school.name}' ({db_alias})...")

    # 1. Physically create the database or schema
    if not driver.create_database(db_alias):
        raise RuntimeError(f"Could not create tenant database '{db_alias}'.")

    # 2. Register dynamic connection config in Django
    register_tenant_connection(db_alias)

    # 3. Run migrations on the new tenant database (router limits apps on tenant DBs)
    try:
        run_tenant_migrations(db_alias, verbosity=0)
        logger.info(f"[Tenants] Successfully applied migrations to database '{db_alias}'.")
    except Exception as e:
        logger.error(f"[Tenants] Failed applying migrations to database '{db_alias}': {e}")
        raise

    # 4. Synchronize School row into the tenant database for local FK resolution
    sync_tenant_school_record(school, db_alias=db_alias)
    from tenants.models import School
    if not School.objects.using(db_alias).filter(pk=school.pk).exists():
        raise RuntimeError(
            f"Tenant School pk={school.pk} missing in database '{db_alias}' after sync."
        )

    # 5. Optional legacy: clone superadmin users into tenant DB (non-fatal)
    try:
        from accounts.models import User
        for sa in User.objects.using('default').filter(role='superadmin'):
            if not User.objects.using(db_alias).filter(pk=sa.pk).exists():
                sa.save(using=db_alias)
    except Exception as e:
        logger.warning(f"[Tenants] Error cloning superadmin users into {db_alias}: {e}")

    return True


def migrate_existing_school_data(school) -> dict:
    """
    Migrates existing school data from the master database ('default')
    into the school's new dedicated database, then removes the copied
    records from 'default' to eliminate data duplication.
    """
    db_alias = school.slug
    register_tenant_connection(db_alias)

    sync_tenant_school_record(school, db_alias=db_alias)
    
    from .router import TENANT_APPS
    migrated_counts = {}

    # Disable foreign key constraints temporarily during bulk transfer to prevent ordering lockups
    tenant_conn = connections[db_alias]
    is_sqlite = 'sqlite' in tenant_conn.vendor
    is_mysql = 'mysql' in tenant_conn.vendor

    try:
        with tenant_conn.cursor() as cursor:
            if is_sqlite:
                cursor.execute("PRAGMA foreign_keys = OFF;")
            elif is_mysql:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # 1. Copy accounts.User records associated with this school
        from accounts.models import User
        users_to_copy = list(User.objects.using('default').filter(school_id=school.id))
        for user_obj in users_to_copy:
            try:
                if not User.objects.using(db_alias).filter(pk=user_obj.pk).exists():
                    user_obj.save(using=db_alias)
            except Exception as err:
                logger.warning(f"[Tenants] Could not copy user {user_obj.email} to {db_alias}: {err}")
        migrated_counts['User'] = len(users_to_copy)

        # 2. Copy all tenant app models with school_id
        for app_label in TENANT_APPS:
            if app_label in ('tenants', 'accounts', 'auth', 'contenttypes'):
                continue
                
            try:
                app_config = apps.get_app_config(app_label)
            except LookupError:
                continue

            for model in app_config.get_models():
                # Check if model has a 'school' field
                has_school_field = any(f.name == 'school' for f in model._meta.fields)
                if not has_school_field:
                    continue

                model_name = model.__name__
                try:
                    # Query existing records from default
                    records = list(model.objects.using('default').filter(school_id=school.id))
                    if not records:
                        continue

                    # Save each record into tenant database
                    for record in records:
                        try:
                            record.save(using=db_alias)
                        except Exception as rec_err:
                            logger.warning(f"[Tenants] Could not save {model_name} pk={record.pk} to {db_alias}: {rec_err}")

                    # Prune from master to ensure zero duplication using raw delete to bypass Python ProtectedError
                    try:
                        model.objects.using('default').filter(school_id=school.id)._raw_delete(using='default')
                    except Exception:
                        model.objects.using('default').filter(school_id=school.id).delete()
                    
                    migrated_counts[model_name] = len(records)
                    logger.info(f"[Tenants] Migrated {len(records)} {model_name} records to '{db_alias}' and cleared from default.")
                except Exception as e:
                    logger.warning(f"[Tenants] Error migrating {model_name} for school {school.slug}: {e}")

    finally:
        # Re-enable foreign key constraints
        try:
            with tenant_conn.cursor() as cursor:
                if is_sqlite:
                    cursor.execute("PRAGMA foreign_keys = ON;")
                elif is_mysql:
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        except Exception:
            pass

    logger.info(f"[Tenants] Completed data migration for {school.name}: {migrated_counts}")
    return migrated_counts


def is_school_database_ready(school) -> bool:
    """Checks if the school's dedicated database exists and is migrated"""
    db_alias = school.slug
    driver = get_tenant_database_driver()
    if not driver.database_exists(db_alias):
        return False

    register_tenant_connection(db_alias)
    try:
        from tenants.models import School
        return School.objects.using(db_alias).filter(pk=school.pk).exists()
    except Exception:
        return False


def ensure_school_database(school) -> bool:
    """
    Ensures that the school's dedicated database exists, is migrated,
    and has its data moved from master.
    """
    if not school:
        return False

    register_tenant_connection(school.slug)

    if not is_school_database_ready(school):
        logger.info(f"[Tenants] School '{school.name}' database '{school.slug}' is not ready. Auto-provisioning now...")
        provision_school_database(school)
        migrate_existing_school_data(school)
        return True

    return True


def purge_school_and_tenant_data(school, notify_admins: bool = True) -> dict:
    """
    Completely and permanently purges a school tenant and all associated data with zero remnants:
    1. Sends notification emails to school admins (optional)
    2. Deletes physical database backup files from disk and metadata
    3. Closes database connections and unregisters from Django
    4. Physically destroys the tenant database file/schema (SQLite, Postgres, or MySQL)
    5. Cleans up school media files (logos, documents)
    6. Deletes all associated users (admins, teachers, students, parents, staff)
    7. Cascades deletion through all school-related models across all apps in the master database
    8. Deletes the School and Domain records
    """
    import os
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail

    User = get_user_model()
    school_name = school.name
    school_slug = school.slug
    db_alias = school_slug

    logger.info(f"[Tenants] Initiating complete purge for school '{school_name}' ({school_slug})...")
    summary = {
        'school_name': school_name,
        'school_slug': school_slug,
        'db_deleted': False,
        'backups_deleted': 0,
        'users_deleted': 0,
        'media_deleted': False,
    }

    # 1. Notify school admins
    admins = list(User.objects.using('default').filter(role__in=['admin', 'school_admin'], school=school))
    if notify_admins:
        from core.services.notification_templates import render_email_template
        from django.core.mail import EmailMultiAlternatives
        for admin in admins:
            try:
                context = {
                    'subject': f'Administrator Account for {school_name} Deleted',
                    'heading': 'School Account & Database Removed',
                    'body': (
                        f"Hello <strong>{admin.get_full_name()}</strong>,<br><br>"
                        f"The school <strong>{school_name}</strong> and its dedicated database have been permanently removed from Clasyo. "
                        f"Your administrator account and all associated school records have been deleted.<br><br>"
                        f"If you believe this was done in error or require data recovery assistance, please contact system support."
                    ),
                    'button_text': 'CONTACT SUPPORT',
                    'button_url': 'mailto:support@timestentechnologies.co.ke',
                }
                subject, html_content, text_content = render_email_template(
                    template_or_code='account_deleted',
                    context=context,
                    school=None
                )
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                msg = EmailMultiAlternatives(subject=subject, body=text_content, from_email=from_email, to=[admin.email])
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
            except Exception as e:
                logger.warning(f"[Tenants] Failed notifying admin {admin.email}: {e}")

    # 2. Delete physical backup files from disk and metadata records
    try:
        from superadmin.models import DatabaseBackup
        backups = DatabaseBackup.objects.using('default').filter(school=school)
        for b in backups:
            if b.file_path and os.path.exists(b.file_path):
                try:
                    os.remove(b.file_path)
                    summary['backups_deleted'] += 1
                except Exception as err:
                    logger.warning(f"[Tenants] Could not remove backup file {b.file_path}: {err}")
        backups.delete()
    except Exception as e:
        logger.warning(f"[Tenants] Error purging backups for {school_slug}: {e}")

    # 3. Close open connections and unregister dynamic DB alias
    if db_alias in connections:
        try:
            connections[db_alias].close()
        except Exception:
            pass
        try:
            del connections[db_alias]
        except Exception:
            pass

    if db_alias in settings.DATABASES:
        try:
            del settings.DATABASES[db_alias]
        except Exception:
            pass

    conn_databases = getattr(connections, 'databases', None)
    if isinstance(conn_databases, dict) and db_alias in conn_databases:
        try:
            del conn_databases[db_alias]
        except Exception:
            pass

    # 4. Physically destroy the dedicated tenant database via driver
    try:
        driver = get_tenant_database_driver()
        summary['db_deleted'] = driver.delete_database(db_alias)
        logger.info(f"[Tenants] Physical database deletion for '{db_alias}': {summary['db_deleted']}")
    except Exception as e:
        logger.error(f"[Tenants] Error deleting physical database for '{db_alias}': {e}")

    # 5. Delete uploaded media files (e.g. school logo)
    try:
        if school.logo and hasattr(school.logo, 'path') and os.path.exists(school.logo.path):
            os.remove(school.logo.path)
            summary['media_deleted'] = True
    except Exception as err:
        logger.warning(f"[Tenants] Error deleting school logo: {err}")

    # 6. Delete all master database records referencing this school
    # (Import models dynamically to avoid circular dependencies)
    from django.db.models import Q
    try:
        from students.models import Student, StudentSubject
        StudentSubject.objects.filter(student__school=school).delete()
        Student.objects.filter(school=school).delete()
        Student.objects.filter(current_class__school=school).delete()
    except Exception as e:
        logger.warning(f"[Tenants] Error deleting students for {school_slug}: {e}")

    # Delete parents whose only children were in this school
    try:
        User.objects.filter(role='parent', children__current_class__school=school).distinct().delete()
    except Exception as e:
        logger.warning(f"[Tenants] Error deleting parents for {school_slug}: {e}")

    # Delete all users linked to this school (admins, teachers, staff, etc.)
    try:
        user_qs = User.objects.using('default').filter(school=school)
        summary['users_deleted'] = user_qs.count()
        user_qs.delete()
    except Exception as e:
        logger.warning(f"[Tenants] Error deleting users for {school_slug}: {e}")

    # Delete academic, finance, library, transport, attendance records
    app_models_to_purge = [
        ('academics', ['Class', 'Subject', 'Classroom', 'Timetable', 'Attendance']),
        ('fees', ['FeeStructure', 'FeeCollection', 'FeeDiscount']),
        ('examinations', ['Exam', 'Grade', 'ExamSchedule', 'Mark']),
        ('library', ['Book', 'BookIssue', 'BookCategory', 'Author', 'Publisher']),
        ('attendance', ['StudentAttendance', 'StaffAttendance']),
        ('subscriptions', ['Subscription', 'Invoice', 'PaymentTransaction']),
        ('transport', ['TransportRoute', 'Vehicle', 'Driver']),
        ('inventory', ['Item', 'ItemCategory', 'Supplier', 'PurchaseOrder', 'Expense', 'ItemDistribution', 'StaffPayment', 'CanteenProduct', 'CanteenSale']),
        ('dormitory', ['Dormitory', 'Room', 'BedAllocation']),
        ('homework', ['HomeworkAssignment', 'HomeworkSubmission']),
        ('lesson_plan', ['LessonPlan', 'LessonPlanTemplate']),
        ('reports', ['ReportType', 'SavedReport']),
        ('communication', ['Notice', 'Event']),
        ('certificates', ['CertificateTemplate', 'GeneratedCertificate']),
        ('finance', ['Account', 'FinanceTransaction', 'JournalEntry']),
        ('clubs', ['Club', 'ClubMembership']),
        ('core', ['AcademicYear', 'AuditLog']),
        ('human_resource', ['Staff', 'Department', 'Designation']),
        ('leave_management', ['LeaveApplication', 'LeaveType']),
        ('online_exam', ['OnlineExam', 'Question', 'ExamSubmission']),
    ]

    for app_label, model_names in app_models_to_purge:
        for model_name in model_names:
            try:
                model_cls = apps.get_model(app_label, model_name)
                if hasattr(model_cls, 'school'):
                    model_cls.objects.filter(school=school).delete()
            except LookupError:
                pass
            except Exception as e:
                logger.warning(f"[Tenants] Error purging {app_label}.{model_name}: {e}")

    # 7. Delete domains and finally the School record itself
    try:
        school.domains.all().delete()
        school.delete()
        logger.info(f"[Tenants] School '{school_name}' record successfully deleted.")
    except Exception as e:
        logger.error(f"[Tenants] Error deleting School record: {e}")
        raise e

    return summary

