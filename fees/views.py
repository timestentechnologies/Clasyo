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
    from .models import FeeStructure, FeePayment, Wallet
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class FeeStructure:
        pass
    class FeePayment:
        pass
    class Wallet:
        pass


@method_decorator(csrf_exempt, name='dispatch')
class FeeStructureView(ListView):
    template_name = 'fees/fee_structure.html'
    context_object_name = 'fee_structures'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return FeeStructure.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
                
            FeeStructure.objects.create(
                name=request.POST.get('name'),
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
class CollectFeesView(ListView):
    template_name = 'fees/collect_fees.html'
    context_object_name = 'payments'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return FeePayment.objects.all()
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
                
            FeePayment.objects.create(
                student_id=request.POST.get('student_id'),
                fee_structure_id=request.POST.get('fee_structure_id'),
                amount_paid=request.POST.get('amount_paid'),
                payment_method=request.POST.get('payment_method'),
                transaction_id=request.POST.get('transaction_id', ''),
                note=request.POST.get('note', '')
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
            return FeePayment.objects.all().order_by('-payment_date')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            total_collected = FeePayment.objects.aggregate(total=models.Sum('amount_paid'))['total'] or 0
        else:
            total_collected = 0
        context['total_collected'] = total_collected
        return context


class WalletView(LoginRequiredMixin, ListView):
    template_name = 'fees/wallet.html'
    context_object_name = 'wallets'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Wallet.objects.all()
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
            return FeePayment.objects.filter(student=student).order_by('-payment_date')
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            context['student'] = student
            
            # Calculate fee statistics
            if MODELS_EXIST:
                total_paid = FeePayment.objects.filter(student=student).aggregate(
                    total=models.Sum('amount_paid'))['total'] or 0
                context['total_paid'] = total_paid
                
                # Get fee structures for the student's class (if available)
                context['fee_structures'] = FeeStructure.objects.filter(is_active=True)[:5]
            else:
                context['total_paid'] = 0
                context['fee_structures'] = []
        
        return context
