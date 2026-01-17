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
            from tenants.models import School
            school_slug = self.kwargs.get('school_slug')
            try:
                school = School.objects.get(slug=school_slug)
                return Dormitory.objects.filter(school=school) | Dormitory.objects.filter(school__isnull=True)
            except:
                return Dormitory.objects.filter(school__isnull=True)
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
            Dormitory.objects.create(
                school=school,
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
            from tenants.models import School
            school_slug = self.kwargs.get('school_slug')
            try:
                school = School.objects.get(slug=school_slug)
                return Room.objects.filter(dormitory__school=school)
            except Exception:
                return Room.objects.none()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            try:
                from tenants.models import School
                school = School.objects.get(slug=context['school_slug'])
                context['dormitories'] = Dormitory.objects.filter(school=school)
            except Exception:
                context['dormitories'] = Dormitory.objects.none()
        else:
            context['dormitories'] = []
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models unavailable'})
            from tenants.models import School
            school_slug = self.kwargs.get('school_slug')
            school = School.objects.get(slug=school_slug)
            dormitory_id = request.POST.get('dormitory')
            dormitory = Dormitory.objects.filter(id=dormitory_id, school=school).first()
            if not dormitory:
                return JsonResponse({'success': False, 'error': 'Invalid dormitory for this school'})
            Room.objects.create(
                dormitory=dormitory,
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
            try:
                from tenants.models import School
                school_slug = self.kwargs.get('school_slug')
                school = School.objects.get(slug=school_slug)
                return RoomAllocation.objects.filter(
                    is_active=True,
                    room__dormitory__school=school
                ).select_related('student', 'room', 'room__dormitory')
            except Exception:
                return RoomAllocation.objects.none()
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
            try:
                from tenants.models import School
                school = School.objects.get(slug=context['school_slug'])
                # Available rooms in current school only
                available_rooms = []
                for room in Room.objects.filter(is_active=True, dormitory__school=school):
                    if not room.is_full():
                        available_rooms.append(room)
                context['available_rooms'] = available_rooms

                # Students belonging to current school (via linked user)
                context['students'] = Student.objects.filter(
                    is_active=True,
                    user__school=school
                ).order_by('first_name', 'last_name')
            except Exception:
                context['available_rooms'] = []
                context['students'] = []
        else:
            context['available_rooms'] = []
            context['students'] = []
        return context


class OccupancyReportView(LoginRequiredMixin, ListView):
    template_name = 'dormitory/occupancy_report.html'
    context_object_name = 'dormitories'
    
    def get_queryset(self):
        if MODELS_EXIST:
            try:
                from tenants.models import School
                school_slug = self.kwargs.get('school_slug')
                school = School.objects.get(slug=school_slug)
                return Dormitory.objects.filter(
                    is_active=True,
                    school=school
                ).prefetch_related('rooms', 'rooms__allocations')
            except Exception:
                return Dormitory.objects.none()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if MODELS_EXIST:
            # Calculate overall statistics
            total_capacity = sum(d.total_capacity for d in self.get_queryset())
            try:
                from tenants.models import School
                school = School.objects.get(slug=context['school_slug'])
                total_occupied = RoomAllocation.objects.filter(
                    is_active=True,
                    room__dormitory__school=school
                ).count()
            except Exception:
                total_occupied = 0
            context['total_capacity'] = total_capacity
            context['total_occupied'] = total_occupied
            context['occupancy_percentage'] = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
        
        return context
