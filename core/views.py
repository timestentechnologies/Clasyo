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
from datetime import datetime, time, timedelta
from pathlib import Path
from django.conf import settings as django_settings
from django.utils import timezone
from tenants.models import School
from core.utils import get_current_school
from superadmin.models import (
    SchoolSMSConfiguration,
    SchoolEmailConfiguration,
    GlobalSMSConfiguration,
    GlobalEmailConfiguration,
    GlobalDatabaseConfiguration,
)
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
        
        # Subscription banner on Apps Home
        try:
            sub_end = None
            current_subscription = None
            if context.get('school'):
                current_subscription = context['school'].subscriptions.all().order_by('-created_at').first()
            if current_subscription and current_subscription.end_date:
                sub_end = current_subscription.end_date
            elif context.get('school') and context['school'].is_trial and getattr(context['school'], 'trial_end_date', None):
                sub_end = context['school'].trial_end_date
            elif context.get('school') and getattr(context['school'], 'subscription_end_date', None):
                sub_end = context['school'].subscription_end_date

            sub_days_remaining = None
            show_banner = False
            if sub_end:
                today = timezone.now().date()
                sub_days_remaining = (sub_end - today).days
                show_banner = sub_days_remaining <= 10 and sub_days_remaining >= 0

            context['sub_days_remaining'] = sub_days_remaining if sub_days_remaining is not None else 0
            context['show_subscription_banner'] = show_banner
        except Exception:
            context['sub_days_remaining'] = 0
            context['show_subscription_banner'] = False
        
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
            from django.db.models import Q

            school = context.get('school')

            # Students and classes scoped to school
            if school:
                context['total_students'] = Student.objects.filter(
                    is_active=True,
                ).filter(
                    Q(current_class__school=school) | Q(user__school=school)
                ).distinct().count()
                context['total_classes'] = Class.objects.filter(
                    is_active=True,
                    school=school,
                ).count()
            else:
                # Fallback (should not happen if URL has correct slug)
                context['total_students'] = 0
                context['total_classes'] = 0

            # Teachers: prefer direct user.school link; also include teachers linked via classes/sections/assignments
            if school:
                teacher_qs = User.objects.filter(role='teacher', is_active=True).filter(
                    Q(school=school) |
                    Q(class_sections__class_name__school=school) |
                    Q(assigned_subjects__class_name__school=school)
                ).distinct()
                context['total_teachers'] = teacher_qs.count()

                # Other staff roles directly linked to the school via User.school
                staff_roles = ['staff', 'accountant', 'librarian', 'receptionist']
                other_staff_qs = User.objects.filter(
                    role__in=staff_roles,
                    is_active=True,
                    school=school,
                ).distinct()
                context['total_staff'] = context['total_teachers'] + other_staff_qs.count()
            else:
                context['total_teachers'] = 0
                context['total_staff'] = 0

            context['pending_tasks'] = ToDoList.objects.filter(
                user=user, is_completed=False
            ).count()
            # Subscription banner: show when <= 10 days remaining
            try:
                sub_end = None
                current_subscription = None
                if school:
                    current_subscription = school.subscriptions.all().order_by('-created_at').first()
                if current_subscription and current_subscription.end_date:
                    sub_end = current_subscription.end_date
                elif school and school.is_trial and getattr(school, 'trial_end_date', None):
                    sub_end = school.trial_end_date
                elif school and getattr(school, 'subscription_end_date', None):
                    sub_end = school.subscription_end_date

                sub_days_remaining = None
                show_banner = False
                if sub_end:
                    today = timezone.now().date()
                    sub_days_remaining = (sub_end - today).days
                    show_banner = sub_days_remaining <= 10 and sub_days_remaining >= 0

                context['sub_days_remaining'] = sub_days_remaining if sub_days_remaining is not None else 0
                context['show_subscription_banner'] = show_banner
            except Exception:
                context['sub_days_remaining'] = 0
                context['show_subscription_banner'] = False
            
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
class SystemSettingsApiView(View):
    """Lightweight JSON API for updating core system settings.

    Currently supports:
    - admission_number_prefix
    - maintenance_mode (on/off)
    """

    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

            settings_obj = SystemSetting.get_settings()
            updated = False

            # Resolve current school from URL (tenant)
            school_slug = kwargs.get('school_slug')
            school = None
            if school_slug:
                try:
                    school = School.objects.get(slug=school_slug, is_active=True)
                except School.DoesNotExist:
                    school = None

            # Update academic year if provided
            if 'current_academic_year' in request.POST:
                year_id = request.POST.get('current_academic_year')
                try:
                    year = AcademicYear.objects.get(pk=year_id)
                    # Deactivate all and activate the selected one
                    AcademicYear.objects.all().update(is_active=False)
                    year.is_active = True
                    year.save(update_fields=['is_active'])
                    return JsonResponse({'success': True, 'message': f'Active academic year set to {year.name}.'})
                except (AcademicYear.DoesNotExist, ValueError):
                    return JsonResponse({'success': False, 'error': 'Invalid academic year selected.'}, status=400)

            # Update notification settings if provided
            notification_fields = ['email_notifications', 'sms_notifications', 'parent_notifications', 'teacher_notifications']
            if any(field in request.POST for field in notification_fields):
                for field in notification_fields:
                    if field in request.POST:
                        enabled_val = request.POST.get(field, '').lower()
                        enabled = enabled_val in ['1', 'true', 'on', 'yes']
                        setattr(settings_obj, field, enabled)
                settings_obj.save(update_fields=notification_fields)
                return JsonResponse({'success': True, 'message': 'Notification settings updated.'})

            # Update grading system if provided
            if 'grading_system' in request.POST:
                grading_system = request.POST.get('grading_system')
                valid_systems = ['letter', 'percentage', 'gpa']
                if grading_system not in valid_systems:
                    return JsonResponse({'success': False, 'error': 'Invalid grading system.'}, status=400)
                settings_obj.grading_system = grading_system
                settings_obj.save(update_fields=['grading_system'])
                return JsonResponse({'success': True, 'message': 'Grading system updated.'})

            # Update school fields if provided
            if school and any(field in request.POST for field in ['school_name', 'school_email', 'school_phone', 'school_address', 'school_website']):
                if 'school_name' in request.POST:
                    school.name = request.POST.get('school_name', '').strip() or school.name
                if 'school_email' in request.POST:
                    school.email = request.POST.get('school_email', '').strip() or school.email
                if 'school_phone' in request.POST:
                    school.phone = request.POST.get('school_phone', '').strip() or school.phone
                if 'school_address' in request.POST:
                    school.address = request.POST.get('school_address', '').strip() or school.address
                if 'school_website' in request.POST:
                    school.website = request.POST.get('school_website', '').strip() or school.website
                school.save(update_fields=['name', 'email', 'phone', 'address', 'website'])
                return JsonResponse({'success': True, 'message': 'School information updated.'})

            # Update institution type for the current school
            if 'institution_type' in request.POST:
                if not school:
                    return JsonResponse({'success': False, 'error': 'School not found'}, status=400)

                institution_type = request.POST.get('institution_type')
                valid_types = [value for value, _ in School.INSTITUTION_TYPE_CHOICES]
                if institution_type not in valid_types:
                    return JsonResponse({'success': False, 'error': 'Invalid institution type'}, status=400)

                school.institution_type = institution_type
                school.save(update_fields=['institution_type'])

                return JsonResponse({
                    'success': True,
                    'institution_type': institution_type,
                    'institution_type_label': school.get_institution_type_display(),
                })

            # Update admission number prefix if provided
            if 'admission_number_prefix' in request.POST:
                prefix = request.POST.get('admission_number_prefix', 'STU').strip().upper()
                if prefix:
                    settings_obj.admission_number_prefix = prefix
                    updated = True

            # Toggle maintenance mode if provided
            if 'maintenance_mode' in request.POST:
                enabled_val = request.POST.get('maintenance_mode', '').lower()
                enabled = enabled_val in ['1', 'true', 'on', 'yes']
                settings_obj.maintenance_mode = enabled
                settings_obj.save()
                return JsonResponse({'success': True, 'maintenance_mode': settings_obj.maintenance_mode})

            if updated:
                settings_obj.save()
                return JsonResponse({'success': True})

            return JsonResponse({'success': False, 'error': 'No valid setting provided'}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class DatabaseActionsApiView(View):
    """Handle database-related maintenance actions from the settings page."""

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

        # Only allow admins / superadmins to perform these actions
        role = getattr(request.user, 'role', '') or ''
        if not (request.user.is_superuser or role in ('superadmin', 'admin')):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        action = request.POST.get('action')
        if not action:
            return JsonResponse({'success': False, 'error': 'No action provided'}, status=400)

        try:
            if action == 'backup':
                # Simple SQLite backup implementation; for other engines, show a helpful message
                db_conf = django_settings.DATABASES['default']
                engine = db_conf.get('ENGINE', '').split('.')[-1]

                if engine == 'sqlite3':
                    db_path = Path(db_conf['NAME'])
                    backup_dir = Path(django_settings.MEDIA_ROOT) / 'backups'
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                    backup_path = backup_dir / f'db_backup_{timestamp}.sqlite3'

                    import shutil
                    shutil.copy2(db_path, backup_path)

                    rel_path = str(backup_path.relative_to(backup_dir.parent))
                    size_bytes = backup_path.stat().st_size
                    size_mb = round(size_bytes / (1024 * 1024), 2)
                    created_at = timezone.now().isoformat()

                    return JsonResponse({
                        'success': True,
                        'message': 'Database backup created successfully.',
                        'file': rel_path,
                        'details': {
                            'path': rel_path,
                            'size_mb': size_mb,
                            'size_bytes': size_bytes,
                            'created_at': created_at,
                            'engine': engine,
                        },
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Automatic backups are only implemented for SQLite in this setup.',
                    }, status=400)

            elif action == 'clear_cache':
                from django.core.cache import cache
                cache.clear()
                cleared_at = timezone.now().isoformat()
                return JsonResponse({
                    'success': True,
                    'message': 'Cache cleared successfully.',
                    'details': {
                        'cleared_at': cleared_at,
                    },
                })

            elif action == 'sync':
                # Placeholder for future sync tasks; currently just acknowledges the action
                run_at = timezone.now().isoformat()
                return JsonResponse({
                    'success': True,
                    'message': 'Data sync triggered successfully.',
                    'details': {
                        'run_at': run_at,
                    },
                })

            else:
                return JsonResponse({'success': False, 'error': 'Unknown action.'}, status=400)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
        from tenants.models import School
        school_slug = self.kwargs.get('school_slug')
        try:
            school = School.objects.get(slug=school_slug)
        except School.DoesNotExist:
            return CalendarEvent.objects.none()
        # Scope events to the current school only
        return CalendarEvent.objects.filter(
            Q(created_by__school=school) | Q(participants__school=school)
        ).distinct()

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
        school_slug = kwargs.get('school_slug', '')
        context['school_slug'] = school_slug

        school = None
        if school_slug:
            try:
                school = School.objects.get(slug=school_slug, is_active=True)
            except School.DoesNotExist:
                school = None

        context['school'] = school
        context['institution_type_choices'] = School.INSTITUTION_TYPE_CHOICES

        # Academic years
        context['academic_years'] = AcademicYear.objects.all()
        # System info
        from accounts.models import User
        from students.models import Student
        user_count = User.objects.count()
        student_count = Student.objects.count()
        db_engine = django_settings.DATABASES['default']['ENGINE'].split('.')[-1]
        system_version = getattr(django_settings, 'SYSTEM_VERSION', '1.0.0')

        context['system_info'] = {
            'version': system_version,
            'db_engine': db_engine,
            'django_version': getattr(__import__('django'), 'get_version', lambda: 'N/A')(),
            'user_count': user_count,
            'student_count': student_count,
        }

        # Global / environment-level messaging & DB configuration fallbacks
        global_sms = GlobalSMSConfiguration.objects.filter(is_active=True).first()
        if not global_sms:
            # Build a lightweight object from env settings
            from collections import namedtuple
            SMSInfo = namedtuple('SMSInfo', ['provider', 'default_sender_id', 'source'])
            global_sms = SMSInfo(
                provider='system',
                default_sender_id=getattr(django_settings, 'SMS_SENDER_ID', None),
                source='env',
            )
        context['global_sms_config'] = global_sms

        global_email = GlobalEmailConfiguration.objects.filter(is_active=True).first()
        if not global_email:
            from collections import namedtuple
            EmailInfo = namedtuple('EmailInfo', ['provider', 'default_from_email', 'source'])
            global_email = EmailInfo(
                provider='system',
                default_from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', None),
                source='env',
            )
        context['global_email_config'] = global_email

        global_db = GlobalDatabaseConfiguration.objects.filter(is_active=True).first()
        if not global_db:
            from collections import namedtuple
            DBInfo = namedtuple('DBInfo', ['name', 'engine', 'host', 'port', 'source'])
            default_db = django_settings.DATABASES['default']
            global_db = DBInfo(
                name=default_db.get('NAME', 'N/A'),
                engine=default_db.get('ENGINE', 'N/A').split('.')[-1],
                host=default_db.get('HOST', 'localhost'),
                port=default_db.get('PORT', ''),
                source='env',
            )
        context['global_db_config'] = global_db

        return context


class AcademicYearListView(LoginRequiredMixin, ListView):
    """List academic years"""
    model = AcademicYear
    template_name = 'core/academic_years.html'
    context_object_name = 'academic_years'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = AcademicYear.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
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
                school=get_current_school(request),
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
            
            school = get_current_school(request)
            qs = AcademicYear.objects.all()
            if school:
                qs = qs.filter(school=school)
            try:
                year = qs.get(pk=pk)
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
            
            school = get_current_school(request)
            qs = AcademicYear.objects.all()
            if school:
                qs = qs.filter(school=school)
            try:
                year = qs.get(pk=pk)
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
            
            school = get_current_school(request)
            qs = AcademicYear.objects.all()
            if school:
                qs = qs.filter(school=school)
            try:
                year = qs.get(pk=pk)
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
            school = get_current_school(request)
            sessions = Session.objects.filter(academic_year_id=year_id)
            if school:
                sessions = sessions.filter(academic_year__school=school)
            print(f"[DEBUG] Found {sessions.count()} sessions (scoped)")
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
                school = get_current_school(request)
                year_qs = AcademicYear.objects.all()
                if school:
                    year_qs = year_qs.filter(school=school)
                year = year_qs.get(pk=academic_year_id)
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
            
            school = get_current_school(request)
            qs = Session.objects.select_related('academic_year')
            if school:
                qs = qs.filter(academic_year__school=school)
            try:
                session = qs.get(pk=pk)
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
        from tenants.models import School
        school_slug = self.kwargs.get('school_slug')
        try:
            school = School.objects.get(slug=school_slug)
        except School.DoesNotExist:
            return CalendarEvent.objects.none()
        # Only events belonging to the current school
        return CalendarEvent.objects.filter(
            Q(created_by__school=school) | Q(participants__school=school)
        ).distinct().order_by('start_date')
    
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
            from django.contrib.auth import login, get_user_model

            UserModel = get_user_model()
            user = get_object_or_404(UserModel, id=request.original_user)
            # Ensure backend is specified since multiple auth backends are configured
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Stopped impersonating {user.get_full_name() or user.email}')
            return redirect('core:dashboard')
        return redirect('core:dashboard')


class BillingView(LoginRequiredMixin, TemplateView):
    """School admin billing and subscription management view"""
    template_name = 'core/billing.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Allow expired users (any role) to reach billing, otherwise restrict to school admins"""
        allow_expired_visit = str(request.GET.get('expired', '')).lower() in ('1', 'true', 'yes')
        if not request.user.is_school_admin and not allow_expired_visit:
            messages.error(request, "Access denied. This page is for school admins only.")
            return redirect('core:dashboard', school_slug=kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug')
        context['school_slug'] = school_slug
        # Flags from middleware redirect for showing expiry modal
        try:
            context['show_expired_modal'] = str(self.request.GET.get('expired', '')).lower() in ('1', 'true', 'yes')
            context['expired_reason'] = (self.request.GET.get('reason') or '').strip()
            # Show a friendly confirmation modal after payment submission
            context['payment_submitted'] = str(self.request.GET.get('submitted', '')).lower() in ('1', 'true', 'yes')
            # Show pending verification modal flag
            context['payment_pending'] = str(self.request.GET.get('pending', '')).lower() in ('1', 'true', 'yes')
        except Exception:
            context['show_expired_modal'] = False
            context['expired_reason'] = ''
            context['payment_submitted'] = False
            context['payment_pending'] = False
        
        # Get school
        from tenants.models import School
        from subscriptions.models import Subscription, SubscriptionPlan
        from django.utils import timezone
        
        try:
            school = School.objects.filter(slug=school_slug).first()
            context['school'] = school
        except Exception:
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

            # Prefer dates from the most recent Subscription record when present
            # so that freshly created subscriptions (even if pending) reflect immediately.
            # Fall back to School fields only when there is no subscription.
            is_trial = bool((current_subscription and current_subscription.is_trial) or (not current_subscription and school.is_trial))
            # If the latest subscription is a paid purchase (plan price > 0), treat it as NOT a trial
            # even if an older bug created it with is_trial=True.
            try:
                if current_subscription and current_subscription.plan and float(getattr(current_subscription.plan, 'price', 0)) > 0:
                    is_trial = False
            except Exception:
                pass
            
            # Enforce: once a free offer (trial or free plan) is used, do not allow selecting a free plan again
            from subscriptions.models import Invoice  # ensure available before use below
            try:
                current_free = bool(current_subscription and getattr(current_subscription.plan, 'price', 0) == 0)
                has_trial_invoice = Invoice.objects.filter(school=school, invoice_type='trial_end').exists()
                has_past_free_invoice = Invoice.objects.filter(
                    school=school,
                    invoice_type__in=['new', 'renewal', 'upgrade'],
                    total_amount=0
                ).exists()
                past_free_sub_qs = school.subscriptions.filter(plan__price=0)
                if current_subscription:
                    past_free_sub_qs = past_free_sub_qs.exclude(id=current_subscription.id)
                has_past_free_sub = past_free_sub_qs.exists()
                has_used_free_offer = (has_trial_invoice or has_past_free_invoice or has_past_free_sub) and not current_free
                for p in context.get('pricing_plans', []):
                    try:
                        p.disable_free_selection = bool(has_used_free_offer and float(getattr(p, 'price', 0)) == 0 and not getattr(p, 'is_current', False))
                    except Exception:
                        p.disable_free_selection = False
            except Exception:
                pass
            context['is_trial'] = is_trial

            # If subscription exists and is not active yet, mark pending flag for UI
            try:
                if current_subscription and current_subscription.status in ['pending', 'processing', 'verified']:
                    context['payment_pending'] = True
            except Exception:
                pass

            # Correct end date ONLY for pending/processing/verified (pre-activation) subscriptions
            # to fix legacy cases where 14 days were set incorrectly. Do not override admin edits on active subs.
            try:
                if (
                    current_subscription and plan and float(getattr(plan, 'price', 0)) > 0 and
                    current_subscription.status in ['pending', 'processing', 'verified']
                ):
                    expected_days = 30
                    if plan.billing_cycle == 'quarterly':
                        expected_days = 90
                    elif plan.billing_cycle == 'half_yearly':
                        expected_days = 180
                    elif plan.billing_cycle == 'yearly':
                        expected_days = 365
                    if current_subscription.start_date and current_subscription.end_date:
                        actual_days = (current_subscription.end_date - current_subscription.start_date).days
                        # Only correct the known legacy bug where 14 days were set erroneously
                        if actual_days == 14 and expected_days != 14:
                            current_subscription.end_date = current_subscription.start_date + timedelta(days=expected_days)
                            current_subscription.save(update_fields=['end_date'])
            except Exception:
                pass

            # Work out start and end dates (for both trial and paid subscriptions),
            # prioritising the Subscription record over School fields.
            subscription_start = None
            subscription_end = None
            subscription_start_dt = None
            subscription_end_dt = None

            if current_subscription:
                subscription_start = current_subscription.start_date
                subscription_end = current_subscription.end_date
                # Fallback: if Subscription.end_date is missing but school has a saved end date, use it for display/math
                try:
                    if not subscription_end and getattr(school, 'subscription_end_date', None):
                        subscription_end = school.subscription_end_date
                    # If superadmin edited School.subscription_end_date, prefer it for display to keep Dashboard and Billing consistent
                    school_end = getattr(school, 'subscription_end_date', None)
                    if school_end and subscription_end and school_end != subscription_end:
                        subscription_end = school_end
                except Exception:
                    pass
                # Use the approval time of the latest approved payment as the true activation time
                try:
                    from subscriptions.models import Payment as _SubPayment
                    latest_approved = _SubPayment.objects.filter(
                        subscription=current_subscription,
                        status='approved',
                        approved_at__isnull=False
                    ).order_by('-approved_at').first()
                except Exception:
                    latest_approved = None

                if latest_approved and latest_approved.approved_at:
                    subscription_start_dt = latest_approved.approved_at
                    # End datetime prioritizes saved end_date (admin edits) with the same time-of-day as activation
                    try:
                        if subscription_end:
                            subscription_end_dt = datetime.combine(
                                subscription_end,
                                time(hour=subscription_start_dt.hour, minute=subscription_start_dt.minute)
                            )
                        else:
                            cycle = (current_subscription.plan.billing_cycle if current_subscription.plan else 'monthly')
                            days_map = {
                                'monthly': 30,
                                'quarterly': 90,
                                'half_yearly': 180,
                                'yearly': 365,
                            }
                            add_days = days_map.get(cycle, 30)
                            subscription_end_dt = subscription_start_dt + timedelta(days=add_days)
                    except Exception:
                        # Fallback to end-of-day of the date-based end_date
                        if subscription_end:
                            try:
                                subscription_end_dt = datetime.combine(subscription_end, time(hour=23, minute=59))
                            except Exception:
                                pass
                else:
                    # Fallbacks when no approved payment timestamp is available
                    try:
                        if current_subscription.created_at:
                            subscription_start_dt = current_subscription.created_at
                        elif subscription_start:
                            subscription_start_dt = datetime.combine(subscription_start, time(hour=0, minute=0))
                    except Exception:
                        pass
                    # End datetime: prefer combining saved end_date with start time-of-day
                    try:
                        if subscription_end and subscription_start_dt:
                            subscription_end_dt = datetime.combine(
                                subscription_end,
                                time(hour=subscription_start_dt.hour, minute=subscription_start_dt.minute)
                            )
                        elif subscription_end:
                            subscription_end_dt = datetime.combine(subscription_end, time(hour=23, minute=59))
                    except Exception:
                        pass
            elif school.is_trial and school.trial_end_date:
                # Trial handled via School fields
                subscription_end = school.trial_end_date
                subscription_start = school.subscription_start_date
                try:
                    if subscription_start:
                        subscription_start_dt = datetime.combine(subscription_start, time(hour=0, minute=0))
                    if subscription_end:
                        subscription_end_dt = datetime.combine(subscription_end, time(hour=23, minute=59))
                except Exception:
                    pass
            elif school.subscription_end_date:
                # Paid subscription dates stored on School (legacy/back-compat)
                subscription_start = school.subscription_start_date
                subscription_end = school.subscription_end_date
                try:
                    if subscription_start:
                        subscription_start_dt = datetime.combine(subscription_start, time(hour=0, minute=0))
                    if subscription_end:
                        subscription_end_dt = datetime.combine(subscription_end, time(hour=23, minute=59))
                except Exception:
                    pass

            context['subscription_start'] = subscription_start
            # Align the end datetime with the authoritative end date (reflects admin edits),
            # preserving the activation time-of-day when available
            try:
                if subscription_end and subscription_start_dt:
                    subscription_end_dt = datetime.combine(
                        subscription_end,
                        time(hour=subscription_start_dt.hour, minute=subscription_start_dt.minute)
                    )
            except Exception:
                pass
            context['subscription_end'] = subscription_end
            context['subscription_start_dt'] = subscription_start_dt
            context['subscription_end_dt'] = subscription_end_dt

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
                # Fix historical bug: paid subscriptions should never be flagged as trials
                try:
                    if sub.plan and float(getattr(sub.plan, 'price', 0)) > 0 and getattr(sub, 'is_trial', False):
                        sub.is_trial = False
                        sub.save(update_fields=['is_trial'])
                except Exception:
                    pass
                # Add payments for this subscription (ensure non-zero amounts for paid plans)
                for p in sub.payments.all():
                    try:
                        plan_price = float(getattr(sub.plan, 'price', 0)) if sub.plan else 0.0
                        amt = float(p.amount or 0)
                        if plan_price > 0 and amt <= 0:
                            # Auto-correct legacy zero-amount payments for paid subscriptions
                            from decimal import Decimal
                            p.amount = Decimal(str(plan_price))
                            p.save(update_fields=['amount'])
                    except Exception:
                        pass
                    payments.append(p)
                
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

            # Fallback trial history from School fields if no Subscription trial exists
            try:
                if not trial_history:
                    trial_end = getattr(school, 'trial_end_date', None)
                    if trial_end:
                        trial_start = trial_end - timedelta(days=14)
                        trial_history.append({
                            'type': 'trial',
                            'date': trial_start,
                            'end_date': trial_end,
                            'status': 'Completed' if trial_end < timezone.now().date() else 'Active',
                            'amount': 0.00,
                            'subscription': None,
                            'created_at': trial_end
                        })
            except Exception:
                pass

            # Get invoices for this school (displayed separately in the Invoices section)
            from subscriptions.models import Invoice
            invoices = Invoice.objects.filter(school=school).order_by('-created_at')
            context['invoices'] = invoices

            # Safety net: if any invoice is still 'sent/overdue' but there's an approved
            # payment for the same subscription, mark the invoice as paid and link it.
            try:
                from subscriptions.models import Payment as _SubPayment
                updated_any = False
                for inv in invoices:
                    try:
                        if inv.status in ['sent', 'overdue']:
                            paid = None
                            # Prefer a payment for the same subscription when available
                            if inv.subscription:
                                paid = _SubPayment.objects.filter(
                                    subscription=inv.subscription,
                                    status='approved'
                                ).order_by('-approved_at', '-payment_date', '-created_at').first()
                            # Fallback: any approved payment for the same school
                            if not paid:
                                paid = _SubPayment.objects.filter(
                                    subscription__school=school,
                                    status='approved'
                                ).order_by('-approved_at', '-payment_date', '-created_at').first()
                            if paid:
                                inv.mark_as_paid(payment=paid)
                                updated_any = True
                    except Exception:
                        continue
                if updated_any:
                    invoices = Invoice.objects.filter(school=school).order_by('-created_at')
                    context['invoices'] = invoices
            except Exception:
                pass
            
            # Combine and sort all history by date (newest first)
            all_history = []
            all_history.extend(payments)
            all_history.extend(trial_history)
            all_history.extend(free_plan_history)
            
            # Sort by created_at if available, otherwise by date
            context['billing_history'] = sorted(
                all_history,
                key=lambda x: (
                    (x.created_at if hasattr(x, 'created_at') else (x.get('created_at', x.get('date')) if isinstance(x, dict) else None)),
                    (getattr(x, 'id', 0) if not isinstance(x, dict) else x.get('id', 0))
                ),
                reverse=True
            )
            
            # Debug information
            print(f"School: {school.name}")
            print(f"Current subscription: {current_subscription}")
            print(f"Plan: {plan}")
            print(f"Is trial: {is_trial}")
            print(f"Existing invoices: {invoices.count()}")
            for inv in invoices:
                print(f"  - {inv.invoice_number}: {inv.invoice_type} ({inv.status})")
            
            # Ensure a trial invoice exists for past free trial, if applicable
            try:
                if getattr(school, 'trial_end_date', None) and not Invoice.objects.filter(school=school, invoice_type='trial_end').exists():
                    t_end = school.trial_end_date
                    Invoice.objects.create(
                        school=school,
                        subscription=None,
                        invoice_type='trial_end',
                        plan_name=(plan.name if plan else 'Free Trial'),
                        plan_description='Free Trial Period',
                        amount=0,
                        tax_amount=0,
                        total_amount=0,
                        invoice_date=t_end,
                        due_date=t_end,
                        billing_start_date=(t_end - timedelta(days=14)),
                        billing_end_date=t_end,
                        status='paid'
                    )
                    invoices = Invoice.objects.filter(school=school).order_by('-created_at')
                    context['invoices'] = invoices
            except Exception:
                pass

            # Generate invoice for current subscription if needed
            if current_subscription and plan:
                # Check if invoice already exists for this subscription
                existing_invoice = Invoice.objects.filter(
                    subscription=current_subscription
                ).order_by('-created_at').first()
                
                if not existing_invoice:
                    # Determine invoice type and details based on subscription
                    today = timezone.now().date()
                    if current_subscription.status in ['pending', 'processing'] and plan and float(getattr(plan, 'price', 0)) > 0:
                        # New paid subscription awaiting manual verification
                        invoice_type = 'new'
                        amount = plan.price if plan else 0
                        status = 'sent'
                        plan_desc = f"{plan.name} - {plan.billing_cycle if plan else 'Monthly'} subscription"
                    elif current_subscription.is_trial or is_trial:
                        # Trial period invoice (zero amount) — informational only
                        invoice_type = 'trial_end'
                        amount = 0
                        status = 'paid'
                        plan_desc = f"{plan.name} - Free Trial Period"
                    elif current_subscription.end_date and current_subscription.end_date < today:
                        invoice_type = 'renewal'
                        amount = plan.price if plan else 0
                        status = 'sent'
                        plan_desc = f"{plan.name} - {plan.billing_cycle if plan else 'Monthly'} subscription"
                    else:
                        invoice_type = 'new'
                        amount = plan.price if plan else 0
                        status = 'sent'
                        plan_desc = f"{plan.name} - {plan.billing_cycle if plan else 'Monthly'} subscription"
                    
                    # Compute due date to align with the authoritative subscription end date
                    try:
                        if subscription_end:
                            due_date = subscription_end
                        else:
                            expected_days = 30
                            if plan.billing_cycle == 'quarterly':
                                expected_days = 90
                            elif plan.billing_cycle == 'half_yearly':
                                expected_days = 180
                            elif plan.billing_cycle == 'yearly':
                                expected_days = 365
                            due_date = timezone.now().date() + timezone.timedelta(days=expected_days)
                    except Exception:
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
                    # If a payment for this subscription has already been approved, mark invoice as paid now
                    try:
                        from subscriptions.models import Payment as _SubPayment
                        paid = _SubPayment.objects.filter(
                            subscription=current_subscription,
                            status='approved'
                        ).order_by('-approved_at', '-payment_date', '-created_at').first()
                        if paid and invoice.status != 'paid':
                            invoice.mark_as_paid(payment=paid)
                    except Exception:
                        pass
                    # Refresh invoices list so UI reflects the newly created invoice and its due date
                    try:
                        invoices = Invoice.objects.filter(school=school).order_by('-created_at')
                        context['invoices'] = invoices
                    except Exception:
                        pass
                    context['current_invoice'] = invoice
                else:
                    # If an invoice exists but is incorrect (e.g., marked as trial for a paid pending subscription), fix it
                    try:
                        if (existing_invoice.invoice_type == 'trial_end' or float(getattr(existing_invoice, 'total_amount', 0)) == 0) and plan and float(getattr(plan, 'price', 0)) > 0:
                            today = timezone.now().date()
                            existing_invoice.invoice_type = 'new'
                            existing_invoice.amount = plan.price
                            existing_invoice.tax_amount = getattr(existing_invoice, 'tax_amount', 0)
                            existing_invoice.total_amount = existing_invoice.amount  # assuming no tax
                            existing_invoice.status = 'sent'
                            existing_invoice.plan_name = plan.name
                            existing_invoice.plan_description = f"{plan.name} - {plan.billing_cycle if plan else 'Monthly'} subscription"
                            existing_invoice.due_date = today + timezone.timedelta(days=30)
                            existing_invoice.billing_start_date = current_subscription.start_date
                            existing_invoice.billing_end_date = current_subscription.end_date
                            existing_invoice.save()
                        # Ensure invoice dates are aligned with the current subscription window and admin edits
                        try:
                            changed = False
                            if subscription_end and existing_invoice.due_date != subscription_end:
                                existing_invoice.due_date = subscription_end
                                changed = True
                            if current_subscription.start_date and existing_invoice.billing_start_date != current_subscription.start_date:
                                existing_invoice.billing_start_date = current_subscription.start_date
                                changed = True
                            if current_subscription.end_date and existing_invoice.billing_end_date != current_subscription.end_date:
                                existing_invoice.billing_end_date = current_subscription.end_date
                                changed = True
                            if changed:
                                existing_invoice.save()
                                # Refresh invoices list so UI reflects due date/billing period changes
                                try:
                                    invoices = Invoice.objects.filter(school=school).order_by('-created_at')
                                    context['invoices'] = invoices
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # If there is an approved payment for this subscription, ensure invoice is marked paid
                        from subscriptions.models import Payment as _SubPayment
                        paid = _SubPayment.objects.filter(
                            subscription=current_subscription,
                            status='approved'
                        ).order_by('-approved_at', '-payment_date', '-created_at').first()
                        if paid and existing_invoice.status != 'paid':
                            existing_invoice.mark_as_paid(payment=paid)
                    except Exception:
                        pass
                    context['current_invoice'] = existing_invoice
            
            # Keep invoices as-is (including trial invoices) to show full history
            if plan and plan.price == 0 and not current_subscription:
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
        if not (request.user.is_school_admin or request.user.is_superadmin):
            messages.error(request, "Access denied.")
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
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT
        import io
        
        try:
            school = School.objects.get(slug=school_slug, is_active=True)
            invoice = Invoice.objects.get(id=invoice_id, school=school)
            
            # Create PDF buffer
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                  leftMargin=42, rightMargin=42,
                                  topMargin=42, bottomMargin=42)
            styles = getSampleStyleSheet()
            story = []

            class RoundedCard(Flowable):
                def __init__(self, flowables, width, padding=12, bg_color=colors.white, border_color=None, radius=10):
                    super().__init__()
                    self.flowables = flowables
                    self.width = width
                    self.padding = padding
                    self.bg_color = bg_color
                    self.border_color = border_color
                    self.radius = radius

                    inner_width = max(0, self.width - (self.padding * 2))
                    for f in self.flowables:
                        if hasattr(f, 'wrap'):
                            try:
                                f.wrap(inner_width, 100000)
                            except Exception:
                                pass

                def wrap(self, availWidth, availHeight):
                    inner_width = max(0, self.width - (self.padding * 2))
                    total_height = self.padding
                    for f in self.flowables:
                        w, h = f.wrap(inner_width, availHeight)
                        total_height += h
                    total_height += self.padding
                    return self.width, total_height

                def draw(self):
                    w, h = self.wrap(self.width, 100000)
                    self.canv.saveState()
                    self.canv.setFillColor(self.bg_color)
                    if self.border_color:
                        self.canv.setStrokeColor(self.border_color)
                        self.canv.setLineWidth(1)
                    else:
                        self.canv.setStrokeColor(self.bg_color)
                        self.canv.setLineWidth(0)

                    try:
                        self.canv.roundRect(0, 0, w, h, self.radius, stroke=1 if self.border_color else 0, fill=1)
                    except Exception:
                        self.canv.rect(0, 0, w, h, stroke=1 if self.border_color else 0, fill=1)

                    x = self.padding
                    y = h - self.padding
                    inner_width = max(0, w - (self.padding * 2))
                    for f in self.flowables:
                        fw, fh = f.wrap(inner_width, y)
                        y -= fh
                        f.drawOn(self.canv, x, y)

                    self.canv.restoreState()
            
            brand_primary = colors.HexColor('#4DD0E1')
            brand_secondary = colors.HexColor('#26C6DA')
            brand_accent = colors.HexColor('#4DD0E1')
            bg_soft = colors.HexColor('#E0F7FA')
            card_soft = colors.HexColor('#f9fafb')
            text_main = colors.HexColor('#111827')
            text_muted = colors.HexColor('#6b7280')
            border_soft = colors.HexColor('#e5e7eb')

            def fmt_ksh(value):
                try:
                    return f"Ksh {value:,.2f}"
                except Exception:
                    return f"Ksh {value}"

            title_style = ParagraphStyle(
                'InvoiceTitle',
                parent=styles['Title'],
                textColor=colors.white,
                fontSize=16,
                leading=18,
                spaceAfter=0,
            )
            header_left_style = ParagraphStyle(
                'InvoiceHeaderLeft',
                parent=styles['Normal'],
                textColor=colors.white,
                fontSize=10,
                leading=13,
            )
            header_right_style = ParagraphStyle(
                'InvoiceHeaderRight',
                parent=styles['Normal'],
                textColor=colors.white,
                fontSize=16,
                leading=18,
                alignment=TA_RIGHT,
                fontName='Helvetica-Bold',
            )
            normal_style = ParagraphStyle(
                'InvoiceNormal',
                parent=styles['Normal'],
                textColor=text_main,
                fontSize=10,
                leading=14,
            )
            meta_label_style = ParagraphStyle(
                'InvoiceMetaLabel',
                parent=styles['Normal'],
                textColor=text_muted,
                fontSize=9,
                leading=12,
                fontName='Helvetica-Bold',
            )
            meta_value_style = ParagraphStyle(
                'InvoiceMetaValue',
                parent=styles['Normal'],
                textColor=text_main,
                fontSize=9,
                leading=12,
            )
            section_heading_style = ParagraphStyle(
                'InvoiceSectionHeading',
                parent=styles['Normal'],
                textColor=brand_primary,
                fontSize=11,
                leading=13,
                fontName='Helvetica-Bold',
                spaceAfter=8,
            )

            invoice_date_text = invoice.invoice_date.strftime('%b %d, %Y') if invoice.invoice_date else ''
            due_date_text = invoice.due_date.strftime('%b %d, %Y') if invoice.due_date else ''
            status_display = invoice.get_status_display().upper() if hasattr(invoice, 'get_status_display') else str(getattr(invoice, 'status', '')).upper()
            status_color = colors.HexColor('#16a34a')
            if str(getattr(invoice, 'status', '')).lower() in ['pending', 'unpaid']:
                status_color = colors.HexColor('#f59e0b')
            if str(getattr(invoice, 'status', '')).lower() in ['overdue', 'cancelled', 'canceled', 'failed']:
                status_color = colors.HexColor('#dc2626')

            header_table = Table(
                [[
                    Paragraph(
                        f"<b>Clasyo</b> by Timesten Technologies Ltd.<br/><font size='9'>Subscription Invoice</font>",
                        header_left_style,
                    ),
                    Paragraph(
                        f"INVOICE<br/><font size='9'>#{invoice.invoice_number}</font>",
                        header_right_style,
                    ),
                ]],
                colWidths=[doc.width * 0.62, doc.width * 0.38],
            )
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 14),
                ('RIGHTPADDING', (0, 0), (-1, -1), 14),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            story.append(RoundedCard([header_table], width=doc.width, padding=0, bg_color=brand_primary, border_color=None, radius=14))
            story.append(Spacer(1, 16))
            
            school_name = getattr(school, 'name', '') or ''
            school_address = getattr(school, 'address', '') or ''
            school_phone = getattr(school, 'phone', '') or ''
            school_email = getattr(school, 'email', '') or ''

            bill_to_html_lines = [
                "<font size='9' color='#6b7280'><b>BILL TO</b></font>",
                f"<b>{school_name}</b>",
            ]
            if school_address:
                bill_to_html_lines.append(school_address)
            if school_phone:
                bill_to_html_lines.append(f"Phone: {school_phone}")
            if school_email:
                bill_to_html_lines.append(f"Email: {school_email}")

            details_html_lines = [
                "<font size='9' color='#6b7280'><b>INVOICE DETAILS</b></font>",
                f"Invoice Date: {invoice_date_text or '-'}",
                f"Due Date: {due_date_text or '-'}",
                f"Status: <font color='{status_color.hexval()}'><b>{status_display or '-'}</b></font>",
            ]
            if invoice.paid_date:
                details_html_lines.append(f"Paid Date: {invoice.paid_date.strftime('%b %d, %Y %H:%M')}")

            info_blocks_table = Table(
                [[
                    Paragraph('<br/>'.join(bill_to_html_lines), normal_style),
                    Paragraph('<br/>'.join(details_html_lines), normal_style),
                ]],
                colWidths=[doc.width * 0.55, doc.width * 0.45],
            )
            info_blocks_table.setStyle(TableStyle([
                ('INNERGRID', (0, 0), (-1, -1), 0.5, border_soft),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(RoundedCard([info_blocks_table], width=doc.width, padding=0, bg_color=card_soft, border_color=border_soft, radius=12))
            story.append(Spacer(1, 18))
            
            # Invoice items table
            item_data = [
                [
                    Paragraph('<b>Description</b>', meta_value_style),
                    Paragraph('<b>Period</b>', meta_value_style),
                    Paragraph('<b>Qty</b>', meta_value_style),
                    Paragraph('<b>Unit Price</b>', meta_value_style),
                    Paragraph('<b>Amount</b>', meta_value_style)
                ],
                [
                    f"{invoice.plan_name}\n{invoice.plan_description}",
                    f"{invoice.billing_start_date.strftime('%b %d, %Y')} - {invoice.billing_end_date.strftime('%b %d, %Y')}" if invoice.billing_start_date and invoice.billing_end_date else "Current period",
                    "1",
                    fmt_ksh(invoice.amount),
                    fmt_ksh(invoice.amount)
                ]
            ]
            
            if invoice.tax_amount > 0:
                item_data.append(['Tax', '', '', '', fmt_ksh(invoice.tax_amount)])
            
            # Total row
            total_amount_display = "FREE" if invoice.total_amount == 0 else fmt_ksh(invoice.total_amount)
            item_data.append([
                'Total', '', '', '', 
                total_amount_display
            ])
            
            item_card_padding = 8
            item_table_width = max(0, doc.width - (item_card_padding * 2))
            item_table = Table(item_data, colWidths=[
                item_table_width * 0.42,
                item_table_width * 0.22,
                item_table_width * 0.08,
                item_table_width * 0.14,
                item_table_width * 0.14,
            ])
            item_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), bg_soft),
                ('TEXTCOLOR', (0, 0), (-1, 0), text_main),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), text_main),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('INNERGRID', (0, 0), (-1, -1), 0.6, border_soft),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            story.append(RoundedCard([item_table], width=doc.width, padding=item_card_padding, bg_color=colors.white, border_color=border_soft, radius=12))
            
            if invoice.notes:
                story.append(Spacer(1, 20))
                story.append(Paragraph("Notes", section_heading_style))
                story.append(Paragraph(invoice.notes, normal_style))
            
            # Footer
            story.append(Spacer(1, 40))
            story.append(Paragraph("This is a computer-generated invoice. No signature is required.", ParagraphStyle('InvoiceFooter', parent=styles['Normal'], textColor=text_muted, fontSize=9, leading=12)))
            story.append(Paragraph("Thank you for your business with Clasyo!", ParagraphStyle('InvoiceFooterAccent', parent=styles['Normal'], textColor=brand_accent, fontSize=10, leading=12, fontName='Helvetica-Bold')))
            story.append(Spacer(1, 10))
            story.append(Paragraph("For questions, contact us at clasyo@timestentechnologies.co.ke", ParagraphStyle('InvoiceFooterSmall', parent=styles['Normal'], textColor=text_muted, fontSize=9, leading=12)))
            story.append(Paragraph("Website: https://clasyo.timestentechnologies.co.ke/", ParagraphStyle('InvoiceFooterSmallUrl', parent=styles['Normal'], textColor=text_muted, fontSize=9, leading=12)))
            
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
        if not (request.user.is_school_admin or request.user.is_superadmin):
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
                    'amount_display': 'FREE' if invoice.amount == 0 else f'Ksh {invoice.amount:,.2f}',
                    'tax_amount': float(invoice.tax_amount),
                    'tax_amount_display': f'Ksh {invoice.tax_amount:,.2f}',
                    'total_amount': float(invoice.total_amount),
                    'total_amount_display': 'FREE' if invoice.total_amount == 0 else f'Ksh {invoice.total_amount:,.2f}',
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


class AiChatApiView(LoginRequiredMixin, View):
    """Handle AI chat requests"""

    def post(self, request, school_slug):
        import json
        from superadmin.models import GlobalAIConfiguration, SchoolAIConfiguration
        prompt = ''
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                prompt = data.get('prompt', '').strip()
            except (json.JSONDecodeError, TypeError):
                prompt = ''
        else:
                prompt = request.POST.get('prompt', '').strip()
        if not prompt:
            return JsonResponse({'success': False, 'error': 'Prompt is required'}, status=400)
        try:
            # Determine effective configuration
            school = School.objects.get(slug=school_slug)
            school_config = SchoolAIConfiguration.objects.filter(school=school).first()
            print(f"School: {school.name}, school_config exists: {bool(school_config)}")
            if school_config:
                print(f"school_config.is_active: {school_config.is_active}")
                print(f"school_config.openai_api_key set: {bool(school_config.openai_api_key)}")
            if school_config and school_config.is_active:
                config = school_config.get_effective_config()
                print("Using school config")
            else:
                global_config = GlobalAIConfiguration.objects.filter(is_active=True).first()
                config = global_config.get_config_data() if global_config else None
                print("Using global config" if global_config else "No global config")
            print("Final config:", config)
            if not config:
                return JsonResponse({'success': False, 'error': 'AI is not configured'}, status=503)

            # Gather school context data
            context_data = self.get_school_context(school, school_config)
            print(f"Context data keys: {list(context_data.keys())}")

            # Prepare shared generation settings
            temperature = float(config.get('temperature', 0.7))
            max_tokens = int(config.get('max_tokens', 1000))
            system_prompt = self.build_system_prompt(context_data)

            # Import OpenAI safely so missing dependency returns JSON instead of an HTML error page
            try:
                from openai import OpenAI
            except ImportError:
                return JsonResponse({
                    'success': False,
                    'error': 'OpenAI Python library is not installed on the server.'
                }, status=500)

            provider = config.get('provider', 'openai')
            print(f"Provider: {provider}")
            
            # Initialize client based on provider
            client = None
            if provider == 'openai':
                if not config.get('openai_api_key'):
                    return JsonResponse({'success': False, 'error': 'OpenAI API key is not configured'}, status=503)
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=config.get('openai_api_key'))
                except ImportError:
                    return JsonResponse({
                        'success': False,
                        'error': 'OpenAI Python library is not installed on the server.'
                    }, status=500)
                model = config.get('openai_model', 'gpt-3.5-turbo')
                
            elif provider == 'azure':
                if not config.get('azure_openai_api_key'):
                    return JsonResponse({'success': False, 'error': 'Azure OpenAI API key is not configured'}, status=503)
                try:
                    from openai import AzureOpenAI
                    client = AzureOpenAI(
                        api_key=config.get('azure_openai_api_key'),
                        azure_endpoint=config.get('azure_openai_endpoint'),
                        api_version="2023-12-01-preview"
                    )
                except ImportError:
                    return JsonResponse({
                        'success': False,
                        'error': 'OpenAI Python library is not installed on the server.'
                    }, status=500)
                model = config.get('azure_openai_deployment', 'gpt-35-turbo')
                
            elif provider == 'anthropic':
                if not config.get('anthropic_api_key'):
                    return JsonResponse({'success': False, 'error': 'Anthropic API key is not configured'}, status=503)
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=config.get('anthropic_api_key'))
                except ImportError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Anthropic Python library is not installed on the server.'
                    }, status=500)
                model = config.get('anthropic_model', 'claude-2')
                
            elif provider == 'google':
                if not config.get('google_api_key'):
                    return JsonResponse({'success': False, 'error': 'Google API key is not configured'}, status=503)
                try:
                    import google.genai as genai
                    # Create a Google GenAI client; actual generate_content call happens later
                    client = genai.Client(api_key=config.get('google_api_key'))
                except ImportError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Google Gen AI library is not installed on the server.'
                    }, status=500)
                # Store the model name to use in the shared call section
                model = config.get('google_model', 'gemini-1.5-flash')
                
            elif provider == 'local':
                return JsonResponse({'success': False, 'error': 'Local model provider not implemented yet'}, status=503)
                
            else:
                return JsonResponse({'success': False, 'error': f'Provider {provider} is not supported'}, status=400)
            
            # Call appropriate API based on provider
            try:
                if provider == 'openai':
                    print(f"Calling OpenAI with model={model}, temperature={temperature}, max_tokens={max_tokens}")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    answer = response.choices[0].message.content
                    
                elif provider == 'azure':
                    print(f"Calling Azure OpenAI with model={model}, temperature={temperature}, max_tokens={max_tokens}")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    answer = response.choices[0].message.content
                    
                elif provider == 'anthropic':
                    print(f"Calling Anthropic with model={model}, temperature={temperature}, max_tokens={max_tokens}")
                    response = client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': prompt}
                        ]
                    )
                    answer = response.content[0].text
                    
                elif provider == 'google':
                    print(f"Calling Google Gemini with model={model}, temperature={temperature}, max_tokens={max_tokens}")
                    # Combine system prompt and user prompt for Gemini
                    contents = f"System: {system_prompt}\n\nUser: {prompt}"
                    # Use the google-genai 0.3.0 API: pass settings via the `config` dict
                    import google.genai as genai
                    response = client.models.generate_content(
                        model=model,
                        contents=contents,
                        config={
                            "temperature": float(temperature),
                            "max_output_tokens": int(max_tokens),
                        },
                    )
                    answer = response.text
                    
                else:
                    return JsonResponse({'success': False, 'error': f'Provider {provider} not implemented'}, status=501)
                    
                return JsonResponse({'success': True, 'answer': answer})
                    
            except School.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'School not found'}, status=404)
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
                
        except School.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'School not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def get_school_context(self, school, school_config):
        """Gather relevant school data for AI context"""
        context = {
            'school_name': school.name,
            'school_email': school.email,
            'school_phone': school.phone,
            'school_address': school.address,
        }
        
        print(f"school_config exists: {bool(school_config)}")
        from django.db.models import Sum, F
        if school_config:
            print(f"include_student_data: {school_config.include_student_data}")
            print(f"include_academic_data: {school_config.include_academic_data}")
            print(f"include_financial_data: {school_config.include_financial_data}")
            
            # Students
            if school_config.include_student_data:
                try:
                    from students.models import Student
                    # Start with all active students
                    base_qs = Student.objects.filter(is_active=True)
                    total_students = base_qs.count()
                    # Prefer students linked to this school via current_class
                    school_students = base_qs.filter(current_class__school=school).count()
                    if school_students > 0:
                        context['student_count'] = school_students
                        print(f"Student count (by class.school): {school_students}")
                    else:
                        context['student_count'] = total_students
                        print(f"Student count (all active, no class.school match): {total_students}")
                except Exception as e:
                    context['student_count'] = 'Unknown'
                    print(f"Error getting student count: {e}")

                # Parents and their children (linked via Student.parent_user)
                try:
                    from accounts.models import User
                    parent_students_qs = Student.objects.filter(
                        is_active=True,
                        parent_user__isnull=False,
                    )
                    if school is not None:
                        parent_students_qs = parent_students_qs.filter(current_class__school=school)

                    parents_map = {}
                    for s in parent_students_qs.select_related('parent_user'):
                        parent = s.parent_user
                        if not parent:
                            continue
                        entry = parents_map.setdefault(parent.id, {
                            'name': parent.get_full_name(),
                            'email': parent.email,
                            'children': [],
                        })
                        entry['children'].append({
                            'name': s.get_full_name(),
                            'admission_number': s.admission_number,
                        })

                    context['parent_count'] = len(parents_map)
                    context['children_with_parents_count'] = parent_students_qs.count()

                    # Build a short textual summary for the prompt (max 10 parents)
                    summary_parts = []
                    for _, info in list(parents_map.items())[:10]:
                        child_names = ", ".join(c['name'] for c in info['children'])
                        summary_parts.append(f"{info['name']} (Children: {child_names})")
                    if summary_parts:
                        context['parent_children_summary'] = "; ".join(summary_parts)

                    print(
                        f"Parents with linked children: {context['parent_count']}, "
                        f"children linked to parents: {context['children_with_parents_count']}"
                    )
                except Exception as e:
                    context['parent_count'] = 'Unknown'
                    context['children_with_parents_count'] = 'Unknown'
                    print(f"Error getting parent/children data: {e}")
            
            # Classes, subjects, teachers
            if school_config.include_academic_data:
                try:
                    from academics.models import Class, Subject
                    from accounts.models import User
                    from examinations.models import Exam
                    from django.utils import timezone
                    from django.db.models import Q
                    context['class_count'] = Class.objects.filter(school=school, is_active=True).count()
                    context['subject_count'] = Subject.objects.filter(school=school, is_active=True).count()
                    # Approximate teacher count: teachers linked to classes/sections for this school
                    teacher_count = User.objects.filter(
                        role='teacher',
                        class_sections__class_name__school=school,
                    ).distinct().count()
                    context['teacher_count'] = teacher_count

                    # Exams linked to this school via class or subject
                    today = timezone.now().date()
                    exam_qs = Exam.objects.all()
                    if school is not None:
                        exam_qs = exam_qs.filter(
                            Q(class_assigned__school=school) |
                            Q(subject__school=school)
                        )
                    exam_count = exam_qs.count()
                    context['exam_count'] = exam_count
                    context['published_exam_count'] = exam_qs.filter(is_published=True).count()
                    context['upcoming_exams_count'] = exam_qs.filter(start_date__gte=today).count()

                    upcoming = []
                    for exam in exam_qs.filter(start_date__gte=today).order_by('start_date')[:5]:
                        try:
                            exam_type = exam.get_exam_type_display()
                        except Exception:
                            exam_type = exam.exam_type
                        upcoming.append(f"{exam.name} ({exam_type}) on {exam.start_date}")
                    if upcoming:
                        context['upcoming_exams'] = upcoming

                    print(
                        f"Class count: {context['class_count']}, Subject count: {context['subject_count']}, "
                        f"Teacher count: {teacher_count}, Exams: {exam_count}, Upcoming exams: {len(upcoming)}"
                    )
                except Exception as e:
                    context['class_count'] = 'Unknown'
                    context['subject_count'] = 'Unknown'
                    context['teacher_count'] = 'Unknown'
                    context['exam_count'] = 'Unknown'
                    context['published_exam_count'] = 'Unknown'
                    context['upcoming_exams_count'] = 'Unknown'
                    print(f"Error getting academic/teacher/exam data: {e}")
            
            # Fee balances (always computed when a school config exists)
            try:
                from fees.models import FeeCollection
                from django.db.models import Q

                fee_qs = FeeCollection.objects.all()
                if school is not None:
                    fee_qs = fee_qs.filter(
                        Q(student__current_class__school=school) |
                        Q(fee_structure__class_name__school=school)
                    )

                # If nothing matched the school filters, fall back to all fee collections
                if not fee_qs.exists():
                    fee_qs = FeeCollection.objects.all()
                    print(f"No fee collections matched school filter; using all collections, total_rows={fee_qs.count()}")

                # Aggregate per student: total expected (amount) vs total paid
                agg = (
                    fee_qs
                    .values('student_id', 'student__first_name', 'student__last_name', 'student__admission_number')
                    .annotate(
                        total_amount=Sum('amount'),
                        total_paid=Sum('paid_amount'),
                    )
                )

                balances = []
                for row in agg:
                    total = row['total_amount'] or 0
                    paid = row['total_paid'] or 0
                    balance = total - paid
                    if balance > 0:
                        balances.append({
                            'student_id': row['student_id'],
                            'name': f"{row['student__first_name']} {row['student__last_name']}".strip(),
                            'admission_number': row['student__admission_number'],
                            'balance': float(balance),
                        })

                balances.sort(key=lambda x: x['balance'], reverse=True)
                context['students_with_fee_balances'] = balances
                context['students_with_fee_balances_count'] = len(balances)
                print(f"Aggregated fee rows: {agg.count()}, students with positive balances: {len(balances)}")

                # Detailed breakdown per fee type for top students with balances
                top_student_ids = [b['student_id'] for b in balances[:10]]
                fee_details_by_student = {}
                if top_student_ids:
                    details_qs = (
                        fee_qs
                        .filter(student_id__in=top_student_ids)
                        .values(
                            'student_id',
                            'fee_structure__name',
                            'fee_structure__fee_type',
                        )
                        .annotate(
                            total_amount=Sum('amount'),
                            total_paid=Sum('paid_amount'),
                        )
                    )
                    for row in details_qs:
                        sid = row['student_id']
                        fee_details_by_student.setdefault(sid, []).append({
                            'fee_name': row['fee_structure__name'],
                            'fee_type': row['fee_structure__fee_type'],
                            'total_amount': float(row['total_amount'] or 0),
                            'total_paid': float(row['total_paid'] or 0),
                            'balance': float((row['total_amount'] or 0) - (row['total_paid'] or 0)),
                        })
                    print(f"Built fee_details_by_student for {len(fee_details_by_student)} students")
                context['fee_details_by_student'] = fee_details_by_student
            except Exception as e:
                context['students_with_fee_balances'] = []
                context['students_with_fee_balances_count'] = 'Unknown'
                context['fee_details_by_student'] = {}
                print(f"Error getting financial data: {e}")
            # Students who both have upcoming exams and positive fee balances
            try:
                if context.get('students_with_fee_balances'):
                    from students.models import Student
                    from examinations.models import Exam
                    from django.utils import timezone

                    today = timezone.now().date()
                    exam_qs = Exam.objects.filter(start_date__gte=today)
                    if school is not None:
                        exam_qs = exam_qs.filter(
                            Q(class_assigned__school=school) |
                            Q(subject__school=school)
                        )

                    class_ids = list(
                        exam_qs.values_list('class_assigned_id', flat=True).distinct()
                    )

                    if class_ids:
                        upcoming_exam_student_ids = set(
                            Student.objects.filter(
                                is_active=True,
                                current_class__school=school,
                                current_class_id__in=class_ids,
                            ).values_list('id', flat=True)
                        )

                        balance_student_ids = {
                            s['student_id'] for s in context.get('students_with_fee_balances', [])
                        }
                        intersect_ids = balance_student_ids & upcoming_exam_student_ids

                        overlapping_students = [
                            s for s in context['students_with_fee_balances']
                            if s['student_id'] in intersect_ids
                        ]

                        context['students_with_upcoming_exams_and_fee_balances'] = overlapping_students
                        context['students_with_upcoming_exams_and_fee_balances_count'] = len(overlapping_students)
                        print(
                            "Students with upcoming exams and positive fee balances: "
                            f"{context['students_with_upcoming_exams_and_fee_balances_count']}"
                        )
                    else:
                        context['students_with_upcoming_exams_and_fee_balances'] = []
                        context['students_with_upcoming_exams_and_fee_balances_count'] = 0
            except Exception as e:
                context['students_with_upcoming_exams_and_fee_balances'] = []
                context['students_with_upcoming_exams_and_fee_balances_count'] = 'Unknown'
                print(f"Error computing students with upcoming exams and fee balances: {e}")
        else:
            # Default: include basic student count
            print("No school config, including default student count")
            try:
                from students.models import Student
                count = Student.objects.filter(
                    is_active=True,
                    current_class__school=school,
                ).count()
                context['student_count'] = count
                print(f"Default student count: {count}")
            except Exception as e:
                context['student_count'] = 'Unknown'
                print(f"Error getting default student count: {e}")
        
        print(f"Final context: {context}")
        return context

    def build_system_prompt(self, context):
        """Build a system prompt with school context"""
        prompt_parts = [
            f"You are an AI assistant for {context['school_name']}.",
            "Answer questions about this school based ONLY on the provided context.",
            "When asked for counts (students, teachers, parents, exams, etc.), always use the exact numbers from the context instead of guessing.",
            "When asked about fee balances, use the list of students with balances and any fee breakdowns from the context (including amounts and fee types).",
            "When asked about parents and their children, use the parent/children information in the context instead of saying you don't know.",
            "When asked about exams, use the exam counts and upcoming exam list from the context.",
            "Be helpful, concise, and professional.",
            "",
            "School Information:"
        ]
        
        if 'student_count' in context:
            prompt_parts.append(f"- Total Students: {context['student_count']}")
        if 'teacher_count' in context:
            prompt_parts.append(f"- Total Teachers (approximate): {context['teacher_count']}")
        if 'class_count' in context:
            prompt_parts.append(f"- Total Classes: {context['class_count']}")
        if 'subject_count' in context:
            prompt_parts.append(f"- Total Subjects: {context['subject_count']}")
        if 'parent_count' in context:
            prompt_parts.append(f"- Parents (with linked children): {context['parent_count']}")
        if 'children_with_parents_count' in context:
            prompt_parts.append(f"- Children linked to parents: {context['children_with_parents_count']}")
        if 'parent_children_summary' in context:
            prompt_parts.append(f"- Parent/Children Sample: {context['parent_children_summary']}")
        if 'exam_count' in context:
            prompt_parts.append(f"- Total Exams: {context['exam_count']}")
        if 'published_exam_count' in context:
            prompt_parts.append(f"- Published Exams: {context['published_exam_count']}")
        if 'upcoming_exams_count' in context:
            prompt_parts.append(f"- Upcoming Exams: {context['upcoming_exams_count']}")
        if context.get('upcoming_exams'):
            prompt_parts.append("- Upcoming Exams (next few): " + "; ".join(context['upcoming_exams']))
        if 'students_with_fee_balances_count' in context:
            prompt_parts.append(f"- Students with Fee Balances: {context['students_with_fee_balances_count']}")
        if context.get('students_with_fee_balances'):
            # Include a short, explicit list (capped) to guide the model
            top = context['students_with_fee_balances'][:10]
            details = ", ".join(
                f"{s['name']} (Adm {s['admission_number']}, Balance {s['balance']})" for s in top
            )
            prompt_parts.append(f"- Students with Fee Balances (sample): {details}")
        if 'students_with_upcoming_exams_and_fee_balances_count' in context:
            prompt_parts.append(
                "- Students with BOTH upcoming exams and fee balances: "
                f"{context['students_with_upcoming_exams_and_fee_balances_count']}"
            )
        if context.get('students_with_upcoming_exams_and_fee_balances'):
            top_overlap = context['students_with_upcoming_exams_and_fee_balances'][:10]
            overlap_details = ", ".join(
                f"{s['name']} (Adm {s['admission_number']}, Balance {s['balance']})" for s in top_overlap
            )
            prompt_parts.append(
                "- Sample of students with upcoming exams AND fee balances: " + overlap_details
            )
        
        prompt_parts.extend([
            "",
            "Use this information to answer questions. If a piece of data is not present in the context, then say you don't have that information available.",
            "After answering the user's question, suggest 2-3 concise, relevant follow-up questions or insights they might find useful about the school (for example, breakdowns by class, trends, or related information from exams, attendance, or fees)."
        ])
        
        return "\n".join(prompt_parts)


@require_GET
def offline_view(request, *args, **kwargs):
    """View for offline page shown during maintenance or offline mode.

    Accepts optional school_slug from the tenant URL pattern but does not
    need to use it directly.
    """
    return render(request, 'offline.html', status=200)
