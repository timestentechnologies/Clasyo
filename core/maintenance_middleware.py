from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.models import SystemSetting


class MaintenanceModeMiddleware(MiddlewareMixin):
    """Restrict access when maintenance mode is enabled.

    When SystemSetting.maintenance_mode is True, only superadmins and
    school admins are allowed to access the tenant apps. Other users
    are redirected to the offline page.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Avoid circular imports and unnecessary work for anonymous/non-tenant paths
        # Allow Django admin, auth, static and offline pages to continue as normal
        path = request.path
        if path.startswith('/admin/') or path.startswith('/superadmin/'):
            return None
        if path.startswith('/static/') or path.startswith('/media/'):
            return None

        # Offline, Maintenance, and Auth pages should always be accessible
        if any(p in path for p in ['/offline/', '/maintenance/', '/accounts/', '/auth/']):
            return None

        # Allow public marketing site access during maintenance (allows "X" to go home)
        # This only allows the marketing pages, helping the logout process feel complete
        if request.resolver_match and getattr(request.resolver_match, 'namespace', '') == 'frontend':
            return None

        try:
            settings_obj = SystemSetting.get_settings()
        except Exception:
            # If settings cannot be loaded, fail open
            return None

        if not getattr(settings_obj, 'maintenance_mode', False):
            return None

        user = getattr(request, 'user', None)
        
        # If not authenticated, redirect to maintenance (landing page)
        # Auth pages are already bypassed above
        if user is None or not user.is_authenticated:
            return self._get_maintenance_redirect(request, view_kwargs)

        # Allow system administrators through based on settings
        user_role = getattr(user, 'role', '') or ''
        is_impersonating = getattr(request, 'is_impersonating', False)
        superadmin_only = getattr(settings_obj, 'superadmin_only_mode', False)
        
        if superadmin_only:
            # ONLY superuser or superadmin role allowed
            if user.is_superuser or user_role == 'superadmin':
                return None
        else:
            # Standard maintenance: superadmins and school admins allowed
            if user.is_superuser or user_role in ('superadmin', 'admin') or is_impersonating:
                return None

        return self._get_maintenance_redirect(request, view_kwargs)

    def _get_maintenance_redirect(self, request, view_kwargs):
        """Helper to generate maintenance page redirect"""
        school_slug = view_kwargs.get('school_slug') or getattr(request, 'school_slug', None)
        try:
            if school_slug:
                maintenance_url = reverse('core:maintenance', kwargs={'school_slug': school_slug})
            else:
                maintenance_url = reverse('core:maintenance', kwargs={'school_slug': 'default'})
        except Exception:
            # Fallback: use a simple hard-coded path
            maintenance_url = '/maintenance/'
            
        return redirect(maintenance_url)
