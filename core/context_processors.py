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

    # Check if active tenant database is currently switched to demo database
    is_demo_mode = False
    if hasattr(request, 'session'):
        is_demo_mode = bool(request.session.get('use_demo_database', False))
    if not is_demo_mode and context.get('school_slug') == 'demo-school':
        is_demo_mode = True
    context['has_sample_data'] = is_demo_mode
    
    # Check if Google Auth is enabled
    try:
        from superadmin.models import GlobalGoogleAuthConfiguration
        google_cfg = GlobalGoogleAuthConfiguration.objects.using('default').first()
        context['google_auth_enabled'] = bool(google_cfg and google_cfg.is_active and google_cfg.client_id)
    except Exception:
        context['google_auth_enabled'] = False

    # Resolve school from middleware or user if not yet found
    school = context.get('school')
    if not school:
        school = getattr(request, 'school', None) or getattr(request, 'tenant', None)
        if not school and user and user.is_authenticated and hasattr(user, 'school') and user.school:
            school = user.school
        if school:
            context['school'] = school
            if 'school_slug' not in context:
                context['school_slug'] = school.slug

    # Dynamic Currency and Language Resolution
    sys_settings = context.get('system_settings')
    curr_code = 'USD'
    curr_sym = '$'
    lang_code = 'en'

    if school:
        curr_code = getattr(school, 'clean_currency', None) or (getattr(school, 'currency', 'USD') or 'USD').strip().upper()
        curr_sym = getattr(school, 'clean_currency_symbol', None) or (getattr(school, 'currency_symbol', '$') or '$').strip()
        if not curr_sym:
            curr_sym = getattr(School, 'DEFAULT_CURRENCY_SYMBOLS', {}).get(curr_code, '$')
        lang_code = getattr(school, 'clean_language', None) or getattr(school, 'language', 'en') or 'en'
    elif sys_settings:
        curr_code = (getattr(sys_settings, 'currency_code', 'USD') or 'USD').strip().upper()
        curr_sym = (getattr(sys_settings, 'currency_symbol', '$') or '$').strip()
        lang_code = (getattr(sys_settings, 'default_language', 'en') or 'en').strip().lower()

    context['currency'] = curr_code
    context['currency_code'] = curr_code
    context['currency_symbol'] = curr_sym
    context['school_currency'] = curr_code
    context['school_currency_symbol'] = curr_sym
    context['school_language'] = lang_code
    context['language'] = lang_code

    return context
