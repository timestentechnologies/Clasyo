from django.db import models
from django.utils.translation import gettext_lazy as _
from academics.models import Class
from students.models import Student
from accounts.models import User


class FeeStructure(models.Model):
    """Fee Structure Model"""
    FEE_TYPE_CHOICES = [
        ('tuition', 'Tuition Fee'),
        ('transport', 'Transport Fee'),
        ('library', 'Library Fee'),
        ('lab', 'Laboratory Fee'),
        ('sports', 'Sports Fee'),
        ('exam', 'Examination Fee'),
        ('admission', 'Admission Fee'),
        ('other', 'Other Fee'),
    ]
    
    name = models.CharField(_("Fee Name"), max_length=200)
    fee_type = models.CharField(_("Fee Type"), max_length=50, choices=FEE_TYPE_CHOICES)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='fee_structures')
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Fee Structure")
        verbose_name_plural = _("Fee Structures")
        ordering = ['class_name', 'fee_type']
    
    def __str__(self):
        return f"{self.name} - {self.class_name.name} - ${self.amount}"


class FeeCollection(models.Model):
    """Fee Collection Model"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_collections')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='collections')
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(_("Paid Amount"), max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(_("Payment Status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(_("Payment Method"), max_length=50, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    payment_date = models.DateField(_("Payment Date"), null=True, blank=True)
    due_date = models.DateField(_("Due Date"))
    receipt_number = models.CharField(_("Receipt Number"), max_length=100, unique=True, null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    # Optional: selected deposit account (Cash/Bank) for this collection
    deposit_account = models.ForeignKey('finance.Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_collections')
    collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='collected_fees')
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Fee Collection")
        verbose_name_plural = _("Fee Collections")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.fee_structure.name}"
