from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from tenants.models import School
from subscriptions.models import Subscription


class SubscriptionEnforcementMiddleware(MiddlewareMixin):
    EXCLUDED_PREFIXES = (
        '/admin/',
        # Do NOT exclude '/superadmin/' globally; we enforce for school admins under '/superadmin/school/<slug>/'
        '/accounts/',
        '/auth/',
        '/subscriptions/',
        '/static/',
        '/media/',
        '/offline/',
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path or ''
        if path.endswith('/offline/'):
            return None
        # Determine enforcement scope: '/school/<slug>/' or '/superadmin/school/<slug>/' for non-superadmins
        scope = None  # 'school' or 'superadmin_school'
        if path.startswith('/school/'):
            scope = 'school'
        elif path.startswith('/superadmin/school/'):
            # Only enforce for non-superadmin users visiting superadmin school-scoped pages
            scope = 'superadmin_school'
        else:
            # Non-school scoped path; skip enforcement early
            return None

        # Apply global exclusions (but keep superadmin school-scoped pages eligible for enforcement)
        for p in self.EXCLUDED_PREFIXES:
            if path.startswith(p):
                return None

        # For generic '/superadmin/' paths that are not school-scoped, allow
        if path.startswith('/superadmin/') and scope != 'superadmin_school':
            return None
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        user_role = getattr(user, 'role', '') or ''
        if getattr(user, 'is_superuser', False) or user_role == 'superadmin':
            return None
        slug = None
        if view_kwargs and 'school_slug' in view_kwargs:
            slug = view_kwargs.get('school_slug')
        if not slug:
            parts = path.strip('/').split('/')
            if scope == 'school' and len(parts) >= 2 and parts[0] == 'school':
                slug = parts[1]
            elif scope == 'superadmin_school' and len(parts) >= 3 and parts[0] == 'superadmin' and parts[1] == 'school':
                slug = parts[2]
        if not slug:
            return None
        if path.startswith(f'/school/{slug}/billing/') or path == f'/school/{slug}/billing/':
            return None
        school = School.objects.filter(slug=slug).first()
        if not school:
            return None
        # If school is deactivated, treat as expired/suspended and redirect to billing
        if hasattr(school, 'is_active') and school.is_active is False:
            billing_url = reverse('core:billing', kwargs={'school_slug': slug})
            return redirect(f"{billing_url}?expired=1&reason=subscription")
        today = timezone.now().date()
        trial_end = getattr(school, 'trial_end_date', None)
        trial_active = bool(trial_end and trial_end >= today)
        trial_expired = bool(trial_end and trial_end < today)
        subscription_expired = False

        # Evaluate latest subscription
        latest_sub = (
            Subscription.objects.filter(school=school)
            .order_by('-created_at')
            .first()
        )
        if latest_sub:
            # Allow access only for active subscriptions within validity window
            if latest_sub.status == 'active' and latest_sub.end_date and latest_sub.end_date >= today:
                return None
            # Prioritize cancelled/suspended handling to avoid misclassifying as pending
            if latest_sub.status in ('cancelled', 'suspended'):
                billing_url = reverse('core:billing', kwargs={'school_slug': slug})
                if latest_sub.status == 'cancelled':
                    can_reactivate = bool(latest_sub.end_date and latest_sub.end_date >= today)
                    qs = '?no_sub=1'
                    if can_reactivate:
                        qs += '&reactivate=1'
                    return redirect(f"{billing_url}{qs}")
                # Suspended: treat as expired/blocked
                return redirect(f"{billing_url}?expired=1&reason=subscription")
            # If subscription is awaiting activation/verification, lock to billing with a pending notice
            if latest_sub.status in ('pending', 'processing', 'verified') or (
                latest_sub.end_date and latest_sub.end_date >= today and latest_sub.status not in ('active', 'cancelled', 'suspended')
            ):
                billing_url = reverse('core:billing', kwargs={'school_slug': slug})
                return redirect(f"{billing_url}?pending=1")

        # Free plan bypass (only if there is no trial context active or expired)
        plan = getattr(school, 'subscription_plan', None)
        try:
            if plan and getattr(plan, 'price', 0) == 0 and not trial_active and not trial_expired:
                return None
        except Exception:
            pass

        # Subscription expiry check (fall back to School dates or latest sub if available)
        end_date = getattr(school, 'subscription_end_date', None)
        if not end_date and latest_sub:
            end_date = latest_sub.end_date
        if end_date:
            subscription_expired = end_date < today

        if trial_expired or subscription_expired:
            reason = 'trial' if trial_expired else 'subscription'
            billing_url = reverse('core:billing', kwargs={'school_slug': slug})
            return redirect(f"{billing_url}?expired=1&reason={reason}")
        return None
