from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class Account(models.Model):
    TYPE_ASSET = 'asset'
    TYPE_LIABILITY = 'liability'
    TYPE_EQUITY = 'equity'
    TYPE_INCOME = 'income'
    TYPE_EXPENSE = 'expense'

    ACCOUNT_TYPE_CHOICES = [
        (TYPE_ASSET, 'Asset'),
        (TYPE_LIABILITY, 'Liability'),
        (TYPE_EQUITY, 'Equity'),
        (TYPE_INCOME, 'Income'),
        (TYPE_EXPENSE, 'Expense'),
    ]

    SUBTYPE_CASH = 'cash'
    SUBTYPE_BANK = 'bank'
    SUBTYPE_RECEIVABLE = 'receivable'
    SUBTYPE_PAYABLE = 'payable'
    SUBTYPE_OTHER = 'other'

    SUB_TYPE_CHOICES = [
        (SUBTYPE_CASH, 'Cash'),
        (SUBTYPE_BANK, 'Bank'),
        (SUBTYPE_RECEIVABLE, 'Receivable'),
        (SUBTYPE_PAYABLE, 'Payable'),
        (SUBTYPE_OTHER, 'Other'),
    ]

    school = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='accounts', null=True, blank=True)
    code = models.CharField(_('Account Code'), max_length=20)
    name = models.CharField(_('Account Name'), max_length=200)
    account_type = models.CharField(_('Account Type'), max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    sub_type = models.CharField(_('Sub-Type'), max_length=20, choices=SUB_TYPE_CHOICES, default=SUBTYPE_OTHER)
    opening_balance = models.DecimalField(_('Opening Balance'), max_digits=14, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        unique_together = [('school', 'code')]
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_cash_or_bank(self) -> bool:
        return self.sub_type in {self.SUBTYPE_CASH, self.SUBTYPE_BANK}

    def opening_balance_effect(self) -> Decimal:
        # Debit-normal accounts (assets, expenses) treat opening_balance as debit
        if self.account_type in {self.TYPE_ASSET, self.TYPE_EXPENSE}:
            return self.opening_balance
        # Credit-normal accounts treat opening as credit (negative in debit-minus-credit view)
        return -self.opening_balance

    @property
    def current_balance(self) -> Decimal:
        # Balance as debit minus credit, plus opening balance effect
        totals = self.journal_lines.filter(entry__posted=True).aggregate(
            debit=models.Sum('debit'), credit=models.Sum('credit')
        )
        debit = totals.get('debit') or Decimal('0.00')
        credit = totals.get('credit') or Decimal('0.00')
        return self.opening_balance_effect() + (debit - credit)


class Transaction(models.Model):
    TYPE_FEE = 'fee_collection'
    TYPE_DONATION = 'donation'
    TYPE_PAYMENT = 'payment'
    TYPE_REVERSAL = 'reversal'

    TXN_TYPE_CHOICES = [
        (TYPE_FEE, 'Fee Collection'),
        (TYPE_DONATION, 'Donation Receipt'),
        (TYPE_PAYMENT, 'Payment'),
        (TYPE_REVERSAL, 'Reversal'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_POSTED = 'posted'
    STATUS_REVERSED = 'reversed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_POSTED, 'Posted'),
        (STATUS_REVERSED, 'Reversed'),
    ]

    school = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='finance_transactions', null=True, blank=True)
    txn_type = models.CharField(_('Transaction Type'), max_length=30, choices=TXN_TYPE_CHOICES)
    date = models.DateField(_('Date'), default=timezone.now)
    reference = models.CharField(_('Reference / Receipt No'), max_length=100, blank=True)
    description = models.CharField(_('Description'), max_length=255, blank=True)
    amount = models.DecimalField(_('Amount'), max_digits=14, decimal_places=2)

    # Context fields
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_transactions')
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_transactions')
    is_advance = models.BooleanField(_('Is Advance (Fees)'), default=False)

    donor_name = models.CharField(_('Donor Name'), max_length=200, blank=True)
    donation_type = models.CharField(_('Donation Type'), max_length=20, choices=[('restricted','Restricted'),('unrestricted','Unrestricted')], blank=True)

    PAYEE_TYPE_CHOICES = [ ('staff','Staff'), ('supplier','Supplier'), ('other','Other') ]
    payee_type = models.CharField(_('Payee Type'), max_length=20, choices=PAYEE_TYPE_CHOICES, blank=True)
    payee_id = models.IntegerField(_('Payee ID'), null=True, blank=True)
    payee_name = models.CharField(_('Payee Name'), max_length=200, blank=True)

    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_finance_transactions')
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_finance_transactions')
    posted_at = models.DateTimeField(_('Posted At'), null=True, blank=True)

    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-date', '-id']
        permissions = [
            ("can_create_finance_transactions", "Can create finance transactions"),
            ("can_post_finance_transactions", "Can approve/post finance transactions"),
        ]

    def __str__(self):
        return f"{self.get_txn_type_display()} - {self.reference or self.id} - {self.amount}"

    def can_delete(self) -> bool:
        return self.status != self.STATUS_POSTED


class JournalEntry(models.Model):
    school = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='journal_entries', null=True, blank=True)
    date = models.DateField(_('Date'), default=timezone.now)
    reference = models.CharField(_('Reference'), max_length=100, blank=True)
    memo = models.CharField(_('Memo/Description'), max_length=255, blank=True)
    posted = models.BooleanField(_('Posted'), default=False)
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries_posted')
    posted_at = models.DateTimeField(_('Posted At'), null=True, blank=True)
    transaction = models.OneToOneField(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entry')

    class Meta:
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        ordering = ['-date', '-id']

    def __str__(self):
        return f"JE {self.id} - {self.date} - {self.reference}"

    @property
    def total_debit(self) -> Decimal:
        agg = self.lines.aggregate(debit=models.Sum('debit'))
        return agg.get('debit') or Decimal('0.00')

    @property
    def total_credit(self) -> Decimal:
        agg = self.lines.aggregate(credit=models.Sum('credit'))
        return agg.get('credit') or Decimal('0.00')

    def validate_balanced(self):
        if self.total_debit != self.total_credit:
            raise ValueError('Journal entry is not balanced: debit != credit')

    def post(self, user: User):
        if self.posted:
            return
        self.validate_balanced()
        self.posted = True
        self.posted_by = user
        self.posted_at = timezone.now()
        self.save(update_fields=['posted', 'posted_by', 'posted_at'])


class JournalEntryLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_lines')
    description = models.CharField(_('Description'), max_length=255, blank=True)
    debit = models.DecimalField(_('Debit'), max_digits=14, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(_('Credit'), max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = _('Journal Entry Line')
        verbose_name_plural = _('Journal Entry Lines')

    def __str__(self):
        return f"{self.account} D{self.debit} C{self.credit}"

    def clean(self):
        # Ensure not both debit and credit and not both zero
        if (self.debit and self.debit > 0) and (self.credit and self.credit > 0):
            from django.core.exceptions import ValidationError
            raise ValidationError(_('A line cannot have both debit and credit amounts'))
        if (self.debit or Decimal('0.00')) == 0 and (self.credit or Decimal('0.00')) == 0:
            from django.core.exceptions import ValidationError
            raise ValidationError(_('A line must have either a debit or a credit amount'))


# Utilities to ensure default Chart of Accounts exists per school
DEFAULT_ACCOUNTS = [
    # code, name, type, subtype, opening
    ('1000', 'Cash in Hand', Account.TYPE_ASSET, Account.SUBTYPE_CASH, Decimal('0.00')),
    ('1010', 'Bank – Tuition Fees Account', Account.TYPE_ASSET, Account.SUBTYPE_BANK, Decimal('0.00')),
    ('1011', 'Bank – Donations Account', Account.TYPE_ASSET, Account.SUBTYPE_BANK, Decimal('0.00')),
    ('1012', 'Bank – Operations Account', Account.TYPE_ASSET, Account.SUBTYPE_BANK, Decimal('0.00')),
    ('1200', 'Student Fees Receivable', Account.TYPE_ASSET, Account.SUBTYPE_RECEIVABLE, Decimal('0.00')),
    ('2100', 'Accounts Payable', Account.TYPE_LIABILITY, Account.SUBTYPE_PAYABLE, Decimal('0.00')),
    ('2300', 'Student Fee Deposits', Account.TYPE_LIABILITY, Account.SUBTYPE_OTHER, Decimal('0.00')),
    ('4000', 'Tuition Fees Income', Account.TYPE_INCOME, Account.SUBTYPE_OTHER, Decimal('0.00')),
    ('4100', 'Donations – Restricted', Account.TYPE_INCOME, Account.SUBTYPE_OTHER, Decimal('0.00')),
    ('4110', 'Donations – Unrestricted', Account.TYPE_INCOME, Account.SUBTYPE_OTHER, Decimal('0.00')),
    ('5000', 'Salaries Expense', Account.TYPE_EXPENSE, Account.SUBTYPE_OTHER, Decimal('0.00')),
    ('5001', 'Operating Expenses', Account.TYPE_EXPENSE, Account.SUBTYPE_OTHER, Decimal('0.00')),
]


def ensure_default_accounts_for_school(school):
    for code, name, acc_type, sub_type, opening in DEFAULT_ACCOUNTS:
        Account.objects.get_or_create(
            school=school, code=code,
            defaults={
                'name': name,
                'account_type': acc_type,
                'sub_type': sub_type,
                'opening_balance': opening,
                'is_active': True,
            }
        )
