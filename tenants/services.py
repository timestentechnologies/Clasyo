import logging
from django.db import connections
from django.core.management import call_command
from django.apps import apps
from django.conf import settings
from .drivers import get_tenant_database_driver

logger = logging.getLogger(__name__)


def register_tenant_connection(db_alias: str) -> dict:
    """
    Dynamically register the tenant's database connection configuration 
    into django.conf.settings.DATABASES and django.db.connections if it is not already present.
    """
    if db_alias in settings.DATABASES:
        return settings.DATABASES[db_alias]

    driver = get_tenant_database_driver()
    config = driver.get_connection_config(db_alias)
    settings.DATABASES[db_alias] = config

    # Ensure connections handler is synced if it holds an active dictionary
    conn_databases = getattr(connections, 'databases', None)
    if isinstance(conn_databases, dict):
        conn_databases[db_alias] = config

    return config


def provision_school_database(school) -> bool:
    """
    Physically creates the dedicated database for the school (using school.slug),
    registers the connection, and runs all tenant schema migrations against it.
    Also copies the School record itself so foreign keys to School resolve properly.
    """
    db_alias = school.slug
    driver = get_tenant_database_driver()

    logger.info(f"[Tenants] Provisioning dedicated database for school '{school.name}' ({db_alias})...")

    # 1. Physically create the database or schema
    driver.create_database(db_alias)

    # 2. Register dynamic connection config in Django
    register_tenant_connection(db_alias)

    # 3. Run migrations on the new tenant database
    try:
        call_command('migrate', database=db_alias, interactive=False, verbosity=0)
        logger.info(f"[Tenants] Successfully applied migrations to database '{db_alias}'.")
    except Exception as e:
        logger.error(f"[Tenants] Failed applying migrations to database '{db_alias}': {e}")
        raise e

    # 4. Copy School row into the tenant database so foreign keys can be resolved
    try:
        from tenants.models import School
        if not School.objects.using(db_alias).filter(pk=school.pk).exists():
            school_record = School.objects.using('default').get(pk=school.pk)
            school_record.subscription_plan = None
            school_record.save(using=db_alias)
    except Exception as e:
        logger.warning(f"[Tenants] Error cloning School into tenant database {db_alias}: {e}")

    return True


def migrate_existing_school_data(school) -> dict:
    """
    Migrates existing school data from the master database ('default')
    into the school's new dedicated database, then removes the copied
    records from 'default' to eliminate data duplication.
    """
    db_alias = school.slug
    register_tenant_connection(db_alias)

    # Ensure school record is in the tenant DB
    from tenants.models import School
    try:
        if not School.objects.using(db_alias).filter(pk=school.pk).exists():
            school_record = School.objects.using('default').get(pk=school.pk)
            school_record.subscription_plan = None
            school_record.save(using=db_alias)
    except Exception as e:
        logger.warning(f"[Tenants] Error ensuring School in {db_alias}: {e}")
    
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
