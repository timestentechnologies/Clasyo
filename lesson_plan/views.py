from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import gettext as _
from core.utils import get_current_school

import html
import re
from django.utils.html import strip_tags

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT

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
        school = get_current_school(self.request)
        
        # Dashboard card counts
        if user.is_school_admin:
            # Admin sees all data
            lp_qs = LessonPlan.objects.all()
            if school:
                lp_qs = lp_qs.filter(school=school)
            context['total_lesson_plans'] = lp_qs.count()
            context['my_lesson_plans'] = lp_qs.filter(created_by=user).count()
            subj_qs = Subject.objects.filter(is_active=True)
            if school:
                subj_qs = subj_qs.filter(school=school)
            context['total_subjects'] = subj_qs.count()
            
            # Today's plans (all approved lessons for today)
            today = timezone.now().date()
            today_qs = LessonPlan.objects.filter(planned_date=today, status='approved')
            if school:
                today_qs = today_qs.filter(school=school)
            context['todays_plans'] = today_qs.count()
        else:
            # Teacher sees their data
            teacher_qs = LessonPlan.objects.filter(Q(created_by=user) | Q(section__class_teacher=user)).distinct()
            if school:
                teacher_qs = teacher_qs.filter(school=school)
            context['total_lesson_plans'] = teacher_qs.count()
            context['my_lesson_plans'] = teacher_qs.filter(created_by=user).count()
            
            # Subjects they teach
            subj_qs = Subject.objects.filter(
                subject_assignments__teacher=user,
                is_active=True
            ).distinct().count()
            if school:
                subj_qs = Subject.objects.filter(
                    subject_assignments__teacher=user,
                    is_active=True,
                    school=school
                ).distinct().count()
            context['total_subjects'] = subj_qs
            
            # Today's plans (their approved lessons for today)
            today = timezone.now().date()
            today_qs = LessonPlan.objects.filter(
                planned_date=today,
                status='approved'
            ).filter(
                Q(created_by=user) | Q(section__class_teacher=user)
            ).distinct()
            if school:
                today_qs = today_qs.filter(school=school)
            context['todays_plans'] = today_qs.count()
            today = timezone.now().date()
            todays_qs = LessonPlan.objects.filter(
                Q(created_by=user) | Q(section__class_teacher=user),
                planned_date=today,
                status='approved'
            ).distinct()
            if school:
                todays_qs = todays_qs.filter(
                    Q(class_ref__school=school) |
                    Q(section__class_name__school=school) |
                    Q(subject__school=school)
                ).distinct()
            context['todays_plans'] = todays_qs.count()
        
        # Recent lesson plans (created by user or for classes taught by user)
        if user.is_teacher:
            # For teachers, show their created lesson plans and those for their classes
            recent_qs = LessonPlan.objects.filter(
                Q(created_by=user) | 
                Q(section__class_teacher=user)
            ).distinct()
            if school:
                recent_qs = recent_qs.filter(school=school)
            context['recent_lesson_plans'] = recent_qs.order_by('-created_at')[:5]
        else:
            # For admins, show all recent lesson plans
            admin_recent_qs = LessonPlan.objects.all()
            if school:
                admin_recent_qs = admin_recent_qs.filter(school=school)
            context['recent_lesson_plans'] = admin_recent_qs.order_by('-created_at')[:5]
        
        # Draft lesson plans
        drafts_qs = LessonPlan.objects.filter(created_by=user, status='draft')
        if school:
            drafts_qs = drafts_qs.filter(school=school)
        context['draft_lesson_plans'] = drafts_qs.order_by('-created_at')
        
        # Pending review (for admins/department heads)
        pending_qs = LessonPlan.objects.filter(status='review')
        if school:
            pending_qs = pending_qs.filter(school=school)
        context['pending_review'] = pending_qs.order_by('-created_at')
        
        # Upcoming lesson plans (planned within the next 7 days)
        today = timezone.now().date()
        next_week = today + timezone.timedelta(days=7)
        upcoming_qs = LessonPlan.objects.filter(
            Q(created_by=user) | Q(section__class_teacher=user),
            planned_date__gte=today,
            planned_date__lte=next_week,
            status='approved'
        ).distinct()
        if school:
            upcoming_qs = upcoming_qs.filter(school=school)
        context['upcoming_lessons'] = upcoming_qs.order_by('planned_date')
        
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
        school = get_current_school(self.request)
        if school:
            queryset = queryset.filter(school=school)
        
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
        school = get_current_school(self.request)
        classes_qs = Class.objects.filter(is_active=True)
        subjects_qs = Subject.objects.filter(is_active=True)
        if school:
            classes_qs = classes_qs.filter(school=school)
            subjects_qs = subjects_qs.filter(school=school)
        context['classes'] = classes_qs
        context['subjects'] = subjects_qs
        context['status_choices'] = LessonPlan.STATUS_CHOICES
        return context


class LessonPlanCreateView(LoginRequiredMixin, CreateView):
    """Create a new lesson plan"""
    model = LessonPlan
    form_class = LessonPlanForm
    template_name = 'lesson_plan/lesson_plan_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        school = get_current_school(self.request)
        
        # Filter academic years to only active ones
        ay_qs = AcademicYear.objects.filter(is_active=True)
        if school:
            ay_qs = ay_qs.filter(school=school)
        form.fields['academic_year'].queryset = ay_qs
        
        # Add appropriate classes
        class_qs = Class.objects.filter(is_active=True)
        if school:
            class_qs = class_qs.filter(school=school)
        form.fields['class_ref'].queryset = class_qs
        
        # Filter sections based on selected class (to be handled via AJAX)
        if 'class_ref' in self.request.GET:
            class_id = self.request.GET['class_ref']
            form.fields['section'].queryset = Section.objects.filter(class_name_id=class_id)
        else:
            form.fields['section'].queryset = Section.objects.none()
            
        # If teacher, pre-select their subjects
        user = self.request.user
        if user.is_teacher:
            subj_qs = Subject.objects.filter(
                subject_assignments__teacher=user,
                is_active=True
            ).distinct()
            if school:
                subj_qs = subj_qs.filter(school=school)
            form.fields['subject'].queryset = subj_qs
        else:
            subj_qs = Subject.objects.filter(is_active=True)
            if school:
                subj_qs = subj_qs.filter(school=school)
            form.fields['subject'].queryset = subj_qs
            
        # Templates - check if field exists
        if 'template' in form.fields:
            tmpl_qs = LessonPlanTemplate.objects.filter(is_active=True)
            if school:
                tmpl_qs = tmpl_qs.filter(school=school)
            form.fields['template'].queryset = tmpl_qs
        
        return form
    
    def form_valid(self, form):
        context = self.get_context_data()
        resource_formset = context['resource_formset']
        form.instance.created_by = self.request.user
        form.instance.school = get_current_school(self.request)
        
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
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = LessonPlan.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
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
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = LessonPlan.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
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
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = LessonPlan.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
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
        
        # Create the PDF HTTP response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{lesson_plan.title}.pdf"'

        # Build a simple, clean PDF using ReportLab
        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            leftMargin=42,
            rightMargin=42,
            topMargin=42,
            bottomMargin=42,
        )
        elements = []
        styles = getSampleStyleSheet()

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
        brand_accent = colors.HexColor('#4DD0E1')
        text_main = colors.HexColor('#111827')
        text_muted = colors.HexColor('#6b7280')
        border_soft = colors.HexColor('#e5e7eb')
        card_soft = colors.HexColor('#f9fafb')

        normal_style = ParagraphStyle(
            'LessonPlanNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=text_main,
        )
        section_heading_style = ParagraphStyle(
            'LessonPlanSectionHeading',
            parent=styles['Normal'],
            fontSize=11,
            leading=13,
            textColor=brand_primary,
            fontName='Helvetica-Bold',
        )
        meta_label_style = ParagraphStyle(
            'LessonPlanMetaLabel',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=text_muted,
            fontName='Helvetica-Bold',
        )
        meta_value_style = ParagraphStyle(
            'LessonPlanMetaValue',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=text_main,
        )
        header_left_style = ParagraphStyle(
            'LessonPlanHeaderLeft',
            parent=styles['Normal'],
            fontSize=12,
            leading=14,
            textColor=colors.white,
        )
        header_right_style = ParagraphStyle(
            'LessonPlanHeaderRight',
            parent=styles['Normal'],
            fontSize=16,
            leading=18,
            textColor=colors.white,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold',
        )

        current_school = get_current_school(request)
        school_name = ''
        if getattr(lesson_plan, 'school', None) and getattr(lesson_plan.school, 'name', ''):
            school_name = lesson_plan.school.name
        elif current_school and getattr(current_school, 'name', ''):
            school_name = current_school.name
        else:
            school_name = 'SchoolSaaS'

        planned_date_value = getattr(lesson_plan, 'planned_date', None)
        planned_date_text = ''
        if planned_date_value:
            planned_date_text = planned_date_value.strftime('%b %d, %Y') if hasattr(planned_date_value, 'strftime') else str(planned_date_value)

        title_text = html.escape(getattr(lesson_plan, 'title', '') or '')
        header_table = Table(
            [[
                Paragraph(
                    f"<b>{html.escape(school_name)}</b><br/><font size='9'>Lesson Plan: {title_text}</font>",
                    header_left_style,
                ),
                Paragraph(
                    f"LESSON PLAN<br/><font size='9'>Planned: {html.escape(planned_date_text) or '-'} </font>",
                    header_right_style,
                ),
            ]],
            colWidths=[doc.width * 0.62, doc.width * 0.38],
        )
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), brand_primary),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 16))

        subject_text = getattr(getattr(lesson_plan, 'subject', None), 'name', '') or ''
        class_text = getattr(getattr(lesson_plan, 'class_ref', None), 'name', '') or ''
        section_value = getattr(lesson_plan, 'section', None)
        section_text = str(section_value) if section_value else ''
        duration_value = getattr(lesson_plan, 'duration_minutes', None)
        duration_text = f"{duration_value} minutes" if duration_value else ''
        status_text = lesson_plan.get_status_display() if hasattr(lesson_plan, 'get_status_display') else (getattr(lesson_plan, 'status', '') or '')

        teacher_text = ''
        if getattr(lesson_plan, 'created_by', None):
            teacher_text = lesson_plan.created_by.get_full_name() or getattr(lesson_plan.created_by, 'username', '')

        academic_year_value = getattr(lesson_plan, 'academic_year', None)
        academic_year_text = str(academic_year_value) if academic_year_value else ''

        def display_value(value):
            return value if value else '-'

        meta_table_data = [
            [
                Paragraph('Subject', meta_label_style),
                Paragraph(html.escape(display_value(subject_text)), meta_value_style),
                Paragraph('Class', meta_label_style),
                Paragraph(html.escape(display_value(class_text)), meta_value_style),
            ],
            [
                Paragraph('Section', meta_label_style),
                Paragraph(html.escape(display_value(section_text)), meta_value_style),
                Paragraph('Planned Date', meta_label_style),
                Paragraph(html.escape(display_value(planned_date_text)), meta_value_style),
            ],
            [
                Paragraph('Duration', meta_label_style),
                Paragraph(html.escape(display_value(duration_text)), meta_value_style),
                Paragraph('Status', meta_label_style),
                Paragraph(html.escape(display_value(status_text)), meta_value_style),
            ],
            [
                Paragraph('Teacher', meta_label_style),
                Paragraph(html.escape(display_value(teacher_text)), meta_value_style),
                Paragraph('Academic Year', meta_label_style),
                Paragraph(html.escape(display_value(academic_year_text)), meta_value_style),
            ],
        ]
        meta_table = Table(
            meta_table_data,
            colWidths=[doc.width * 0.18, doc.width * 0.32, doc.width * 0.18, doc.width * 0.32],
        )
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), card_soft),
            ('BOX', (0, 0), (-1, -1), 1, border_soft),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_soft),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(RoundedCard([meta_table], width=doc.width, padding=12, bg_color=colors.white, border_color=border_soft, radius=12))
        elements.append(Spacer(1, 18))

        def sanitize_rich_text(value):
            if value is None:
                return ''

            raw = str(value)

            # Preserve basic structure before stripping tags
            raw = re.sub(r'(?i)<\s*br\s*/?\s*>', '\n', raw)
            raw = re.sub(r'(?i)</\s*p\s*>', '\n', raw)
            raw = re.sub(r'(?i)</\s*div\s*>', '\n', raw)
            raw = re.sub(r'(?i)</\s*li\s*>', '\n', raw)

            # Strip all tags (removes spans/styles from CKEditor)
            text = strip_tags(raw)
            text = html.unescape(text)

            # Normalize whitespace/blank lines
            lines = [ln.strip() for ln in text.splitlines()]
            text = '\n'.join([ln for ln in lines if ln != ''])
            return text

        # Helper to add a section with heading and body
        def add_section(heading, body):
            cleaned = sanitize_rich_text(body)
            if not cleaned:
                return
            section_flow = []
            section_flow.append(Paragraph(heading, section_heading_style))
            section_flow.append(Spacer(1, 6))

            # Escape special chars then preserve line breaks
            safe_body = html.escape(cleaned).replace("\n", "<br/>")
            section_flow.append(Paragraph(safe_body, normal_style))

            elements.append(RoundedCard(section_flow, width=doc.width, padding=12, bg_color=card_soft, border_color=border_soft, radius=12))
            elements.append(Spacer(1, 12))

        add_section("Learning Objectives", lesson_plan.learning_objectives)
        add_section("Materials & Resources", lesson_plan.materials_resources)
        add_section("Introduction", lesson_plan.introduction)
        add_section("Main Content", lesson_plan.main_content)
        add_section("Activities", lesson_plan.activities)
        add_section("Assessment", lesson_plan.assessment)
        add_section("Differentiation Strategies", lesson_plan.differentiation)
        add_section("Conclusion", lesson_plan.conclusion)
        add_section("Homework Assignment", lesson_plan.homework)
        add_section("Additional Notes", lesson_plan.notes)

        # Build and return the PDF
        site_url = "https://clasyo.timestentechnologies.co.ke/"

        def add_footer(canvas, doc_ref):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(text_muted)
            canvas.drawCentredString(doc_ref.leftMargin + (doc_ref.width / 2.0), 24, f"Website: {site_url}")
            canvas.restoreState()

        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
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
        
        school = get_current_school(self.request)
        if school:
            queryset = queryset.filter(school=school)
        
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
        form.instance.school = getattr(self.class_obj, 'school', None)
        
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
