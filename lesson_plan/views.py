from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import gettext as _

from .models import LessonPlanTemplate, LessonPlan, LessonPlanStandard, LessonPlanFeedback, LessonPlanResource
from .forms import LessonPlanForm, LessonPlanResourceFormSet
from academics.models import Class, Section, Subject
from core.models import AcademicYear


class LessonPlanDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for lesson plans"""
    template_name = 'lesson_plan/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        school_slug = self.kwargs.get('school_slug', '')
        
        # Dashboard card counts
        if user.is_school_admin:
            # Admin sees all data
            context['total_lesson_plans'] = LessonPlan.objects.count()
            context['my_lesson_plans'] = LessonPlan.objects.filter(created_by=user).count()
            context['total_subjects'] = Subject.objects.filter(is_active=True).count()
            
            # Today's plans (all approved lessons for today)
            today = timezone.now().date()
            context['todays_plans'] = LessonPlan.objects.filter(
                planned_date=today,
                status='approved'
            ).count()
        else:
            # Teacher sees their data
            context['total_lesson_plans'] = LessonPlan.objects.filter(
                Q(created_by=user) | Q(section__class_teacher=user)
            ).distinct().count()
            context['my_lesson_plans'] = LessonPlan.objects.filter(created_by=user).count()
            
            # Subjects they teach
            context['total_subjects'] = Subject.objects.filter(
                subject_assignments__teacher=user,
                is_active=True
            ).distinct().count()
            
            # Today's plans (their approved lessons for today)
            today = timezone.now().date()
            context['todays_plans'] = LessonPlan.objects.filter(
                Q(created_by=user) | Q(section__class_teacher=user),
                planned_date=today,
                status='approved'
            ).distinct().count()
        
        # Recent lesson plans (created by user or for classes taught by user)
        if user.is_teacher:
            # For teachers, show their created lesson plans and those for their classes
            context['recent_lesson_plans'] = LessonPlan.objects.filter(
                Q(created_by=user) | 
                Q(section__class_teacher=user)
            ).distinct().order_by('-created_at')[:5]
        else:
            # For admins, show all recent lesson plans
            context['recent_lesson_plans'] = LessonPlan.objects.all().order_by('-created_at')[:5]
        
        # Draft lesson plans
        context['draft_lesson_plans'] = LessonPlan.objects.filter(
            created_by=user,
            status='draft'
        ).order_by('-created_at')
        
        # Pending review (for admins/department heads)
        context['pending_review'] = LessonPlan.objects.filter(
            status='review'
        ).order_by('-created_at')
        
        # Upcoming lesson plans (planned within the next 7 days)
        today = timezone.now().date()
        next_week = today + timezone.timedelta(days=7)
        context['upcoming_lessons'] = LessonPlan.objects.filter(
            Q(created_by=user) | Q(section__class_teacher=user),
            planned_date__gte=today,
            planned_date__lte=next_week,
            status='approved'
        ).order_by('planned_date')
        
        context['school_slug'] = school_slug
        return context


class LessonPlanListView(LoginRequiredMixin, ListView):
    """List all lesson plans"""
    model = LessonPlan
    template_name = 'lesson_plan/lesson_plan_list.html'
    context_object_name = 'lesson_plans'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = LessonPlan.objects.all().select_related('class_ref', 'subject', 'created_by')
        
        # Filter by user if not admin
        user = self.request.user
        if not user.is_school_admin:
            queryset = queryset.filter(
                Q(created_by=user) | Q(section__class_teacher=user)
            ).distinct()
        
        # Apply filters from query params
        class_id = self.request.GET.get('class_id')
        if class_id:
            queryset = queryset.filter(class_ref_id=class_id)
            
        subject_id = self.request.GET.get('subject_id')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
            
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(learning_objectives__icontains=search)
            )
        
        return queryset.order_by('-planned_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['classes'] = Class.objects.filter(is_active=True)
        context['subjects'] = Subject.objects.filter(is_active=True)
        context['status_choices'] = LessonPlan.STATUS_CHOICES
        return context


class LessonPlanCreateView(LoginRequiredMixin, CreateView):
    """Create a new lesson plan"""
    model = LessonPlan
    form_class = LessonPlanForm
    template_name = 'lesson_plan/lesson_plan_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filter academic years to only active ones
        form.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
        
        # Add appropriate classes
        form.fields['class_ref'].queryset = Class.objects.filter(is_active=True)
        
        # Filter sections based on selected class (to be handled via AJAX)
        if 'class_ref' in self.request.GET:
            class_id = self.request.GET['class_ref']
            form.fields['section'].queryset = Section.objects.filter(class_name_id=class_id)
        else:
            form.fields['section'].queryset = Section.objects.none()
            
        # If teacher, pre-select their subjects
        user = self.request.user
        if user.is_teacher:
            form.fields['subject'].queryset = Subject.objects.filter(
                subject_assignments__teacher=user,
                is_active=True
            ).distinct()
        else:
            form.fields['subject'].queryset = Subject.objects.filter(is_active=True)
            
        # Templates - check if field exists
        if 'template' in form.fields:
            form.fields['template'].queryset = LessonPlanTemplate.objects.filter(is_active=True)
        
        return form
    
    def form_valid(self, form):
        context = self.get_context_data()
        resource_formset = context['resource_formset']
        form.instance.created_by = self.request.user
        
        if resource_formset.is_valid():
            self.object = form.save()
            resource_formset.instance = self.object
            resource_instances = resource_formset.save(commit=False)
            
            # Set created_by for each resource
            for resource in resource_instances:
                resource.created_by = self.request.user
                resource.save()
                
            # Delete the marked for deletion
            for obj in resource_formset.deleted_objects:
                obj.delete()
                
            messages.success(self.request, _('Lesson plan created successfully'))
            return super(LessonPlanCreateView, self).form_valid(form)
        else:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('lesson_plan:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.pk
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create Lesson Plan')
        
        if self.request.POST:
            context['resource_formset'] = LessonPlanResourceFormSet(self.request.POST, self.request.FILES)
        else:
            context['resource_formset'] = LessonPlanResourceFormSet()
        
        return context


class LessonPlanDetailView(LoginRequiredMixin, DetailView):
    """View lesson plan details"""
    model = LessonPlan
    template_name = 'lesson_plan/lesson_plan_detail.html'
    context_object_name = 'lesson_plan'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson_plan = self.object
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Get associated resources
        context['resources'] = lesson_plan.resources.all()
        
        # Get feedback
        context['feedback'] = lesson_plan.feedback.all().order_by('-created_at')
        
        # Check if user can edit
        user = self.request.user
        can_edit = (user == lesson_plan.created_by or user.is_school_admin)
        context['can_edit'] = can_edit and lesson_plan.status in ['draft', 'rejected']
        
        # Check if user can review/approve
        context['can_review'] = user.is_school_admin or user.is_teacher
        
        return context


class LessonPlanUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update a lesson plan"""
    model = LessonPlan
    form_class = LessonPlanForm
    template_name = 'lesson_plan/lesson_plan_form.html'
    
    def test_func(self):
        # Only creator or admin can edit, and only if in draft or rejected status
        lesson_plan = self.get_object()
        user = self.request.user
        
        is_creator_or_admin = (user == lesson_plan.created_by or user.is_school_admin)
        is_editable_status = lesson_plan.status in ['draft', 'rejected']
        
        return is_creator_or_admin and is_editable_status
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filter academic years to only active ones
        form.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
        
        # Add appropriate classes
        form.fields['class_ref'].queryset = Class.objects.filter(is_active=True)
        
        # Filter sections based on selected class
        class_id = self.object.class_ref_id
        form.fields['section'].queryset = Section.objects.filter(class_name_id=class_id)
            
        # If teacher, pre-select their subjects
        user = self.request.user
        if user.is_teacher and not user.is_school_admin:
            form.fields['subject'].queryset = Subject.objects.filter(
                subject_assignments__teacher=user,
                is_active=True
            ).distinct()
        else:
            form.fields['subject'].queryset = Subject.objects.filter(is_active=True)
            
        # Templates - check if field exists
        if 'template' in form.fields:
            form.fields['template'].queryset = LessonPlanTemplate.objects.filter(is_active=True)
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Lesson Plan')
        
        if self.request.POST:
            context['resource_formset'] = LessonPlanResourceFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['resource_formset'] = LessonPlanResourceFormSet(instance=self.object)
        
        return context
        
    def form_valid(self, form):
        context = self.get_context_data()
        resource_formset = context['resource_formset']
        
        # Always save the main lesson plan first
        self.object = form.save()
        
        # Handle resources if formset is valid
        if resource_formset.is_valid():
            resource_formset.instance = self.object
            resource_instances = resource_formset.save(commit=False)
            
            # Set created_by for each new resource
            for resource in resource_instances:
                if not resource.created_by:
                    resource.created_by = self.request.user
                resource.save()
                
            # Delete the marked for deletion
            for obj in resource_formset.deleted_objects:
                obj.delete()
        else:
            # If formset is invalid, still save the main lesson plan but log the formset errors
            print(f"Resource formset errors: {resource_formset.errors}")
                
        messages.success(self.request, _('Lesson plan updated successfully'))
        return super(LessonPlanUpdateView, self).form_valid(form)
    
    def get_success_url(self):
        return reverse('lesson_plan:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.pk
        })


class LessonPlanDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a lesson plan"""
    model = LessonPlan
    template_name = 'lesson_plan/confirm_delete.html'
    context_object_name = 'object'
    
    def test_func(self):
        # Only creator or admin can delete
        lesson_plan = self.get_object()
        user = self.request.user
        return user == lesson_plan.created_by or user.is_school_admin
    
    def get_success_url(self):
        messages.success(self.request, _('Lesson plan deleted successfully'))
        return reverse('lesson_plan:dashboard', kwargs={
            'school_slug': self.kwargs.get('school_slug', '')
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class LessonPlanExportPDF(LoginRequiredMixin, DetailView):
    """Export lesson plan as PDF"""
    model = LessonPlan
    
    def get(self, request, *args, **kwargs):
        lesson_plan = self.get_object()
        
        # Create the PDF response (placeholder - would use a PDF library in production)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{lesson_plan.title}.pdf"'
        
        # Here you would use a PDF library like ReportLab, WeasyPrint, or xhtml2pdf
        # For demonstration purposes, we'll return a simple PDF stub
        pdf_content = f"""
        Lesson Plan: {lesson_plan.title}
        Subject: {lesson_plan.subject.name}
        Class: {lesson_plan.class_ref.name}
        Date: {lesson_plan.planned_date}
        
        Learning Objectives:
        {lesson_plan.learning_objectives}
        
        Materials:
        {lesson_plan.materials_resources}
        
        Main Content:
        {lesson_plan.main_content}
        """
        
        response.write(pdf_content.encode())
        return response


class ClassLessonPlansView(LoginRequiredMixin, ListView):
    """View lesson plans for a specific class and subject"""
    model = LessonPlan
    template_name = 'lesson_plan/lesson_plan_list.html'
    context_object_name = 'lesson_plans'
    paginate_by = 10
    
    def get_queryset(self):
        class_id = self.kwargs.get('class_id')
        subject_id = self.kwargs.get('subject_id')
        
        queryset = LessonPlan.objects.filter(
            class_ref_id=class_id,
            subject_id=subject_id
        ).select_related('class_ref', 'subject', 'created_by')
        
        return queryset.order_by('-planned_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['classes'] = Class.objects.filter(is_active=True)
        context['subjects'] = Subject.objects.filter(is_active=True)
        context['status_choices'] = LessonPlan.STATUS_CHOICES
        
        # Get class and subject for header
        class_id = self.kwargs.get('class_id')
        subject_id = self.kwargs.get('subject_id')
        context['current_class'] = get_object_or_404(Class, pk=class_id)
        context['current_subject'] = get_object_or_404(Subject, pk=subject_id)
        
        return context


class LessonPlanCreateForClassView(LoginRequiredMixin, CreateView):
    """Create a new lesson plan for a specific class and subject"""
    model = LessonPlan
    form_class = LessonPlanForm
    template_name = 'lesson_plan/lesson_plan_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filter academic years to only active ones
        form.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
        
        # Pre-fill class and subject
        class_id = self.kwargs.get('class_id')
        self.class_obj = get_object_or_404(Class, pk=class_id)
        
        subject_id = self.kwargs.get('subject_id')
        self.subject_obj = get_object_or_404(Subject, pk=subject_id)
        
        # Filter sections based on selected class
        form.fields['section'].queryset = Section.objects.filter(class_name_id=class_id)
            
        # Templates - check if field exists
        if 'template' in form.fields:
            form.fields['template'].queryset = LessonPlanTemplate.objects.filter(is_active=True)
        
        return form
    
    def form_valid(self, form):
        context = self.get_context_data()
        resource_formset = context['resource_formset']
        form.instance.created_by = self.request.user
        form.instance.class_ref = self.class_obj
        form.instance.subject = self.subject_obj
        
        if resource_formset.is_valid():
            self.object = form.save()
            resource_formset.instance = self.object
            resource_instances = resource_formset.save(commit=False)
            
            # Set created_by for each resource
            for resource in resource_instances:
                resource.created_by = self.request.user
                resource.save()
                
            # Delete the marked for deletion
            for obj in resource_formset.deleted_objects:
                obj.delete()
                
            messages.success(self.request, _('Lesson plan created successfully'))
            return super(LessonPlanCreateForClassView, self).form_valid(form)
        else:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('lesson_plan:detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.pk
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create Lesson Plan')
        context['class_obj'] = self.class_obj
        context['subject_obj'] = self.subject_obj
        
        if self.request.POST:
            context['resource_formset'] = LessonPlanResourceFormSet(self.request.POST, self.request.FILES)
        else:
            context['resource_formset'] = LessonPlanResourceFormSet()
            
        return context
