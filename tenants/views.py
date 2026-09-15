from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.urls import reverse
from .models import School
from .services import provision_school_database, is_school_database_ready, ensure_school_database


class WorkspaceProvisioningView(View):
    """
    Renders the 'Setting up your workspace...' loading screen
    while the school's dedicated database is created and migrated.
    """
    template_name = 'tenants/provisioning.html'

    def get(self, request, school_slug):
        school = get_object_or_404(School.objects.using('default'), slug=school_slug)
        
        # If already provisioned, go straight to dashboard
        if is_school_database_ready(school):
            return redirect('core:dashboard', school_slug=school.slug)

        context = {
            'school': school,
            'db_name': school.slug,
        }
        return render(request, self.template_name, context)


class WorkspaceProvisioningApiView(View):
    """
    AJAX endpoint called by the provisioning screen to execute 
    database creation and migrations asynchronously.
    """
    def post(self, request, school_slug):
        school = get_object_or_404(School.objects.using('default'), slug=school_slug)
        
        try:
            # Ensure the dedicated database is created and migrated
            ensure_school_database(school)
            
            dashboard_url = reverse('core:dashboard', kwargs={'school_slug': school.slug})
            return JsonResponse({
                'success': True,
                'status': 'ready',
                'message': f"Workspace and database '{school.slug}' initialized successfully!",
                'redirect_url': dashboard_url
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'status': 'error',
                'message': str(e)
            }, status=500)


class WorkspaceStatusApiView(View):
    """
    Status poll endpoint to check whether the school's database is ready.
    """
    def get(self, request, school_slug):
        school = get_object_or_404(School.objects.using('default'), slug=school_slug)
        ready = is_school_database_ready(school)
        
        dashboard_url = reverse('core:dashboard', kwargs={'school_slug': school.slug}) if ready else ''
        return JsonResponse({
            'ready': ready,
            'redirect_url': dashboard_url
        })
