"""
Idempotent synchronization of master School records into tenant databases.

The master ``School`` row is authoritative. Each tenant database holds a copy
with the same primary key so local foreign keys (e.g. finance_account.school_id)
resolve without cross-database references.
"""
from __future__ import annotations

import logging

from django.db import models

from tenants.models import School

logger = logging.getLogger(__name__)

# Master-only FK: subscription plans live on the default database only.
_TENANT_SCHOOL_EXCLUDE_FIELDS = frozenset({'subscription_plan'})


def school_copy_defaults(master: School) -> dict:
    """Build field values to upsert on the tenant copy (excludes primary key)."""
    defaults: dict = {}
    for field in School._meta.concrete_fields:
        if field.primary_key:
            continue
        if field.name in _TENANT_SCHOOL_EXCLUDE_FIELDS:
            defaults['subscription_plan'] = None
            continue
        defaults[field.name] = field.value_from_object(master)
    return defaults


def sync_tenant_school_record(school, db_alias: str | None = None) -> str:
    """
    Upsert the master School row into the tenant database, preserving ``pk``.

    Returns one of: ``created``, ``updated``, ``unchanged``.
    Raises on connection or persistence errors (does not swallow failures).
    """
    from tenants.services import register_tenant_connection

    db_alias = db_alias or school.slug
    register_tenant_connection(db_alias)

    master = School.objects.using('default').get(pk=school.pk)
    defaults = school_copy_defaults(master)

    existing = School.objects.using(db_alias).filter(pk=master.pk).first()
    if existing is None:
        School.objects.using(db_alias).create(pk=master.pk, **defaults)
        logger.info("[Tenants] Created tenant School pk=%s in database '%s'.", master.pk, db_alias)
        return 'created'

    changed_fields: list[str] = []
    for name, value in defaults.items():
        current = getattr(existing, name)
        if isinstance(current, models.Model):
            current = current.pk
        if isinstance(value, models.Model):
            value = value.pk
        if current != value:
            setattr(existing, name, value)
            changed_fields.append(name)

    if changed_fields:
        existing.save(using=db_alias, update_fields=changed_fields)
        logger.info(
            "[Tenants] Updated tenant School pk=%s in database '%s' (%s).",
            master.pk,
            db_alias,
            ', '.join(changed_fields),
        )
        return 'updated'

    return 'unchanged'


def sync_tenant_school_record_by_pk(school_pk: int, db_alias: str) -> str:
    """Sync using master School primary key and explicit tenant database alias."""
    master = School.objects.using('default').get(pk=school_pk)
    return sync_tenant_school_record(master, db_alias=db_alias)


def sync_tenant_user_record(user, db_alias: str | None = None) -> str:
    """
    Upsert a master User row into the tenant database, preserving ``pk``.
    Ensures local foreign keys to accounts_user resolve correctly in the tenant database.
    """
    if not user:
        return 'unchanged'

    from django.contrib.auth import get_user_model
    User = get_user_model()
    from tenants.services import register_tenant_connection

    # Resolve target database alias
    if not db_alias:
        if getattr(user, 'school', None) and getattr(user.school, 'slug', None):
            db_alias = user.school.slug
        elif getattr(user, 'school_id', None):
            school = School.objects.using('default').filter(id=user.school_id).first()
            if school:
                db_alias = school.slug

    if not db_alias or db_alias == 'default':
        return 'unchanged'

    try:
        register_tenant_connection(db_alias)
    except Exception as e:
        logger.warning("[Tenants] Could not register tenant connection '%s' for user sync: %s", db_alias, e)
        return 'unchanged'

    master = User.objects.using('default').filter(pk=user.pk).first()
    if not master:
        return 'unchanged'

    exclude_fields = {'groups', 'user_permissions', 'department', 'designation'}
    defaults: dict = {}
    for field in User._meta.concrete_fields:
        if field.primary_key or field.name in exclude_fields:
            continue
        if field.name == 'school':
            defaults['school_id'] = master.school_id
            continue
        defaults[field.name] = field.value_from_object(master)

    # Ensure school exists in tenant database if school_id is set
    school_id = defaults.get('school_id')
    if school_id:
        try:
            if not School.objects.using(db_alias).filter(pk=school_id).exists():
                if master.school:
                    sync_tenant_school_record(master.school, db_alias=db_alias)
                else:
                    defaults['school_id'] = None
        except Exception:
            defaults['school_id'] = None

    try:
        existing = User.objects.using(db_alias).filter(pk=master.pk).first()
        if existing is None:
            User.objects.using(db_alias).create(pk=master.pk, **defaults)
            logger.info("[Tenants] Created tenant User pk=%s (%s) in database '%s'.", master.pk, master.email, db_alias)
            return 'created'

        changed_fields: list[str] = []
        for name, value in defaults.items():
            if name in ('created_at', 'updated_at', 'last_login'):
                continue
            current = getattr(existing, name)
            if current != value:
                setattr(existing, name, value)
                changed_fields.append(name)

        if changed_fields:
            existing.save(using=db_alias, update_fields=changed_fields)
            logger.info("[Tenants] Updated tenant User pk=%s in database '%s' (%s).", master.pk, db_alias, ', '.join(changed_fields))
            return 'updated'

        return 'unchanged'
    except Exception as e:
        logger.warning("[Tenants] Failed syncing user pk=%s into database '%s': %s", master.pk, db_alias, e)
        return 'error'


def sync_tenant_user_by_id(user_id: int, db_alias: str | None = None) -> str:
    """Sync a user by ID from master DB into the tenant DB."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    master = User.objects.using('default').filter(pk=user_id).first()
    if not master:
        return 'unchanged'
    return sync_tenant_user_record(master, db_alias=db_alias)

