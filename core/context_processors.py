"""
Context processors to make variables available globally in templates
"""
from tenants.models import School


def school_context(request):
    """
    Add school object to context for all views that have school_slug
    """
    context = {}
    
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
