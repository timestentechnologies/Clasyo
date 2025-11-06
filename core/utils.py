"""Utility functions for the core application"""
from django.utils.text import slugify
from accounts.models import User


def generate_email(first_name, last_name, school_slug, role='student'):
    """
    Generate email address in format: firstname.lastname@schoolslug.com
    If email already exists, append number: firstname.lastname2@schoolslug.com
    
    Args:
        first_name: User's first name
        last_name: User's last name
        school_slug: School's slug (used as domain)
        role: User role (student, teacher, staff, parent)
    
    Returns:
        Generated email address
    """
    # Clean and lowercase names
    first = slugify(first_name).replace('-', '')
    last = slugify(last_name).replace('-', '')
    
    # Base email
    base_email = f"{first}.{last}@{school_slug}.com"
    
    # Check if email exists
    if not User.objects.filter(email=base_email).exists():
        return base_email
    
    # If exists, try with numbers
    counter = 2
    while counter < 100:  # Limit to prevent infinite loop
        email = f"{first}.{last}{counter}@{school_slug}.com"
        if not User.objects.filter(email=email).exists():
            return email
        counter += 1
    
    # Fallback with timestamp if too many duplicates
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{first}.{last}.{timestamp}@{school_slug}.com"


def get_school_slug_from_request(request):
    """
    Get school slug from request (tenant or URL)
    
    Args:
        request: Django request object
    
    Returns:
        School slug or 'school' as default
    """
    # Try from tenant middleware
    if hasattr(request, 'tenant') and request.tenant:
        return request.tenant.slug
    
    # Try from URL path
    path_parts = request.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'school':
        return path_parts[1]
    
    # Default fallback
    return 'school'
