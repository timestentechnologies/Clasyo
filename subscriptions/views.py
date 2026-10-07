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
import urllib.parse


def resolve_school(request, school_slug=None):
    """Safely resolve the active school across request, user, session, or parameters without throwing DoesNotExist."""
    if school_slug:
        try:
            school = School.objects.using('default').filter(slug=school_slug).first()
            if school:
                return school
        except Exception:
            pass

    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        try:
            school = getattr(user, 'school', None)
            if school:
                return school
        except Exception:
            pass

        try:
            school_id = getattr(user, 'school_id', None)
            if school_id:
                school = School.objects.using('default').filter(id=school_id).first()
                if school:
                    return school
        except Exception:
            pass

    slug = request.GET.get('school_slug') or request.POST.get('school_slug')
    if slug:
        try:
            school = School.objects.using('default').filter(slug=slug).first()
            if school:
                return school
        except Exception:
            pass

    # Check session for impersonated or active school
    try:
        sess_school_id = request.session.get('impersonate_school_id') or request.session.get('active_school_id') or request.session.get('school_id')
        if sess_school_id:
            school = School.objects.using('default').filter(id=sess_school_id).first()
            if school:
                return school
    except Exception:
        pass

    # Fallback to first active school for single-tenant / local development
    try:
        school = School.objects.using('default').filter(is_active=True).first() or School.objects.using('default').first()
        if school:
            return school
    except Exception:
        pass

    return None


class SubscriptionPlansView(ListView):
    """View to display all subscription plans"""
    model = SubscriptionPlan
    template_name = 'subscriptions/plans.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        return SubscriptionPlan.objects.using('default').filter(is_active=True).exclude(price=0)

    def dispatch(self, request, *args, **kwargs):
        """If a logged-in school user lands here, send them to Billing which shows plans."""
        school = resolve_school(request)
        if request.user.is_authenticated and school:
            return redirect('core:billing', school_slug=school.slug)
        return super().dispatch(request, *args, **kwargs)


class SubscribeView(View):
    """View to handle subscription purchase - returns payment modal data for AJAX or redirects browser to Billing"""
    
    def get(self, request, plan_slug=None, *args, **kwargs):
        try:
            # Query plan from master database safely with fallback casing, name, and id lookup
            raw_identifier = (
                plan_slug or 
                request.GET.get('plan_slug') or 
                request.GET.get('plan_id') or 
                request.GET.get('slug') or 
                ''
            )
            clean_identifier = urllib.parse.unquote(str(raw_identifier)).strip().strip("'\"")

            plan = None
            if clean_identifier:
                plan = SubscriptionPlan.objects.using('default').filter(slug=clean_identifier, is_active=True).first()
                if not plan:
                    plan = SubscriptionPlan.objects.using('default').filter(slug__iexact=clean_identifier, is_active=True).first()
                if not plan and clean_identifier.isdigit():
                    plan = SubscriptionPlan.objects.using('default').filter(id=int(clean_identifier), is_active=True).first()
                if not plan:
                    plan = SubscriptionPlan.objects.using('default').filter(name__iexact=clean_identifier, is_active=True).first()

            plan_id = request.GET.get('plan_id')
            if not plan and plan_id and str(plan_id).isdigit():
                plan = SubscriptionPlan.objects.using('default').filter(id=int(plan_id), is_active=True).first()

            school = resolve_school(request, school_slug=kwargs.get('school_slug'))

            # Direct browser page navigations (e.g. typing URL in address bar or link navigation)
            # should redirect to the school's billing checkout page with payment modal opened.
            # Fetch / API requests should ALWAYS return JSON.
            accept_header = (request.headers.get('accept') or '').lower()
            is_explicit_api = (
                request.GET.get('format') == 'json' or
                request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                'application/json' in accept_header or
                request.headers.get('sec-fetch-mode') in ('cors', 'same-origin')
            )

            is_browser_navigation = (
                not is_explicit_api and (
                    request.headers.get('sec-fetch-mode') == 'navigate' or
                    request.headers.get('sec-fetch-dest') == 'document' or
                    accept_header.startswith('text/html')
                )
            )

            if is_browser_navigation:
                plan_slug_param = plan.slug if plan else clean_identifier
                if school:
                    billing_url = reverse('core:billing', kwargs={'school_slug': school.slug})
                    return redirect(f"{billing_url}?plan_slug={plan_slug_param}&action=renew")
                return redirect(f"{reverse('subscriptions:plans')}?plan_slug={plan_slug_param}&action=renew")

            if not plan:
                return JsonResponse({
                    'success': False,
                    'error': f"Subscription plan '{raw_identifier}' was not found or is currently inactive."
                }, status=404)

            school = resolve_school(request, school_slug=kwargs.get('school_slug'))

            methods = []
            icon_map = {
                'mpesa': '📱',
                'mpesa_stk': '📱',
                'mpesa_paybill': '📱',
                'mpesa_buygoods': '🛒',
                'mpesa_send_money': '💸',
                'mpesa_pochi': '🧺',
                'paypal': '💳',
                'stripe': '💳',
                'bank': '🏦',
                'cash': '💵',
                'cheque': '🧾',
            }
            name_map = {
                'mpesa': 'M-Pesa STK Push',
                'mpesa_stk': 'M-Pesa STK Push',
                'mpesa_paybill': 'M-Pesa Paybill',
                'mpesa_buygoods': 'Lipa na M-Pesa (Buy Goods & Services)',
                'mpesa_send_money': 'M-Pesa Send Money',
                'mpesa_pochi': 'M-Pesa Pochi la Biashara',
                'paypal': 'PayPal',
                'stripe': 'Stripe',
                'bank': 'Bank Transfer',
                'cash': 'Cash',
                'cheque': 'Cheque',
            }

            # Query global payment configurations, fallback to current DB or school configs if none found
            configs = []
            try:
                configs = list(PaymentConfiguration.objects.using('default').filter(is_active=True))
            except Exception:
                pass
            if not configs:
                try:
                    configs = list(PaymentConfiguration.objects.filter(is_active=True))
                except Exception:
                    pass
            if not configs and school:
                try:
                    configs = list(SchoolPaymentConfiguration.objects.using('default').filter(school=school, is_active=True))
                except Exception:
                    pass
                if not configs:
                    try:
                        configs = list(SchoolPaymentConfiguration.objects.filter(school=school, is_active=True))
                    except Exception:
                        pass

            for cfg in configs:
                gw = cfg.gateway
                normalized_gw = 'mpesa_stk' if gw == 'mpesa' else gw
                method_id = normalized_gw if normalized_gw != 'bank' else 'bank_transfer'
                details = {}

                shortcode = getattr(cfg, 'mpesa_shortcode', None) or getattr(cfg, 'shortcode', None)
                till_number = getattr(cfg, 'mpesa_till_number', None) or getattr(cfg, 'till_number', None)
                paybill_number = getattr(cfg, 'mpesa_paybill_number', None) or getattr(cfg, 'paybill_number', None)
                account_name = getattr(cfg, 'mpesa_paybill_account_name', None) or getattr(cfg, 'account_name', None)
                recipient = getattr(cfg, 'mpesa_send_money_recipient', None) or getattr(cfg, 'phone_number', None)
                pochi_number = getattr(cfg, 'mpesa_pochi_number', None) or getattr(cfg, 'phone_number', None)

                if normalized_gw == 'mpesa_stk':
                    if shortcode:
                        details['shortcode'] = shortcode
                    if till_number:
                        details['till_number'] = till_number
                    if paybill_number:
                        details['paybill_number'] = paybill_number
                elif normalized_gw == 'mpesa_paybill':
                    if paybill_number:
                        details['paybill_number'] = paybill_number
                    elif shortcode:
                        details['paybill_number'] = shortcode
                    if account_name:
                        details['account_name'] = account_name
                    if getattr(cfg, 'mpesa_paybill_instructions', None):
                        details['instructions'] = cfg.mpesa_paybill_instructions
                elif normalized_gw == 'mpesa_buygoods':
                    if till_number:
                        details['till_number'] = till_number
                    elif shortcode:
                        details['till_number'] = shortcode
                    if getattr(cfg, 'mpesa_buygoods_instructions', None):
                        details['instructions'] = cfg.mpesa_buygoods_instructions
                elif normalized_gw == 'mpesa_send_money':
                    if recipient:
                        details['recipient'] = recipient
                    elif shortcode:
                        details['recipient'] = shortcode
                    if getattr(cfg, 'mpesa_send_money_instructions', None):
                        details['instructions'] = cfg.mpesa_send_money_instructions
                elif normalized_gw == 'mpesa_pochi':
                    if pochi_number:
                        details['pochi_number'] = pochi_number
                    elif recipient:
                        details['pochi_number'] = recipient
                    if getattr(cfg, 'mpesa_pochi_instructions', None):
                        details['instructions'] = cfg.mpesa_pochi_instructions
                elif normalized_gw in ('bank', 'bank_transfer'):
                    if getattr(cfg, 'bank_name', None):
                        details['bank_name'] = cfg.bank_name
                    if getattr(cfg, 'bank_account_name', None):
                        details['account_name'] = cfg.bank_account_name
                    if getattr(cfg, 'bank_account_number', None):
                        details['account_number'] = cfg.bank_account_number
                    if getattr(cfg, 'bank_branch', None):
                        details['branch'] = cfg.bank_branch
                elif normalized_gw == 'paypal':
                    if getattr(cfg, 'paypal_client_id', None):
                        details['paypal_email'] = ''
                elif normalized_gw == 'stripe':
                    if getattr(cfg, 'stripe_publishable_key', None):
                        details['publishable_key'] = cfg.stripe_publishable_key

                display_name = (
                    name_map.get(gw) or 
                    name_map.get(normalized_gw) or 
                    (getattr(cfg, 'get_gateway_display', None) and cfg.get_gateway_display()) or 
                    str(gw).replace('_', ' ').title()
                )
                icon = icon_map.get(gw) or icon_map.get(normalized_gw) or '💳'

                methods.append({
                    'id': method_id,
                    'gateway': gw,
                    'name': display_name,
                    'icon': icon,
                    'details': details
                })

            features_data = plan.features
            if isinstance(features_data, str):
                try:
                    features_data = json.loads(features_data)
                except Exception:
                    features_data = [f.strip() for f in features_data.split('\n') if f.strip()]
            elif not features_data:
                features_data = {}

            return JsonResponse({
                'success': True,
                'plan': {
                    'id': plan.id,
                    'name': plan.name,
                    'slug': plan.slug,
                    'price': float(plan.price),
                    'billing_cycle': plan.billing_cycle,
                    'discount_percentage': float(plan.discount_percentage or 0),
                    'yearly_discount_percentage': float(plan.yearly_discount_percentage or 0),
                    'period_price': float(plan.get_period_price),
                    'annual_base_price': float(plan.get_annual_base_price),
                    'annual_price': float(plan.get_annual_price),
                    'annual_savings': float(plan.get_annual_savings),
                    'annual_term_equivalent': float(plan.get_annual_term_equivalent),
                    'description': plan.description,
                    'features': features_data,
                    'trial_days': plan.trial_days
                },
                'payment_methods': methods
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"Error loading payment methods: {str(e)}"
            }, status=500)
    
    def post(self, request, plan_slug=None, *args, **kwargs):
        try:
            raw_identifier = (
                plan_slug or 
                request.POST.get('plan_slug') or 
                request.POST.get('plan_id') or 
                request.GET.get('plan_slug') or 
                request.GET.get('plan_id') or 
                ''
            )
            clean_identifier = urllib.parse.unquote(str(raw_identifier)).strip().strip("'\"")

            plan = None
            if clean_identifier:
                plan = SubscriptionPlan.objects.using('default').filter(slug=clean_identifier, is_active=True).first()
                if not plan:
                    plan = SubscriptionPlan.objects.using('default').filter(slug__iexact=clean_identifier, is_active=True).first()
                if not plan and clean_identifier.isdigit():
                    plan = SubscriptionPlan.objects.using('default').filter(id=int(clean_identifier), is_active=True).first()
                if not plan:
                    plan = SubscriptionPlan.objects.using('default').filter(name__iexact=clean_identifier, is_active=True).first()

            plan_id = request.POST.get('plan_id') or request.GET.get('plan_id')
            if not plan and plan_id and str(plan_id).isdigit():
                plan = SubscriptionPlan.objects.using('default').filter(id=int(plan_id), is_active=True).first()

            if not plan:
                return JsonResponse({'success': False, 'error': f"Plan '{raw_identifier}' not found."}, status=404)
            payment_method = request.POST.get('payment_method')
            
            with transaction.atomic():
                # Determine billing cycle and calculate discounted amounts
                requested_cycle = (request.POST.get('billing_cycle') or request.GET.get('billing_cycle') or plan.billing_cycle or '').lower()
                is_yearly = requested_cycle in ('yearly', 'annually')
                
                if is_yearly:
                    sub_cycle = 'yearly'
                    base_amount = plan.get_annual_base_price
                    discount_amount = plan.get_annual_savings
                    final_amount = plan.get_annual_price
                    cycle_days = 365
                else:
                    sub_cycle = plan.billing_cycle or 'termly'
                    base_amount = plan.price
                    discount_amount = plan.get_period_savings
                    final_amount = plan.get_period_price
                    days_map = {
                        'monthly': 30,
                        'termly': 90,
                        'quarterly': 90,
                        'half_yearly': 180,
                        'yearly': 365,
                    }
                    cycle_days = days_map.get(plan.billing_cycle, 90)

                start_date = timezone.now().date()
                end_date = start_date + timedelta(days=cycle_days)
                is_trial = False
                
                # Resolve school safely
                school = resolve_school(request, school_slug=kwargs.get('school_slug'))
                if not school:
                    return JsonResponse({'success': False, 'error': 'School context not found. Please access this page from your school account.'}, status=400)

                # Server-side guard: disallow upgrading/subscribing to a free plan if a free offer was already used
                try:
                    if float(plan.price) == 0:
                        current_sub = school.subscriptions.using('default').order_by('-created_at').first()
                        current_free = bool(current_sub and current_sub.plan and float(getattr(current_sub.plan, 'price', 0)) == 0)
                        has_trial_invoice = Invoice.objects.using('default').filter(school=school, invoice_type='trial_end').exists()
                        has_past_free_invoice = Invoice.objects.using('default').filter(
                            school=school,
                            invoice_type__in=['new', 'renewal', 'upgrade'],
                            total_amount=0
                        ).exists()
                        past_free_sub_qs = school.subscriptions.using('default').filter(plan__price=0)
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
                    'stripe': 'stripe',
                    'mpesa_paybill': 'mpesa_paybill',
                    'mpesa_stk': 'mpesa_stk',
                    'mpesa_buygoods': 'mpesa_buygoods',
                    'mpesa_send_money': 'mpesa_send_money',
                    'mpesa_pochi': 'mpesa_pochi',
                    'cash': 'cash',
                    'cheque': 'cheque',
                }
                gw = method_to_gateway.get(payment_method)
                if not gw or not PaymentConfiguration.objects.using('default').filter(gateway=gw, is_active=True).exists():
                    return JsonResponse({'success': False, 'error': 'Selected payment method is not available.'}, status=400)

                # Create subscription linked to school
                subscription = Subscription.objects.using('default').create(
                    school=school,
                    plan=plan,
                    billing_cycle=sub_cycle,
                    discount_applied=discount_amount,
                    start_date=start_date,
                    end_date=end_date,
                    is_trial=is_trial,
                    status='pending'
                )

                # Create payment record
                amount = final_amount
                payment = Payment(
                    subscription=subscription,
                    amount=amount,
                    payment_method=payment_method,
                    status='pending'
                )

                # Create or update invoice with accurate discount applied
                cycle_label = "Annual" if is_yearly else plan.get_billing_cycle_display()
                inv_desc = f"{plan.name} - {cycle_label} subscription"
                if discount_amount > 0:
                    inv_desc += f" (Includes Ksh {discount_amount:,.2f} discount)"
                
                invoice = Invoice.objects.using('default').create(
                    school=school,
                    subscription=subscription,
                    invoice_type='new',
                    plan_name=f"{plan.name} ({cycle_label})",
                    plan_description=inv_desc,
                    amount=base_amount,
                    discount_amount=discount_amount,
                    tax_amount=0,
                    total_amount=final_amount,
                    due_date=end_date,
                    billing_start_date=start_date,
                    billing_end_date=end_date,
                    status='sent'
                )
                payment.invoice_number_ref = invoice.invoice_number

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


class MySubscriptionView(View):
    """Redirect users to the Billing page instead of rendering a separate subscription page."""
    def get(self, request):
        school = resolve_school(request)
        if school:
            return redirect('core:billing', school_slug=school.slug)
        messages.info(request, 'Please access billing from your school dashboard.')
        return redirect('frontend:home')


class RenewSubscriptionView(View):
    """View to renew subscription"""
    def post(self, request):
        school = resolve_school(request)
        # Get current subscription
        sub_qs = Subscription.objects.using('default').filter(status__in=['active', 'expired'])
        if school:
            sub_qs = sub_qs.filter(school=school)
        current_subscription = sub_qs.order_by('-created_at').first()
        
        if not current_subscription:
            messages.error(request, 'No subscription found to renew.')
            if school:
                return redirect('core:billing', school_slug=school.slug)
            return redirect('subscriptions:plans')
        
        # Open renewal checkout for same plan
        plan = current_subscription.plan
        if school:
            billing_url = reverse('core:billing', kwargs={'school_slug': school.slug})
            return redirect(f"{billing_url}?plan_slug={plan.slug}&action=renew")
        return redirect(f"{reverse('subscriptions:plans')}?plan_slug={plan.slug}&action=renew")

    def get(self, request):
        return self.post(request)


class CancelSubscriptionView(View):
    """View to cancel subscription"""
    def post(self, request):
        today = timezone.now().date()
        school = resolve_school(request)
        if not school:
            messages.error(request, 'School context not found.')
            return redirect('frontend:home')
        subscription = Subscription.objects.using('default').filter(school=school, status='active').order_by('-created_at').first()

        if subscription:
            subscription.status = 'cancelled'
            subscription.auto_renew = False
            subscription.save(using='default')
            can_reactivate = bool(subscription.end_date and subscription.end_date >= today)
            messages.success(request, 'Subscription cancelled successfully.')
            # Always route to Billing, show a cancelled modal, and if still valid allow reactivation
            billing_url = reverse('core:billing', kwargs={'school_slug': school.slug})
            suffix = '?cancelled=1' + ('&reactivate=1' if can_reactivate else '')
            return redirect(f"{billing_url}{suffix}")
        else:
            messages.error(request, 'No active subscription found.')
        # Fallback
        return redirect('frontend:home')


class ReactivateSubscriptionView(View):
    """Reactivate a cancelled but still valid subscription (end date not reached)."""
    def post(self, request):
        today = timezone.now().date()
        school = resolve_school(request)
        if not school:
            # Support AJAX response
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'School context not found.'}, status=400)
            messages.error(request, 'School context not found.')
            return redirect('frontend:home')

        sub = Subscription.objects.using('default').filter(school=school).order_by('-created_at').first()
        if not sub or sub.status != 'cancelled' or not sub.end_date or sub.end_date < today:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Subscription cannot be reactivated.'}, status=400)
            messages.error(request, 'Subscription cannot be reactivated.')
            return redirect('core:billing', school_slug=school.slug)

        sub.status = 'active'
        sub.auto_renew = True
        sub.save()

        # Always set a success message so it appears after reload/redirect
        messages.success(request, 'Subscription reactivated successfully.')

        billing_url = reverse('core:billing', kwargs={'school_slug': school.slug})
        # For AJAX requests, return JSON but keep the message in storage
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect': f"{billing_url}?reactivated=1"})
        return redirect(f"{billing_url}?reactivated=1")


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
