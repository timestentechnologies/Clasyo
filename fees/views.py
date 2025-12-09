from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import models
from django.utils import timezone
from students.models import Student
from accounts.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Check if models exist
try:
    from .models import FeeStructure, FeeCollection
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class FeeStructure:
        pass
    class FeeCollection:
        pass


@method_decorator(csrf_exempt, name='dispatch')
class FeeStructureView(LoginRequiredMixin, ListView):
    template_name = 'fees/fee_structure.html'
    context_object_name = 'fee_structures'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return FeeStructure.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        from academics.models import Class
        context['classes'] = Class.objects.filter(is_active=True)
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Fee models are not available'})
                
            FeeStructure.objects.create(
                name=request.POST.get('name'),
                class_name_id=request.POST.get('class_id'),
                amount=request.POST.get('amount'),
                fee_type=request.POST.get('fee_type'),
                description=request.POST.get('description', '')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


STAFF_ROLES = ['admin', 'teacher', 'accountant', 'librarian', 'receptionist']


@method_decorator(csrf_exempt, name='dispatch')
class CollectFeesView(LoginRequiredMixin, ListView):
    template_name = 'fees/collect_fees.html'
    context_object_name = 'payments'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return FeeCollection.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['students'] = Student.objects.filter(is_active=True)
        if MODELS_EXIST:
            context['fee_structures'] = FeeStructure.objects.filter(is_active=True)
        else:
            context['fee_structures'] = []
        context['fee_collectors'] = User.objects.filter(
            role__in=STAFF_ROLES,
            is_active=True
        ).order_by('first_name', 'last_name')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Fee models are not available'})
                
            # Get the fee structure to determine the amount
            fee_structure = FeeStructure.objects.get(id=request.POST.get('fee_structure_id'))
            paid_amount = request.POST.get('amount_paid', 0)
            collected_by = None
            collected_by_id = request.POST.get('collected_by_id')
            if collected_by_id:
                collected_by = User.objects.filter(
                    id=collected_by_id,
                    role__in=STAFF_ROLES,
                    is_active=True
                ).first()
            if not collected_by:
                collected_by = request.user
            
            FeeCollection.objects.create(
                student_id=request.POST.get('student_id'),
                fee_structure_id=request.POST.get('fee_structure_id'),
                amount=fee_structure.amount,
                paid_amount=paid_amount,
                payment_method=request.POST.get('payment_method'),
                payment_date=request.POST.get('payment_date'),
                due_date=request.POST.get('due_date'),
                receipt_number=request.POST.get('transaction_id', ''),
                notes=request.POST.get('note', ''),
                collected_by=collected_by,
                payment_status='paid' if float(paid_amount) >= float(fee_structure.amount) else 'partial'
            )
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class FeeTransactionView(LoginRequiredMixin, ListView):
    template_name = 'fees/transactions.html'
    context_object_name = 'transactions'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return FeeCollection.objects.all().order_by('-payment_date')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            total_collected = FeeCollection.objects.aggregate(total=models.Sum('paid_amount'))['total'] or 0
        else:
            total_collected = 0
        context['total_collected'] = total_collected
        return context


class WalletView(LoginRequiredMixin, ListView):
    template_name = 'fees/wallet.html'
    context_object_name = 'wallets'
    
    def get_queryset(self):
        # TODO: Wallet model needs to be created
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class MyFeesView(LoginRequiredMixin, ListView):
    """View for students to see their fee payments and balances"""
    template_name = 'fees/my_fees.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        if MODELS_EXIST and hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            return FeeCollection.objects.filter(student=student).order_by('-payment_date')
        elif MODELS_EXIST and self.request.user.role == 'parent':
            # For parents, get payments for their children
            from students.models import Student
            children = Student.objects.filter(parent_user=self.request.user)
            return FeeCollection.objects.filter(student__in=children).order_by('-payment_date')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Get student (for students) or children (for parents)
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            context['student'] = student
        elif self.request.user.role == 'parent':
            from students.models import Student
            children = Student.objects.filter(parent_user=self.request.user)
            if children.exists():
                context['student'] = children.first()  # Default to first child
            else:
                context['student'] = None
        
        student = context.get('student')
        
        # Calculate fee statistics
        if student and MODELS_EXIST:
            # Get fee structures for the student's class
            fee_structures = FeeStructure.objects.filter(
                class_name=student.current_class,
                is_active=True
            )
            context['fee_structures'] = fee_structures
            
            # Calculate total fees, paid amount, and balance
            total_fees = sum(structure.amount for structure in fee_structures)
            total_paid = FeeCollection.objects.filter(student=student).aggregate(
                total=models.Sum('paid_amount'))['total'] or 0
            balance = total_fees - total_paid
            
            context['total_fees'] = total_fees
            context['total_paid'] = total_paid
            context['balance'] = balance
            
            # Add payment status to each fee structure
            for structure in fee_structures:
                paid_for_structure = FeeCollection.objects.filter(
                    student=student, 
                    fee_structure=structure
                ).aggregate(total=models.Sum('paid_amount'))['total'] or 0
                structure.balance = structure.amount - paid_for_structure
                structure.is_paid = structure.balance <= 0
                structure.is_overdue = (
                    structure.balance > 0 and 
                    hasattr(structure, 'due_date') and 
                    structure.due_date and 
                    structure.due_date < timezone.now().date()
                )
        
        # Get payment configurations for parents
        if self.request.user.role == 'parent':
            try:
                from superadmin.models import SchoolPaymentConfiguration
                from tenants.models import School
                
                # Get the current school
                school = School.objects.get(slug=self.kwargs.get('school_slug'))
                payment_configs = SchoolPaymentConfiguration.objects.filter(
                    school=school,
                    is_active=True
                )
                context['payment_configurations'] = payment_configs
            except (ImportError, School.DoesNotExist):
                context['payment_configurations'] = []
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class MpesaStkPushView(LoginRequiredMixin, View):
    """Handle M-Pesa STK Push payments"""
    
    def post(self, request, school_slug):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Payment system not available'})
        
        try:
            # Get form data
            phone_number = request.POST.get('phone_number')
            amount = request.POST.get('amount')
            fee_type_id = request.POST.get('fee_type')
            payment_config_id = request.POST.get('payment_config_id')
            
            # Validate data
            if not all([phone_number, amount, fee_type_id, payment_config_id]):
                return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
            # Get payment configuration
            from superadmin.models import SchoolPaymentConfiguration
            from tenants.models import School
            
            school = School.objects.get(slug=school_slug)
            payment_config = SchoolPaymentConfiguration.objects.get(
                id=payment_config_id,
                school=school,
                gateway='mpesa_stk',
                is_active=True
            )
            
            # Get fee structure
            fee_structure = FeeStructure.objects.get(id=fee_type_id)
            
            # Get student (for students) or child (for parents)
            if hasattr(request.user, 'student_profile'):
                student = request.user.student_profile
            elif request.user.role == 'parent':
                from students.models import Student
                children = Student.objects.filter(parent_user=request.user)
                if not children.exists():
                    return JsonResponse({'success': False, 'error': 'No students found'})
                student = children.first()
            else:
                return JsonResponse({'success': False, 'error': 'Unauthorized'})
            
            # Generate transaction ID
            import uuid
            receipt_number = f"MPESA-{uuid.uuid4().hex[:8].upper()}"
            
            # Create payment record
            payment = FeeCollection.objects.create(
                student=student,
                fee_structure=fee_structure,
                amount=fee_structure.amount,
                paid_amount=0,  # Will be updated after successful payment
                payment_status='pending',
                payment_method='online',  # Use valid choice
                receipt_number=receipt_number,  # Use receipt_number field
                due_date=timezone.now().date(),  # Use current date as due_date
                notes=f"M-Pesa STK Push initiated for {phone_number}"
            )
            
            # TODO: Implement actual M-Pesa STK Push API call
            # For now, simulate successful initiation
            success = self.simulate_mpesa_stk_push(
                payment_config, phone_number, amount, receipt_number
            )
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': 'STK Push sent successfully',
                    'receipt_number': receipt_number
                })
            else:
                payment.delete()  # Remove the payment record if STK push failed
                return JsonResponse({'success': False, 'error': 'STK Push failed'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def simulate_mpesa_stk_push(self, config, phone_number, amount, receipt_number):
        """
        Simulate M-Pesa STK Push API call
        In production, this would make actual API calls to M-Pesa
        """
        import time
        import random
        
        # Simulate API delay
        time.sleep(1)
        
        # Simulate success (90% success rate for demo)
        return random.random() > 0.1


@method_decorator(csrf_exempt, name='dispatch')
class ConfirmPaymentView(LoginRequiredMixin, View):
    """Handle payment confirmation for manual payment methods"""
    
    def post(self, request, school_slug):
        if not MODELS_EXIST:
            return JsonResponse({'success': False, 'error': 'Payment system not available'})
        
        try:
            # Get form data
            amount = request.POST.get('amount')
            fee_type_id = request.POST.get('fee_type')
            payment_config_id = request.POST.get('payment_config_id')
            payment_method = request.POST.get('payment_method')
            receipt_number = request.POST.get('transaction_id')  # Use receipt_number field
            payment_date = request.POST.get('payment_date')
            
            # Validate data
            if not all([amount, fee_type_id, payment_config_id, payment_method, receipt_number, payment_date]):
                return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
            # Get payment configuration
            from superadmin.models import SchoolPaymentConfiguration
            from tenants.models import School
            
            school = School.objects.get(slug=school_slug)
            payment_config = SchoolPaymentConfiguration.objects.get(
                id=payment_config_id,
                school=school,
                is_active=True
            )
            
            # Get fee structure
            fee_structure = FeeStructure.objects.get(id=fee_type_id)
            
            # Get student (for students) or child (for parents)
            if hasattr(request.user, 'student_profile'):
                student = request.user.student_profile
            elif request.user.role == 'parent':
                from students.models import Student
                children = Student.objects.filter(parent_user=request.user)
                if not children.exists():
                    return JsonResponse({'success': False, 'error': 'No students found'})
                student = children.first()
            else:
                return JsonResponse({'success': False, 'error': 'Unauthorized'})
            
            # Generate unique receipt number
            import uuid
            unique_receipt = f"PAY-{uuid.uuid4().hex[:12].upper()}"
            
            # Create payment record with pending status for verification
            payment = FeeCollection.objects.create(
                student=student,
                fee_structure=fee_structure,
                amount=fee_structure.amount,
                paid_amount=amount,
                payment_method=payment_method.replace('mpesa_paybill', 'online').replace('bank', 'bank_transfer'),  # Map to valid choices
                receipt_number=unique_receipt,  # Use unique receipt number
                payment_date=payment_date,
                due_date=payment_date,  # Use payment_date as due_date since FeeStructure doesn't have due_date
                payment_status='pending',  # Requires admin verification
                notes=f"Payment confirmation submitted via {payment_config.get_gateway_display()}. Transaction ID: {receipt_number}"
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Payment confirmation submitted successfully',
                'payment_id': payment.id
            })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
