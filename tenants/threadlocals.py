import threading

_thread_locals = threading.local()


def set_current_tenant_db(db_alias: str):
    """Set the database alias for the current request/thread"""
    _thread_locals.tenant_db = db_alias


def get_current_tenant_db() -> str | None:
    """Get the database alias for the current request/thread, or None"""
    return getattr(_thread_locals, 'tenant_db', None)


def clear_current_tenant_db():
    """Clear tenant database context for the current request/thread"""
    if hasattr(_thread_locals, 'tenant_db'):
        del _thread_locals.tenant_db
