from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
import json

from .models import HomeworkAssignment, HomeworkSubmission, HomeworkComment, HomeworkResource
from students.models import Student
from academics.models import Class, Section, Subject
from core.models import AcademicYear
from django import forms


# Form classes for inline use
class HomeworkSubmissionForm(forms.ModelForm):
    """Form for submitting homework"""
    class Meta:
        model = HomeworkSubmission
        fields = ['submission_text', 'submission_file', 'submission_url']
        widgets = {
            'submission_text': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'submission_file': forms.FileInput(attrs={'class': 'form-control'}),
            'submission_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }


class HomeworkGradeForm(forms.ModelForm):
    """Form for grading homework submissions"""
    class Meta:
        model = HomeworkSubmission
        fields = ['points_earned', 'grade', 'feedback']
        widgets = {
            'points_earned': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grade': forms.TextInput(attrs={'class': 'form-control'}),
            'feedback': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


class HomeworkCommentForm(forms.ModelForm):
    """Form for adding comments to homework submissions"""
    class Meta:
        model = HomeworkComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('Add a comment...')}),
        }


class HomeworkDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for homework"""
    template_name = 'homework/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        school_slug = self.kwargs.get('school_slug', '')
        today = timezone.now().date()
        
        # Different dashboard content based on user role
        if user.is_student:
            # Student dashboard
            student = Student.objects.filter(user=user).first()
            if student:
                # Upcoming assignments (due in the next 7 days)
                next_week = today + timezone.timedelta(days=7)
                context['upcoming_assignments'] = HomeworkAssignment.objects.filter(
                    class_ref=student.current_class,
                    due_date__gte=today,
                    due_date__lte=next_week,
                    status='published'
                ).order_by('due_date')
                
                # Recently submitted
                context['recent_submissions'] = HomeworkSubmission.objects.filter(
                    student=student
                ).order_by('-submitted_at')[:5]
                
                # Overdue assignments
                context['overdue_assignments'] = HomeworkAssignment.objects.filter(
                    class_ref=student.current_class,
                    due_date__lt=today,
                    status='published'
                ).exclude(
                    submissions__student=student,
                    submissions__status__in=['submitted', 'late', 'graded', 'returned']
                ).order_by('due_date')
                
                # Graded submissions
                context['graded_submissions'] = HomeworkSubmission.objects.filter(
                    student=student,
                    status__in=['graded', 'returned']
                ).order_by('-graded_at')[:5]
            
        elif user.is_teacher:
            # Teacher dashboard
            # Recent assignments created by this teacher
            context['recent_assignments'] = HomeworkAssignment.objects.filter(
                created_by=user
            ).order_by('-created_at')[:5]
            
            # Assignments due soon
            context['due_soon_assignments'] = HomeworkAssignment.objects.filter(
                created_by=user,
                due_date__gte=today,
                due_date__lte=today + timezone.timedelta(days=3),
                status='published'
            ).order_by('due_date')
            
            # Submissions to grade
            context['submissions_to_grade'] = HomeworkSubmission.objects.filter(
                homework__created_by=user,
                status__in=['submitted', 'late']
            ).order_by('submitted_at')
            
            # Recently graded
            context['recently_graded'] = HomeworkSubmission.objects.filter(
                homework__created_by=user,
                status='graded',
                graded_by=user
            ).order_by('-graded_at')[:5]
        
        else:
            # Admin dashboard - overview of system
            context['total_assignments'] = HomeworkAssignment.objects.count()
            context['active_assignments'] = HomeworkAssignment.objects.filter(status='published').count()
            context['total_submissions'] = HomeworkSubmission.objects.filter(status__in=['submitted', 'late', 'graded', 'returned']).count()
            context['recent_assignments'] = HomeworkAssignment.objects.order_by('-created_at')[:10]
        
        context['school_slug'] = school_slug
        return context


class HomeworkAssignmentListView(LoginRequiredMixin, ListView):
    """List of homework assignments"""
    model = HomeworkAssignment
    template_name = 'homework/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = HomeworkAssignment.objects.all()
        user = self.request.user
        
        # Filter by role
        if user.is_teacher and not user.is_school_admin:
            queryset = queryset.filter(created_by=user)
        elif user.is_student:
            student = Student.objects.filter(user=user).first()
            if student:
                queryset = queryset.filter(
                    Q(class_ref=student.current_class) &
                    (Q(section__isnull=True) | Q(section=student.section))
                )
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        class_id = self.request.GET.get('class_id')
        if class_id:
            queryset = queryset.filter(class_ref_id=class_id)
            
        subject_id = self.request.GET.get('subject_id')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
            
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Default ordering
        sort = self.request.GET.get('sort', '-assigned_date')
        if sort not in ['title', 'due_date', '-due_date', 'assigned_date', '-assigned_date', 'subject__name']:
            sort = '-assigned_date'
        queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['classes'] = Class.objects.filter(is_active=True)
        context['subjects'] = Subject.objects.filter(is_active=True)
        context['status_choices'] = HomeworkAssignment.STATUS_CHOICES
        
        # Get any active filters
        context['current_filters'] = {}
        for param in ['status', 'class_id', 'subject_id', 'search', 'sort']:
            value = self.request.GET.get(param)
            if value:
                context['current_filters'][param] = value
        
        return context


class HomeworkAssignmentCreateView(LoginRequiredMixin, CreateView):
    """Create new homework assignment"""
    model = HomeworkAssignment
    template_name = 'homework/assignment_form.html'
    fields = ['title', 'description', 'instructions', 'class_ref', 'section', 'subject', 
              'academic_year', 'assigned_date', 'due_date', 'points', 'grading_type', 
              'is_graded', 'submission_type', 'allow_late_submissions', 
              'late_penalty_percentage', 'max_attempts', 'attachment']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Enhanced form field styling and widgets
        form.fields['title'].widget.attrs.update({'class': 'form-control', 'placeholder': _('Assignment Title')})
        form.fields['description'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        form.fields['instructions'].widget = forms.Textarea(attrs={'class': 'form-control rich-editor', 'rows': 5})
        
        # Date and time fields
        form.fields['assigned_date'].widget = forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        form.fields['due_date'].widget = forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        form.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        
        # Academic references
        form.fields['class_ref'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['section'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['subject'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['academic_year'].widget.attrs.update({'class': 'form-select'})
        
        # Filter academic years to only active ones
        form.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
        
        # Filter subjects for teachers
        user = self.request.user
        if user.is_teacher and not user.is_school_admin:
            form.fields['subject'].queryset = Subject.objects.filter(
                subject_assignments__teacher=user,
                is_active=True
            ).distinct()
        
        # Handle section choices dynamically (to be enhanced with AJAX)
        if 'class_ref' in self.request.POST:
            class_id = self.request.POST.get('class_ref')
            form.fields['section'].queryset = Section.objects.filter(class_name_id=class_id)
        else:
            form.fields['section'].queryset = Section.objects.none()
        
        return form
    
    def form_valid(self, form):
        # Set the creator
        form.instance.created_by = self.request.user
        
        # Associate with school
        school_slug = self.kwargs.get('school_slug')
        from tenants.models import School
        try:
            school = School.objects.get(slug=school_slug)
            form.instance.school = school
        except School.DoesNotExist:
            pass
        
        # Auto-publish if requested
        publish_now = self.request.POST.get('publish_now') == 'on'
        if publish_now:
            form.instance.is_published = True
            form.instance.status = 'published'
        
        messages.success(self.request, _('Homework assignment created successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('homework:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.id
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create Homework Assignment')
        return context


class HomeworkAssignmentDetailView(LoginRequiredMixin, DetailView):
    """View homework assignment details"""
    model = HomeworkAssignment
    template_name = 'homework/assignment_detail.html'
    context_object_name = 'assignment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        assignment = self.object
        user = self.request.user
        
        # Submissions data
        if user.is_teacher or user.is_school_admin:
            # For teachers - show all submissions
            submissions = HomeworkSubmission.objects.filter(homework=assignment)
            context['submission_stats'] = {
                'total': submissions.count(),
                'submitted': submissions.filter(status__in=['submitted', 'late', 'graded', 'returned']).count(),
                'graded': submissions.filter(status__in=['graded', 'returned']).count(),
                'average_score': submissions.filter(points_earned__isnull=False).aggregate(Avg('points_earned'))['points_earned__avg']
            }
            
            # Get all students who should submit
            context['students'] = Student.objects.filter(
                current_class=assignment.class_ref,
                is_active=True
            ).filter(
                Q(section__isnull=True) | Q(section=assignment.section) if assignment.section else Q()
            )
            
        elif user.is_student:
            # For students - show only their submission
            student = Student.objects.filter(user=user).first()
            if student:
                context['student'] = student
                try:
                    context['submission'] = HomeworkSubmission.objects.get(
                        homework=assignment,
                        student=student
                    )
                except HomeworkSubmission.DoesNotExist:
                    context['submission'] = None
                    # Check if can submit
                    can_submit = not assignment.is_past_due or assignment.allow_late_submissions
                    context['can_submit'] = can_submit
                    if can_submit:
                        context['submission_form'] = HomeworkSubmissionForm()
        
        # Resources
        context['resources'] = assignment.resources.all()
        
        # Permissions
        context['can_edit'] = user == assignment.created_by or user.is_school_admin
        context['is_teacher'] = user.is_teacher
        
        return context


class HomeworkAssignmentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update homework assignment"""
    model = HomeworkAssignment
    template_name = 'homework/assignment_form.html'
    fields = ['title', 'description', 'instructions', 'class_ref', 'section', 'subject', 
              'academic_year', 'assigned_date', 'due_date', 'points', 'grading_type', 
              'is_graded', 'submission_type', 'allow_late_submissions', 
              'late_penalty_percentage', 'max_attempts', 'attachment']
    
    def test_func(self):
        assignment = self.get_object()
        return self.request.user == assignment.created_by or self.request.user.is_school_admin
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Apply same field styling as in create view
        form.fields['title'].widget.attrs.update({'class': 'form-control', 'placeholder': _('Assignment Title')})
        form.fields['description'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        form.fields['instructions'].widget = forms.Textarea(attrs={'class': 'form-control rich-editor', 'rows': 5})
        
        # Date and time fields
        form.fields['assigned_date'].widget = forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        form.fields['due_date'].widget = forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        form.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        
        # Academic references
        form.fields['class_ref'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['section'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['subject'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['academic_year'].widget.attrs.update({'class': 'form-select'})
        
        # Filter academic years to only active ones
        form.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
        
        # Setup section dropdown based on selected class
        if self.object.class_ref:
            form.fields['section'].queryset = Section.objects.filter(class_name=self.object.class_ref)
        
        return form
    
    def form_valid(self, form):
        # Update published status if requested
        publish_now = self.request.POST.get('publish_now') == 'on'
        if publish_now and not form.instance.is_published:
            form.instance.is_published = True
            form.instance.status = 'published'
        
        messages.success(self.request, _('Homework assignment updated successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('homework:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.id
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Homework Assignment')
        return context


class HomeworkAssignmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete homework assignment"""
    model = HomeworkAssignment
    template_name = 'homework/confirm_delete.html'
    
    def test_func(self):
        assignment = self.get_object()
        return self.request.user == assignment.created_by or self.request.user.is_school_admin
    
    def get_success_url(self):
        return reverse('homework:list', kwargs={'school_slug': self.kwargs.get('school_slug', '')})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Homework Assignment')
        context['message'] = _('Are you sure you want to delete this homework assignment?')
        context['note'] = _('This will also delete all student submissions for this assignment.')
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Homework assignment deleted successfully'))
        return super().delete(request, *args, **kwargs)


class HomeworkSubmitView(LoginRequiredMixin, FormView):
    """Submit homework as student"""
    form_class = HomeworkSubmissionForm
    template_name = 'homework/submit_form.html'
    
    def get_success_url(self):
        return reverse('homework:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.kwargs.get('assignment_id')
        })
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is a student
        if not request.user.is_student:
            messages.error(request, _('Only students can submit homework'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
            
        # Get the assignment and student
        self.assignment = get_object_or_404(HomeworkAssignment, pk=self.kwargs['assignment_id'])
        self.student = Student.objects.filter(user=request.user).first()
        
        if not self.student:
            messages.error(request, _('Student profile not found'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        # Check if student belongs to the right class
        if self.student.current_class != self.assignment.class_ref:
            messages.error(request, _('This assignment is not for your class'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        # Check if section matches (if assignment is section-specific)
        if self.assignment.section and self.student.section != self.assignment.section:
            messages.error(request, _('This assignment is not for your section'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
            
        # Check if past due date and late submissions are not allowed
        if self.assignment.is_past_due and not self.assignment.allow_late_submissions:
            messages.error(request, _('The deadline for this assignment has passed'))
            return redirect('homework:detail', 
                         school_slug=self.kwargs.get('school_slug', ''), 
                         pk=self.assignment.id)
        
        # Check if submission exists and max attempts reached
        existing_submissions = HomeworkSubmission.objects.filter(
            homework=self.assignment,
            student=self.student
        ).count()
        
        if existing_submissions >= self.assignment.max_attempts and self.assignment.max_attempts > 0:
            messages.error(request, _('You have reached the maximum number of allowed attempts'))
            return redirect('homework:detail', 
                         school_slug=self.kwargs.get('school_slug', ''), 
                         pk=self.assignment.id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['assignment'] = self.assignment
        context['title'] = _('Submit Homework')
        context['is_late'] = self.assignment.is_past_due
        
        # Adjust form based on submission type
        if self.assignment.submission_type == 'text':
            context['show_text'] = True
            context['show_file'] = False
            context['show_url'] = False
        elif self.assignment.submission_type == 'file':
            context['show_text'] = False
            context['show_file'] = True
            context['show_url'] = False
        elif self.assignment.submission_type == 'link':
            context['show_text'] = False
            context['show_file'] = False
            context['show_url'] = True
        
        return context
    
    def form_valid(self, form):
        # Create or update submission
        attempt = HomeworkSubmission.objects.filter(
            homework=self.assignment,
            student=self.student
        ).count() + 1
        
        submission = form.save(commit=False)
        submission.homework = self.assignment
        submission.student = self.student
        submission.attempt_number = attempt
        submission.status = 'submitted'
        
        # Check if late submission
        if self.assignment.is_past_due:
            submission.is_late = True
            submission.status = 'late'
        
        submission.save()
        
        messages.success(self.request, _('Homework submitted successfully'))
        return super().form_valid(form)


class HomeworkSubmissionDetailView(LoginRequiredMixin, DetailView):
    """View homework submission details"""
    model = HomeworkSubmission
    template_name = 'homework/submission_detail.html'
    context_object_name = 'submission'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        submission = self.object
        user = self.request.user
        
        # Check permissions
        is_owner = user.is_student and hasattr(user, 'student') and user.student == submission.student
        is_teacher = user.is_teacher and user == submission.homework.created_by
        is_admin = user.is_school_admin
        
        if not (is_owner or is_teacher or is_admin):
            raise Http404("You do not have permission to view this submission")
        
        # Add grading form for teachers
        if is_teacher or is_admin:
            context['grade_form'] = HomeworkGradeForm(instance=submission)
            
        # Add comment form
        context['comment_form'] = HomeworkCommentForm()
        
        # Get comments
        context['comments'] = submission.comments.all().order_by('created_at')
        
        # Get assignment details
        context['assignment'] = submission.homework
        
        return context


class HomeworkSubmissionGradeView(LoginRequiredMixin, UpdateView):
    """Grade a homework submission"""
    model = HomeworkSubmission
    form_class = HomeworkGradeForm
    template_name = 'homework/submission_grade.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Only teachers/admins can grade
        if not (request.user.is_teacher or request.user.is_school_admin):
            messages.error(request, _('You do not have permission to grade submissions'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        self.object = self.get_object()
        
        # Check if this teacher owns the assignment or is admin
        assignment = self.object.homework
        if not (request.user == assignment.created_by or request.user.is_school_admin):
            messages.error(request, _('You can only grade your own assignments'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
            
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Update status to graded
        form.instance.status = 'graded'
        form.instance.graded_at = timezone.now()
        form.instance.graded_by = self.request.user
        
        messages.success(self.request, _('Submission graded successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('homework:submission_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.id
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Grade Submission')
        context['submission'] = self.object
        context['assignment'] = self.object.homework
        return context


class StudentHomeworkListView(LoginRequiredMixin, ListView):
    """List homework assignments for a student"""
    model = HomeworkAssignment
    template_name = 'homework/student_assignments.html'
    context_object_name = 'assignments'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_student:
            messages.error(request, _('This page is only for students'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        student = Student.objects.filter(user=user).first()
        
        if not student:
            return HomeworkAssignment.objects.none()
        
        # Get assignments for student's class and section
        queryset = HomeworkAssignment.objects.filter(
            class_ref=student.current_class,
            status='published'
        ).filter(
            Q(section__isnull=True) | Q(section=student.section)
        )
        
        # Apply filters
        filter_type = self.request.GET.get('filter', 'all')
        today = timezone.now()
        
        if filter_type == 'upcoming':
            queryset = queryset.filter(due_date__gt=today)
        elif filter_type == 'past':
            queryset = queryset.filter(due_date__lte=today)
        elif filter_type == 'submitted':
            # Get IDs of assignments the student has submitted
            submitted_ids = HomeworkSubmission.objects.filter(
                student=student,
                status__in=['submitted', 'late', 'graded', 'returned']
            ).values_list('homework_id', flat=True)
            queryset = queryset.filter(id__in=submitted_ids)
        elif filter_type == 'not_submitted':
            # Get IDs of assignments the student has submitted
            submitted_ids = HomeworkSubmission.objects.filter(
                student=student,
                status__in=['submitted', 'late', 'graded', 'returned']
            ).values_list('homework_id', flat=True)
            queryset = queryset.exclude(id__in=submitted_ids)
        elif filter_type == 'graded':
            # Get IDs of assignments the student has received grades for
            graded_ids = HomeworkSubmission.objects.filter(
                student=student,
                status__in=['graded', 'returned']
            ).values_list('homework_id', flat=True)
            queryset = queryset.filter(id__in=graded_ids)
        
        # Order by due date (closest first)
        queryset = queryset.order_by('due_date')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Get current filter
        context['current_filter'] = self.request.GET.get('filter', 'all')
        
        # Get student and their submissions
        student = Student.objects.filter(user=self.request.user).first()
        if student:
            submissions = HomeworkSubmission.objects.filter(student=student)
            
            # Create a map of assignment_id -> submission for quick access
            submission_map = {sub.homework_id: sub for sub in submissions}
            
            # Add submission info to each assignment
            for assignment in context['assignments']:
                if assignment.id in submission_map:
                    assignment.student_submission = submission_map[assignment.id]
        
        return context


class ClassHomeworkListView(LoginRequiredMixin, ListView):
    """List homework assignments for a specific class"""
    model = HomeworkAssignment
    template_name = 'homework/class_assignments.html'
    context_object_name = 'assignments'
    paginate_by = 15
    
    def dispatch(self, request, *args, **kwargs):
        # Only teachers and admins can access
        if not (request.user.is_teacher or request.user.is_school_admin):
            messages.error(request, _('You do not have permission to view this page'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
            
        # Get the class
        self.class_obj = get_object_or_404(Class, id=self.kwargs['class_id'])
        
        # Check if teacher is associated with this class
        if request.user.is_teacher and not request.user.is_school_admin:
            from academics.models import SubjectTeacherAssignment
            has_access = SubjectTeacherAssignment.objects.filter(
                teacher=request.user,
                class_assigned=self.class_obj
            ).exists()
            
            if not has_access:
                messages.error(request, _('You do not have permission to view this class'))
                return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        class_id = self.kwargs['class_id']
        queryset = HomeworkAssignment.objects.filter(class_ref_id=class_id)
        
        # Additional filters
        subject_id = self.request.GET.get('subject_id')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
            
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        sort = self.request.GET.get('sort', '-due_date')
        if sort in ['due_date', '-due_date', 'assigned_date', '-assigned_date', 'subject__name']:
            queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-due_date')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['class'] = self.class_obj
        
        # Available subjects for this class
        context['subjects'] = Subject.objects.filter(
            subject_assignments__class_name=self.class_obj
        ).distinct()
        
        # Filter options
        context['status_choices'] = HomeworkAssignment.STATUS_CHOICES
        
        # Current filters
        context['current_filters'] = {}
        for param in ['subject_id', 'status', 'sort']:
            value = self.request.GET.get(param)
            if value:
                context['current_filters'][param] = value
        
        return context


class ClassSubmissionsView(LoginRequiredMixin, ListView):
    """View all submissions for a class"""
    model = HomeworkSubmission
    template_name = 'homework/class_submissions.html'
    context_object_name = 'submissions'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        # Only teachers and admins can access
        if not (request.user.is_teacher or request.user.is_school_admin):
            messages.error(request, _('You do not have permission to view this page'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
            
        # Get the class
        self.class_obj = get_object_or_404(Class, id=self.kwargs['class_id'])
        
        # Check if teacher is associated with this class
        if request.user.is_teacher and not request.user.is_school_admin:
            from academics.models import SubjectTeacherAssignment
            has_access = SubjectTeacherAssignment.objects.filter(
                teacher=request.user,
                class_assigned=self.class_obj
            ).exists()
            
            if not has_access:
                messages.error(request, _('You do not have permission to view this class'))
                return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        # Get assignment if specified
        assignment_id = self.request.GET.get('assignment_id')
        if assignment_id:
            self.assignment = get_object_or_404(HomeworkAssignment, id=assignment_id)
            if self.assignment.class_ref != self.class_obj:
                messages.error(request, _('The specified assignment does not belong to this class'))
                return redirect('homework:class_assignments', 
                             school_slug=self.kwargs.get('school_slug', ''), 
                             class_id=self.class_obj.id)
        else:
            self.assignment = None
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        # Start with submissions for this class
        queryset = HomeworkSubmission.objects.filter(
            homework__class_ref=self.class_obj
        ).select_related('student', 'homework')
        
        # Filter by assignment if specified
        if self.assignment:
            queryset = queryset.filter(homework=self.assignment)
            
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        subject_id = self.request.GET.get('subject_id')
        if subject_id:
            queryset = queryset.filter(homework__subject_id=subject_id)
            
        student_id = self.request.GET.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        is_graded = self.request.GET.get('is_graded')
        if is_graded == 'yes':
            queryset = queryset.filter(status__in=['graded', 'returned'])
        elif is_graded == 'no':
            queryset = queryset.filter(status__in=['submitted', 'late'])
            
        # Default sorting
        sort = self.request.GET.get('sort', '-submitted_at')
        if sort in ['submitted_at', '-submitted_at', 'student__first_name', 'homework__title']:
            queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-submitted_at')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['class'] = self.class_obj
        context['assignment'] = self.assignment
        
        # Students in this class
        context['students'] = Student.objects.filter(
            current_class=self.class_obj,
            is_active=True
        )
        
        # Available subjects
        context['subjects'] = Subject.objects.filter(
            subject_assignments__class_name=self.class_obj
        ).distinct()
        
        # Available assignments
        context['assignments'] = HomeworkAssignment.objects.filter(
            class_ref=self.class_obj
        ).order_by('-due_date')
        
        # Filter options
        context['status_choices'] = HomeworkSubmission.STATUS_CHOICES
        
        # Current filters
        context['current_filters'] = {}
        for param in ['assignment_id', 'subject_id', 'status', 'student_id', 'is_graded', 'sort']:
            value = self.request.GET.get(param)
            if value:
                context['current_filters'][param] = value
        
        # Add statistics if assignment is specified
        if self.assignment:
            total_students = Student.objects.filter(
                current_class=self.class_obj,
                is_active=True
            ).count()
            
            submitted = self.get_queryset().filter(
                status__in=['submitted', 'late', 'graded', 'returned']
            ).count()
            
            graded = self.get_queryset().filter(
                status__in=['graded', 'returned']
            ).count()
            
            context['submission_stats'] = {
                'total_students': total_students,
                'submitted': submitted,
                'not_submitted': total_students - submitted,
                'graded': graded,
                'to_grade': submitted - graded,
                'submission_rate': (submitted / total_students * 100) if total_students > 0 else 0
            }
            
        return context


class AddCommentView(LoginRequiredMixin, CreateView):
    """Add comment to a homework submission"""
    model = HomeworkComment
    form_class = HomeworkCommentForm
    http_method_names = ['post']
    
    def dispatch(self, request, *args, **kwargs):
        # Get the submission
        self.submission = get_object_or_404(HomeworkSubmission, pk=self.kwargs['submission_id'])
        
        # Check if user has permission to comment on this submission
        user = request.user
        is_owner = user.is_student and hasattr(user, 'student') and user.student == self.submission.student
        is_teacher = user.is_teacher and (user == self.submission.homework.created_by or 
                                        user == self.submission.student.current_class.class_teacher)
        is_admin = user.is_school_admin
        
        if not (is_owner or is_teacher or is_admin):
            messages.error(request, _('You do not have permission to comment on this submission'))
            return redirect('homework:dashboard', school_slug=self.kwargs.get('school_slug', ''))
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Set the submission and author
        form.instance.submission = self.submission
        form.instance.author = self.request.user
        
        response = super().form_valid(form)
        
        # If AJAX request
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment_id': self.object.id,
                'author_name': self.object.author.get_full_name(),
                'text': self.object.text,
                'created_at': self.object.created_at.strftime('%Y-%m-%d %H:%M')
            })
            
        messages.success(self.request, _('Comment added successfully'))
        return response
    
    def form_invalid(self, form):
        # If AJAX request
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
            
        messages.error(self.request, _('Error adding comment'))
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('homework:submission_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.submission.id
        })
