from .threadlocals import get_current_tenant_db

# Applications that are strictly global / master-only
# IMPORTANT: 'auth' must be here so AuthenticationMiddleware always reads
# the User from the master DB (default). If 'auth' were in TENANT_APPS,
# tenant-scoped requests would look up the session user in the tenant DB,
# fail to find them (users live in master DB), and produce an infinite
# login redirect loop for school admins.
MASTER_ONLY_APPS = {
    'superadmin',
    'frontend',
    'sessions',
    'sites',
    'admin',
    'auth',          # User auth lookups must always use master DB
    'contenttypes',  # Content types are global
}

# Applications that belong to tenant databases
TENANT_APPS = {
    'tenants',
    'subscriptions',
    'core',
    'accounts',
    'students',
    'academics',
    'fees',
    'examinations',
    'online_exam',
    'homework',
    'human_resource',
    'leave_management',
    'communication',
    'library',
    'inventory',
    'transport',
    'dormitory',
    'attendance',
    'lesson_plan',
    'certificates',
    'reports',
    'finance',
    'chat',
    'clubs',
}


class TenantDatabaseRouter:
    """
    Multi-tenant database router.
    Directs queries to the master database ('default') or to the
    active school's dedicated database based on the active request context.
    """

    def db_for_read(self, model, **hints):
        app_label = model._meta.app_label
        
        # Master-only apps always read from 'default'
        if app_label in MASTER_ONLY_APPS:
            return 'default'

        # SystemSetting is strictly global master branding and configurations
        if app_label == 'core' and getattr(model._meta, 'model_name', None) == 'systemsetting':
            return 'default'
            
        # If tenant context is active, route tenant models to tenant DB
        tenant_db = get_current_tenant_db()
        if tenant_db and app_label in TENANT_APPS:
            return tenant_db
            
        return 'default'

    def db_for_write(self, model, **hints):
        app_label = model._meta.app_label
        
        # Master-only apps always write to 'default'
        if app_label in MASTER_ONLY_APPS:
            return 'default'

        # SystemSetting is strictly global master branding and configurations
        if app_label == 'core' and getattr(model._meta, 'model_name', None) == 'systemsetting':
            return 'default'
            
        # If tenant context is active, route tenant models to tenant DB
        tenant_db = get_current_tenant_db()
        if tenant_db and app_label in TENANT_APPS:
            return tenant_db
            
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between tenant models"""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control which migrations run on which database.
        - 'default' gets all apps (master + base schemas).
        - Tenant DBs get tenant apps only.
        """
        if db == 'default':
            return True
            
        # On a tenant database, do not migrate master-only apps
        if app_label in MASTER_ONLY_APPS:
            return False
            
        if app_label in TENANT_APPS:
            return True
            
        return False
