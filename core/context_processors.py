from tenants.models import School
from core.models import SystemSetting


def school_context(request):
    """
    Add school and system settings to context globally
    """
    context = {
        'system_settings': SystemSetting.get_settings()
    }
    
    # Try to get school_slug from URL kwargs
    if hasattr(request, 'resolver_match') and request.resolver_match:
        school_slug = request.resolver_match.kwargs.get('school_slug')
        
        if school_slug:
            context['school_slug'] = school_slug
            
            # Fetch school object
            try:
                school = School.objects.get(slug=school_slug, is_active=True)
                context['school'] = school
            except School.DoesNotExist:
                context['school'] = None
    
    # Navigation layout resolution (user preference or system default)
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and hasattr(user, 'get_navigation_layout'):
        context['navigation_layout'] = user.get_navigation_layout()
    else:
        sys_settings = context['system_settings']
        context['navigation_layout'] = getattr(sys_settings, 'default_navigation_layout', 'sidebar') or 'sidebar'
    
    return context
