"""
Shared helpers for iterating tenants and running tenant-scoped migrations.

Backend selection follows ``get_tenant_database_driver()`` (SQLite files locally,
separate PostgreSQL databases in production). Management commands never hard-code
an engine and never call ``CREATE DATABASE`` — they only migrate/sync existing
tenant storage.
"""
from __future__ import annotations

import logging
from typing import Iterator

from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.db.models import QuerySet

from tenants.drivers import SQLiteTenantDriver, get_tenant_database_driver
from tenants.models import School

logger = logging.getLogger(__name__)


def registered_tenant_schools(slug: str | None = None) -> QuerySet:
    """All schools registered on the master database (optional slug filter)."""
    qs = School.objects.using('default').order_by('pk')
    if slug:
        qs = qs.filter(slug=slug)
    return qs


def describe_tenant_backend() -> str:
    """Human-readable label for the active tenant storage driver (for command output)."""
    driver = get_tenant_database_driver()
    if isinstance(driver, SQLiteTenantDriver):
        return f"SQLite tenant files ({driver.dbs_dir})"
    engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    if 'postgresql' in engine:
        return 'PostgreSQL (separate database per tenant slug)'
    if 'mysql' in engine:
        return 'MySQL (separate database per tenant slug)'
    return type(driver).__name__


def tenant_database_is_provisioned(db_alias: str) -> bool:
    """True when the driver reports that this tenant's storage already exists."""
    return get_tenant_database_driver().database_exists(db_alias)


def assert_tenant_database_provisioned(db_alias: str) -> None:
    """
    Ensure tenant storage exists before connecting.

    Prevents SQLite from implicitly creating a new empty file on first connect when
    only running migrate/sync commands (provisioning still uses ``create_database``).
    """
    if not tenant_database_is_provisioned(db_alias):
        backend = describe_tenant_backend()
        raise RuntimeError(
            f"Tenant database '{db_alias}' is not provisioned yet ({backend}). "
            f"Run workspace provisioning first; migrate_tenants does not create tenant storage."
        )


def iter_provisioned_tenant_schools(
    slug: str | None = None,
    *,
    skip_missing_database: bool = True,
) -> Iterator[School]:
    """
    Yield schools whose dedicated tenant database already exists on the server.
    """
    driver = get_tenant_database_driver()
    for school in registered_tenant_schools(slug=slug):
        if driver.database_exists(school.slug):
            yield school
        elif not skip_missing_database:
            yield school


def _sqlite_foreign_keys_off(db_alias: str) -> bool:
    """Disable SQLite FK enforcement for legacy local tenant files during schema migrations."""
    conn = connections[db_alias]
    if conn.vendor != 'sqlite':
        return False
    with conn.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = OFF;')
    return True


def _sqlite_foreign_keys_on(db_alias: str) -> None:
    conn = connections[db_alias]
    if conn.vendor != 'sqlite':
        return
    with conn.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = ON;')


def repair_sqlite_legacy_user_fks(db_alias: str, *, max_passes: int = 25) -> int:
    """
    Local SQLite tenant files may reference ``accounts_user`` rows that exist on
    the master DB but not in the tenant copy. Django's SQLite schema editor runs
    ``PRAGMA foreign_key_check`` after each migration batch.

    Copy missing users from master or null out nullable FKs. No-op on PostgreSQL/MySQL.
    """
    conn = connections[db_alias]
    if conn.vendor != 'sqlite':
        return 0

    from accounts.models import User

    repairs = 0

    with conn.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = OFF;')

    for _ in range(max_passes):
        with conn.cursor() as cursor:
            violations = list(cursor.execute('PRAGMA foreign_key_check').fetchall())
        if not violations:
            break

        progressed = False
        for table_name, rowid, ref_table, fk_index in violations:
            if ref_table != 'accounts_user':
                continue

            with conn.cursor() as cursor:
                fk_list = cursor.execute(
                    f'PRAGMA foreign_key_list({conn.ops.quote_name(table_name)})'
                ).fetchall()
                if fk_index >= len(fk_list):
                    continue
                column_name = fk_list[fk_index][3]
                cursor.execute(
                    f'SELECT {conn.ops.quote_name(column_name)} FROM '
                    f'{conn.ops.quote_name(table_name)} WHERE rowid = %s',
                    (rowid,),
                )
                row = cursor.fetchone()
                if not row:
                    continue
                bad_user_id = row[0]
                if bad_user_id is None:
                    continue

            if not User.objects.using(db_alias).filter(pk=bad_user_id).exists():
                master_user = User.objects.using('default').filter(pk=bad_user_id).first()
                if master_user is not None:
                    master_user.save(using=db_alias)
                    repairs += 1
                    progressed = True
                    continue

            with conn.cursor() as cursor:
                cursor.execute(
                    f'UPDATE {conn.ops.quote_name(table_name)} '
                    f'SET {conn.ops.quote_name(column_name)} = NULL '
                    f'WHERE rowid = %s',
                    (rowid,),
                )
                if cursor.rowcount:
                    repairs += 1
                    progressed = True

        if not progressed:
            break

    with conn.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = ON;')

    return repairs


def run_tenant_migrations(db_alias: str, *, verbosity: int = 0) -> None:
    """
    Apply migrations for tenant apps on the given database alias (idempotent).

    Uses ``TenantDatabaseRouter`` via ``migrate --database=alias``. Does not create
    tenant storage; PostgreSQL ``CREATE DATABASE`` is only used from provisioning.
    """
    from tenants.services import register_tenant_connection

    assert_tenant_database_provisioned(db_alias)
    register_tenant_connection(db_alias)

    if connections[db_alias].vendor == 'sqlite':
        repaired = repair_sqlite_legacy_user_fks(db_alias)
        if repaired:
            logger.info(
                "[Tenants] Repaired %s legacy SQLite user FK reference(s) in '%s'.",
                repaired,
                db_alias,
            )

    fk_disabled = False
    try:
        fk_disabled = _sqlite_foreign_keys_off(db_alias)
        call_command('migrate', database=db_alias, interactive=False, verbosity=verbosity)
    finally:
        if fk_disabled:
            _sqlite_foreign_keys_on(db_alias)
