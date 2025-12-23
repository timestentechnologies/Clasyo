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

        # Offline page itself should always be accessible
        if path.endswith('/offline/') or path == '/offline/':
            return None

        try:
            settings_obj = SystemSetting.get_settings()
        except Exception:
            # If settings cannot be loaded, fail open
            return None

        if not getattr(settings_obj, 'maintenance_mode', False):
            return None

        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            # Let unauthenticated users reach login; once logged in and not admin,
            # they will be blocked on subsequent requests.
            return None

        # Allow system administrators through
        user_role = getattr(user, 'role', '') or ''
        if user.is_superuser or user_role in ('superadmin', 'admin'):
            return None

        # For all other authenticated users, redirect to offline page.
        # We try to preserve the current school_slug if present in kwargs.
        school_slug = view_kwargs.get('school_slug') or getattr(request, 'school_slug', None)
        try:
            if school_slug:
                offline_url = reverse('core:offline', kwargs={'school_slug': school_slug})
            else:
                offline_url = reverse('core:offline', kwargs={'school_slug': 'default'})
        except Exception:
            # Fallback: use a simple hard-coded path that should exist per-tenant
            offline_url = '/offline/'

        return redirect(offline_url)
