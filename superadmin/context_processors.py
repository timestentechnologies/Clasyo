"""Context processors for superadmin app"""


def impersonation_context(request):
    """Add impersonation context to all templates"""
    # Use the values set by ImpersonationMiddleware
    context = {
        'is_impersonating': getattr(request, 'is_impersonating', False),
        'original_user': getattr(request, 'original_user', None),
    }
    
    return context
