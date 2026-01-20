from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.utils import timezone

from .models import (
    Account,
    Transaction,
    JournalEntry,
    JournalEntryLine,
    ensure_default_accounts_for_school,
)

# Optional external models
try:
    from fees.models import FeeCollection
except Exception:  # pragma: no cover
    FeeCollection = None

try:
    from inventory.models import Expense, StaffPayment
except Exception:  # pragma: no cover
    Expense = None  # type: ignore
    StaffPayment = None  # type: ignore

# Simple in-process cache to avoid repeated full backfills during a single server run
_BACKFILLED_SCHOOLS = set()


def _get_school_from_fee_collection(obj):
    school = None
    try:
        if getattr(obj.student, 'academic_year', None) and obj.student.academic_year and obj.student.academic_year.school:
            school = obj.student.academic_year.school
    except Exception:
        school = None
    if not school:
        try:
            if obj.fee_structure and obj.fee_structure.class_name and obj.fee_structure.class_name.school:
                school = obj.fee_structure.class_name.school
        except Exception:
            school = None
    return school


def _get_payment_account_for_method(school, method, context="fees"):
    method = (method or '').lower()
    ensure_default_accounts_for_school(school)
    if method == 'cash':
        acc = Account.objects.filter(school=school, code='1000').first()
        if acc:
            return acc
    code = '1010' if context == 'fees' else '1012'
    acc = Account.objects.filter(school=school, code=code).first()
    return acc


def _get_expense_debit_account(school, expense_type):
    ensure_default_accounts_for_school(school)
    if (expense_type or '') == 'salary':
        acc = Account.objects.filter(school=school, code='5000').first()
    else:
        acc = Account.objects.filter(school=school, code='5001').first()
    return acc


def _post_fee_delta(school, instance, amount):
    deposit_account = getattr(instance, 'deposit_account', None) or _get_payment_account_for_method(school, getattr(instance, 'payment_method', None), context="fees")
    income_acc = Account.objects.filter(school=school, code='4000').first()
    if not deposit_account or not income_acc:
        return
    date = getattr(instance, 'payment_date', None) or timezone.now().date()
    description = f"Fee collection for {getattr(instance.student, 'get_full_name', lambda: 'Student')()}"
    reference = f"FEE-{instance.pk}-{int(timezone.now().timestamp())}"
    with db_transaction.atomic():
        txn = Transaction.objects.create(
            school=school,
            txn_type=Transaction.TYPE_FEE,
            date=date,
            reference=reference,
            description=description,
            amount=amount,
            student=getattr(instance, 'student', None),
            academic_year=getattr(getattr(instance, 'student', None), 'academic_year', None),
            is_advance=False,
            created_by=getattr(instance, 'collected_by', None),
            status=Transaction.STATUS_PENDING,
        )
        je = JournalEntry.objects.create(
            school=school,
            date=date,
            reference=reference,
            memo=description,
            transaction=txn,
            posted=False,
        )
        JournalEntryLine.objects.create(entry=je, account=deposit_account, description='Fee collection', debit=amount, credit=Decimal('0.00'))
        JournalEntryLine.objects.create(entry=je, account=income_acc, description='Fee collection', debit=Decimal('0.00'), credit=amount)
        je.validate_balanced()
        je.post(None)
        txn.status = Transaction.STATUS_POSTED
        txn.posted_by = None
        txn.posted_at = timezone.now()
        txn.save(update_fields=['status', 'posted_by', 'posted_at'])


def _post_expense_payment(school, instance, reference=None):
    amount = instance.amount
    if (amount or Decimal('0')) <= 0:
        return
    payment_account = _get_payment_account_for_method(school, instance.payment_method, context="expenses")
    debit_account = _get_expense_debit_account(school, instance.expense_type)
    if not payment_account or not debit_account:
        return
    date = instance.expense_date or timezone.now().date()
    description = instance.description or f"Expense: {instance.payee_name}"
    ref = reference or instance.expense_number
    with db_transaction.atomic():
        txn = Transaction.objects.create(
            school=school,
            txn_type=Transaction.TYPE_PAYMENT,
            date=date,
            reference=ref,
            description=description,
            amount=amount,
            payee_type='supplier' if instance.expense_type == 'purchase' else 'other',
            payee_name=instance.payee_name,
            created_by=getattr(instance, 'created_by', None),
            status=Transaction.STATUS_PENDING,
        )
        je = JournalEntry.objects.create(
            school=school,
            date=date,
            reference=ref,
            memo=description,
            transaction=txn,
            posted=False,
        )
        JournalEntryLine.objects.create(entry=je, account=debit_account, description='Expense', debit=amount, credit=Decimal('0.00'))
        JournalEntryLine.objects.create(entry=je, account=payment_account, description='Expense', debit=Decimal('0.00'), credit=amount)
        je.validate_balanced()
        je.post(None)
        txn.status = Transaction.STATUS_POSTED
        txn.posted_by = None
        txn.posted_at = timezone.now()
        txn.save(update_fields=['status', 'posted_by', 'posted_at'])


def backfill_school_finance(school, force: bool = False):
    if not school:
        return
    key = getattr(school, 'id', None) or str(school)
    if (not force) and key in _BACKFILLED_SCHOOLS:
        return

    ensure_default_accounts_for_school(school)

    # Backfill FeeCollections
    if FeeCollection is not None:
        try:
            fc_qs = FeeCollection.objects.exclude(paid_amount__lte=0)
            # Scope to this school via any available relation path
            fc_qs = fc_qs.filter(
                Q(student__academic_year__school=school)
                | Q(fee_structure__class_name__school=school)
                | Q(student__current_class__school=school)
            )
            for fc in fc_qs.iterator():
                prefix = f"FEE-{fc.pk}-"
                prev_total = Transaction.objects.filter(
                    school=school, txn_type=Transaction.TYPE_FEE, reference__startswith=prefix
                ).aggregate(total=Sum('amount')).get('total') or Decimal('0.00')
                delta = (fc.paid_amount or Decimal('0.00')) - prev_total
                if delta > 0:
                    _post_fee_delta(school, fc, delta)
        except Exception:
            # Ignore backfill errors silently to avoid blocking page loads
            pass

    # Backfill Expenses (includes Purchases and any previously created from StaffPayment)
    if Expense is not None:
        try:
            exp_qs = Expense.objects.filter(school=school)
            for exp in exp_qs.iterator():
                reference = exp.expense_number
                exists = Transaction.objects.filter(school=school, reference=reference, txn_type=Transaction.TYPE_PAYMENT).exists()
                if not exists:
                    _post_expense_payment(school, exp, reference=reference)
        except Exception:
            pass

    # Backfill Staff Payments that are paid but missing an Expense record
    if StaffPayment is not None and Expense is not None:
        try:
            sp_qs = StaffPayment.objects.filter(school=school, status__iexact='paid', expense__isnull=True)
            for sp in sp_qs.iterator():
                # Create Expense and post
                exp = Expense.objects.create(
                    school=school,
                    expense_number=f"EXP-{sp.payment_number}",
                    expense_type='salary',
                    description=f"Salary payment for {sp.staff_name}",
                    amount=sp.net_salary,
                    expense_date=sp.payment_date,
                    payment_method=sp.payment_method,
                    reference_number=sp.reference_number,
                    payee_name=sp.staff_name,
                    created_by=getattr(sp, 'created_by', None),
                )
                sp.expense = exp
                sp.save(update_fields=['expense'])
                _post_expense_payment(school, exp, reference=exp.expense_number)
        except Exception:
            pass

    if not force:
        _BACKFILLED_SCHOOLS.add(key)
