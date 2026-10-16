from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.models import SystemSetting


class MaintenanceModeMiddleware(MiddlewareMixin):
    """Restrict access when maintenance mode is enabled.

    Supports two distinct maintenance levels:
    1. Entire System / Platform Maintenance (configured by Superadmin via SystemSetting):
       Affects all schools across the platform.
       - If superadmin_only_mode: ONLY superadmins can log in / access.
       - Else: Superadmins and School Admins can access.
    2. Per-School Tenant Maintenance (configured by School Admin via School.maintenance_mode):
       Affects ONLY that specific school's portal.
       - School Admins (and Superadmins / impersonators) can access.
       - Regular users (students, parents, teachers, and public) are redirected to the maintenance page
         showing that school's custom maintenance message and schedule.
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
        if request.resolver_match and getattr(request.resolver_match, 'namespace', '') == 'frontend':
            return None

        user = getattr(request, 'user', None)
        user_role = getattr(user, 'role', '') if user and user.is_authenticated else ''
        is_impersonating = getattr(request, 'is_impersonating', False)

        # -------------------------------------------------------------
        # LEVEL 1: Global Platform Maintenance (Controlled by Superadmin)
        # -------------------------------------------------------------
        try:
            settings_obj = SystemSetting.get_settings()
        except Exception:
            settings_obj = None

        if settings_obj and getattr(settings_obj, 'maintenance_mode', False):
            superadmin_only = getattr(settings_obj, 'superadmin_only_mode', False)
            if user and user.is_authenticated:
                if superadmin_only:
                    if user.is_superuser or user_role == 'superadmin':
                        return None
                else:
                    if user.is_superuser or user_role in ('superadmin', 'admin') or is_impersonating:
                        return None
            return self._get_maintenance_redirect(request, view_kwargs)

        # -------------------------------------------------------------
        # LEVEL 2: Per-School Tenant Maintenance (Controlled by School Admin)
        # -------------------------------------------------------------
        school_slug = view_kwargs.get('school_slug') or getattr(request, 'school_slug', None)
        if school_slug:
            try:
                from tenants.models import School
                school = School.objects.get(slug=school_slug, is_active=True)
                if school.is_in_maintenance:
                    # Allow superadmins, impersonators, and this school's admin
                    if user and user.is_authenticated:
                        if user.is_superuser or user_role == 'superadmin' or is_impersonating:
                            return None
                        # Check if user is an admin of this school
                        user_school = getattr(user, 'school', None)
                        if user_role in ('admin', 'school_admin') and user_school and user_school.slug == school.slug:
                            return None

                    # Otherwise redirect students, parents, teachers, and anonymous visitors
                    return self._get_maintenance_redirect(request, view_kwargs)
            except Exception:
                pass

        return None

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
