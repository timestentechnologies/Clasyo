from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Student
from accounts.models import User
from core.models import SystemSetting
from core.utils import generate_email, get_school_slug_from_request


class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'students/list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_active=True).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    context_object_name = 'student'
    
    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'HTTP_X_REQUESTED_WITH' in self.request.META:
            return ['students/detail_modal.html']
        return ['students/detail.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class StudentCreateView(CreateView):
    model = Student
    template_name = 'students/form.html'
    fields = []
    
    def get_success_url(self):
        return f"/school/{self.kwargs.get('school_slug')}/students/"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        # Get admission number prefix from settings
        settings = SystemSetting.objects.first()
        prefix = settings.admission_number_prefix if settings else 'STU'
        context['next_admission_number'] = Student.generate_admission_number(prefix)
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            from datetime import date
            
            # Get or create settings for prefix
            settings = SystemSetting.objects.first()
            prefix = settings.admission_number_prefix if settings else 'STU'
            
            # Generate admission number or use provided
            admission_number = request.POST.get('admission_number')
            if not admission_number or admission_number.strip() == '':
                admission_number = Student.generate_admission_number(prefix)
            
            # Create user account first
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip()
            
            # Auto-generate email if not provided
            if not email:
                school_slug = get_school_slug_from_request(request)
                email = generate_email(first_name, last_name, school_slug, 'student')
            
            # Check if user with this email already exists
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False, 
                    'error': f'A user with email {email} already exists. Please use a different email.'
                })
            
            user = User.objects.create(
                email=email,
                password='student123',  # Will be hashed
                first_name=first_name,
                last_name=last_name,
                role='student',
                is_active=True
            )
            user.set_password('student123')  # Hash the password properly
            user.save()
            
            # Get admission date or use today
            admission_date = request.POST.get('admission_date')
            if not admission_date:
                admission_date = date.today()
            
            # Create parent user account if father email provided or can be generated
            parent_user = None
            father_email = request.POST.get('father_email', '').strip()
            mother_email = request.POST.get('mother_email', '').strip()
            father_name = request.POST.get('father_name', '').strip()
            mother_name = request.POST.get('mother_name', '').strip()
            
            # Determine parent email and name
            parent_email = father_email if father_email else mother_email
            parent_full_name = father_name if father_name else mother_name
            parent_first_name = parent_full_name.split()[0] if parent_full_name else ''
            parent_last_name = parent_full_name.split()[-1] if parent_full_name and ' ' in parent_full_name else last_name
            
            # Auto-generate parent email if name provided but no email
            if not parent_email and parent_full_name:
                school_slug = get_school_slug_from_request(request)
                parent_email = generate_email(parent_first_name, parent_last_name, school_slug, 'parent')
            
            if parent_email:
                # Check if parent account already exists
                try:
                    parent_user = User.objects.get(email=parent_email, role='parent')
                except User.DoesNotExist:
                    # Create new parent account
                    try:
                        parent_user = User.objects.create(
                            email=parent_email,
                            first_name=parent_first_name or 'Parent',
                            last_name=parent_last_name,  # Already set to student's last name if not provided
                            role='parent',
                            phone=request.POST.get('father_phone', '') or request.POST.get('mother_phone', ''),
                            is_active=True
                        )
                        parent_user.set_password('parent123')  # Default password
                        parent_user.save()
                    except Exception as e:
                        print(f"[WARNING] Could not create parent account: {e}")
            
            # Create student with all fields including parent details
            student = Student.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                admission_number=admission_number,
                admission_date=admission_date,
                date_of_birth=request.POST.get('date_of_birth') or None,
                gender=request.POST.get('gender', ''),
                blood_group=request.POST.get('blood_group', ''),
                religion=request.POST.get('religion', ''),
                current_address=request.POST.get('current_address', ''),
                city=request.POST.get('city', ''),
                state=request.POST.get('state', ''),
                country=request.POST.get('country', 'US'),
                postal_code=request.POST.get('postal_code', ''),
                # Parent Details
                father_name=request.POST.get('father_name', ''),
                father_phone=request.POST.get('father_phone', ''),
                father_email=father_email,
                father_occupation=request.POST.get('father_occupation', ''),
                mother_name=request.POST.get('mother_name', ''),
                mother_phone=request.POST.get('mother_phone', ''),
                mother_email=mother_email,
                mother_occupation=request.POST.get('mother_occupation', ''),
                guardian_name=request.POST.get('guardian_name', ''),
                guardian_phone=request.POST.get('guardian_phone', ''),
                guardian_email=request.POST.get('guardian_email', ''),
                guardian_relation=request.POST.get('guardian_relation', ''),
                parent_user=parent_user,  # Link to parent user account
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Student added successfully',
                'admission_number': admission_number
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class StudentUpdateView(UpdateView):
    model = Student
    template_name = 'students/edit_modal.html'
    fields = []
    
    def get_success_url(self):
        return f"/school/{self.kwargs.get('school_slug')}/students/"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['student'] = self.get_object()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            student = self.get_object()
            
            # Update student fields
            student.first_name = request.POST.get('first_name', student.first_name)
            student.last_name = request.POST.get('last_name', student.last_name)
            student.email = request.POST.get('email', student.email)
            student.date_of_birth = request.POST.get('date_of_birth', student.date_of_birth)
            student.gender = request.POST.get('gender', student.gender)
            student.blood_group = request.POST.get('blood_group', student.blood_group)
            student.current_address = request.POST.get('current_address', student.current_address)
            student.city = request.POST.get('city', student.city)
            student.state = request.POST.get('state', student.state)
            student.postal_code = request.POST.get('postal_code', student.postal_code)
            
            # Update parent details
            student.father_name = request.POST.get('father_name', student.father_name)
            student.father_phone = request.POST.get('father_phone', student.father_phone)
            father_email = request.POST.get('father_email', '').strip()
            student.father_email = father_email
            student.father_occupation = request.POST.get('father_occupation', student.father_occupation)
            student.mother_name = request.POST.get('mother_name', student.mother_name)
            student.mother_phone = request.POST.get('mother_phone', student.mother_phone)
            mother_email = request.POST.get('mother_email', '').strip()
            student.mother_email = mother_email
            student.mother_occupation = request.POST.get('mother_occupation', student.mother_occupation)
            student.guardian_name = request.POST.get('guardian_name', student.guardian_name)
            student.guardian_phone = request.POST.get('guardian_phone', student.guardian_phone)
            student.guardian_email = request.POST.get('guardian_email', student.guardian_email)
            student.guardian_relation = request.POST.get('guardian_relation', student.guardian_relation)
            
            # Create or link parent user account if email provided or can be generated
            parent_email = father_email if father_email else mother_email
            father_name = request.POST.get('father_name', '').strip()
            mother_name = request.POST.get('mother_name', '').strip()
            parent_full_name = father_name if father_name else mother_name
            parent_first_name = parent_full_name.split()[0] if parent_full_name else ''
            parent_last_name = parent_full_name.split()[-1] if parent_full_name and ' ' in parent_full_name else student.last_name
            
            # Auto-generate parent email if name provided but no email
            if not parent_email and parent_full_name and not student.parent_user:
                school_slug = get_school_slug_from_request(request)
                parent_email = generate_email(parent_first_name, parent_last_name, school_slug, 'parent')
                # Update the student's email fields with the auto-generated email
                if father_name:
                    student.father_email = parent_email
                else:
                    student.mother_email = parent_email
            
            if parent_email and not student.parent_user:
                # Check if parent account already exists
                try:
                    parent_user = User.objects.get(email=parent_email, role='parent')
                    student.parent_user = parent_user
                except User.DoesNotExist:
                    # Create new parent account
                    try:
                        parent_user = User.objects.create(
                            email=parent_email,
                            first_name=parent_first_name or 'Parent',
                            last_name=parent_last_name or student.last_name,
                            role='parent',
                            phone=request.POST.get('father_phone', '') or request.POST.get('mother_phone', ''),
                            is_active=True
                        )
                        parent_user.set_password('parent123')  # Default password
                        parent_user.save()
                        student.parent_user = parent_user
                    except Exception as e:
                        print(f"[WARNING] Could not create parent account: {e}")
            
            student.save()
            
            # Update user email if changed
            if student.user.email != student.email:
                student.user.email = student.email
                student.user.first_name = student.first_name
                student.user.last_name = student.last_name
                student.user.save()
            
            return JsonResponse({'success': True, 'message': 'Student updated successfully'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class StudentDeleteView(DeleteView):
    model = Student
    
    def get_success_url(self):
        return f"/school/{self.kwargs.get('school_slug')}/students/"
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
                
            student = self.get_object()
            student.user.delete()  # This will cascade delete the student
            return JsonResponse({'success': True, 'message': 'Student deleted successfully'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class ParentListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'students/parents.html'
    context_object_name = 'parents'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.filter(role='parent', is_active=True).order_by('first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class ParentDetailView(LoginRequiredMixin, DetailView):
    model = User
    
    def get(self, request, *args, **kwargs):
        try:
            parent = self.get_object()
            if parent.role != 'parent':
                return JsonResponse({'success': False, 'error': 'Not a parent user'})
            
            # Get children (students linked to this parent)
            children = Student.objects.filter(parent_user=parent)
            children_data = [{
                'name': f"{child.first_name} {child.last_name}",
                'admission_number': child.admission_number
            } for child in children]
            
            return JsonResponse({
                'success': True,
                'parent': {
                    'name': parent.get_full_name(),
                    'first_name': parent.first_name,
                    'last_name': parent.last_name,
                    'email': parent.email,
                    'phone': str(parent.phone) if parent.phone else '',
                    'is_active': parent.is_active
                },
                'children': children_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
