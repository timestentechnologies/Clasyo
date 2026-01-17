from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal
from tenants.models import School

User = get_user_model()


class ItemCategory(models.Model):
    """Category for inventory items"""
    CATEGORY_CHOICES = [
        ('stationery', 'Stationery'),
        ('food', 'Food & Beverages'),
        ('equipment', 'Equipment'),
        ('furniture', 'Furniture'),
        ('supplies', 'Supplies'),
        ('other', 'Other'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='item_categories', null=True, blank=True)
    name = models.CharField(_("Category Name"), max_length=100)
    category_type = models.CharField(_("Type"), max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Item Category")
        verbose_name_plural = _("Item Categories")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Item(models.Model):
    """Inventory Item/Product"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='items', null=True, blank=True)
    name = models.CharField(_("Item Name"), max_length=200)
    code = models.CharField(_("Item Code"), max_length=50, unique=True)
    category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, null=True, related_name='items')
    description = models.TextField(_("Description"), blank=True)
    unit = models.CharField(_("Unit"), max_length=50, default='piece')  # piece, box, kg, liter, etc.
    unit_price = models.DecimalField(_("Unit Price"), max_digits=10, decimal_places=2)
    quantity_in_stock = models.DecimalField(_("Quantity in Stock"), max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(_("Reorder Level"), max_digits=10, decimal_places=2, default=10)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def needs_reorder(self):
        return self.quantity_in_stock <= self.reorder_level
    
    @property
    def stock_value(self):
        return self.quantity_in_stock * self.unit_price


class Supplier(models.Model):
    """Supplier/Vendor"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='suppliers', null=True, blank=True)
    name = models.CharField(_("Supplier Name"), max_length=200)
    contact_person = models.CharField(_("Contact Person"), max_length=100, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    phone = models.CharField(_("Phone"), max_length=20)
    address = models.TextField(_("Address"))
    city = models.CharField(_("City"), max_length=100)
    tax_id = models.CharField(_("Tax ID/VAT"), max_length=50, blank=True)
    payment_terms = models.CharField(_("Payment Terms"), max_length=100, default='Net 30')
    is_active = models.BooleanField(_("Is Active"), default=True)
    notes = models.TextField(_("Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """Purchase Order"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='purchase_orders', null=True, blank=True)
    po_number = models.CharField(_("PO Number"), max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(_("Order Date"))
    expected_delivery_date = models.DateField(_("Expected Delivery Date"), null=True, blank=True)
    actual_delivery_date = models.DateField(_("Actual Delivery Date"), null=True, blank=True)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(_("Total Amount"), max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(_("Notes"), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")
        ordering = ['-order_date', '-po_number']
    
    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"
    
    def calculate_totals(self):
        """Calculate subtotal, tax, and total from line items"""
        items = self.items.all()
        self.subtotal = sum(item.total for item in items)
        self.tax_amount = self.subtotal * Decimal('0.00')  # Add tax rate if needed
        self.total_amount = self.subtotal + self.tax_amount
        self.save()


class PurchaseOrderItem(models.Model):
    """Purchase Order Line Item"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='purchase_order_items')
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(_("Unit Price"), max_digits=10, decimal_places=2)
    total = models.DecimalField(_("Total"), max_digits=12, decimal_places=2)
    received_quantity = models.DecimalField(_("Received Quantity"), max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(_("Notes"), blank=True)
    
    class Meta:
        verbose_name = _("Purchase Order Item")
        verbose_name_plural = _("Purchase Order Items")
    
    def __str__(self):
        return f"{self.item.name} - {self.quantity} {self.item.unit}"
    
    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class ItemDistribution(models.Model):
    """Track distribution of items to staff, teachers, or students"""
    RECIPIENT_TYPE_CHOICES = [
        ('teacher', 'Teacher'),
        ('staff', 'Staff'),
        ('student', 'Student'),
        ('department', 'Department'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='item_distributions', null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='distributions')
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2)
    recipient_type = models.CharField(_("Recipient Type"), max_length=20, choices=RECIPIENT_TYPE_CHOICES)
    recipient_id = models.IntegerField(_("Recipient ID"))
    recipient_name = models.CharField(_("Recipient Name"), max_length=200)
    distribution_date = models.DateField(_("Distribution Date"))
    purpose = models.CharField(_("Purpose"), max_length=200, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    distributed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='distributed_items')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Item Distribution")
        verbose_name_plural = _("Item Distributions")
        ordering = ['-distribution_date']
    
    def __str__(self):
        return f"{self.item.name} - {self.recipient_name}"


class Expense(models.Model):
    """Expense Tracking"""
    EXPENSE_TYPE_CHOICES = [
        ('purchase', 'Purchase/Procurement'),
        ('salary', 'Salary Payment'),
        ('utility', 'Utility Bills'),
        ('maintenance', 'Maintenance'),
        ('transport', 'Transport'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
    expense_number = models.CharField(_("Expense Number"), max_length=50, unique=True)
    expense_type = models.CharField(_("Expense Type"), max_length=20, choices=EXPENSE_TYPE_CHOICES)
    description = models.CharField(_("Description"), max_length=300)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    expense_date = models.DateField(_("Expense Date"))
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(_("Reference Number"), max_length=100, blank=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    payee_name = models.CharField(_("Payee Name"), max_length=200)
    notes = models.TextField(_("Notes"), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Expense")
        verbose_name_plural = _("Expenses")
        ordering = ['-expense_date', '-expense_number']
    
    def __str__(self):
        return f"{self.expense_number} - {self.description}"


class StaffPayment(models.Model):
    """Staff and Teacher Payment Records"""
    STAFF_TYPE_CHOICES = [
        ('teacher', 'Teacher'),
        ('staff', 'Staff'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='staff_payments', null=True, blank=True)
    payment_number = models.CharField(_("Payment Number"), max_length=50, unique=True)
    staff_type = models.CharField(_("Staff Type"), max_length=20, choices=STAFF_TYPE_CHOICES)
    staff_id = models.IntegerField(_("Staff/Teacher ID"))
    staff_name = models.CharField(_("Staff/Teacher Name"), max_length=200)
    payment_month = models.DateField(_("Payment Month"))
    basic_salary = models.DecimalField(_("Basic Salary"), max_digits=12, decimal_places=2)
    allowances = models.DecimalField(_("Allowances"), max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(_("Deductions"), max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(_("Net Salary"), max_digits=12, decimal_places=2)
    payment_date = models.DateField(_("Payment Date"))
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=Expense.PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(_("Reference Number"), max_length=100, blank=True)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(_("Notes"), blank=True)
    expense = models.OneToOneField(Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_payment')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payments')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Staff Payment")
        verbose_name_plural = _("Staff Payments")
        ordering = ['-payment_date', '-payment_number']
    
    def __str__(self):
        return f"{self.payment_number} - {self.staff_name}"
    
    def save(self, *args, **kwargs):
        # Calculate net salary
        self.net_salary = self.basic_salary + self.allowances - self.deductions
        
        # Ensure StaffPayment.school is set if creator has a school
        if not self.school and getattr(self.created_by, 'school', None):
            self.school = self.created_by.school

        # Create expense record if paid
        if self.status == 'paid' and not self.expense:
            expense = Expense.objects.create(
                school=self.school or getattr(self.created_by, 'school', None),
                expense_number=f"EXP-{self.payment_number}",
                expense_type='salary',
                description=f"Salary payment for {self.staff_name}",
                amount=self.net_salary,
                expense_date=self.payment_date,
                payment_method=self.payment_method,
                reference_number=self.reference_number,
                payee_name=self.staff_name,
                created_by=self.created_by
            )
            self.expense = expense
        
        super().save(*args, **kwargs)
