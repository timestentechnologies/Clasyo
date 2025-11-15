from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.utils.translation import gettext as _
import random

from .models import OnlineExam, ExamQuestion, QuestionChoice, ExamAttempt, StudentAnswer
from students.models import Student
from academics.models import Class, Section, Subject
from django import forms


class OnlineExamDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for online exams"""
    template_name = 'online_exam/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        user = self.request.user
        
        # Different dashboard content based on user role
        if user.is_student:
            # Student dashboard
            student = Student.objects.filter(user=user).first()
            if student:
                # Current exams
                now = timezone.now()
                context['current_exams'] = OnlineExam.objects.filter(
                    class_ref=student.current_class,
                    is_published=True,
                    start_time__lte=now,
                    end_time__gte=now
                ).order_by('end_time')
                
                # Upcoming exams
                context['upcoming_exams'] = OnlineExam.objects.filter(
                    class_ref=student.current_class,
                    is_published=True,
                    start_time__gt=now
                ).order_by('start_time')[:5]
                
                # Recent attempts
                context['recent_attempts'] = ExamAttempt.objects.filter(
                    student=student,
                    is_completed=True
                ).order_by('-submitted_at')[:5]
                
                # Stats
                total_attempts = ExamAttempt.objects.filter(student=student, is_completed=True).count()
                context['stats'] = {
                    'total_attempts': total_attempts,
                    'exams_passed': ExamAttempt.objects.filter(student=student, is_completed=True, passed=True).count(),
                    'average_score': ExamAttempt.objects.filter(student=student, is_completed=True).aggregate(avg=Avg('percentage'))['avg']
                }
        
        elif user.is_teacher or user.is_school_admin:
            # Teacher dashboard
            # Recent exams created by this teacher
            if user.is_school_admin:
                recent_exams = OnlineExam.objects.all().order_by('-created_at')[:5]
            else:
                recent_exams = OnlineExam.objects.filter(created_by=user).order_by('-created_at')[:5]
            
            context['recent_exams'] = recent_exams
            
            # Active exams
            now = timezone.now()
            context['active_exams'] = OnlineExam.objects.filter(
                is_published=True,
                start_time__lte=now,
                end_time__gte=now
            ).order_by('end_time')
            
            # Exams requiring grading
            if user.is_school_admin:
                grading_exams = OnlineExam.objects.filter(
                    attempts__status='submitted'
                ).distinct()
            else:
                grading_exams = OnlineExam.objects.filter(
                    created_by=user,
                    attempts__status='submitted'
                ).distinct()
            
            context['grading_exams'] = grading_exams
            
            # Stats
            context['stats'] = {
                'total_exams': OnlineExam.objects.filter(created_by=user).count() if not user.is_school_admin else OnlineExam.objects.all().count(),
                'total_attempts': ExamAttempt.objects.count(),
                'pass_rate': ExamAttempt.objects.filter(passed=True).count() / max(ExamAttempt.objects.filter(is_completed=True).count(), 1) * 100
            }
        
        return context


class OnlineExamListView(LoginRequiredMixin, ListView):
    """List of online exams"""
    model = OnlineExam
    template_name = 'online_exam/online_exam_list.html'
    context_object_name = 'exams'
    paginate_by = 15
    
    def get_queryset(self):
        user = self.request.user
        queryset = OnlineExam.objects.all()
        
        # Filter by user role
        if user.is_student:
            # Students see only published exams for their class
            student = Student.objects.filter(user=user).first()
            if student:
                queryset = queryset.filter(
                    is_published=True,
                    class_ref=student.current_class
                )
        elif user.is_teacher and not user.is_school_admin:
            # Teachers see exams they created
            queryset = queryset.filter(created_by=user)
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
            
        class_id = self.request.GET.get('class')
        if class_id:
            queryset = queryset.filter(class_ref_id=class_id)
            
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Default sorting
        sort = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Filter options
        context['subjects'] = Subject.objects.filter(is_active=True)
        context['classes'] = Class.objects.filter(is_active=True)
        context['status_choices'] = OnlineExam.STATUS_CHOICES
        
        # Current filters
        context['current_filters'] = {}
        for param in ['status', 'subject', 'class', 'search', 'sort']:
            value = self.request.GET.get(param)
            if value:
                context['current_filters'][param] = value
        
        return context


class OnlineExamDetailView(LoginRequiredMixin, DetailView):
    """View online exam details"""
    model = OnlineExam
    template_name = 'online_exam/online_exam_detail.html'
    context_object_name = 'exam'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        exam = self.object
        user = self.request.user
        
        # Check access permissions
        if user.is_student:
            student = Student.objects.filter(user=user).first()
            if student and student.current_class != exam.class_ref:
                raise Http404("Exam not available for your class")
            
            # Student specific data
            if student:
                # Check if student has attempted this exam
                context['attempts'] = ExamAttempt.objects.filter(
                    exam=exam,
                    student=student
                ).order_by('-attempt_number')
                
                # Check if can attempt
                context['can_attempt'] = (
                    exam.is_published and 
                    timezone.now() >= exam.start_time and
                    timezone.now() <= exam.end_time and
                    context['attempts'].count() < exam.max_attempts
                )
        
        # Common data
        context['questions_count'] = exam.questions.count()
        context['total_marks'] = exam.total_marks
        
        # Teacher/admin specific data
        if user.is_teacher or user.is_school_admin:
            # Questions
            context['questions'] = exam.questions.all().order_by('order')
            
            # Attempts
            attempts = ExamAttempt.objects.filter(exam=exam)
            context['attempts_count'] = attempts.count()
            context['completed_attempts'] = attempts.filter(is_completed=True).count()
            
            # Permissions
            context['can_edit'] = user == exam.created_by or user.is_school_admin
            context['can_delete'] = user == exam.created_by or user.is_school_admin
        
        return context


class OnlineExamCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new online exam"""
    model = OnlineExam
    template_name = 'online_exam/online_exam_form.html'
    fields = ['title', 'description', 'subject', 'class_ref', 'section', 'instructions',
              'start_time', 'end_time', 'duration_minutes', 'passing_percentage',
              'negative_marking', 'negative_mark_value', 'is_randomized',
              'allow_attempt_review', 'difficulty_level', 'publish_results',
              'show_answer_key', 'require_webcam', 'prevent_tab_switching', 'max_attempts']
    
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Enhanced form field styling and widgets
        form.fields['title'].widget.attrs.update({'class': 'form-control'})
        form.fields['description'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        form.fields['instructions'].widget = forms.Textarea(attrs={'class': 'form-control rich-editor', 'rows': 5})
        
        # Date and time fields
        form.fields['start_time'].widget = forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        form.fields['end_time'].widget = forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        form.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        form.fields['end_time'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        
        # Academic references
        form.fields['class_ref'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['section'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['subject'].widget.attrs.update({'class': 'form-select select2'})
        
        # Filter subjects for teachers
        user = self.request.user
        if user.is_teacher and not user.is_school_admin:
            form.fields['subject'].queryset = Subject.objects.filter(
                subject_assignments__teacher=user,
                is_active=True
            ).distinct()
        
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
        
        messages.success(self.request, _('Exam created successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('online_exam:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.pk
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create Online Exam')
        return context


class OnlineExamUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update online exam"""
    model = OnlineExam
    template_name = 'online_exam/online_exam_form.html'
    fields = ['title', 'description', 'subject', 'class_ref', 'section', 'instructions',
              'start_time', 'end_time', 'duration_minutes', 'passing_percentage',
              'negative_marking', 'negative_mark_value', 'is_randomized',
              'allow_attempt_review', 'difficulty_level', 'publish_results',
              'show_answer_key', 'require_webcam', 'prevent_tab_switching', 'max_attempts']
    
    def test_func(self):
        exam = self.get_object()
        return self.request.user == exam.created_by or self.request.user.is_school_admin
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Enhanced form field styling and widgets (same as create view)
        form.fields['title'].widget.attrs.update({'class': 'form-control'})
        form.fields['description'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        form.fields['instructions'].widget = forms.Textarea(attrs={'class': 'form-control rich-editor', 'rows': 5})
        
        # Date and time fields
        form.fields['start_time'].widget = forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        form.fields['end_time'].widget = forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        form.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        form.fields['end_time'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        
        # Academic references
        form.fields['class_ref'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['section'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['subject'].widget.attrs.update({'class': 'form-select select2'})
        
        return form
    
    def form_valid(self, form):
        # Auto-publish if requested
        publish_now = self.request.POST.get('publish_now') == 'on'
        if publish_now and not form.instance.is_published:
            form.instance.is_published = True
        
        messages.success(self.request, _('Exam updated successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('online_exam:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.pk
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Online Exam')
        return context


class OnlineExamDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete online exam"""
    model = OnlineExam
    template_name = 'online_exam/confirm_delete.html'
    
    def test_func(self):
        exam = self.get_object()
        return self.request.user == exam.created_by or self.request.user.is_school_admin
    
    def get_success_url(self):
        return reverse('online_exam:list', kwargs={
            'school_slug': self.kwargs.get('school_slug', '')
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Exam')
        context['message'] = _('Are you sure you want to delete this exam?')
        context['warning'] = _('This will also delete all questions and student attempts.')
        return context


# Additional views required by the URLs
class ExamResultsView(LoginRequiredMixin, View):
    """View exam results"""
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('exam_id')
        
        # This is a placeholder view
        return render(request, 'online_exam/results_placeholder.html', {
            'school_slug': school_slug,
            'exam_id': exam_id,
            'message': 'Exam results would be shown here.'
        })


class GradeExamAttemptView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Grade an exam attempt"""
    
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        attempt_id = self.kwargs.get('attempt_id')
        
        # This is a placeholder view
        return render(request, 'online_exam/grade_placeholder.html', {
            'school_slug': school_slug,
            'attempt_id': attempt_id,
            'message': 'Grading interface would be shown here.'
        })


class TakeExamView(LoginRequiredMixin, View):
    """Take an online exam"""
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('pk')
        
        # This is a placeholder view
        return render(request, 'online_exam/take_exam_placeholder.html', {
            'school_slug': school_slug,
            'exam_id': exam_id,
            'message': 'Exam taking interface would be shown here.'
        })


class PreviewExamView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Preview an exam"""
    
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('pk')
        
        # Get the exam with related data
        exam = get_object_or_404(
            OnlineExam.objects.select_related('subject', 'class_ref', 'section')
                            .prefetch_related('questions__choices'),
            pk=exam_id
        )
        
        # Get questions with their choices
        questions = exam.questions.all().order_by('order')
        
        # Calculate total marks if not set
        if not exam.total_marks:
            exam.total_marks = sum(question.marks for question in questions)
        
        context = {
            'school_slug': school_slug,
            'exam': exam,
            'questions': questions,
            'question_count': questions.count(),
            'total_marks': exam.total_marks,
            'duration_hours': exam.duration_minutes // 60,
            'duration_minutes': exam.duration_minutes % 60,
        }
        
        return render(request, 'online_exam/preview_placeholder.html', context)


class ToggleExamStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Toggle exam active status"""
    
    def test_func(self):
        exam_id = self.kwargs.get('pk')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        return self.request.user == exam.created_by or self.request.user.is_school_admin
    
    def post(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('pk')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        
        # Toggle the is_published status instead of is_active
        exam.is_published = not exam.is_published
        
        # If publishing the exam, ensure the status is set correctly
        if exam.is_published and exam.status == 'draft':
            exam.status = 'published' if timezone.now() < exam.start_time else 'in_progress'
        
        exam.save()
        
        status = 'published' if exam.is_published else 'unpublished'
        messages.success(request, _(f'Exam {status} successfully'))
        
        return redirect('online_exam:detail', school_slug=school_slug, pk=exam_id)


class ManageQuestionsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Manage exam questions"""
    
    def test_func(self):
        exam_id = self.kwargs.get('exam_id')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        return self.request.user == exam.created_by or self.request.user.is_school_admin
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('exam_id')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        
        # This is a placeholder view
        return render(request, 'online_exam/manage_questions_placeholder.html', {
            'school_slug': school_slug,
            'exam_id': exam_id,
            'exam': exam,
            'message': 'Question management interface would be shown here.'
        })


class AddQuestionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Add question to exam"""
    
    def test_func(self):
        exam_id = self.kwargs.get('exam_id')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        return self.request.user == exam.created_by or self.request.user.is_school_admin
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('exam_id')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        
        # This is a placeholder view
        return render(request, 'online_exam/add_question_placeholder.html', {
            'school_slug': school_slug,
            'exam_id': exam_id,
            'exam': exam,
            'message': 'Add question form would be shown here.'
        })


class EditQuestionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Edit exam question"""
    
    def test_func(self):
        exam_id = self.kwargs.get('exam_id')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        return self.request.user == exam.created_by or self.request.user.is_school_admin
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('exam_id')
        question_id = self.kwargs.get('question_id')
        
        # This is a placeholder view
        return render(request, 'online_exam/edit_question_placeholder.html', {
            'school_slug': school_slug,
            'exam_id': exam_id,
            'question_id': question_id,
            'message': 'Edit question form would be shown here.'
        })


class DeleteQuestionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Delete exam question"""
    
    def test_func(self):
        exam_id = self.kwargs.get('exam_id')
        exam = get_object_or_404(OnlineExam, pk=exam_id)
        return self.request.user == exam.created_by or self.request.user.is_school_admin
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        exam_id = self.kwargs.get('exam_id')
        question_id = self.kwargs.get('question_id')
        
        # This is a placeholder view
        return render(request, 'online_exam/delete_question_placeholder.html', {
            'school_slug': school_slug,
            'exam_id': exam_id,
            'question_id': question_id,
            'message': 'Confirm delete question would be shown here.'
        })
