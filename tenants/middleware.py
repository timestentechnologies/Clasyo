from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from .models import School


class TenantMiddleware(MiddlewareMixin):
    """Simple tenant middleware using subdomain or URL parameter"""
    
    def process_request(self, request):
        # Resolve tenant first without relying on authentication
        host = request.get_host().split(':')[0]
        parts = host.split('.')
        if len(parts) > 2 or (len(parts) == 2 and parts[0] not in ['localhost', '127']):
            subdomain = parts[0]
            try:
                school = School.objects.get(slug=subdomain, is_active=True)
                request.tenant = school
                request.school = school
            except School.DoesNotExist:
                request.tenant = None
                request.school = None
        else:
            # Try to get from URL (e.g., /school/demo-school/)
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'school':
                slug = path_parts[1]
                try:
                    school = School.objects.get(slug=slug, is_active=True)
                    request.tenant = school
                    request.school = school
                except School.DoesNotExist:
                    request.tenant = None
                    request.school = None
            else:
                request.tenant = None
                request.school = None

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Enforce that authenticated non-superadmin users access only their own school slug
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False) and request.path.startswith('/school/'):
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) >= 2:
                slug = path_parts[1]
                user_school = getattr(user, 'school', None)
                if user_school and getattr(user, 'role', None) != 'superadmin' and slug != user_school.slug:
                    full_path = request.get_full_path()
                    return redirect(full_path.replace(f'/school/{slug}/', f'/school/{user_school.slug}/', 1))
