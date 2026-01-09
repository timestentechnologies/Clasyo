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


def attach_student_balances(payments):
    """Attach running balance after each payment to payment instances."""
    if not MODELS_EXIST:
        return payments

    # Group payments by student and fee type
    payment_groups = {}
    for payment in payments:
        student_id = getattr(payment, 'student_id', None)
        fee_type = getattr(payment.fee_structure, 'fee_type', None) if hasattr(payment, 'fee_structure') else None
        
        if student_id and fee_type:
            key = (student_id, fee_type)
            if key not in payment_groups:
                payment_groups[key] = []
            payment_groups[key].append(payment)
    
    # Sort each group by payment date and calculate running balances
    for (student_id, fee_type), group_payments in payment_groups.items():
        # Sort by payment date
        group_payments.sort(key=lambda x: getattr(x, 'payment_date', None))
        
        # Get the total fee amount for this fee type
        try:
            student = Student.objects.get(id=student_id)
            fee_structure = FeeStructure.objects.get(
                class_name_id=student.current_class_id,
                fee_type=fee_type,
                is_active=True
            )
            total_fee_amount = fee_structure.amount
        except:
            total_fee_amount = 0
        
        # Calculate running balance for each payment
        running_balance = total_fee_amount
        for i, payment in enumerate(group_payments):
            running_balance -= getattr(payment, 'paid_amount', 0)
            payment.running_balance = max(running_balance, 0)
            # Mark the last payment as current for this student
            payment.is_current_balance = (i == len(group_payments) - 1)
    
    return payments


def calculate_fee_aggregates(class_id=None, balance_status=None):
    """Calculate total expected, collected, and remaining fees for the school.

    Expected:
        For each class, sum active fee structures (per-student fee), then
        multiply by the number of active students in that class.
    Collected:
        Sum of paid_amount for all fee collections of active students.
    Remaining:
        max(Expected - Collected, 0).

    Optional parameters are currently ignored for aggregates, which are
    intended to be global across all classes and students.
    """
    if not MODELS_EXIST:
        return 0, 0, 0

    # Active students with a class assigned
    students_qs = Student.objects.filter(is_active=True, current_class__isnull=False)
    if class_id:
        students_qs = students_qs.filter(current_class_id=class_id)

    class_counts = list(
        students_qs.values('current_class_id').annotate(count=models.Count('id'))
    )
    if not class_counts:
        return 0, 0, 0

    class_ids = [row['current_class_id'] for row in class_counts]

    # Total fees per student for each class
    fee_totals_qs = FeeStructure.objects.filter(
        class_name_id__in=class_ids,
        is_active=True
    ).values('class_name_id').annotate(total=models.Sum('amount'))
    fee_per_class = {row['class_name_id']: row['total'] or 0 for row in fee_totals_qs}

    # Expected = per-class total fee * number of students in that class
    total_expected = 0
    for row in class_counts:
        cls_id = row['current_class_id']
        student_count = row['count'] or 0
        per_student_fee = fee_per_class.get(cls_id, 0)
        total_expected += per_student_fee * student_count

    # Total collected from active students
    total_collected = FeeCollection.objects.filter(
        student__is_active=True,
        student__current_class__isnull=False
    ).aggregate(total=models.Sum('paid_amount'))['total'] or 0

    total_remaining = max(total_expected - total_collected, 0)

    return total_expected, total_collected, total_remaining


@method_decorator(csrf_exempt, name='dispatch')
class CollectFeesView(LoginRequiredMixin, ListView):
    template_name = 'fees/collect_fees.html'
    context_object_name = 'payments'
    
    def get_queryset(self):
        if not MODELS_EXIST:
            return []

        queryset = FeeCollection.objects.select_related('student__current_class', 'fee_structure').order_by('-payment_date')

        # Optional filter by class
        class_id = self.request.GET.get('class_id')
        if class_id:
            queryset = queryset.filter(student__current_class_id=class_id)

        # Attach student balances for all payments in the current queryset
        payments = attach_student_balances(queryset)

        # Optional filter by balance status
        balance_status = self.request.GET.get('balance_status')
        if balance_status == 'with_balance':
            payments = [payment for payment in payments if getattr(payment, 'running_balance', 0) > 0]
        elif balance_status == 'fully_paid':
            payments = [payment for payment in payments if getattr(payment, 'running_balance', 0) <= 0]

        return payments
    
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
        try:
            from academics.models import Class
            context['classes'] = Class.objects.filter(is_active=True)
        except Exception:
            context['classes'] = []

        # Preserve selected filters in the template
        selected_class_id = self.request.GET.get('class_id', '')
        selected_balance_status = self.request.GET.get('balance_status', '')
        context['selected_class_id'] = selected_class_id
        context['selected_balance_status'] = selected_balance_status

        # Global fee aggregates for summary cards (all students, all grades)
        total_expected, total_collected, total_remaining = calculate_fee_aggregates()
        context['total_expected'] = total_expected
        context['total_collected'] = total_collected
        context['total_remaining'] = total_remaining
        
        # Calculate totals for the table
        payments = self.get_queryset()
        if MODELS_EXIST and payments:
            from django.db.models import Sum
            table_totals = payments.aggregate(
                total_collected=Sum('paid_amount')
            )
            context['table_total_collected'] = table_totals['total_collected'] or 0
        else:
            context['table_total_collected'] = 0
        
        import json

# Get complete student data for accurate filtering calculations
        if MODELS_EXIST:
            from django.db.models import Q
            # Get all active students with their fee structures
            students_data = []
            active_students = Student.objects.filter(is_active=True, current_class__isnull=False)
            
            for student in active_students:
                # Get all fee structures for this student's class
                fee_structures = FeeStructure.objects.filter(
                    class_name_id=student.current_class_id,
                    is_active=True
                )
                
                for fee_structure in fee_structures:
                    # Calculate total paid for this student and fee type
                    paid_amount = FeeCollection.objects.filter(
                        student=student,
                        fee_structure=fee_structure
                    ).aggregate(total=Sum('paid_amount'))['total'] or 0
                    
                    students_data.append({
                        'student_id': student.id,
                        'student_name': student.get_full_name(),
                        'class_id': student.current_class_id,
                        'class_name': student.current_class.name,
                        'fee_type': fee_structure.fee_type,
                        'fee_amount': float(fee_structure.amount),
                        'paid_amount': float(paid_amount),
                        'balance': float(fee_structure.amount - paid_amount)
                    })
            
            context['students_fee_data'] = json.dumps(students_data)
        else:
            context['students_fee_data'] = json.dumps([])
            
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
        if not MODELS_EXIST:
            return []

        queryset = FeeCollection.objects.select_related('student__current_class', 'fee_structure').order_by('-payment_date')

        # Optional filter by class
        class_id = self.request.GET.get('class_id')
        if class_id:
            queryset = queryset.filter(student__current_class_id=class_id)

        # Attach student balances for all transactions
        transactions = attach_student_balances(queryset)

        # Optional filter by balance status
        balance_status = self.request.GET.get('balance_status')
        if balance_status == 'with_balance':
            transactions = [txn for txn in transactions if getattr(txn, 'running_balance', 0) > 0]
        elif balance_status == 'fully_paid':
            transactions = [txn for txn in transactions if getattr(txn, 'running_balance', 0) <= 0]

        return transactions
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        # Provide class list and preserve selected filters for the template
        try:
            from academics.models import Class
            context['classes'] = Class.objects.filter(is_active=True)
        except Exception:
            context['classes'] = []

        selected_class_id = self.request.GET.get('class_id', '')
        selected_balance_status = self.request.GET.get('balance_status', '')
        context['selected_class_id'] = selected_class_id
        context['selected_balance_status'] = selected_balance_status

        # Fee aggregates for summary cards
        class_id_for_calc = selected_class_id or None
        balance_status_for_calc = selected_balance_status or None
        total_expected, total_collected, total_remaining = calculate_fee_aggregates(
            class_id=class_id_for_calc,
            balance_status=balance_status_for_calc
        )
        context['total_expected'] = total_expected
        context['total_collected'] = total_collected
        context['total_remaining'] = total_remaining
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


@method_decorator(csrf_exempt, name='dispatch')
class StudentBalancesView(LoginRequiredMixin, View):
    """API endpoint to get student balances for fee collection modal"""
    
    def get(self, request, school_slug=None):
        if not MODELS_EXIST:
            return JsonResponse({'balances': {}})
        
        # Get all active students with their class assignments
        students_qs = Student.objects.filter(is_active=True, current_class__isnull=False)
        
        # Get fee totals per class per fee type
        class_ids = list(students_qs.values_list('current_class_id', flat=True).distinct())
        fee_totals_qs = FeeStructure.objects.filter(
            class_name_id__in=class_ids,
            is_active=True
        ).values('class_name_id', 'fee_type').annotate(total=models.Sum('amount'))
        
        # Organize fees by class and fee type
        fee_per_class_type = {}
        for row in fee_totals_qs:
            class_id = row['class_name_id']
            fee_type = row['fee_type']
            amount = row['total'] or 0
            if class_id not in fee_per_class_type:
                fee_per_class_type[class_id] = {}
            fee_per_class_type[class_id][fee_type] = amount
        
        # Get paid totals per student per fee type
        student_ids = list(students_qs.values_list('id', flat=True))
        paid_totals_qs = FeeCollection.objects.filter(
            student_id__in=student_ids
        ).values('student_id', 'fee_structure__fee_type').annotate(total=models.Sum('paid_amount'))
        
        # Organize paid amounts by student and fee type
        paid_totals_map = {}
        for row in paid_totals_qs:
            student_id = row['student_id']
            fee_type = row['fee_structure__fee_type']
            amount = row['total'] or 0
            if student_id not in paid_totals_map:
                paid_totals_map[student_id] = {}
            paid_totals_map[student_id][fee_type] = amount
        
        # Calculate balances per student per fee type
        balances = {}
        payment_history = {}
        
        for student in students_qs:
            student_id = str(student.id)
            class_id = student.current_class_id
            
            # Get all fee types for this student's class
            class_fees = fee_per_class_type.get(class_id, {})
            student_paid = paid_totals_map.get(student.id, {})
            
            # Calculate balance for each fee type
            for fee_type, fee_amount in class_fees.items():
                paid_amount = student_paid.get(fee_type, 0)
                balance = max(fee_amount - paid_amount, 0)
                
                # Store as nested structure: {student_id: {fee_type: balance}}
                if student_id not in balances:
                    balances[student_id] = {}
                balances[student_id][fee_type] = float(balance)
                
                # Get payment history for this student and fee type
                payments = FeeCollection.objects.filter(
                    student_id=student.id,
                    fee_structure__fee_type=fee_type
                ).order_by('payment_date')
                
                if student_id not in payment_history:
                    payment_history[student_id] = {}
                payment_history[student_id][fee_type] = []
                
                # Calculate running balance
                running_balance = fee_amount
                for payment in payments:
                    running_balance -= payment.paid_amount
                    payment_history[student_id][fee_type].append({
                        'date': payment.payment_date.strftime('%Y-%m-%d'),
                        'amount_paid': float(payment.paid_amount),
                        'balance_after': float(running_balance)
                    })
        
        return JsonResponse({'balances': balances, 'payment_history': payment_history})
