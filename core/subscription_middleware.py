from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from tenants.models import School
from subscriptions.models import Subscription


class SubscriptionEnforcementMiddleware(MiddlewareMixin):
    EXCLUDED_PREFIXES = (
        '/admin/',
        '/superadmin/',
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
        if not path.startswith('/school/'):
            return None
        for p in self.EXCLUDED_PREFIXES:
            if path.startswith(p):
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
            if len(parts) >= 2 and parts[0] == 'school':
                slug = parts[1]
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
            # Allow access only for active subscriptions
            if latest_sub.status == 'active' and latest_sub.end_date and latest_sub.end_date >= today:
                return None
            # If subscription exists but is not active yet (pending/processing), lock access to billing until approval
            if latest_sub.status in ('pending', 'suspended', 'cancelled') or (
                latest_sub.end_date and latest_sub.end_date >= today and latest_sub.status != 'active'
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
