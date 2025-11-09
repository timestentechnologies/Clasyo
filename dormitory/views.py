from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from students.models import Student

# Check if models exist
try:
    from .models import Dormitory, Room, RoomAllocation
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Dormitory:
        pass
    class Room:
        pass
    class RoomAllocation:
        pass


class DormitoryListView(LoginRequiredMixin, ListView):
    template_name = 'dormitory/dormitory_list.html'
    context_object_name = 'dormitories'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Dormitory.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            Dormitory.objects.create(
                name=request.POST.get('name'),
                dormitory_type=request.POST.get('dormitory_type'),
                address=request.POST.get('address'),
                description=request.POST.get('description', '')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class RoomListView(LoginRequiredMixin, ListView):
    template_name = 'dormitory/rooms.html'
    context_object_name = 'rooms'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Room.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            context['dormitories'] = Dormitory.objects.all()
        else:
            context['dormitories'] = []
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            Room.objects.create(
                dormitory_id=request.POST.get('dormitory'),
                room_number=request.POST.get('room_number'),
                room_type=request.POST.get('room_type'),
                capacity=request.POST.get('capacity')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class RoomAllocationListView(LoginRequiredMixin, ListView):
    template_name = 'dormitory/allocations.html'
    context_object_name = 'allocations'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return RoomAllocation.objects.filter(is_active=True).select_related('student', 'room', 'room__dormitory')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class AllocateRoomView(LoginRequiredMixin, CreateView):
    template_name = 'dormitory/allocate_room.html'
    model = RoomAllocation if MODELS_EXIST else None
    fields = ['student', 'room', 'bed_number', 'monthly_fee', 'start_date', 'end_date']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            context['available_rooms'] = Room.objects.filter(is_active=True).exclude(is_full=True)
        return context


class OccupancyReportView(LoginRequiredMixin, ListView):
    template_name = 'dormitory/occupancy_report.html'
    context_object_name = 'dormitories'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Dormitory.objects.filter(is_active=True).prefetch_related('rooms', 'rooms__allocations')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if MODELS_EXIST:
            # Calculate overall statistics
            total_capacity = sum(d.total_capacity for d in self.get_queryset())
            total_occupied = RoomAllocation.objects.filter(is_active=True).count()
            context['total_capacity'] = total_capacity
            context['total_occupied'] = total_occupied
            context['occupancy_percentage'] = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
        
        return context
