from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from decimal import Decimal
from datetime import datetime
from accounts.models import User
from .models import Department, Designation, Teacher, Staff
from core.utils import generate_email, get_school_slug_from_request, get_current_school


class TeacherListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'human_resource/teacher_list.html'
    context_object_name = 'teachers'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role='teacher', is_active=True)
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

            # Auto-generate employee id on User for consistency
            employee_id = f"TCHR-{teacher.id}"
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
            return JsonResponse({'success': True})
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
                    'employment_type': getattr(profile, 'employment_type', ''),
                    'address': getattr(profile, 'address', ''),
                }
            })
        
        # Return HTML template for regular requests
        return super().get(request, *args, **kwargs)


class TeacherAssignmentsView(LoginRequiredMixin, View):
    template_name = 'human_resource/teacher_assignments.html'

    def _get_active_year(self, school):
        from core.models import AcademicYear

        qs = AcademicYear.objects.filter(is_active=True)
        if school:
            qs = qs.filter(school=school)
        return qs.first()

    def _get_teacher(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role='teacher')
        if school:
            qs = qs.filter(school=school)
        return qs.get(pk=self.kwargs.get('pk'))

    def get(self, request, *args, **kwargs):
        from academics.models import AssignedSubject, Class, Section, Subject

        teacher = self._get_teacher()
        school = get_current_school(request)
        active_year = self._get_active_year(school)

        classes_qs = Class.objects.filter(is_active=True)
        subjects_qs = Subject.objects.filter(is_active=True)
        sections_qs = Section.objects.filter(is_active=True)
        if school:
            classes_qs = classes_qs.filter(school=school)
            subjects_qs = subjects_qs.filter(school=school)
            sections_qs = sections_qs.filter(class_name__school=school)

        assigned_qs = AssignedSubject.objects.filter(is_active=True)
        if active_year:
            assigned_qs = assigned_qs.filter(academic_year=active_year)
        if school:
            assigned_qs = assigned_qs.filter(
                class_name__school=school,
                subject__school=school,
            )
        assigned_qs = assigned_qs.select_related('class_name', 'section', 'subject', 'teacher').order_by('class_name__order', 'class_name__name', 'section__name', 'subject__name')

        context = {
            'school_slug': self.kwargs.get('school_slug', ''),
            'teacher': teacher,
            'active_year': active_year,
            'assigned_subjects': assigned_qs,
            'selected_assigned_ids': set(assigned_qs.filter(teacher=teacher).values_list('id', flat=True)),
            'sections': sections_qs.select_related('class_name').order_by('class_name__order', 'class_name__name', 'name'),
            'selected_section_ids': set(sections_qs.filter(class_teacher=teacher).values_list('id', flat=True)),
            'has_active_year': bool(active_year),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        from academics.models import AssignedSubject, Section

        teacher = self._get_teacher()
        school = get_current_school(request)
        active_year = self._get_active_year(school)

        selected_assigned_ids = set(map(int, request.POST.getlist('assigned_subject_ids')))
        selected_section_ids = set(map(int, request.POST.getlist('section_ids')))

        if active_year:
            assigned_qs = AssignedSubject.objects.filter(is_active=True, academic_year=active_year)
            if school:
                assigned_qs = assigned_qs.filter(class_name__school=school, subject__school=school)

            assigned_qs.filter(teacher=teacher).exclude(id__in=selected_assigned_ids).update(teacher=None)
            assigned_qs.filter(id__in=selected_assigned_ids).update(teacher=teacher)

        sections_qs = Section.objects.filter(is_active=True)
        if school:
            sections_qs = sections_qs.filter(class_name__school=school)

        sections_qs.filter(class_teacher=teacher).exclude(id__in=selected_section_ids).update(class_teacher=None)
        sections_qs.filter(id__in=selected_section_ids).update(class_teacher=teacher)

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
            
            # Handle password update if provided
            password = request.POST.get('password', '').strip()
            if password and password != 'teacher123':
                teacher.set_password(password)
            
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
            return JsonResponse({'success': True, 'message': 'Teacher updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class TeacherDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    
    def post(self, request, *args, **kwargs):
        try:
            teacher = self.get_object()
            if teacher.role == 'teacher':
                teacher.delete()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'error': 'Not a teacher'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = User.objects.filter(role='teacher')
        if school:
            qs = qs.filter(school=school)
        return qs


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

            # Auto-generate employee id on User for consistency
            employee_id = f"STF-{staff.id}"
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
            
            # Handle password update
            password = request.POST.get('password', '').strip()
            if password and password != 'staff123':
                staff.set_password(password)
            
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
            self.get_object().delete()
            return JsonResponse({'success': True})
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
