from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class SubscriptionPlan(models.Model):
    """Subscription Plan Model"""
    PLAN_TYPE_CHOICES = [
        ('free_trial', 'Free Trial'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(_("Plan Name"), max_length=100)
    slug = models.SlugField(_("Slug"), unique=True)
    plan_type = models.CharField(_("Plan Type"), max_length=20, choices=PLAN_TYPE_CHOICES)
    description = models.TextField(_("Description"), blank=True)
    
    # Pricing
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2, 
                                validators=[MinValueValidator(0)])
    billing_cycle = models.CharField(_("Billing Cycle"), max_length=20, choices=BILLING_CYCLE_CHOICES)
    trial_days = models.IntegerField(_("Trial Days"), default=0)
    setup_fee = models.DecimalField(_("One-time Setup Fee"), max_digits=10, decimal_places=2,
                                    default=0, validators=[MinValueValidator(0)])
    data_migration_fee = models.DecimalField(_("Data Migration Fee"), max_digits=10, decimal_places=2,
                                             default=0, validators=[MinValueValidator(0)])
    license_fee = models.DecimalField(_("License Fee"), max_digits=10, decimal_places=2,
                                      default=0, validators=[MinValueValidator(0)])
    training_fee = models.DecimalField(_("Training Fee"), max_digits=10, decimal_places=2,
                                       default=0, validators=[MinValueValidator(0)])
    
    # Limits
    max_students = models.IntegerField(_("Max Students"), default=100)
    max_teachers = models.IntegerField(_("Max Teachers"), default=20)
    max_staff = models.IntegerField(_("Max Staff"), default=10)
    max_branches = models.IntegerField(_("Max Branches"), default=1)
    storage_limit_gb = models.IntegerField(_("Storage Limit (GB)"), default=5)
    
    # Features
    features = models.JSONField(_("Features"), default=dict, blank=True)
    enable_online_exam = models.BooleanField(_("Enable Online Exam"), default=True)
    enable_online_payment = models.BooleanField(_("Enable Online Payment"), default=True)
    enable_chat = models.BooleanField(_("Enable Chat"), default=True)
    enable_sms = models.BooleanField(_("Enable SMS"), default=False)
    enable_library = models.BooleanField(_("Enable Library"), default=True)
    enable_transport = models.BooleanField(_("Enable Transport"), default=True)
    enable_dormitory = models.BooleanField(_("Enable Dormitory"), default=True)
    enable_inventory = models.BooleanField(_("Enable Inventory"), default=True)
    enable_hr = models.BooleanField(_("Enable HR Management"), default=True)
    enable_reports = models.BooleanField(_("Enable Advanced Reports"), default=True)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_popular = models.BooleanField(_("Is Popular"), default=False)
    display_order = models.IntegerField(_("Display Order"), default=0)
    
    # Metadata
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")
        ordering = ['display_order', 'price']

    def __str__(self):
        return f"{self.name} - {self.get_billing_cycle_display()}"

    def get_features_list(self):
        """Return features as a flat list of strings for display.

        The JSON `features` field may be stored as a list of strings or as a
        dict. This helper tries to handle both gracefully so that templates
        can always iterate over a simple list.
        """
        items = []
        data = self.features or {}

        try:
            # If it's already a list, normalise it to strings
            if isinstance(data, list):
                items.extend(str(f).strip() for f in data if str(f).strip())
            # If it's a dict, either treat truthy keys as feature labels or
            # use non-empty values as labels.
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, bool):
                        if value:
                            items.append(str(key).replace('_', ' ').title())
                    else:
                        text = str(value).strip()
                        if text:
                            items.append(text)
        except Exception:
            # Never break the page because of malformed JSON; just return
            # whatever we safely collected.
            pass

        return items

    @property
    def one_time_total(self):
        """Total of all one-time fees for this plan."""
        return self.setup_fee + self.data_migration_fee + self.license_fee + self.training_fee


class Subscription(models.Model):
    """Individual Subscription Record"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]
    
    school = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    # Subscription Details
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Auto Renewal
    auto_renew = models.BooleanField(_("Auto Renew"), default=False)
    
    # Trial
    is_trial = models.BooleanField(_("Is Trial"), default=False)
    
    # Metadata
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.school.name} - {self.plan.name} ({self.status})"


class Payment(models.Model):
    """Payment Transaction Model"""
    PAYMENT_METHOD_CHOICES = [
        ('mpesa_paybill', 'M-Pesa Paybill'),
        ('mpesa_stk', 'M-Pesa STK Push'),
        ('mpesa_buygoods', 'M-Pesa Buy Goods & Services'),
        ('mpesa_send_money', 'M-Pesa Send Money'),
        ('mpesa_pochi', 'M-Pesa Pochi la Biashara'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]
    
    STATUS_CHOICES = [
        ('pending_verification', 'Pending Verification'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    payment_id = models.UUIDField(_("Payment ID"), default=uuid.uuid4, editable=False, unique=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    currency = models.CharField(_("Currency"), max_length=10, default='KES')
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(_("Status"), max_length=25, choices=STATUS_CHOICES, default='pending_verification')
    
    # Transaction Details
    transaction_id = models.CharField(_("Transaction ID"), max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(_("Gateway Response"), default=dict, blank=True)
    
    # Payment Method Specific Details
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True, null=True)
    full_name = models.CharField(_("Full Name"), max_length=255, blank=True, null=True)
    account_name = models.CharField(_("Account Name"), max_length=255, blank=True, null=True)
    account_number = models.CharField(_("Account Number"), max_length=50, blank=True, null=True)
    paypal_email = models.EmailField(_("PayPal Email"), blank=True, null=True)
    invoice_number_ref = models.CharField(_("Invoice Number Reference"), max_length=100, blank=True, null=True)
    
    # Approval Workflow
    verified_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='verified_payments', verbose_name=_("Verified By"))
    verified_at = models.DateTimeField(_("Verified At"), null=True, blank=True)
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_payments', verbose_name=_("Approved By"))
    approved_at = models.DateTimeField(_("Approved At"), null=True, blank=True)
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)
    
    # Invoice
    invoice_number = models.CharField(_("Invoice Number"), max_length=50, unique=True, blank=True, null=True)
    invoice_date = models.DateField(_("Invoice Date"), blank=True, null=True)
    
    # Metadata
    payment_date = models.DateTimeField(_("Payment Date"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    # Notes
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number
            from django.utils import timezone
            last_payment = Payment.objects.filter(
                invoice_number__isnull=False
            ).order_by('-created_at').first()
            
            if last_payment and last_payment.invoice_number:
                try:
                    last_num = int(last_payment.invoice_number.split('-')[-1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            
            self.invoice_number = f"INV-{timezone.now().year}-{new_num:05d}"
            self.invoice_date = timezone.now().date()
        
        super().save(*args, **kwargs)
    
    def verify_payment(self, user):
        """Mark payment as verified"""
        self.status = 'verified'
        self.verified_by = user
        self.verified_at = timezone.now()
        self.save()
    
    def approve_payment(self, user):
        """Approve payment and activate subscription"""
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.payment_date = timezone.now()
        
        # Update subscription status
        if self.subscription:
            self.subscription.status = 'active'
            self.subscription.save()
        
        # Save payment first
        self.save()

        # Link and mark the related invoice as paid
        try:
            inv = None
            # If this payment references a specific invoice number, try that first
            if self.invoice_number_ref:
                inv = Invoice.objects.filter(invoice_number=self.invoice_number_ref).first()
            # Prefer invoices already linked to this payment and still unpaid
            if not inv:
                inv = self.invoices.filter(status__in=['sent', 'overdue', 'draft']).order_by('-invoice_date', '-created_at').first()
            # Try match by subscription and amount first
            if not inv and self.subscription:
                inv = Invoice.objects.filter(
                    subscription=self.subscription,
                    status__in=['sent', 'overdue', 'draft'],
                    total_amount=self.amount
                ).order_by('-invoice_date', '-created_at').first() or Invoice.objects.filter(
                    subscription=self.subscription,
                    status__in=['sent', 'overdue', 'draft'],
                    amount=self.amount
                ).order_by('-invoice_date', '-created_at').first()
            # Otherwise, find the latest outstanding invoice for this subscription
            if not inv and self.subscription:
                inv = Invoice.objects.filter(
                    subscription=self.subscription,
                    status__in=['sent', 'overdue']
                ).order_by('-invoice_date', '-created_at').first()
            # As a fallback, try matching by school for any outstanding invoice
            if not inv and self.subscription:
                inv = Invoice.objects.filter(
                    school=self.subscription.school,
                    status__in=['sent', 'overdue']
                ).order_by('-invoice_date', '-created_at').first()
            if inv:
                inv.mark_as_paid(payment=self)
            else:
                # Final fallback: mark all outstanding invoices for this subscription as paid
                if self.subscription:
                    for _inv in Invoice.objects.filter(
                        subscription=self.subscription,
                        status__in=['sent', 'overdue', 'draft']
                    ).order_by('-invoice_date', '-created_at'):
                        _inv.mark_as_paid(payment=self)
        except Exception:
            # Do not block approval on invoice linking errors
            pass
    
    def reject_payment(self, user, reason):
        """Reject payment"""
        self.status = 'rejected'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    @property
    def needs_verification(self):
        """Check if payment needs verification"""
        return self.status in ['pending_verification', 'pending']
    
    @property
    def is_approved(self):
        """Check if payment is approved"""
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        """Check if payment is rejected"""
        return self.status == 'rejected'


class Coupon(models.Model):
    """Discount Coupon Model"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(_("Coupon Code"), max_length=50, unique=True)
    description = models.TextField(_("Description"), blank=True)
    
    # Discount
    discount_type = models.CharField(_("Discount Type"), max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(_("Discount Value"), max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(_("Max Discount"), max_digits=10, decimal_places=2, 
                                      null=True, blank=True)
    
    # Validity
    valid_from = models.DateTimeField(_("Valid From"))
    valid_until = models.DateTimeField(_("Valid Until"))
    
    # Usage Limits
    max_uses = models.IntegerField(_("Max Uses"), default=0)  # 0 means unlimited
    max_uses_per_user = models.IntegerField(_("Max Uses Per User"), default=1)
    times_used = models.IntegerField(_("Times Used"), default=0)
    
    # Applicable Plans
    applicable_plans = models.ManyToManyField(SubscriptionPlan, blank=True, 
                                             related_name='coupons')
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    # Metadata
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Coupon")
        verbose_name_plural = _("Coupons")
        ordering = ['-created_at']

    def __str__(self):
        return self.code
    
    def is_valid(self):
        """Check if coupon is valid"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if now < self.valid_from or now > self.valid_until:
            return False
        
        if self.max_uses > 0 and self.times_used >= self.max_uses:
            return False
        
        return True


class Invoice(models.Model):
    """Invoice for subscription payments and renewals"""
    INVOICE_TYPES = [
        ('new', 'New Subscription'),
        ('renewal', 'Subscription Renewal'),
        ('upgrade', 'Plan Upgrade'),
        ('trial_end', 'Trial End'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    school = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPES, default='new')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Invoice details
    plan_name = models.CharField(max_length=100)
    plan_description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    paid_date = models.DateTimeField(null=True, blank=True)
    
    # Billing period
    billing_start_date = models.DateField(null=True, blank=True)
    billing_end_date = models.DateField(null=True, blank=True)
    
    # Additional fields
    notes = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    due_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    overdue_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', '-created_at']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.school.name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate unique invoice number
            year = timezone.now().year
            month = timezone.now().month
            last_invoice = Invoice.objects.filter(
                invoice_date__year=year,
                invoice_date__month=month
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                try:
                    last_num = int(last_invoice.invoice_number.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            
            self.invoice_number = f"INV-{year}{month:02d}-{new_num:04d}"
        
        # Calculate total if not set
        if self.total_amount == 0 and self.amount > 0:
            self.total_amount = self.amount + self.tax_amount
        
        super().save(*args, **kwargs)
    
    @property
    def is_paid(self):
        return self.status == 'paid'
    
    @property
    def is_overdue(self):
        return self.status != 'paid' and self.due_date < timezone.now().date()
    
    def mark_as_paid(self, payment=None):
        """Mark invoice as paid"""
        self.status = 'paid'
        self.paid_date = timezone.now()
        if payment:
            self.payment = payment
        self.save()
