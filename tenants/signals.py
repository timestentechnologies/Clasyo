import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver
from tenants.models import School
from tenants.drivers import get_tenant_database_driver

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=School)
def school_post_delete_cleanup(sender, instance, **kwargs):
    """
    Universal safety net:
    Whenever a School model is deleted (whether through admin, shell, or ORM),
    ensure the physical dedicated tenant database is destroyed and database connection
    references are completely removed from settings.DATABASES and connections.
    """
    db_alias = getattr(instance, 'schema_name', None) or getattr(instance, 'slug', None)
    if not db_alias:
        return

    try:
        from django.conf import settings
        from django.db import connections

        # Close and remove connection
        if db_alias in connections:
            try:
                connections[db_alias].close()
            except Exception:
                pass
            try:
                del connections[db_alias]
            except Exception:
                pass

        # Remove from settings.DATABASES
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

        driver = get_tenant_database_driver()
        deleted = driver.delete_database(db_alias)
        logger.info(f"[Tenants Signal] post_delete cleanup for tenant db '{db_alias}': {deleted}")
    except Exception as e:
        logger.warning(f"[Tenants Signal] Error during post_delete cleanup for '{db_alias}': {e}")
