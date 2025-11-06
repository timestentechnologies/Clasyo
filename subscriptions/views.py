from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import SubscriptionPlan, Subscription, Payment, Coupon
from datetime import timedelta
import json


class SubscriptionPlansView(ListView):
    """View to display all subscription plans"""
    model = SubscriptionPlan
    template_name = 'subscriptions/plans.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True)


class SubscribeView(View):
    """View to handle subscription purchase"""
    template_name = 'subscriptions/subscribe.html'
    
    def get(self, request, plan_slug):
        plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
        context = {
            'plan': plan,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, plan_slug):
        plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
        payment_method = request.POST.get('payment_method')
        
        # Create subscription
        with transaction.atomic():
            # Calculate dates
            start_date = timezone.now().date()
            if plan.trial_days > 0:
                end_date = start_date + timedelta(days=plan.trial_days)
                is_trial = True
            else:
                if plan.billing_cycle == 'monthly':
                    end_date = start_date + timedelta(days=30)
                elif plan.billing_cycle == 'quarterly':
                    end_date = start_date + timedelta(days=90)
                elif plan.billing_cycle == 'half_yearly':
                    end_date = start_date + timedelta(days=180)
                elif plan.billing_cycle == 'yearly':
                    end_date = start_date + timedelta(days=365)
                is_trial = False
            
            # Create subscription (will be linked to school during tenant creation)
            subscription = Subscription.objects.create(
                plan=plan,
                start_date=start_date,
                end_date=end_date,
                is_trial=is_trial,
                status='pending'
            )
            
            # Create payment record
            payment = Payment.objects.create(
                subscription=subscription,
                amount=plan.price if not is_trial else 0,
                payment_method=payment_method,
                status='pending'
            )
            
            # Redirect to payment processing
            return redirect('subscriptions:payment', payment_id=payment.payment_id)


class PaymentView(View):
    """View to handle payment processing"""
    template_name = 'subscriptions/payment.html'
    
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, payment_id=payment_id)
        context = {
            'payment': payment,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, payment_id=payment_id)
        
        # Process payment based on payment method
        # This is a simplified version - implement actual payment gateway integration
        
        payment.status = 'completed'
        payment.payment_date = timezone.now()
        payment.transaction_id = f"TXN-{timezone.now().timestamp()}"
        payment.save()
        
        # Activate subscription
        subscription = payment.subscription
        subscription.status = 'active'
        subscription.save()
        
        messages.success(request, 'Payment successful! Your subscription is now active.')
        return redirect('subscriptions:payment_success')


class PaymentSuccessView(TemplateView):
    """Payment success page"""
    template_name = 'subscriptions/payment_success.html'


class PaymentFailedView(TemplateView):
    """Payment failed page"""
    template_name = 'subscriptions/payment_failed.html'


class MySubscriptionView(DetailView):
    """View to display user's current subscription"""
    model = Subscription
    template_name = 'subscriptions/my_subscription.html'
    context_object_name = 'subscription'
    
    def get_object(self):
        # Get current active subscription for the tenant
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q
        
        # This will be tenant-specific
        return Subscription.objects.filter(
            status='active'
        ).order_by('-created_at').first()


class RenewSubscriptionView(View):
    """View to renew subscription"""
    def post(self, request):
        # Get current subscription
        current_subscription = Subscription.objects.filter(
            status__in=['active', 'expired']
        ).order_by('-created_at').first()
        
        if not current_subscription:
            messages.error(request, 'No subscription found to renew.')
            return redirect('subscriptions:plans')
        
        # Create new subscription with same plan
        plan = current_subscription.plan
        return redirect('subscriptions:subscribe', plan_slug=plan.slug)


class CancelSubscriptionView(View):
    """View to cancel subscription"""
    def post(self, request):
        subscription = Subscription.objects.filter(
            status='active'
        ).order_by('-created_at').first()
        
        if subscription:
            subscription.status = 'cancelled'
            subscription.auto_renew = False
            subscription.save()
            messages.success(request, 'Subscription cancelled successfully.')
        else:
            messages.error(request, 'No active subscription found.')
        
        return redirect('subscriptions:my_subscription')


class ApplyCouponView(View):
    """View to apply coupon code"""
    def post(self, request):
        coupon_code = request.POST.get('coupon_code')
        plan_id = request.POST.get('plan_id')
        
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            
            if not coupon.is_valid():
                return json.dumps({'success': False, 'message': 'Invalid or expired coupon.'})
            
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # Check if coupon is applicable to this plan
            if coupon.applicable_plans.exists() and plan not in coupon.applicable_plans.all():
                return json.dumps({'success': False, 'message': 'Coupon not applicable to this plan.'})
            
            # Calculate discount
            if coupon.discount_type == 'percentage':
                discount = (plan.price * coupon.discount_value) / 100
                if coupon.max_discount and discount > coupon.max_discount:
                    discount = coupon.max_discount
            else:
                discount = coupon.discount_value
            
            final_price = max(0, plan.price - discount)
            
            return json.dumps({
                'success': True,
                'discount': float(discount),
                'final_price': float(final_price)
            })
            
        except Coupon.DoesNotExist:
            return json.dumps({'success': False, 'message': 'Invalid coupon code.'})
        except Exception as e:
            return json.dumps({'success': False, 'message': str(e)})
