from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from students.models import Student

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
            return Route.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            Route.objects.create(
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
            return Vehicle.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            context['routes'] = Route.objects.all()
        else:
            context['routes'] = []
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            Vehicle.objects.create(
                vehicle_number=request.POST.get('vehicle_number'),
                vehicle_model=request.POST.get('vehicle_model'),
                capacity=request.POST.get('capacity'),
                route_id=request.POST.get('route'),
                driver_name=request.POST.get('driver_name'),
                driver_contact=request.POST.get('driver_contact')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
