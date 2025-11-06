from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from students.models import Student

# Check if models exist
try:
    from .models import Dormitory, Room
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Dormitory:
        pass
    class Room:
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
