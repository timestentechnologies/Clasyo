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
    
    return context
