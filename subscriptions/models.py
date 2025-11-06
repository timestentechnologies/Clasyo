from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
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
        ('stripe', 'Stripe'),
        ('razorpay', 'Razorpay'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    payment_id = models.UUIDField(_("Payment ID"), default=uuid.uuid4, editable=False, unique=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    currency = models.CharField(_("Currency"), max_length=10, default='USD')
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Transaction Details
    transaction_id = models.CharField(_("Transaction ID"), max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(_("Gateway Response"), default=dict, blank=True)
    
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
