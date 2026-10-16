import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from accounts.models import User
from .models import Department, Designation, Teacher, Staff
from core.utils import generate_email, get_school_slug_from_request, get_current_school


def _save_teacher_inline_assignments(teacher, school, request):
    from core.models import AcademicYear
    from academics.models import AssignedSubject, Section

    active_year = AcademicYear.objects.filter(is_active=True)
    if school:
        active_year = active_year.filter(school=school)
    active_year = active_year.first()
    if not active_year and school:
        active_year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()

    teaching_classes = request.POST.getlist('teaching_class[]')
    teaching_sections = request.POST.getlist('teaching_section[]')
    teaching_subjects = request.POST.getlist('teaching_subject[]')

    desired_tuples = []
    for i in range(len(teaching_subjects)):
        if i < len(teaching_classes) and str(teaching_classes[i]).isdigit() and str(teaching_subjects[i]).isdigit():
            cid = int(teaching_classes[i])
            sid = int(teaching_sections[i]) if (i < len(teaching_sections) and str(teaching_sections[i]).isdigit()) else None
            subid = int(teaching_subjects[i])
            desired_tuples.append((cid, sid, subid))

    if active_year:
        assigned_qs = AssignedSubject.objects.filter(is_active=True, academic_year=active_year)
        if school:
            assigned_qs = assigned_qs.filter(class_name__school=school, subject__school=school)

        # Unassign any subjects previously taught by this teacher that are not in desired_tuples
        for ca in assigned_qs.filter(teacher=teacher):
            matched = (
                (ca.class_name_id, ca.section_id, ca.subject_id) in desired_tuples or
                (ca.section_id is not None and (ca.class_name_id, None, ca.subject_id) in desired_tuples)
            )
            if not matched:
                ca.teacher = None
                ca.save(update_fields=['teacher'])

        # Assign or create desired assignments
        for cid, sid, subid in desired_tuples:
            if sid is not None:
                asub = assigned_qs.filter(class_name_id=cid, section_id=sid, subject_id=subid).first()
                if asub:
                    if asub.teacher_id != teacher.id:
                        asub.teacher = teacher
                        asub.save(update_fields=['teacher'])
                else:
                    AssignedSubject.objects.create(
                        class_name_id=cid,
                        section_id=sid,
                        subject_id=subid,
                        teacher=teacher,
                        academic_year=active_year,
                        is_active=True
                    )
            else:
                # All sections for this class & subject
                all_subs = list(assigned_qs.filter(class_name_id=cid, subject_id=subid))
                if all_subs:
                    for asub in all_subs:
                        if asub.teacher_id != teacher.id:
                            asub.teacher = teacher
                            asub.save(update_fields=['teacher'])
                else:
                    AssignedSubject.objects.create(
                        class_name_id=cid,
                        section_id=None,
                        subject_id=subid,
                        teacher=teacher,
                        academic_year=active_year,
                        is_active=True
                    )



class TeacherListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'human_resource/teacher_list.html'
    context_object_name = 'teachers'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        if not school:
            if hasattr(self.request.user, 'school') and self.request.user.school:
                school = self.request.user.school
        
        if not school:
            if not self.request.user.is_superuser and getattr(self.request.user, 'role', '') != 'superadmin':
                return User.objects.none()
            return User.objects.filter(role='teacher').select_related('department', 'designation').prefetch_related('assigned_subjects', 'class_sections')
            
        return User.objects.filter(role='teacher', school=school).select_related('department', 'designation').prefetch_related('assigned_subjects', 'class_sections')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        departments_qs = Department.objects.filter(is_active=True)
        designations_qs = Designation.objects.filter(is_active=True)
        if school:
            departments_qs = departments_qs.filter(school=school)
            designations_qs = designations_qs.filter(school=school)
        context['departments'] = departments_qs
        context['designations'] = designations_qs

        # Classes, subjects and sections for dynamic line rows
        from core.models import AcademicYear
        from academics.models import Class, Section, Subject, AssignedSubject

        active_year = AcademicYear.objects.filter(is_active=True)
        if school:
            active_year = active_year.filter(school=school)
        active_year = active_year.first()
        if not active_year and school:
            active_year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()
        context['active_year'] = active_year
        context['has_active_year'] = bool(active_year)

        classes_qs = Class.objects.filter(is_active=True)
        subjects_qs = Subject.objects.filter(is_active=True)
        if school:
            classes_qs = classes_qs.filter(school=school)
            subjects_qs = subjects_qs.filter(school=school)

        classes_qs = classes_qs.prefetch_related('sections').order_by('order', 'name')
        subjects_qs = subjects_qs.order_by('name')

        assigned_qs = AssignedSubject.objects.filter(is_active=True)
        if active_year:
            assigned_qs = assigned_qs.filter(academic_year=active_year)
        if school:
            assigned_qs = assigned_qs.filter(
                class_name__school=school,
                subject__school=school,
            )
        assigned_qs = assigned_qs.select_related('class_name', 'section', 'subject', 'teacher')

        # Map class_id -> dict of subject_id -> {id, name, code, all_sections, section_ids}
        class_subjects_dict = {}
        for asub in assigned_qs:
            cid = asub.class_name_id
            sub_map = class_subjects_dict.setdefault(cid, {})
            sub_info = sub_map.setdefault(asub.subject_id, {
                'id': asub.subject_id,
                'name': asub.subject.name,
                'code': asub.subject.code,
                'all_sections': False,
                'section_ids': []
            })
            if asub.section_id:
                if asub.section_id not in sub_info['section_ids']:
                    sub_info['section_ids'].append(asub.section_id)
            else:
                sub_info['all_sections'] = True

        # Fallback for classes that don't have active year assignments yet
        classes_without_subs = [c.id for c in classes_qs if c.id not in class_subjects_dict]
        if classes_without_subs:
            fallback_qs = AssignedSubject.objects.filter(
                class_name_id__in=classes_without_subs,
                is_active=True
            )
            if school:
                fallback_qs = fallback_qs.filter(class_name__school=school, subject__school=school)
            fallback_qs = fallback_qs.select_related('subject')
            for asub in fallback_qs:
                cid = asub.class_name_id
                sub_map = class_subjects_dict.setdefault(cid, {})
                sub_info = sub_map.setdefault(asub.subject_id, {
                    'id': asub.subject_id,
                    'name': asub.subject.name,
                    'code': asub.subject.code,
                    'all_sections': False,
                    'section_ids': []
                })
                if asub.section_id:
                    if asub.section_id not in sub_info['section_ids']:
                        sub_info['section_ids'].append(asub.section_id)
                else:
                    sub_info['all_sections'] = True

        classes_meta = []
        for c in classes_qs:
            c_sections = [{'id': s.id, 'name': s.name} for s in c.sections.filter(is_active=True)]
            assigned_subs = list(class_subjects_dict.get(c.id, {}).values())
            classes_meta.append({
                'id': c.id,
                'name': c.name,
                'sections': c_sections,
                'subjects': assigned_subs
            })

        all_subjects_meta = [{'id': s.id, 'name': s.name, 'code': s.code} for s in subjects_qs]
        context['classes_meta_json'] = json.dumps(classes_meta)
        context['all_subjects_meta_json'] = json.dumps(all_subjects_meta)

        # Precompute teacher teaching assignments
        teacher_teaching_map = {}
        if active_year:
            for asub in assigned_qs.filter(teacher__isnull=False):
                teacher_teaching_map.setdefault(asub.teacher_id, []).append({
                    'class_id': asub.class_name_id,
                    'section_id': asub.section_id or '',
                    'subject_id': asub.subject_id
                })

        teachers_list = context.get('teachers')
        if teachers_list:
            for t in teachers_list:
                t.teaching_assignments_json = json.dumps(teacher_teaching_map.get(t.id, []))

        return context


class TeacherCreateView(LoginRequiredMixin, CreateView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip()
            
            # Auto-generate email if not provided
            if not email:
                school_slug = get_school_slug_from_request(request)
                email = generate_email(first_name, last_name, school_slug, 'teacher')
            
            teacher = User.objects.create_user(
                email=email,
                password='teacher123',
                first_name=first_name,
                last_name=last_name,
                role='teacher',
                phone=request.POST.get('phone') or request.POST.get('phone_number', ''),
                department_id=request.POST.get('department') or None,
                designation_id=request.POST.get('designation') or None,
                is_active=True
            )
            school = get_current_school(request)
            if school:
                teacher.school = school
                teacher.save(update_fields=["school"])

            # Auto-generate or use custom employee id on User for consistency
            custom_emp_id = request.POST.get('employee_id', '').strip()
            employee_id = custom_emp_id or f"TCHR-{teacher.id}"
            teacher.employee_id = employee_id
            teacher.save(update_fields=["employee_id"]) 

            # Create HR Teacher profile
            dept_id = request.POST.get('department') or None
            desig_id = request.POST.get('designation') or None
            basic_salary = Decimal(request.POST.get('basic_salary') or 0)
            allowances = Decimal(request.POST.get('allowances') or 0)
            doj_str = request.POST.get('date_of_joining')
            date_of_joining = datetime.strptime(doj_str, '%Y-%m-%d').date() if doj_str else None
            employment_type = request.POST.get('employment_type') or 'permanent'
            phone = request.POST.get('phone') or request.POST.get('phone_number', '')
            address = request.POST.get('address', '')
            is_active = str(request.POST.get('is_active', 'on')).lower() in ['1', 'true', 'on', 'yes']

            Teacher.objects.create(
                user=teacher,
                first_name=first_name,
                last_name=last_name,
                employee_id=employee_id or f"TCHR-{teacher.id}",
                department_id=dept_id,
                designation_id=desig_id,
                basic_salary=basic_salary,
                allowances=allowances,
                date_of_joining=date_of_joining or datetime.today().date(),
                employment_type=employment_type,
                phone=str(phone or ''),
                email=email,
                address=address,
                is_active=is_active,
            )

            # Save inline teacher assignments
            if request.POST.get('assignments_submitted') == '1' or 'teaching_subject[]' in request.POST or 'teaching_class[]' in request.POST:
                _save_teacher_inline_assignments(teacher, school, request)

            return JsonResponse({'success': True, 'teacher_id': teacher.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class TeacherDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'human_resource/teacher_detail.html'
    context_object_name = 'teacher'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role='teacher')
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get(self, request, *args, **kwargs):
        teacher = self.get_object()
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Include HR profile details if present
            try:
                profile = teacher.teacher_profile
            except Teacher.DoesNotExist:
                profile = None

            # Get assigned subjects and sections for this teacher
            from core.models import AcademicYear
            from academics.models import AssignedSubject, Section

            school = get_current_school(request)
            active_year = AcademicYear.objects.filter(is_active=True)
            if school:
                active_year = active_year.filter(school=school)
            active_year = active_year.first()
            if not active_year and school:
                active_year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()

            teaching_assignments = []
            if active_year:
                for a in AssignedSubject.objects.filter(
                    is_active=True, academic_year=active_year, teacher=teacher
                ):
                    teaching_assignments.append({
                        'class_id': a.class_name_id,
                        'section_id': a.section_id or '',
                        'subject_id': a.subject_id
                    })

            return JsonResponse({
                'success': True,
                'teacher': {
                    'id': teacher.id,
                    'first_name': teacher.first_name,
                    'last_name': teacher.last_name,
                    'email': teacher.email,
                    'phone': str(teacher.phone) if teacher.phone else '',
                    'department': teacher.department.name if teacher.department else '',
                    'department_id': teacher.department_id,
                    'designation': teacher.designation.name if teacher.designation else '',
                    'designation_id': teacher.designation_id,
                    'is_active': teacher.is_active,
                    'employee_id': getattr(profile, 'employee_id', ''),
                    'basic_salary': str(getattr(profile, 'basic_salary', '0')),
                    'allowances': str(getattr(profile, 'allowances', '0')),
                    'date_of_joining': getattr(profile, 'date_of_joining', None).isoformat() if getattr(profile, 'date_of_joining', None) else '',
                    'date_of_leaving': getattr(profile, 'date_of_leaving', None).isoformat() if getattr(profile, 'date_of_leaving', None) else '',
                    'exit_reason': getattr(profile, 'exit_reason', ''),
                    'exit_remarks': getattr(profile, 'exit_remarks', ''),
                    'employment_type': getattr(profile, 'employment_type', ''),
                    'address': getattr(profile, 'address', ''),
                    'teaching_assignments': teaching_assignments,
                }
            })
        
        # Return HTML template for regular requests
        return super().get(request, *args, **kwargs)


class TeacherAssignmentsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        school_slug = self.kwargs.get('school_slug', '')
        if school_slug:
            return redirect(f'/school/{school_slug}/hr/teachers/?edit={pk}')
        return redirect(f'/hr/teachers/?edit={pk}')

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class TeacherUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role='teacher')
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def post(self, request, *args, **kwargs):
        try:
            teacher = self.get_object()
            school = get_current_school(request) or getattr(teacher, 'school', None)
            if teacher.role != 'teacher':
                return JsonResponse({'success': False, 'error': 'Not a teacher'})
            
            teacher.first_name = request.POST.get('first_name')
            teacher.last_name = request.POST.get('last_name')
            teacher.email = request.POST.get('email')
            teacher.phone = request.POST.get('phone') or request.POST.get('phone_number', '')
            # Update active and department/designation on User
            teacher.is_active = str(request.POST.get('is_active', teacher.is_active)).lower() in ['1', 'true', 'on', 'yes']
            dept_val = request.POST.get('department')
            desig_val = request.POST.get('designation')
            if dept_val is not None:
                teacher.department_id = dept_val or None
            if desig_val is not None:
                teacher.designation_id = desig_val or None
            emp_id_val = request.POST.get('employee_id', '').strip()
            if emp_id_val:
                teacher.employee_id = emp_id_val

            teacher.save()

            # Sync HR Teacher profile including HR fields
            profile, _ = Teacher.objects.get_or_create(
                user=teacher,
                defaults={
                    'first_name': teacher.first_name,
                    'last_name': teacher.last_name,
                    'employee_id': f"TCHR-{teacher.id}",
                    'date_of_joining': datetime.today().date(),
                }
            )
            profile.first_name = teacher.first_name
            profile.last_name = teacher.last_name
            profile.email = teacher.email
            profile.phone = str(teacher.phone or '')
            profile.department_id = teacher.department_id
            profile.designation_id = teacher.designation_id
            if emp_id_val:
                profile.employee_id = emp_id_val
            # HR specific fields
            basic_salary = request.POST.get('basic_salary')
            allowances = request.POST.get('allowances')
            doj_str = request.POST.get('date_of_joining')
            employment_type = request.POST.get('employment_type')
            address = request.POST.get('address')
            prof_active = request.POST.get('is_active')
            if basic_salary not in (None, ''):
                profile.basic_salary = Decimal(basic_salary)
            if allowances not in (None, ''):
                profile.allowances = Decimal(allowances)
            if doj_str:
                try:
                    profile.date_of_joining = datetime.strptime(doj_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if employment_type:
                profile.employment_type = employment_type
            if address is not None:
                profile.address = address
            if prof_active is not None:
                profile.is_active = str(prof_active).lower() in ['1', 'true', 'on', 'yes']
            profile.save()

            # Save inline teacher assignments if submitted with form
            if request.POST.get('assignments_submitted') == '1' or 'teaching_subject[]' in request.POST or 'teaching_class[]' in request.POST:
                _save_teacher_inline_assignments(teacher, school, request)

            return JsonResponse({'success': True, 'message': 'Teacher updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class TeacherDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            teacher = self.get_object()
            if getattr(teacher, 'is_sample_data', False):
                return JsonResponse({'success': False, 'error': 'Sample/Demo data cannot be deleted.'})
            if teacher.role == 'teacher':
                from academics.models import ClassTeacherAssignment, Section, AssignedSubject
                
                # Soft deactivate teacher user
                teacher.is_active = False
                teacher.save(update_fields=['is_active'])
                
                # Soft deactivate HR profile if exists
                if hasattr(teacher, 'teacher_profile'):
                    profile = teacher.teacher_profile
                    profile.is_active = False
                    profile.save(update_fields=['is_active'])
                
                # Cleanly unassign active class teaching & subject assignments
                ClassTeacherAssignment.objects.filter(teacher=teacher, is_active=True).update(is_active=False)
                Section.objects.filter(class_teacher=teacher).update(class_teacher=None)
                AssignedSubject.objects.filter(teacher=teacher, is_active=True).update(is_active=False)
                Department.objects.filter(head=teacher).update(head=None)
                
                return JsonResponse({'success': True, 'message': 'Teacher deactivated successfully'})
            return JsonResponse({'success': False, 'error': 'Not a teacher'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role='teacher')
        if school:
            qs = qs.filter(school=school)
        return qs


class TeacherExitView(LoginRequiredMixin, View):
    """
    Handle teacher relieving / exit / resignation workflow.
    - Records date_of_leaving, exit_reason, exit_remarks
    - Sets is_active = False on both Teacher HR profile and User account
    - Automatically unassigns active class teacher duties, assigned subjects, and department head roles
    """
    def post(self, request, pk, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = User.objects.filter(role='teacher')
            if school:
                qs = qs.filter(school=school)
            
            teacher_user = get_object_or_404(qs, pk=pk)
            
            if getattr(teacher_user, 'is_sample_data', False):
                return JsonResponse({'success': False, 'error': 'Sample/Demo data cannot be modified.'})

            date_of_leaving_str = request.POST.get('date_of_leaving', '').strip()
            exit_reason = request.POST.get('exit_reason', 'resigned').strip()
            exit_remarks = request.POST.get('exit_remarks', '').strip()

            from django.utils.dateparse import parse_date
            date_of_leaving = parse_date(date_of_leaving_str) if date_of_leaving_str else timezone.now().date()
            if not date_of_leaving:
                date_of_leaving = timezone.now().date()

            # 1. Update or create Teacher HR Profile
            profile, _ = Teacher.objects.get_or_create(
                user=teacher_user,
                defaults={
                    'first_name': teacher_user.first_name,
                    'last_name': teacher_user.last_name,
                    'employee_id': getattr(teacher_user, 'employee_id', f"TCHR-{teacher_user.id}"),
                    'date_of_joining': timezone.now().date(),
                }
            )
            profile.is_active = False
            profile.date_of_leaving = date_of_leaving
            profile.exit_reason = exit_reason
            profile.exit_remarks = exit_remarks
            profile.save(update_fields=['is_active', 'date_of_leaving', 'exit_reason', 'exit_remarks', 'updated_at'])

            # 2. Soft deactivate User login
            teacher_user.is_active = False
            teacher_user.save(update_fields=['is_active'])

            # 3. Cleanly unassign active class teaching, subjects, and head of department
            from academics.models import ClassTeacherAssignment, Section, AssignedSubject
            ClassTeacherAssignment.objects.filter(teacher=teacher_user, is_active=True).update(is_active=False)
            Section.objects.filter(class_teacher=teacher_user).update(class_teacher=None)
            AssignedSubject.objects.filter(teacher=teacher_user, is_active=True).update(is_active=False)
            Department.objects.filter(head=teacher_user).update(head=None)

            reason_display = dict(Teacher._meta.get_field('exit_reason').choices).get(exit_reason, exit_reason.title())

            return JsonResponse({
                'success': True,
                'message': f"Teacher {teacher_user.get_full_name()} has been successfully relieved ({reason_display}) as of {date_of_leaving}."
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Staff Views
class StaffListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'human_resource/staff_list.html'
    context_object_name = 'staff'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role__in=['staff', 'accountant', 'librarian', 'driver'], is_active=True)
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        departments_qs = Department.objects.filter(is_active=True)
        designations_qs = Designation.objects.filter(is_active=True)
        if school:
            departments_qs = departments_qs.filter(school=school)
            designations_qs = designations_qs.filter(school=school)
        context['departments'] = departments_qs
        context['designations'] = designations_qs
        return context


@method_decorator(csrf_exempt, name='dispatch')
class StaffCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip()
            role = request.POST.get('role', 'staff')
            
            # Auto-generate email if not provided
            if not email:
                school_slug = get_school_slug_from_request(request)
                email = generate_email(first_name, last_name, school_slug, role)
            
            staff = User.objects.create_user(
                email=email,
                password='staff123',
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone=request.POST.get('phone', ''),
                department_id=request.POST.get('department') or None,
                designation_id=request.POST.get('designation') or None,
                is_active=True
            )
            school = get_current_school(request)
            if school:
                staff.school = school
                staff.save(update_fields=["school"])

            # Auto-generate or use custom employee id on User for consistency
            custom_emp_id = request.POST.get('employee_id', '').strip()
            employee_id = custom_emp_id or f"STF-{staff.id}"
            staff.employee_id = employee_id
            staff.save(update_fields=["employee_id"]) 

            # Create HR Staff profile
            dept_id = request.POST.get('department') or None
            desig_id = request.POST.get('designation') or None
            basic_salary = Decimal(request.POST.get('basic_salary') or 0)
            allowances = Decimal(request.POST.get('allowances') or 0)
            doj_str = request.POST.get('date_of_joining')
            date_of_joining = datetime.strptime(doj_str, '%Y-%m-%d').date() if doj_str else None
            employment_type = request.POST.get('employment_type') or 'permanent'
            phone = request.POST.get('phone', '')
            address = request.POST.get('address', '')
            is_active = str(request.POST.get('is_active', 'on')).lower() in ['1', 'true', 'on', 'yes']

            Staff.objects.create(
                user=staff,
                first_name=first_name,
                last_name=last_name,
                employee_id=employee_id or f"STF-{staff.id}",
                department_id=dept_id,
                designation_id=desig_id,
                basic_salary=basic_salary,
                allowances=allowances,
                date_of_joining=date_of_joining or datetime.today().date(),
                employment_type=employment_type,
                phone=str(phone or ''),
                email=email,
                address=address,
                is_active=is_active,
            )
            return JsonResponse({'success': True, 'message': 'Staff added successfully!'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class StaffDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'human_resource/staff_detail.html'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role__in=['staff', 'accountant', 'librarian', 'driver'])
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get(self, request, *args, **kwargs):
        staff = self.get_object()
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'staff': {
                    'id': staff.id,
                    'first_name': staff.first_name,
                    'last_name': staff.last_name,
                    'email': staff.email,
                    'phone': str(staff.phone) if staff.phone else '',
                    'role': staff.role,
                    'is_active': staff.is_active
                }
            })
        
        return super().get(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role__in=['staff', 'accountant', 'librarian', 'driver'])
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def post(self, request, *args, **kwargs):
        try:
            staff = self.get_object()
            staff.first_name = request.POST.get('first_name')
            staff.last_name = request.POST.get('last_name')
            staff.email = request.POST.get('email')
            staff.phone = request.POST.get('phone', '')
            staff.role = request.POST.get('role', staff.role)
            # Update active and department/designation on User
            staff.is_active = str(request.POST.get('is_active', staff.is_active)).lower() in ['1', 'true', 'on', 'yes']
            dept_val = request.POST.get('department')
            desig_val = request.POST.get('designation')
            if dept_val is not None:
                staff.department_id = dept_val or None
            if desig_val is not None:
                staff.designation_id = desig_val or None
            
            emp_id_val = request.POST.get('employee_id', '').strip()
            if emp_id_val:
                staff.employee_id = emp_id_val

            staff.save()

            # Sync HR Staff profile including HR fields
            profile, _ = Staff.objects.get_or_create(
                user=staff,
                defaults={
                    'first_name': staff.first_name,
                    'last_name': staff.last_name,
                    'employee_id': f"STF-{staff.id}",
                    'date_of_joining': datetime.today().date(),
                }
            )
            profile.first_name = staff.first_name
            profile.last_name = staff.last_name
            profile.email = staff.email
            profile.phone = str(staff.phone or '')
            profile.department_id = staff.department_id
            profile.designation_id = staff.designation_id
            if emp_id_val:
                profile.employee_id = emp_id_val
            # HR specific fields
            basic_salary = request.POST.get('basic_salary')
            allowances = request.POST.get('allowances')
            doj_str = request.POST.get('date_of_joining')
            employment_type = request.POST.get('employment_type')
            address = request.POST.get('address')
            prof_active = request.POST.get('is_active')
            if basic_salary not in (None, ''):
                profile.basic_salary = Decimal(basic_salary)
            if allowances not in (None, ''):
                profile.allowances = Decimal(allowances)
            if doj_str:
                try:
                    profile.date_of_joining = datetime.strptime(doj_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if employment_type:
                profile.employment_type = employment_type
            if address is not None:
                profile.address = address
            if prof_active is not None:
                profile.is_active = str(prof_active).lower() in ['1', 'true', 'on', 'yes']
            profile.save()
            return JsonResponse({'success': True, 'message': 'Staff updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class StaffDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            obj = self.get_object()
            if getattr(obj, 'is_sample_data', False):
                return JsonResponse({'success': False, 'error': 'Sample/Demo data cannot be deleted.'})
            
            # Soft deactivate staff user
            obj.is_active = False
            obj.save(update_fields=['is_active'])
            
            # Soft deactivate HR staff profile if exists
            if hasattr(obj, 'staff_profile'):
                profile = obj.staff_profile
                profile.is_active = False
                profile.save(update_fields=['is_active'])
            
            # Cleanly unassign from headed departments
            Department.objects.filter(head=obj).update(head=None)
            
            return JsonResponse({'success': True, 'message': 'Staff deactivated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role__in=['staff', 'accountant', 'librarian', 'driver'])
        if school:
            qs = qs.filter(school=school)
        return qs


# Department Views
class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'human_resource/department_list.html'
    context_object_name = 'departments'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Department.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class DepartmentCreateView(LoginRequiredMixin, View):
    model = Department
    
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            Department.objects.create(
                school=school,
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                description=request.POST.get('description', ''),
                is_active=True
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DepartmentUpdateView(LoginRequiredMixin, View):
    model = Department
    
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = Department.objects.all()
            if school:
                qs = qs.filter(school=school)
            pk = kwargs.get('pk')
            department = qs.get(pk=pk)
            
            name = request.POST.get('name')
            code = request.POST.get('code')
            description = request.POST.get('description', '')
            
            department.name = name
            department.code = code
            department.description = description
            department.save()
            
            return JsonResponse({'success': True})
        except Department.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Department not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DepartmentDeleteView(LoginRequiredMixin, View):
    model = Department
    
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = Department.objects.all()
            if school:
                qs = qs.filter(school=school)
            pk = kwargs.get('pk')
            department = qs.get(pk=pk)
            department.delete()
            return JsonResponse({'success': True})
        except Department.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Department not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# Designation Views
class DesignationListView(LoginRequiredMixin, ListView):
    model = Designation
    template_name = 'human_resource/designation_list.html'
    context_object_name = 'designations'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Designation.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class DesignationCreateView(LoginRequiredMixin, View):
    model = Designation
    
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            Designation.objects.create(
                school=school,
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                description=request.POST.get('description', ''),
                level=request.POST.get('level', 1),
                is_active=True
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DesignationDeleteView(LoginRequiredMixin, View):
    model = Designation
    
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            qs = Designation.objects.all()
            if school:
                qs = qs.filter(school=school)
            pk = kwargs.get('pk')
            designation = qs.get(pk=pk)
            designation.delete()
            return JsonResponse({'success': True})
        except Designation.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Designation not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
