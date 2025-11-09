from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from .models import (
    AcademicYear, Session, Holiday, SystemSetting,
    Notification, ToDoList, CalendarEvent
)


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
            
            # Get class teachers (only for THIS child's class)
            if child.current_class:
                try:
                    from academics.models import ClassTeacher
                    class_teachers = ClassTeacher.objects.filter(
                        class_assigned=child.current_class
                    ).select_related('teacher')
                    child_info['teachers'] = [ct.teacher for ct in class_teachers]
                except:
                    pass
            
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
                ).select_related('exam', 'subject').order_by('-exam__date')[:5]
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
    """Mark notification as read"""
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_read()
        return redirect('core:notifications')


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Mark all notifications as read"""
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
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
    success_url = reverse_lazy('core:todos')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'To-do item created successfully!')
        return super().form_valid(form)


class ToDoToggleView(LoginRequiredMixin, View):
    """Toggle to-do completion status"""
    def post(self, request, pk):
        todo = get_object_or_404(ToDoList, pk=pk, user=request.user)
        todo.is_completed = not todo.is_completed
        if todo.is_completed:
            from django.utils import timezone
            todo.completed_at = timezone.now()
        else:
            todo.completed_at = None
        todo.save()
        return redirect('core:todos')


class ToDoDeleteView(LoginRequiredMixin, View):
    """Delete to-do"""
    def post(self, request, pk):
        todo = get_object_or_404(ToDoList, pk=pk, user=request.user)
        todo.delete()
        messages.success(request, 'To-do item deleted successfully!')
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
    """List calendar events (for AJAX)"""
    model = CalendarEvent
    
    def get_queryset(self):
        user = self.request.user
        return CalendarEvent.objects.filter(
            Q(is_public=True) | Q(participants=user) | Q(created_by=user)
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class CalendarEventCreateView(View):
    """Create calendar event"""
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            CalendarEvent.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description', ''),
                event_type=request.POST.get('event_type', 'other'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
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


class StopImpersonationView(LoginRequiredMixin, View):
    """Stop impersonating and return to original admin account"""
    
    def get(self, request, *args, **kwargs):
        if 'original_user_id' in request.session:
            del request.session['impersonated_user_id']
            del request.session['original_user_id']
            messages.success(request, 'You have returned to your admin account.')
        
        return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
