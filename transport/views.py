from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Prefetch
from students.models import Student
from tenants.models import School
from .models import Driver

# Check if models exist
try:
    from .models import Route, Vehicle
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Route:
        pass
    class Vehicle:
        pass


class RouteListView(LoginRequiredMixin, ListView):
    template_name = 'transport/routes.html'
    context_object_name = 'routes'
    
    def get_queryset(self):
        if MODELS_EXIST:
            from tenants.models import School
            school_slug = self.kwargs.get('school_slug')
            try:
                school = School.objects.get(slug=school_slug)
                return Route.objects.filter(school=school) | Route.objects.filter(school__isnull=True)
            except:
                return Route.objects.filter(school__isnull=True)
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            from tenants.models import School
            school_slug = self.kwargs.get('school_slug')
            school = School.objects.get(slug=school_slug)
            Route.objects.create(
                school=school,
                name=request.POST.get('name'),
                start_place=request.POST.get('start_place'),
                end_place=request.POST.get('end_place'),
                distance=request.POST.get('distance'),
                fare=request.POST.get('fare')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class VehicleListView(LoginRequiredMixin, ListView):
    template_name = 'transport/vehicles.html'
    context_object_name = 'vehicles'
    
    def get_queryset(self):
        if MODELS_EXIST:
            from tenants.models import School
            from django.db.models import Prefetch
            
            school_slug = self.kwargs.get('school_slug')
            try:
                school = School.objects.get(slug=school_slug)
                vehicles = Vehicle.objects.filter(school=school) | Vehicle.objects.filter(school__isnull=True)
            except School.DoesNotExist:
                vehicles = Vehicle.objects.filter(school__isnull=True)
                
            # Prefetch related drivers to avoid N+1 queries
            vehicles = vehicles.prefetch_related(
                Prefetch('drivers', queryset=Driver.objects.select_related('user'))
            )
            
            # Add driver_name and driver_contact properties to each vehicle
            for vehicle in vehicles:
                driver = vehicle.drivers.first()  # Get the first driver assigned to the vehicle
                if driver and driver.user:
                    vehicle.driver_name = driver.user.get_full_name()
                    vehicle.driver_contact = driver.user.phone or driver.user.mobile or 'No contact'
                else:
                    vehicle.driver_name = 'No driver assigned'
                    vehicle.driver_contact = 'N/A'
                    
            return vehicles
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if MODELS_EXIST:
            from tenants.models import School
            from accounts.models import User
            
            school_slug = self.kwargs.get('school_slug')
            try:
                school = School.objects.get(slug=school_slug)
                # Get all routes for the school
                context['routes'] = Route.objects.filter(school=school) | Route.objects.filter(school__isnull=True)
                # Get all staff members who are not already assigned as drivers
                # Get all staff members who are not already drivers
                # Only include users with the driver role
                staff_roles = ['driver']
                
                # Get all users with staff roles who are active and not already drivers
                context['staff_members'] = User.objects.filter(
                    is_active=True,
                    role__in=staff_roles
                ).exclude(
                    driver_profile__isnull=False  # Exclude users who are already drivers
                ).select_related('staff_profile').only(
                    'id', 'first_name', 'last_name', 'phone', 'mobile', 'email', 'role'
                ).order_by('first_name', 'last_name')
                
                # Debug output (will be shown in the template)
                print("Available staff members:", list(context['staff_members'].values('id', 'first_name', 'last_name', 'role')))
            except School.DoesNotExist:
                context['routes'] = Route.objects.filter(school__isnull=True)
                context['staff_members'] = User.objects.none()
        else:
            context['routes'] = []
            context['staff_members'] = []
            
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            from django.db import IntegrityError
            from django.core.exceptions import ValidationError
            from accounts.models import User
            
            school_slug = self.kwargs.get('school_slug')
            vehicle_number = request.POST.get('vehicle_number', '').strip()
            vehicle_model = request.POST.get('vehicle_model', '').strip()
            capacity = request.POST.get('capacity', '').strip()
            route_id = request.POST.get('route')
            driver_id = request.POST.get('driver')
            
            # Basic validation
            if not all([vehicle_number, vehicle_model, capacity, route_id, driver_id]):
                return JsonResponse({
                    'success': False,
                    'message': 'All fields are required.',
                    'errors': {
                        'vehicle_number': ['This field is required.'] if not vehicle_number else None,
                        'vehicle_model': ['This field is required.'] if not vehicle_model else None,
                        'capacity': ['This field is required.'] if not capacity else None,
                        'route': ['Please select a route.'] if not route_id else None,
                        'driver': ['Please select a driver.'] if not driver_id else None
                    }
                }, status=400)
                
            # Check if vehicle with same number already exists
            if Vehicle.objects.filter(vehicle_number__iexact=vehicle_number).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'A vehicle with this number already exists.',
                    'errors': {
                        'vehicle_number': ['A vehicle with this number already exists.']
                    }
                }, status=400)
                
            # Get the school and create the vehicle
            school = School.objects.get(slug=school_slug)
            
            # Get the driver (remove school filter as it doesn't exist on User)
            try:
                driver = User.objects.get(id=driver_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected driver not found.',
                    'errors': {'driver': ['Selected driver not found.']}
                }, status=400)
            
            # Create the vehicle
            try:
                vehicle = Vehicle.objects.create(
                    school=school,
                    vehicle_number=vehicle_number,
                    vehicle_model=vehicle_model,
                    capacity=capacity,
                    route_id=route_id
                )
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error creating vehicle: {str(e)}',
                    'errors': {'__all__': [str(e)]}
                }, status=400)
            
            # Create driver profile if it doesn't exist
            from .models import Driver
            from datetime import date, timedelta
            
            try:
                driver_profile, created = Driver.objects.get_or_create(
                    user=driver,
                    defaults={
                        'name': driver.get_full_name(),
                        'phone': driver.phone or driver.mobile or '',
                        'license_number': f'PENDING-{driver.id}-{date.today().year}',
                        'license_expiry': date.today() + timedelta(days=365),  # 1 year from now
                        'school': school,
                        'is_active': True
                    }
                )
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error creating driver profile: {str(e)}',
                    'errors': {'__all__': [str(e)]}
                }, status=400)
            
            # Assign the driver to the vehicle
            driver_profile.vehicle = vehicle
            driver_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Vehicle added successfully!',
                'vehicle_id': vehicle.id
            })
            
        except School.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'School not found.',
                'errors': {'school': ['School not found.']}
            }, status=404)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected driver not found.',
                'errors': {'driver': ['Selected driver not found.']}
            }, status=400)
        except IntegrityError as e:
            return JsonResponse({
                'success': False,
                'message': 'A database error occurred.',
                'errors': {'__all__': ['A database error occurred. Please try again.']}
            }, status=400)
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': 'Validation error',
                'errors': e.message_dict
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e),
                'errors': {'__all__': [str(e)]}
            }, status=400)
