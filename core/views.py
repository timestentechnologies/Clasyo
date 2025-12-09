from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from datetime import datetime, time
from .models import (
    AcademicYear, Session, Holiday, SystemSetting,
    Notification, ToDoList, CalendarEvent
)


class AppsHomeView(LoginRequiredMixin, TemplateView):
    """Apps home page - landing page after login"""
    template_name = 'core/apps_home.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect super admins to their own dashboard"""
        if request.user.is_authenticated and request.user.role == 'superadmin':
            return redirect('superadmin:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug')
        context['school_slug'] = school_slug
        
        # Fetch the actual school object
        from tenants.models import School
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            context['school'] = school
        except School.DoesNotExist:
            context['school'] = None
        
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'core/dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect super admins to their own dashboard"""
        if request.user.is_authenticated and request.user.role == 'superadmin':
            return redirect('superadmin:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_template_names(self):
        """Return different templates based on user role"""
        user = self.request.user
        
        if user.is_superadmin:
            return ['superadmin/dashboard.html']
        elif user.is_school_admin:
            return ['core/admin_dashboard.html']
        elif user.is_teacher:
            return ['core/teacher_dashboard.html']
        elif user.is_parent:
            return ['core/parent_dashboard.html']
        elif user.is_student:
            return ['core/student_dashboard.html']
        else:
            return ['core/dashboard.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get school from URL
        school_slug = self.kwargs.get('school_slug')
        context['school_slug'] = school_slug
        
        # Fetch the actual school object
        from tenants.models import School
        from datetime import date
        from django.db.models import Q
        
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            context['school'] = school
        except School.DoesNotExist:
            context['school'] = None
        
        # Common data for all users
        try:
            context['notifications'] = Notification.objects.filter(
                user=user, is_read=False
            )[:5]
        except:
            context['notifications'] = []
        
        try:
            context['todos'] = ToDoList.objects.filter(
                user=user, is_completed=False
            )[:5]
        except:
            context['todos'] = []
        
        try:
            context['upcoming_events'] = CalendarEvent.objects.filter(
                Q(is_public=True) | Q(participants=user),
                start_date__gte=date.today()
            ).order_by('start_date')[:5]
        except:
            context['upcoming_events'] = []
        
        # Message count (assuming there's a Message model with is_read field)
        # If Message model doesn't exist yet, this will be 0
        context['unread_messages_count'] = 0
        try:
            from communication.models import Message
            context['unread_messages_count'] = Message.objects.filter(
                recipient=user, is_read=False
            ).count()
        except:
            pass
        
        # Role-specific data
        if user.is_school_admin or user.role == 'school_admin':
            from students.models import Student
            from accounts.models import User
            from academics.models import Class
            
            context['total_students'] = Student.objects.filter(is_active=True).count()
            context['total_teachers'] = User.objects.filter(
                role='teacher', 
                is_active=True
            ).count()
            context['total_classes'] = Class.objects.filter(is_active=True).count()
            context['total_staff'] = User.objects.filter(
                role__in=['teacher', 'staff', 'accountant'], 
                is_active=True
            ).count()
            context['pending_tasks'] = ToDoList.objects.filter(
                user=user, is_completed=False
            ).count()
            
        elif user.is_teacher:
            # Teacher specific data
            pass
        
        elif user.is_parent:
            # Parent specific data - get children
            from students.models import Student
            children = Student.objects.filter(parent_user=user, is_active=True).select_related('current_class', 'section')
            context['children'] = children
            
            # Calculate average attendance for all children
            if children.exists():
                from attendance.models import StudentAttendance
                from django.db.models import Count
                total_present = 0
                total_records = 0
                for child in children:
                    attendance_stats = StudentAttendance.objects.filter(student=child).aggregate(
                        total=Count('id'),
                        present=Count('id', filter=Q(status='present'))
                    )
                    total_records += attendance_stats['total'] or 0
                    total_present += attendance_stats['present'] or 0
                
                if total_records > 0:
                    context['avg_attendance'] = round((total_present / total_records) * 100, 1)
                else:
                    context['avg_attendance'] = 0
            else:
                context['avg_attendance'] = 0
        
        elif user.is_student:
            # Student specific data
            # Check if student_profile exists before accessing it
            try:
                student_profile = user.student_profile
                context['student_profile'] = student_profile
                context['student'] = student_profile  # Also add as 'student' for template compatibility
            except:
                # User has student role but no student profile yet
                context['student_profile'] = None
                context['student'] = None
        
        return context


class MyChildrenView(LoginRequiredMixin, TemplateView):
    """Parent view to see ONLY their own children with performance details"""
    template_name = 'core/my_children.html'
    
    def dispatch(self, request, *args, **kwargs):
        # SECURITY: Only parents can access this view
        if not request.user.is_parent:
            messages.error(request, "Access denied. This page is for parents only.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        school_slug = self.kwargs.get('school_slug')
        context['school_slug'] = school_slug
        
        from students.models import Student
        from django.db.models import Avg, Count, Q
        from tenants.models import School
        
        # Get school
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            context['school'] = school
        except School.DoesNotExist:
            context['school'] = None
        
        # SECURITY: Get ONLY children linked to this parent user
        children_data = []
        children = Student.objects.filter(
            parent_user=user,  # CRITICAL: Only this parent's children
            is_active=True
        ).select_related('current_class', 'section')
        
        # For each child, get their detailed information
        for child in children:
            child_info = {
                'student': child,
                'teachers': [],
                'attendance_percentage': 0,
                'recent_results': [],
                'average_grade': None,
            }
            
            # Get class teachers (only for THIS child's section)
            if child.section and child.section.class_teacher:
                child_info['teachers'] = [child.section.class_teacher]
            else:
                child_info['teachers'] = []
            
            # Get attendance stats (only for THIS child)
            try:
                from attendance.models import StudentAttendance
                attendance_records = StudentAttendance.objects.filter(student=child)
                total = attendance_records.count()
                present = attendance_records.filter(status='present').count()
                if total > 0:
                    child_info['attendance_percentage'] = round((present / total) * 100, 1)
            except:
                pass
            
            # Get recent exam results (only for THIS child)
            try:
                from examinations.models import ExamResult
                recent_results = ExamResult.objects.filter(
                    student=child
                ).select_related('exam', 'student', 'grade').order_by('-exam__start_date')[:5]
                child_info['recent_results'] = recent_results
                
                # Calculate average grade
                if recent_results:
                    total_marks = sum(r.marks_obtained for r in recent_results if r.marks_obtained)
                    total_possible = sum(r.total_marks for r in recent_results if r.total_marks)
                    if total_possible > 0:
                        child_info['average_grade'] = round((total_marks / total_possible) * 100, 1)
            except:
                pass
            
            children_data.append(child_info)
        
        context['children_data'] = children_data
        context['children_count'] = len(children_data)
        
        return context


class NotificationListView(LoginRequiredMixin, ListView):
    """List all notifications"""
    model = Notification
    template_name = 'core/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class MarkNotificationReadView(LoginRequiredMixin, View):
    """Mark single notification as read"""
    def post(self, request, pk, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_read()
        school_slug = kwargs.get('school_slug')
        if school_slug:
            return redirect('core:notifications', school_slug=school_slug)
        return redirect('core:notifications')


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Mark all notifications as read"""
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        school_slug = kwargs.get('school_slug')
        if school_slug:
            return redirect('core:notifications', school_slug=school_slug)
        return redirect('core:notifications')


class ToDoListView(LoginRequiredMixin, ListView):
    """List all to-dos"""
    model = ToDoList
    template_name = 'core/todos.html'
    context_object_name = 'todos'
    
    def get_queryset(self):
        return ToDoList.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class ToDoCreateView(LoginRequiredMixin, CreateView):
    """Create new to-do"""
    model = ToDoList
    template_name = 'core/todo_form.html'
    fields = ['title', 'description', 'priority', 'due_date']
    success_url = None
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'To-do item created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        school_slug = self.kwargs.get('school_slug', '')
        if school_slug:
            return reverse_lazy('core:todos', kwargs={'school_slug': school_slug})
        return reverse_lazy('core:todos')


class ToDoToggleView(LoginRequiredMixin, View):
    """Toggle to-do completion status"""
    def post(self, request, pk, *args, **kwargs):
        todo = get_object_or_404(ToDoList, pk=pk, user=request.user)
        todo.is_completed = not todo.is_completed
        if todo.is_completed:
            from django.utils import timezone
            todo.completed_at = timezone.now()
        else:
            todo.completed_at = None
        todo.save()

        school_slug = kwargs.get('school_slug')
        if school_slug:
            return redirect('core:todos', school_slug=school_slug)
        return redirect('core:todos')


class ToDoDeleteView(LoginRequiredMixin, View):
    """Delete to-do"""
    def post(self, request, pk, *args, **kwargs):
        todo = get_object_or_404(ToDoList, pk=pk, user=request.user)
        todo.delete()
        messages.success(request, 'To-do item deleted successfully!')
        school_slug = kwargs.get('school_slug')
        if school_slug:
            return redirect('core:todos', school_slug=school_slug)
        return redirect('core:todos')


@method_decorator(csrf_exempt, name='dispatch')
class SystemSettingsUpdateView(View):
    """Update system settings"""
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            settings, created = SystemSetting.objects.get_or_create(id=1)
            
            # Update admission number prefix if provided
            if 'admission_number_prefix' in request.POST:
                prefix = request.POST.get('admission_number_prefix', 'STU').strip().upper()
                if prefix:
                    settings.admission_number_prefix = prefix
                    settings.save()
                    return JsonResponse({
                        'success': True, 
                        'message': f'Admission number prefix updated to: {prefix}'
                    })
            
            messages.success(request, 'Settings updated successfully!')
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class CalendarView(LoginRequiredMixin, TemplateView):
    """Calendar view"""
    template_name = 'core/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class CalendarEventListView(LoginRequiredMixin, ListView):
    """List calendar events as JSON (for AJAX)"""
    model = CalendarEvent

    def get_queryset(self):
        user = self.request.user
        return CalendarEvent.objects.filter(
            Q(is_public=True) | Q(participants=user) | Q(created_by=user)
        )

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

        queryset = self.get_queryset()

        # Optional filter by specific date (YYYY-MM-DD)
        date_str = request.GET.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_dt = datetime.combine(target_date, time.min)
                end_dt = datetime.combine(target_date, time.max)
                queryset = queryset.filter(start_date__lte=end_dt, end_date__gte=start_dt)
            except ValueError:
                pass

        events_data = []
        for event in queryset.order_by('start_date'):
            events_data.append({
                'id': event.id,
                'title': event.title,
                'event_type': event.get_event_type_display(),
                'start': event.start_date.isoformat() if event.start_date else '',
                'end': event.end_date.isoformat() if event.end_date else '',
                'location': event.location,
                'description': event.description,
                'start_date_display': event.start_date.strftime('%b %d, %Y %I:%M %p') if event.start_date else '',
            })

        return JsonResponse({'success': True, 'events': events_data})


@method_decorator(csrf_exempt, name='dispatch')
class CalendarEventCreateView(View):
    """Create calendar event"""
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})

            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            start_time_str = request.POST.get('start_time') or '00:00'
            end_time_str = request.POST.get('end_time') or start_time_str

            try:
                start_dt = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M") if start_date_str else None
                end_dt = datetime.strptime(f"{end_date_str} {end_time_str}", "%Y-%m-%d %H:%M") if end_date_str else None
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date or time format'}, status=400)

            CalendarEvent.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description', ''),
                event_type=request.POST.get('event_type', 'other'),
                start_date=start_dt,
                end_date=end_dt,
                location=request.POST.get('location', ''),
                created_by=request.user
            )
            return JsonResponse({'success': True, 'message': 'Event created successfully!'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class CalendarEventDeleteView(View):
    """Delete calendar event"""
    def post(self, request, pk, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            event = CalendarEvent.objects.get(pk=pk)
            event.delete()
            return JsonResponse({'success': True, 'message': 'Event deleted successfully!'})
        except CalendarEvent.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Event not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class CalendarEventDetailView(View):
    """Return a single event as JSON"""
    def get(self, request, pk, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
            
            event = get_object_or_404(
                CalendarEvent.objects.filter(
                    Q(is_public=True) | Q(participants=request.user) | Q(created_by=request.user)
                ),
                pk=pk
            )
            return JsonResponse({
                'success': True,
                'event': {
                    'id': event.id,
                    'title': event.title,
                    'type': event.get_event_type_display(),
                    'start_date': event.start_date.strftime('%b %d, %Y %I:%M %p') if event.start_date else '',
                    'end_date': event.end_date.strftime('%b %d, %Y %I:%M %p') if event.end_date else '',
                    'location': event.location,
                    'description': event.description,
                }
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class SystemSettingsView(LoginRequiredMixin, TemplateView):
    """System settings view"""
    template_name = 'core/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['settings'] = SystemSetting.get_settings()
        return context


class SystemSettingsUpdateView(LoginRequiredMixin, UpdateView):
    """Update system settings"""
    model = SystemSetting
    template_name = 'core/settings_form.html'
    fields = '__all__'
    success_url = reverse_lazy('core:settings')
    
    def get_object(self):
        return SystemSetting.get_settings()
    
    def form_valid(self, form):
        messages.success(self.request, 'Settings updated successfully!')
        return super().form_valid(form)


class AcademicYearListView(LoginRequiredMixin, ListView):
    """List academic years"""
    model = AcademicYear
    template_name = 'core/academic_years.html'
    context_object_name = 'academic_years'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class AcademicYearCreateView(View):
    """Create academic year"""
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
                
            AcademicYear.objects.create(
                name=request.POST.get('name'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                is_active=request.POST.get('is_active') == 'on'
            )
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class AcademicYearUpdateView(View):
    """Update academic year"""
    
    def post(self, request, pk, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            try:
                year = AcademicYear.objects.get(pk=pk)
            except AcademicYear.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Academic year not found'})
                
            year.name = request.POST.get('name')
            year.start_date = request.POST.get('start_date')
            year.end_date = request.POST.get('end_date')
            year.is_active = request.POST.get('is_active') == 'on'
            year.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})
    
    def get(self, request, pk, *args, **kwargs):
        """Get academic year data for editing"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            try:
                year = AcademicYear.objects.get(pk=pk)
            except AcademicYear.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Academic year not found'})
                
            return JsonResponse({
                'success': True,
                'data': {
                    'id': year.id,
                    'name': year.name,
                    'start_date': year.start_date.strftime('%Y-%m-%d'),
                    'end_date': year.end_date.strftime('%Y-%m-%d'),
                    'is_active': year.is_active
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class AcademicYearDeleteView(View):
    """Delete academic year"""
    def post(self, request, pk, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            try:
                year = AcademicYear.objects.get(pk=pk)
            except AcademicYear.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Academic year not found'})
                
            year.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class SessionListView(LoginRequiredMixin, View):
    """List sessions/terms for an academic year"""
    def get(self, request, year_id, *args, **kwargs):
        try:
            print(f"[DEBUG] SessionListView - Fetching sessions for year_id: {year_id}")
            sessions = Session.objects.filter(academic_year_id=year_id)
            print(f"[DEBUG] Found {sessions.count()} sessions")
            data = [{
                'id': s.id,
                'name': s.name,
                'start_date': s.start_date.strftime('%Y-%m-%d'),
                'end_date': s.end_date.strftime('%Y-%m-%d')
            } for s in sessions]
            print(f"[DEBUG] Returning data: {data}")
            return JsonResponse({'success': True, 'terms': data})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class SessionCreateView(View):
    """Create session/term"""
    
    def dispatch(self, *args, **kwargs):
        # Override dispatch to ensure we always return JSON
        try:
            return super().dispatch(*args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f'Dispatch error: {str(e)}'})
    
    def post(self, request, *args, **kwargs):
        try:
            # Check authentication manually since we're using csrf_exempt
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            academic_year_id = request.POST.get('academic_year')
            name = request.POST.get('name')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            print(f"[DEBUG] SessionCreate - Received:")
            print(f"  academic_year_id: {academic_year_id}")
            print(f"  name: {name}")
            print(f"  start_date: {start_date}")
            print(f"  end_date: {end_date}")
            
            if not all([academic_year_id, name, start_date, end_date]):
                return JsonResponse({'success': False, 'error': 'All fields are required'})
            
            # Verify academic year exists
            try:
                year = AcademicYear.objects.get(pk=academic_year_id)
                print(f"[DEBUG] Found academic year: {year}")
            except AcademicYear.DoesNotExist:
                print(f"[DEBUG] Academic year not found: {academic_year_id}")
                return JsonResponse({'success': False, 'error': f'Academic year not found'})
            
            session = Session.objects.create(
                academic_year=year,
                name=name,
                start_date=start_date,
                end_date=end_date
            )
            print(f"[DEBUG] Created session: {session}")
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] SessionCreate exception:")
            print(error_trace)
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class SessionDeleteView(View):
    """Delete session/term"""
    def post(self, request, pk, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            try:
                session = Session.objects.get(pk=pk)
            except Session.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Session not found'})
                
            session.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class HolidayListView(LoginRequiredMixin, ListView):
    """List holidays"""
    model = Holiday
    template_name = 'core/holidays.html'
    context_object_name = 'holidays'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class HolidayCreateView(LoginRequiredMixin, CreateView):
    """Create holiday"""
    model = Holiday
    template_name = 'core/holiday_form.html'
    fields = ['title', 'description', 'holiday_type', 'from_date', 'to_date', 'is_active']
    success_url = reverse_lazy('core:holidays')


class EventsView(LoginRequiredMixin, ListView):
    """Events view"""
    model = CalendarEvent
    template_name = 'core/events.html'
    context_object_name = 'events'
    
    def get_queryset(self):
        user = self.request.user
        return CalendarEvent.objects.filter(
            Q(is_public=True) | Q(participants=user) | Q(created_by=user)
        ).order_by('start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'core/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class SearchView(LoginRequiredMixin, TemplateView):
    """Global search view"""
    template_name = 'core/search.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        query = self.request.GET.get('q', '')
        context['query'] = query
        
        # Simple search implementation (can be enhanced)
        if query:
            from students.models import Student
            from accounts.models import User
            
            context['students'] = Student.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(admission_number__icontains=query) |
                Q(roll_number__icontains=query)
            )[:10]
            
            context['staff'] = User.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query),
                role__in=['teacher', 'staff', 'accountant']
            )[:10]
        
        return context


class LoginAsView(LoginRequiredMixin, View):
    """Allow school admins to login as other users (impersonation)"""
    
    def get(self, request, user_id, *args, **kwargs):
        from accounts.models import User
        
        # Get the real admin user (either current user or original user if already impersonating)
        if hasattr(request, 'original_user') and request.original_user:
            admin_user = request.original_user
        else:
            admin_user = request.user
        
        # Only allow admin, school_admin and super_admin to impersonate
        if admin_user.role not in ['admin', 'school_admin', 'super_admin']:
            messages.error(request, 'You do not have permission to perform this action.')
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        
        try:
            target_user = User.objects.get(pk=user_id)
            
            # Don't allow impersonating other admins
            if target_user.role in ['admin', 'super_admin', 'school_admin']:
                messages.error(request, 'Cannot impersonate other administrators.')
                return redirect(request.META.get('HTTP_REFERER', '/'))
            
            # Store the original user ID in session (use admin_user's ID)
            if 'original_user_id' not in request.session:
                request.session['original_user_id'] = admin_user.id
            
            # Store impersonated user in session
            request.session['impersonated_user_id'] = target_user.id
            
            messages.success(
                request, 
                f'You are now logged in as {target_user.get_full_name()} ({target_user.get_role_display()})'
            )
            
            # Redirect to appropriate dashboard
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
            
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect(request.META.get('HTTP_REFERER', '/'))


class StopImpersonationView(View):
    """Stop impersonating and return to original admin account"""

    def get(self, request, *args, **kwargs):
        if hasattr(request, 'original_user') and request.original_user:
            from django.contrib.auth import login
            from django.contrib.auth.models import User

            user = get_object_or_404(User, id=request.original_user)
            login(request, user)
            messages.success(request, f'Stopped impersonating {user.get_full_name() or user.username}')
            return redirect('core:dashboard')
        return redirect('core:dashboard')


class BillingView(LoginRequiredMixin, TemplateView):
    """School admin billing and subscription management view"""
    template_name = 'core/billing.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Only allow school admins to access billing"""
        if not request.user.is_school_admin:
            messages.error(request, "Access denied. This page is for school admins only.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug')
        context['school_slug'] = school_slug
        
        # Get school
        from tenants.models import School
        from subscriptions.models import Subscription, SubscriptionPlan
        from django.utils import timezone
        
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            context['school'] = school
        except School.DoesNotExist:
            context['school'] = None
            context['subscription'] = None
            context['plan'] = None
            context['is_trial'] = False
            context['days_remaining'] = 0
            # Pricing plans: use SubscriptionPlan as single source of truth
            pricing_plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'price'))
            context['pricing_plans'] = pricing_plans
            return context

        # Pricing plans: use SubscriptionPlan as single source of truth
        pricing_plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'price'))
        context['pricing_plans'] = pricing_plans
        
        # Get current subscription - include all statuses to show trial and expired subscriptions
        try:
            # Get the most recent subscription record for this school (if any)
            current_subscription = school.subscriptions.all().order_by('-created_at').first()
            context['subscription'] = current_subscription

            # Determine current plan:
            # 1) Prefer the plan linked to the Subscription record
            # 2) Fallback to the plan stored on the School model
            plan = None
            if current_subscription and current_subscription.plan:
                plan = current_subscription.plan
            elif school.subscription_plan:
                plan = school.subscription_plan
            context['plan'] = plan

            # Mark which pricing plan (public-facing) corresponds to the current plan
            for p in context.get('pricing_plans', []):
                try:
                    p.is_current = bool(plan and p.name.lower() == plan.name.lower())
                except Exception:
                    p.is_current = False

            # Trial / expiry information comes primarily from the School record
            is_trial = bool(school.is_trial or (current_subscription and current_subscription.is_trial))
            context['is_trial'] = is_trial

            # Work out start and end dates (for both trial and paid subscriptions)
            subscription_start = None
            subscription_end = None

            # Trial handled via School fields
            if school.is_trial and school.trial_end_date:
                subscription_end = school.trial_end_date
                # Use school's subscription_start_date if present; otherwise leave as None
                subscription_start = school.subscription_start_date
            # Paid subscription dates stored on School
            elif school.subscription_end_date:
                subscription_start = school.subscription_start_date
                subscription_end = school.subscription_end_date
            # Fallback to Subscription model dates if available
            elif current_subscription:
                subscription_start = current_subscription.start_date
                subscription_end = current_subscription.end_date

            context['subscription_start'] = subscription_start
            context['subscription_end'] = subscription_end

            # Days remaining until expiry (for both trial and paid)
            if subscription_end:
                today = timezone.now().date()
                days_remaining = (subscription_end - today).days
                context['days_remaining'] = days_remaining
                context['subscription_expired'] = days_remaining < 0
            else:
                context['days_remaining'] = 0
                context['subscription_expired'] = False

            # Available plans for upgrade: always use active SubscriptionPlan records
            # If there is a current plan, exclude it so only upgrade options remain
            plans_qs = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'price')
            if plan:
                plans_qs = plans_qs.exclude(id=plan.id)
            context['available_plans'] = plans_qs

            # Payment and trial history: include both payments and trial records
            payments = []
            trial_history = []
            free_plan_history = []
            
            # Get all subscriptions for this school, ordered by creation date (newest first)
            all_subscriptions = school.subscriptions.all().order_by('-created_at')
            
            # If no paid subscriptions but school has a free plan, add it to history
            if not all_subscriptions.exists() and school.subscription_plan and school.subscription_plan.price == 0:
                free_plan_history.append({
                    'type': 'free_plan',
                    'date': school.created_on.date() if hasattr(school, 'created_on') and school.created_on else timezone.now().date(),
                    'end_date': None,
                    'status': 'Active',
                    'amount': 0.00,
                    'subscription': None,
                    'created_at': school.created_on if hasattr(school, 'created_on') and school.created_on else timezone.now()
                })
            
            # Process each subscription to build history
            for sub in all_subscriptions:
                # Add payments for this subscription
                payments.extend(list(sub.payments.all()))
                
                # Add subscription to history
                if sub.is_trial:
                    trial_history.append({
                        'type': 'trial',
                        'date': sub.start_date,
                        'end_date': sub.end_date,
                        'status': 'Completed' if sub.end_date and sub.end_date < timezone.now().date() else 'Active',
                        'amount': 0.00,
                        'subscription': sub,
                        'created_at': sub.created_at
                    })
                elif sub.plan and sub.plan.price == 0:  # Free plan
                    free_plan_history.append({
                        'type': 'free_plan',
                        'date': sub.start_date,
                        'end_date': sub.end_date,
                        'status': 'Active',
                        'amount': 0.00,
                        'subscription': sub,
                        'created_at': sub.created_at
                    })
            
            # Combine and sort all history by date (newest first)
            all_history = []
            all_history.extend(payments)
            all_history.extend(trial_history)
            all_history.extend(free_plan_history)
            
            # Sort by created_at if available, otherwise by date
            context['billing_history'] = sorted(
                all_history,
                key=lambda x: (
                    x.created_at if hasattr(x, 'created_at') else x.get('created_at', x.get('date')),
                    x.get('id', 0)  # For stable sorting
                ),
                reverse=True
            )
            
            # Get invoices for this school
            from subscriptions.models import Invoice
            invoices = Invoice.objects.filter(school=school).order_by('-created_at')
            context['invoices'] = invoices
            
            # Debug information
            print(f"School: {school.name}")
            print(f"Current subscription: {current_subscription}")
            print(f"Plan: {plan}")
            print(f"Is trial: {is_trial}")
            print(f"Existing invoices: {invoices.count()}")
            for inv in invoices:
                print(f"  - {inv.invoice_number}: {inv.invoice_type} ({inv.status})")
            
            # Generate invoice for current subscription if needed
            if current_subscription and plan:
                # Check if invoice already exists for this subscription
                existing_invoice = Invoice.objects.filter(
                    subscription=current_subscription
                ).first()
                
                if not existing_invoice:
                    # Determine invoice type and details based on subscription
                    if current_subscription.is_trial or is_trial:
                        invoice_type = 'trial_end'
                        amount = 0
                        status = 'paid'  # Trial invoices are automatically marked as paid
                        plan_desc = f"{plan.name} - Free Trial Period"
                    elif current_subscription.end_date and current_subscription.end_date < timezone.now().date():
                        invoice_type = 'renewal'
                        amount = plan.price if plan else 0
                        status = 'sent'
                        plan_desc = f"{plan.name} - {plan.billing_cycle if plan else 'Monthly'} subscription"
                    else:
                        invoice_type = 'new'
                        amount = plan.price if plan else 0
                        status = 'sent'
                        plan_desc = f"{plan.name} - {plan.billing_cycle if plan else 'Monthly'} subscription"
                    
                    due_date = timezone.now().date() + timezone.timedelta(days=30)
                    
                    invoice = Invoice.objects.create(
                        school=school,
                        subscription=current_subscription,
                        invoice_type=invoice_type,
                        plan_name=plan.name,
                        plan_description=plan_desc,
                        amount=amount,
                        tax_amount=0,  # Add tax calculation if needed
                        total_amount=amount,
                        due_date=due_date,
                        billing_start_date=current_subscription.start_date,
                        billing_end_date=current_subscription.end_date,
                        status=status
                    )
                    context['current_invoice'] = invoice
                else:
                    context['current_invoice'] = existing_invoice
            elif plan and plan.price == 0:
                # School has a free plan but no subscription record, create a free plan invoice
                existing_invoice = Invoice.objects.filter(
                    school=school,
                    subscription__isnull=True,
                    invoice_type='new'
                ).first()
                
                if not existing_invoice:
                    invoice = Invoice.objects.create(
                        school=school,
                        subscription=None,
                        invoice_type='new',
                        plan_name=plan.name,
                        plan_description=f"{plan.name} - Free Plan",
                        amount=0,
                        tax_amount=0,
                        total_amount=0,
                        due_date=timezone.now().date() + timezone.timedelta(days=30),
                        billing_start_date=school.created_on.date() if hasattr(school, 'created_on') and school.created_on else timezone.now().date(),
                        status='paid'  # Free plans are automatically marked as paid
                    )
                    context['current_invoice'] = invoice
                else:
                    context['current_invoice'] = existing_invoice
            
        except Exception as e:
            import traceback
            print(f"Error fetching subscription: {str(e)}")
            traceback.print_exc()
            context['subscription'] = None
            context['plan'] = None
            context['is_trial'] = False
            context['subscription_start'] = None
            context['subscription_end'] = None
            context['days_remaining'] = 0
            context['subscription_expired'] = False
            context['invoices'] = []
            context['current_invoice'] = None
            context['payments'] = []
            context['available_plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'price')
        
        return context


class InvoiceDownloadView(LoginRequiredMixin, View):
    """Download invoice as PDF"""
    
    def dispatch(self, request, *args, **kwargs):
        """Only allow school admins to access invoices"""
        if not request.user.is_school_admin:
            messages.error(request, "Access denied. This page is for school admins only.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, school_slug, invoice_id):
        from subscriptions.models import Invoice
        from tenants.models import School
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        import io
        
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            invoice = Invoice.objects.get(id=invoice_id, school=school)
            
            # Create PDF buffer
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                  leftMargin=72, rightMargin=72,
                                  topMargin=72, bottomMargin=72)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom colors
            navy_blue = colors.HexColor('#003366')
            cyan = colors.HexColor('#00CED1')
            light_cyan = colors.HexColor('#E0FFFF')
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                textColor=navy_blue,
                fontSize=18,
                spaceAfter=12,
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                textColor=cyan,
                fontSize=14,
                spaceAfter=12,
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                textColor=navy_blue,
                fontSize=10,
            )
            
            # Header with company info
            header_data = [
                [Paragraph("Clasyo by Timesten Technologies Ltd.", title_style), 
                 Paragraph(f"Invoice #{invoice.invoice_number}", heading_style)],
                ["", Paragraph(f"Date: {invoice.invoice_date.strftime('%B %d, %Y')}", normal_style)],
            ]
            
            header_table = Table(header_data, colWidths=[4*inch, 3*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                # Remove the problematic LINEBELOW style
                ('LINEBELOW', (1, 0), (1, 1), 1, navy_blue),  # Simplified line style
]))
            story.append(header_table)
            story.append(Spacer(1, 20))
            
            # Bill To section
            story.append(Paragraph("Bill To:", heading_style))
            story.append(Paragraph(f"{school.name}", normal_style))
            if hasattr(school, 'address') and school.address:
                story.append(Paragraph(school.address, normal_style))
            if hasattr(school, 'phone') and school.phone:
                story.append(Paragraph(f"Phone: {school.phone}", normal_style))
            if hasattr(school, 'email') and school.email:
                story.append(Paragraph(f"Email: {school.email}", normal_style))
            story.append(Spacer(1, 20))
            
            # Invoice Details section
            story.append(Paragraph("Invoice Details:", heading_style))
            
            # Invoice info table
            info_data = [
                ['Invoice Date:', invoice.invoice_date.strftime('%B %d, %Y')],
                ['Due Date:', invoice.due_date.strftime('%B %d, %Y')],
                ['Status:', invoice.get_status_display().title()],
            ]
            
            if invoice.paid_date:
                info_data.append(['Paid Date:', invoice.paid_date.strftime('%B %d, %Y %H:%M')])
            
            info_table = Table(info_data, colWidths=[2*inch, 3*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), light_cyan),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # Invoice items table
            item_data = [
                [
                    Paragraph('Description', normal_style), 
                    Paragraph('Period', normal_style), 
                    Paragraph('Qty', normal_style), 
                    Paragraph('Unit Price', normal_style), 
                    Paragraph('Amount', normal_style)
                ],
                [
                    f"{invoice.plan_name}\n{invoice.plan_description}",
                    f"{invoice.billing_start_date.strftime('%b %d, %Y')} - {invoice.billing_end_date.strftime('%b %d, %Y')}" if invoice.billing_start_date and invoice.billing_end_date else "Current period",
                    "1",
                    f"Ksh {invoice.amount:.2f}",
                    f"Ksh {invoice.amount:.2f}"
                ]
            ]
            
            if invoice.tax_amount > 0:
                item_data.append(['Tax', '', '', '', f"Ksh {invoice.tax_amount:.2f}"])
            
            # Total row
            total_amount_display = "FREE" if invoice.total_amount == 0 else f"Ksh {invoice.total_amount:.2f}"
            item_data.append([
                'Total', '', '', '', 
                total_amount_display
            ])
            
            item_table = Table(item_data, colWidths=[3*inch, 1.5*inch, 0.8*inch, 1*inch, 1*inch])
            item_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), navy_blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), light_cyan),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, navy_blue),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(item_table)
            
            if invoice.notes:
                story.append(Spacer(1, 20))
                story.append(Paragraph("Notes:", heading_style))
                story.append(Paragraph(invoice.notes, normal_style))
            
            # Footer
            story.append(Spacer(1, 40))
            story.append(Paragraph("This is a computer-generated invoice. No signature is required.", normal_style))
            story.append(Paragraph("Thank you for your business with Clasyo!", heading_style))
            story.append(Spacer(1, 10))
            story.append(Paragraph("For questions, contact us at clasyo@timestentechnologies.co.ke", normal_style))
            
            # Build PDF
            doc.build(story)
            
            # Create response
            buffer.seek(0)
            pdf = buffer.getvalue()
            buffer.close()
            
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
            
            return response
            
        except (School.DoesNotExist, Invoice.DoesNotExist):
            messages.error(request, "Invoice not found.")
            return redirect('core:billing', school_slug=school_slug)
        except Exception as e:
            messages.error(request, f"Error generating invoice: {str(e)}")
            return redirect('core:billing', school_slug=school_slug)


class InvoicePreviewView(LoginRequiredMixin, View):
    """API endpoint for invoice preview"""
    
    def dispatch(self, request, *args, **kwargs):
        """Only allow school admins to access invoices"""
        if not request.user.is_school_admin:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, school_slug, invoice_id):
        from subscriptions.models import Invoice
        from tenants.models import School
        from django.http import JsonResponse
        
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            invoice = Invoice.objects.get(id=invoice_id, school=school)
            
            # Prepare invoice data for preview
            billing_period = ""
            if invoice.billing_start_date and invoice.billing_end_date:
                billing_period = f"{invoice.billing_start_date.strftime('%b %d, %Y')} - {invoice.billing_end_date.strftime('%b %d, %Y')}"
            else:
                billing_period = "Current period"
            
            data = {
                'success': True,
                'invoice': {
                    'invoice_number': invoice.invoice_number,
                    'invoice_date': invoice.invoice_date.strftime('%B %d, %Y'),
                    'due_date': invoice.due_date.strftime('%B %d, %Y'),
                    'status': invoice.status,
                    'status_display': invoice.get_status_display().title(),
                    'paid_date': invoice.paid_date.strftime('%B %d, %Y %H:%M') if invoice.paid_date else None,
                    'school_name': school.name,
                    'school_address': getattr(school, 'address', ''),
                    'school_phone': getattr(school, 'phone', ''),
                    'school_email': getattr(school, 'email', ''),
                    'plan_name': invoice.plan_name,
                    'plan_description': invoice.plan_description,
                    'billing_period': billing_period,
                    'amount': float(invoice.amount),
                    'amount_display': 'FREE' if invoice.amount == 0 else f'Ksh {invoice.amount:.2f}',
                    'tax_amount': float(invoice.tax_amount),
                    'total_amount': float(invoice.total_amount),
                    'notes': invoice.notes,
                    'invoice_type': invoice.invoice_type,
                    'invoice_type_display': invoice.get_invoice_type_display()
                }
            }
            
            return JsonResponse(data)
            
        except (School.DoesNotExist, Invoice.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Invoice not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@require_GET
def offline_view(request):
    """View for offline page"""
    return render(request, 'offline.html', status=200)
