from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import models
from students.models import Student
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
                collected_by=request.user,
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
            total_collected = FeeCollection.objects.aggregate(total=models.Sum('amount_paid'))['total'] or 0
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
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            context['student'] = student
            
            # Calculate fee statistics
            if MODELS_EXIST:
                total_paid = FeeCollection.objects.filter(student=student).aggregate(
                    total=models.Sum('amount_paid'))['total'] or 0
                context['total_paid'] = total_paid
                
                # Get fee structures for the student's class (if available)
                context['fee_structures'] = FeeStructure.objects.filter(is_active=True)[:5]
            else:
                context['total_paid'] = 0
                context['fee_structures'] = []
        
        return context
