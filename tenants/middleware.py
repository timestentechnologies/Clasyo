from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from .models import School
from .threadlocals import set_current_tenant_db, clear_current_tenant_db
from .services import register_tenant_connection


class TenantMiddleware(MiddlewareMixin):
    """
    Multi-tenant middleware:
    - Resolves tenant via subdomain or /school/<slug>/ path
    - Sets active database connection for the thread/request
    - Auto-provisions and migrates tenant database on first access
    - Guarantees superadmin always operates against master ('default')
    """
    
    def process_request(self, request):
        # 1. Superadmin path check: always use master ('default')
        if request.path.startswith('/superadmin/'):
            clear_current_tenant_db()
            request.tenant = None
            request.school = None
            return None

        school = None

        # 2. Resolve tenant from URL (e.g., /school/demo-school/)
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'school':
            slug = path_parts[1]
            try:
                school = School.objects.using('default').get(slug=slug, is_active=True)
            except School.DoesNotExist:
                school = None

        # 3. Fallback: Resolve tenant by subdomain (e.g. tenant.domain.com) if not IP or localhost
        if not school:
            host = request.get_host().split(':')[0]
            is_ip_or_local = host.replace('.', '').isdigit() or host in ('localhost', '127.0.0.1')
            if not is_ip_or_local:
                parts = host.split('.')
                if len(parts) > 2:
                    subdomain = parts[0]
                    try:
                        school = School.objects.using('default').get(slug=subdomain, is_active=True)
                    except School.DoesNotExist:
                        school = None

        request.tenant = school
        request.school = school

        # 4. Attach active tenant database
        if school:
            use_demo_db = bool(getattr(request, 'session', {}).get('use_demo_database', False))
            # Demo database mode is only active when visiting demo-school
            if use_demo_db and school.slug == 'demo-school':
                register_tenant_connection('demo-school')
                demo_school = School.objects.using('default').filter(slug='demo-school').first()
                if demo_school:
                    request.tenant = demo_school
                    request.school = demo_school
                set_current_tenant_db('demo-school')
            else:
                # If visiting a real school URL, ensure session demo flag is reset
                if school.slug != 'demo-school' and use_demo_db:
                    if hasattr(request, 'session'):
                        request.session.pop('use_demo_database', None)
                        request.session.pop('real_school_slug', None)
                        request.session.modified = True

                register_tenant_connection(school.slug)
                set_current_tenant_db(school.slug)
        else:
            clear_current_tenant_db()

        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Enforce that authenticated non-superadmin users access only their own school slug
        user = getattr(request, 'user', None)
        use_demo_db = bool(getattr(request, 'session', {}).get('use_demo_database', False))
        if user and getattr(user, 'is_authenticated', False) and request.path.startswith('/school/'):
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) >= 2:
                slug = path_parts[1]
                user_school = None
                try:
                    user_school = getattr(user, 'school', None)
                except Exception:
                    user_school = None

                if not user_school and getattr(user, 'school_id', None):
                    try:
                        user_school = School.objects.using('default').filter(id=user.school_id).first()
                    except Exception:
                        user_school = None

                if user_school and getattr(user, 'role', None) != 'superadmin' and slug != user_school.slug:
                    if not (slug == 'demo-school' and use_demo_db):
                        full_path = request.get_full_path()
                        return redirect(full_path.replace(f'/school/{slug}/', f'/school/{user_school.slug}/', 1))

        return None

    def process_response(self, request, response):
        # Clear thread-local tenant context to prevent leaking across requests
        clear_current_tenant_db()
        return response

    def process_exception(self, request, exception):
        clear_current_tenant_db()
        return None
