from __future__ import annotations

from typing import Optional

from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone


class AuditLogMiddleware(MiddlewareMixin):
    """Middleware to record request/response metadata into AuditLog.

    - Captures user, school (if available), path, method, status code, ip, UA.
    - Skips static and media URLs.
    """

    def _get_ip(self, request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            # XFF format: client, proxy1, proxy2
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _get_school(self, request):
        try:
            match = getattr(request, "resolver_match", None)
            school_slug = None
            if match and match.kwargs.get("school_slug"):
                school_slug = match.kwargs.get("school_slug")
            else:
                # Fallback: parse path /school/<slug>/...
                parts = (request.path or "/").strip("/").split("/")
                if len(parts) >= 2 and parts[0] == "school":
                    school_slug = parts[1]
            if not school_slug:
                return None
            from tenants.models import School
            return School.objects.filter(slug=school_slug).first()
        except Exception:
            return None

    def process_response(self, request, response):
        try:
            path = request.path or "/"
            if path.startswith("/static/") or path.startswith("/media/"):
                return response

            from core.models import AuditLog

            AuditLog.objects.create(
                user=(request.user if getattr(request, "user", None) and request.user.is_authenticated else None),
                school=self._get_school(request),
                path=path[:512],
                method=(request.method or "").upper()[:10],
                status_code=getattr(response, "status_code", 0) or 0,
                ip_address=self._get_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:500],
                action="",
                metadata={},
            )
        except Exception:
            # Do not break user requests on logging failures
            pass
        return response
