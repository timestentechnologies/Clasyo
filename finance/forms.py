from django import forms
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

from core.utils import get_current_school
from students.models import Student
from core.models import AcademicYear
from finance.models import Account
from accounts.models import User
from inventory.models import Supplier


PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('bank_transfer', 'Bank Transfer'),
    ('cheque', 'Cheque'),
    ('mobile_money', 'Mobile Money'),
    ('other', 'Other'),
]

DONATION_TYPE_CHOICES = [
    ('restricted', 'Restricted'),
    ('unrestricted', 'Unrestricted'),
]


class CollectFeesForm(forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.none(), label=_('Student'))
    academic_year = forms.ModelChoiceField(queryset=AcademicYear.objects.none(), label=_('Academic Year'))
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES)
    deposit_account = forms.ModelChoiceField(queryset=Account.objects.none(), label=_('Deposit Account'))
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    reference = forms.CharField(max_length=100, required=False, label=_('Reference / Receipt No'))
    is_advance = forms.BooleanField(required=False, initial=False, label=_('Treat as Advance/Deposit'))

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = get_current_school(request)
        self.fields['student'].queryset = Student.objects.all()
        self.fields['academic_year'].queryset = AcademicYear.objects.all()
        self.fields['deposit_account'].queryset = Account.objects.filter(is_active=True, sub_type__in=['cash', 'bank'])
        if school:
            self.fields['student'].queryset = self.fields['student'].queryset.filter(academic_year__school=school)
            self.fields['academic_year'].queryset = self.fields['academic_year'].queryset.filter(school=school)
            self.fields['deposit_account'].queryset = self.fields['deposit_account'].queryset.filter(school=school)

    def clean_deposit_account(self):
        acc = self.cleaned_data['deposit_account']
        if not acc.is_active:
            raise forms.ValidationError(_('Selected account is inactive'))
        if not acc.is_cash_or_bank:
            raise forms.ValidationError(_('Deposit account must be a Cash/Bank account'))
        return acc


class ReceiveDonationForm(forms.Form):
    donor_name = forms.CharField(max_length=200)
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    donation_type = forms.ChoiceField(choices=DONATION_TYPE_CHOICES)
    deposit_account = forms.ModelChoiceField(queryset=Account.objects.none(), label=_('Deposit Account'))
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    notes = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = get_current_school(request)
        qs = Account.objects.filter(is_active=True, sub_type__in=['cash', 'bank'])
        if school:
            qs = qs.filter(school=school)
        self.fields['deposit_account'].queryset = qs

    def clean_deposit_account(self):
        acc = self.cleaned_data['deposit_account']
        if not acc.is_active:
            raise forms.ValidationError(_('Selected account is inactive'))
        return acc


class MakePaymentForm(forms.Form):
    PAYEE_TYPE_CHOICES = [
        ('staff', 'Staff'),
        ('supplier', 'Supplier'),
        ('other', 'Other'),
    ]

    payee_type = forms.ChoiceField(choices=PAYEE_TYPE_CHOICES)
    staff = forms.ModelChoiceField(queryset=User.objects.none(), required=False, label=_('Staff/Teacher'))
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.none(), required=False)
    other_payee = forms.CharField(max_length=200, required=False, label=_('Other Payee Name'))

    debit_account = forms.ModelChoiceField(queryset=Account.objects.none(), label=_('Expense/Payable Account'))
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    payment_account = forms.ModelChoiceField(queryset=Account.objects.none(), label=_('Payment Account (Cash/Bank)'))
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = get_current_school(request)

        staff_qs = User.objects.filter(role__in=['teacher', 'admin', 'accountant', 'librarian', 'receptionist'])
        supplier_qs = Supplier.objects.all()
        debit_qs = Account.objects.filter(account_type__in=['expense', 'liability'], is_active=True)
        pay_qs = Account.objects.filter(sub_type__in=['cash', 'bank'], is_active=True)

        if school:
            staff_qs = staff_qs.filter(school=school)
            supplier_qs = supplier_qs.filter(school=school)
            debit_qs = debit_qs.filter(school=school)
            pay_qs = pay_qs.filter(school=school)

        self.fields['staff'].queryset = staff_qs
        self.fields['supplier'].queryset = supplier_qs
        self.fields['debit_account'].queryset = debit_qs
        self.fields['payment_account'].queryset = pay_qs

    def clean(self):
        cleaned = super().clean()
        payee_type = cleaned.get('payee_type')
        staff = cleaned.get('staff')
        supplier = cleaned.get('supplier')
        other = cleaned.get('other_payee')
        payment_account = cleaned.get('payment_account')
        amount = cleaned.get('amount') or Decimal('0.00')

        # Ensure a payee is provided according to type
        if payee_type == 'staff' and not staff:
            self.add_error('staff', _('Please select a staff/teacher'))
        if payee_type == 'supplier' and not supplier:
            self.add_error('supplier', _('Please select a supplier'))
        if payee_type == 'other' and not other:
            self.add_error('other_payee', _('Please enter the payee name'))

        if not payment_account:
            self.add_error('payment_account', _('Please select a payment account'))
        else:
            if not payment_account.is_active:
                self.add_error('payment_account', _('Selected payment account is inactive'))
            if not payment_account.is_cash_or_bank:
                self.add_error('payment_account', _('Payment account must be Cash/Bank'))
            # Check sufficient funds
            if amount > payment_account.current_balance:
                self.add_error('amount', _('Insufficient funds in selected account'))

        return cleaned

    def get_payee_display(self):
        t = self.cleaned_data.get('payee_type')
        if t == 'staff' and self.cleaned_data.get('staff'):
            return self.cleaned_data['staff'].get_full_name()
        if t == 'supplier' and self.cleaned_data.get('supplier'):
            return self.cleaned_data['supplier'].name
        return self.cleaned_data.get('other_payee') or ''


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'sub_type', 'opening_balance', 'is_active']
        widgets = {
            'opening_balance': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # nothing dynamic beyond instance scoping in view save
