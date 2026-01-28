from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import SubscriptionPlan, Subscription, Payment, Coupon, Invoice
from tenants.models import School
from superadmin.models import SchoolPaymentConfiguration, PaymentConfiguration
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
    """View to handle subscription purchase - returns payment modal data"""
    
    def get(self, request, plan_slug):
        plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)

        school = getattr(request, 'school', None) or getattr(request, 'tenant', None) or getattr(request.user, 'school', None)
        if not school:
            slug = request.GET.get('school_slug')
            if slug:
                school = School.objects.filter(slug=slug).first()

        methods = []
        icon_map = {
            'mpesa_stk': '📱',
            'mpesa_paybill': '📱',
            'mpesa_buygoods': '🛒',
            'mpesa_send_money': '💸',
            'mpesa_pochi': '🧺',
            'paypal': '💳',
            'bank': '🏦',
            'cash': '💵',
            'cheque': '🧾',
        }
        name_map = {
            'mpesa_stk': 'M-Pesa STK Push',
            'mpesa_paybill': 'M-Pesa Paybill',
            'mpesa_buygoods': 'Lipa na M-Pesa (Buy Goods & Services)',
            'mpesa_send_money': 'M-Pesa Send Money',
            'mpesa_pochi': 'M-Pesa Pochi la Biashara',
            'paypal': 'PayPal',
            'bank': 'Bank Transfer',
            'cash': 'Cash',
            'cheque': 'Cheque',
        }

        # Use superadmin (global) payment configurations for subscription payments
        configs = PaymentConfiguration.objects.filter(is_active=True)
        for cfg in configs:
            gw = cfg.gateway
            if gw not in name_map:
                continue
            method_id = gw if gw != 'bank' else 'bank_transfer'
            details = {}
            if gw == 'mpesa_stk':
                if cfg.mpesa_shortcode:
                    details['shortcode'] = cfg.mpesa_shortcode
            elif gw == 'mpesa_paybill':
                if cfg.mpesa_paybill_number:
                    details['paybill_number'] = cfg.mpesa_paybill_number
                if hasattr(cfg, 'mpesa_paybill_account_name') and cfg.mpesa_paybill_account_name:
                    details['account_name'] = cfg.mpesa_paybill_account_name
                if hasattr(cfg, 'mpesa_paybill_instructions') and cfg.mpesa_paybill_instructions:
                    details['instructions'] = cfg.mpesa_paybill_instructions
            elif gw == 'mpesa_buygoods':
                if hasattr(cfg, 'mpesa_till_number') and cfg.mpesa_till_number:
                    details['till_number'] = cfg.mpesa_till_number
                if hasattr(cfg, 'mpesa_buygoods_instructions') and cfg.mpesa_buygoods_instructions:
                    details['instructions'] = cfg.mpesa_buygoods_instructions
            elif gw == 'mpesa_send_money':
                if hasattr(cfg, 'mpesa_send_money_recipient') and cfg.mpesa_send_money_recipient:
                    details['recipient'] = cfg.mpesa_send_money_recipient
                if hasattr(cfg, 'mpesa_send_money_instructions') and cfg.mpesa_send_money_instructions:
                    details['instructions'] = cfg.mpesa_send_money_instructions
            elif gw == 'mpesa_pochi':
                if hasattr(cfg, 'mpesa_pochi_number') and cfg.mpesa_pochi_number:
                    details['pochi_number'] = cfg.mpesa_pochi_number
                if hasattr(cfg, 'mpesa_pochi_instructions') and cfg.mpesa_pochi_instructions:
                    details['instructions'] = cfg.mpesa_pochi_instructions
            elif gw == 'bank':
                if cfg.bank_name:
                    details['bank_name'] = cfg.bank_name
                if cfg.bank_account_name:
                    details['account_name'] = cfg.bank_account_name
                if cfg.bank_account_number:
                    details['account_number'] = cfg.bank_account_number
                if cfg.bank_branch:
                    details['branch'] = cfg.bank_branch
            elif gw == 'paypal':
                # For subscriptions, show PayPal availability if configured
                if cfg.paypal_client_id:
                    details['paypal_email'] = ''
            # cash/cheque and other gateways may not have extra details globally
            methods.append({
                'id': method_id,
                'name': name_map.get(gw, gw),
                'icon': icon_map.get(gw, ''),
                'details': details
            })

        return JsonResponse({
            'success': True,
            'plan': {
                'id': plan.id,
                'name': plan.name,
                'slug': plan.slug,
                'price': float(plan.price),
                'billing_cycle': plan.billing_cycle,
                'description': plan.description,
                'features': plan.features,
                'trial_days': plan.trial_days
            },
            'payment_methods': methods
        })
    
    def post(self, request, plan_slug):
        try:
            plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
            payment_method = request.POST.get('payment_method')
            
            with transaction.atomic():
                # Calculate subscription dates for a paid purchase.
                # Do NOT start/extend a trial here even if the plan has trial_days configured.
                start_date = timezone.now().date()
                if plan.billing_cycle == 'monthly':
                    end_date = start_date + timedelta(days=30)
                elif plan.billing_cycle == 'quarterly':
                    end_date = start_date + timedelta(days=90)
                elif plan.billing_cycle == 'half_yearly':
                    end_date = start_date + timedelta(days=180)
                elif plan.billing_cycle == 'yearly':
                    end_date = start_date + timedelta(days=365)
                else:
                    end_date = start_date + timedelta(days=30)
                is_trial = False
                
                # Resolve school (user.school, request.tenant, or posted school_slug)
                school = getattr(request.user, 'school', None) or getattr(request, 'tenant', None)
                if not school:
                    school_slug = request.POST.get('school_slug')
                    if school_slug:
                        school = School.objects.filter(slug=school_slug).first()
                if not school:
                    return JsonResponse({'success': False, 'error': 'School context not found. Please access this page from your school account.'}, status=400)

                # Server-side guard: disallow upgrading/subscribing to a free plan if a free offer was already used
                try:
                    if float(plan.price) == 0:
                        current_sub = school.subscriptions.order_by('-created_at').first()
                        current_free = bool(current_sub and current_sub.plan and float(getattr(current_sub.plan, 'price', 0)) == 0)
                        has_trial_invoice = Invoice.objects.filter(school=school, invoice_type='trial_end').exists()
                        has_past_free_invoice = Invoice.objects.filter(
                            school=school,
                            invoice_type__in=['new', 'renewal', 'upgrade'],
                            total_amount=0
                        ).exists()
                        past_free_sub_qs = school.subscriptions.filter(plan__price=0)
                        if current_sub:
                            past_free_sub_qs = past_free_sub_qs.exclude(id=current_sub.id)
                        has_past_free_sub = past_free_sub_qs.exists()
                        if not current_free and (has_trial_invoice or has_past_free_invoice or has_past_free_sub):
                            return JsonResponse({'success': False, 'error': 'You have already used your free plan limit.'}, status=400)
                except Exception:
                    # On any error in detection, do not block paid flows
                    pass

                # Validate selected method is enabled globally (superadmin)
                method_to_gateway = {
                    'bank_transfer': 'bank',
                    'paypal': 'paypal',
                    'mpesa_paybill': 'mpesa_paybill',
                    'mpesa_stk': 'mpesa_stk',
                    'mpesa_buygoods': 'mpesa_buygoods',
                    'mpesa_send_money': 'mpesa_send_money',
                    'mpesa_pochi': 'mpesa_pochi',
                    'cash': 'cash',
                    'cheque': 'cheque',
                }
                gw = method_to_gateway.get(payment_method)
                if not gw or not PaymentConfiguration.objects.filter(gateway=gw, is_active=True).exists():
                    return JsonResponse({'success': False, 'error': 'Selected payment method is not available.'}, status=400)

                # Create subscription linked to school
                subscription = Subscription.objects.create(
                    school=school,
                    plan=plan,
                    start_date=start_date,
                    end_date=end_date,
                    is_trial=is_trial,
                    status='pending'
                )

                # Create payment record and store method-specific details
                amount = plan.price
                payment = Payment(
                    subscription=subscription,
                    amount=amount,
                    payment_method=payment_method,
                    status='pending'
                )

                if payment_method == 'cash':
                    payment.invoice_number_ref = request.POST.get('invoice_number', '')
                    payment.status = 'pending_verification'
                elif payment_method in ['mpesa_paybill', 'mpesa_stk', 'mpesa_buygoods', 'mpesa_send_money', 'mpesa_pochi']:
                    payment.phone_number = request.POST.get('phone_number', '')
                    payment.full_name = request.POST.get('full_name', '')
                    if payment_method in ['mpesa_paybill', 'mpesa_buygoods', 'mpesa_send_money', 'mpesa_pochi']:
                        payment.transaction_id = request.POST.get('transaction_id', '')
                        payment.status = 'pending_verification'
                    # mpesa_stk remains 'pending' to be processed asynchronously
                elif payment_method == 'bank_transfer':
                    payment.full_name = request.POST.get('full_name', '')
                    payment.account_name = request.POST.get('account_name', '')
                    payment.account_number = request.POST.get('account_number', '')
                    payment.transaction_id = request.POST.get('transaction_id', '')
                    payment.status = 'pending_verification'
                elif payment_method == 'paypal':
                    payment.paypal_email = request.POST.get('paypal_email', '')
                    # remains 'pending'
                elif payment_method == 'cheque':
                    payment.transaction_id = request.POST.get('transaction_id', '')
                    payment.status = 'pending_verification'
                else:
                    payment.status = 'pending_verification'

                payment.save()

                # Update school's visible subscription fields to reflect the new subscription immediately
                try:
                    school.subscription_plan = plan
                    if is_trial:
                        school.is_trial = True
                        school.trial_end_date = end_date
                        # Clear paid subscription dates for clarity
                        school.subscription_start_date = None
                        school.subscription_end_date = None
                    else:
                        school.is_trial = False
                        school.subscription_start_date = start_date
                        school.subscription_end_date = end_date
                    school.save(update_fields=[
                        'subscription_plan', 'is_trial', 'trial_end_date',
                        'subscription_start_date', 'subscription_end_date'
                    ])
                except Exception:
                    # Do not fail purchase flow if school update fails
                    pass

                # Send email notifications (school + superadmins)
                try:
                    User = get_user_model()
                    school_admin_emails = list(
                        User.objects.filter(school=school, role='school_admin', is_active=True)
                        .values_list('email', flat=True)
                    )
                    superadmin_emails = list(
                        User.objects.filter(role='superadmin', is_active=True)
                        .values_list('email', flat=True)
                    )
                    # Deduplicate recipients
                    recipients_school = [e for e in [school.email] + school_admin_emails if e]
                    recipients_super = [e for e in superadmin_emails if e]
                    subject = f"Payment Submitted - {school.name} - {plan.name}"
                    message = (
                        f"A payment has been submitted and is pending verification.\n\n"
                        f"School: {school.name}\n"
                        f"Plan: {plan.name}\n"
                        f"Amount: {amount} {getattr(settings, 'DEFAULT_CURRENCY', 'KES')}\n"
                        f"Method: {payment.payment_method}\n"
                        f"Payment ID: {payment.payment_id}\n"
                        f"Status: {payment.status}\n\n"
                        f"You will receive another email once the payment is approved."
                    )
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    if recipients_school:
                        send_mail(subject, message, from_email, recipients_school, fail_silently=True)
                    if recipients_super:
                        send_mail(f"[Admin] {subject}", message, from_email, recipients_super, fail_silently=True)
                except Exception:
                    pass

                billing_url = reverse('core:billing', kwargs={'school_slug': school.slug})
                return JsonResponse({'success': True, 'redirect_url': f"{billing_url}?submitted=1"})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class PaymentView(View):
    """View to handle payment processing"""
    template_name = 'subscriptions/payment.html'
    
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, payment_id=payment_id)
        context = {
            'payment': payment,
            'payment_methods': [
                {'id': 'cash', 'name': 'Cash', 'icon': '💵'},
                {'id': 'mpesa_paybill', 'name': 'M-Pesa Paybill', 'icon': '📱'},
                {'id': 'mpesa_stk', 'name': 'M-Pesa STK Push', 'icon': '📱'},
                {'id': 'bank_transfer', 'name': 'Bank Transfer', 'icon': '🏦'},
                {'id': 'paypal', 'name': 'PayPal', 'icon': '💳'}
            ]
        }
        return render(request, self.template_name, context)
    
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, payment_id=payment_id)
        payment_method = request.POST.get('payment_method', payment.payment_method)
        
        # Update payment method and details
        payment.payment_method = payment_method
        
        # Store payment method specific details
        if payment_method == 'cash':
            payment.invoice_number_ref = request.POST.get('invoice_number', '')
        elif payment_method in ['mpesa_paybill', 'mpesa_stk']:
            payment.phone_number = request.POST.get('phone_number', '')
            payment.full_name = request.POST.get('full_name', '')
            if payment_method == 'mpesa_paybill':
                payment.transaction_id = request.POST.get('transaction_id', '')
        elif payment_method == 'bank_transfer':
            payment.full_name = request.POST.get('full_name', '')
            payment.account_name = request.POST.get('account_name', '')
            payment.account_number = request.POST.get('account_number', '')
            payment.transaction_id = request.POST.get('transaction_id', '')
        elif payment_method == 'paypal':
            payment.paypal_email = request.POST.get('paypal_email', '')
        
        # Set status to pending verification for manual payment methods
        if payment_method in ['cash', 'mpesa_paybill', 'bank_transfer']:
            payment.status = 'pending_verification'
            messages.info(request, 'Payment submitted! Your payment is now pending verification by our team.')
        elif payment_method == 'mpesa_stk':
            payment.status = 'pending'
            messages.info(request, 'M-Pesa STK Push initiated! Please complete the payment on your phone.')
        elif payment_method == 'paypal':
            payment.status = 'pending'
            messages.info(request, 'Redirecting to PayPal for payment...')
            # TODO: Implement PayPal redirect
            # For now, just mark as pending
        else:
            payment.status = 'pending_verification'
        
        payment.save()
        
        # For online payment methods, redirect to payment processing
        if payment_method in ['mpesa_stk', 'paypal']:
            return redirect('subscriptions:payment_processing', payment_id=payment.payment_id)
        else:
            # For manual payment methods, show success message
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
