"""
Middleware for handling user impersonation (Login As functionality)
"""
from django.contrib.auth import get_user_model

User = get_user_model()


class ImpersonationMiddleware:
    """
    Middleware to handle impersonation by school admins.
    Allows admins to login as other users while keeping their original session.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if there's an impersonated user in the session
            impersonated_user_id = request.session.get('impersonated_user_id')
            original_user_id = request.session.get('original_user_id')
            
            if impersonated_user_id and original_user_id:
                try:
                    # Get the original admin user
                    original_user = User.objects.get(pk=original_user_id)
                    
                    # Validate: Only allow impersonation if original user is admin/superadmin
                    if original_user.role not in ['admin', 'school_admin', 'superadmin']:
                        # Invalid impersonation - clear it
                        del request.session['impersonated_user_id']
                        del request.session['original_user_id']
                        request.is_impersonating = False
                        request.original_user = None
                    else:
                        # Valid impersonation - Replace the current user with the impersonated user
                        impersonated_user = User.objects.get(pk=impersonated_user_id)
                        
                        # Store the original admin user for reference
                        request.original_user = original_user
                        
                        # Replace request.user with the impersonated user
                        request.user = impersonated_user
                        
                        # Set a flag to indicate impersonation is active
                        request.is_impersonating = True
                except User.DoesNotExist:
                    # If user doesn't exist, clear the impersonation session
                    if 'impersonated_user_id' in request.session:
                        del request.session['impersonated_user_id']
                    if 'original_user_id' in request.session:
                        del request.session['original_user_id']
                    request.is_impersonating = False
                    request.original_user = None
            else:
                request.is_impersonating = False
                request.original_user = None
        else:
            request.is_impersonating = False
            request.original_user = None
        
        response = self.get_response(request)
        return response
