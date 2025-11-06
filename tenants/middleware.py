from django.utils.deprecation import MiddlewareMixin
from .models import School


class TenantMiddleware(MiddlewareMixin):
    """Simple tenant middleware using subdomain or URL parameter"""
    
    def process_request(self, request):
        # Try to get tenant from subdomain
        host = request.get_host().split(':')[0]
        
        # Check if it's a subdomain
        parts = host.split('.')
        if len(parts) > 2 or (len(parts) == 2 and parts[0] not in ['localhost', '127']):
            subdomain = parts[0]
            try:
                school = School.objects.get(slug=subdomain, is_active=True)
                request.tenant = school
                return
            except School.DoesNotExist:
                pass
        
        # Try to get from URL (e.g., /school/demo-school/)
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'school':
            slug = path_parts[1]
            try:
                school = School.objects.get(slug=slug, is_active=True)
                request.tenant = school
                return
            except School.DoesNotExist:
                pass
        
        # No tenant found - this is public site
        request.tenant = None
