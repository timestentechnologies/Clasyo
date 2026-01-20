from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Account, Transaction, JournalEntry, JournalEntryLine, ensure_default_accounts_for_school
from core.models import Notification

# External models
try:
    from fees.models import FeeCollection
except Exception:
    FeeCollection = None

try:
    from inventory.models import Expense
except Exception:
    Expense = None


def _get_school_from_fee_collection(obj):
    # Try student.academic_year.school, fallback to fee_structure.class_name.school
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
    """Map payment method to a cash/bank account depending on context."""
    method = (method or '').lower()
    ensure_default_accounts_for_school(school)
    if method == 'cash':
        acc = Account.objects.filter(school=school, code='1000').first()
        if acc:
            return acc
    # For fees -> tuition bank, for expenses -> operations bank
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


@receiver(post_save, sender=FeeCollection)
def post_fee_collection_to_ledger(sender, instance: 'FeeCollection', created, **kwargs):
    if instance is None:
        return
    # Post when there is a paid amount and a payment_date (supports partial and full)
    try:
        if (instance.paid_amount or Decimal('0')) <= 0:
            return
    except Exception:
        return

    school = _get_school_from_fee_collection(instance)
    if not school:
        return

    ensure_default_accounts_for_school(school)

    # Post only the delta of paid amount. Track previous postings by FEE-{fee_id}- prefix.
    prefix = f"FEE-{instance.pk}-"
    prev_total = Transaction.objects.filter(
        school=school, txn_type=Transaction.TYPE_FEE, reference__startswith=prefix
    ).aggregate(total=Sum('amount')).get('total') or Decimal('0.00')
    amount = (instance.paid_amount or Decimal('0.00')) - prev_total
    if amount <= 0:
        return

    # Prefer explicitly selected deposit account on the collection, fallback to method mapping
    deposit_account = getattr(instance, 'deposit_account', None) or _get_payment_account_for_method(school, instance.payment_method, context="fees")
    income_acc = Account.objects.filter(school=school, code='4000').first()
    if not deposit_account or not income_acc:
        return
    # Prepare common fields
    date = instance.payment_date or timezone.now().date()
    description = f"Fee collection for {instance.student.get_full_name()}"
    reference = f"{prefix}{int(timezone.now().timestamp())}"
    # Block if deposit account inactive
    if deposit_account and not deposit_account.is_active:
        # Create pending txn and notify collector if available
        with db_transaction.atomic():
            txn = Transaction.objects.create(
                school=school,
                txn_type=Transaction.TYPE_FEE,
                date=date,
                reference=f"{prefix}INACTIVE",
                description=f"INACTIVE ACCOUNT: {description}",
                amount=amount,
                student=instance.student,
                academic_year=getattr(instance.student, 'academic_year', None),
                is_advance=False,
                created_by=instance.collected_by,
                status=Transaction.STATUS_PENDING,
            )
            if instance.collected_by:
                Notification.objects.create(
                    user=instance.collected_by,
                    title="Fee not posted",
                    message=f"Fee receipt {instance.receipt_number or instance.pk} not posted: deposit account is inactive.",
                    notification_type='warning',
                )
        return

    with db_transaction.atomic():
        txn = Transaction.objects.create(
            school=school,
            txn_type=Transaction.TYPE_FEE,
            date=date,
            reference=reference,
            description=description,
            amount=amount,
            student=instance.student,
            academic_year=getattr(instance.student, 'academic_year', None),
            is_advance=False,
            created_by=instance.collected_by,
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


@receiver(post_save, sender=Expense)
def post_expense_to_ledger(sender, instance: 'Expense', created, **kwargs):
    if instance is None:
        return
    school = getattr(instance, 'school', None)
    if not school:
        return

    ensure_default_accounts_for_school(school)

    # Use expense_number as stable reference
    if not instance.expense_number:
        return
    reference = instance.expense_number
    if Transaction.objects.filter(school=school, reference=reference, txn_type=Transaction.TYPE_PAYMENT).exists():
        return  # already posted

    amount = instance.amount
    if (amount or Decimal('0')) <= 0:
        return

    payment_method = instance.payment_method
    payment_account = _get_payment_account_for_method(school, payment_method, context="expenses")
    debit_account = _get_expense_debit_account(school, instance.expense_type)
    if not payment_account or not debit_account:
        return
    # Prepare common fields
    date = instance.expense_date or timezone.now().date()
    description = instance.description or f"Expense: {instance.payee_name}"
    # Block if any account inactive
    if (payment_account and not payment_account.is_active) or (debit_account and not debit_account.is_active):
        with db_transaction.atomic():
            txn = Transaction.objects.create(
                school=school,
                txn_type=Transaction.TYPE_PAYMENT,
                date=date,
                reference=f"{reference}-INACTIVE",
                description=f"INACTIVE ACCOUNT: {description}",
                amount=amount,
                payee_type='supplier' if instance.expense_type == 'purchase' else 'other',
                payee_name=instance.payee_name,
                created_by=instance.created_by,
                status=Transaction.STATUS_PENDING,
            )
            if instance.created_by:
                Notification.objects.create(
                    user=instance.created_by,
                    title="Expense not posted",
                    message=f"Expense {instance.expense_number} not posted: selected account is inactive.",
                    notification_type='warning',
                )
        return

    with db_transaction.atomic():
        # Block posting if insufficient funds; create pending txn and notify
        if amount > (payment_account.current_balance or Decimal('0.00')):
            txn = Transaction.objects.create(
                school=school,
                txn_type=Transaction.TYPE_PAYMENT,
                date=date,
                reference=reference,
                description=f"INSUFFICIENT FUNDS: {description}",
                amount=amount,
                payee_type='supplier' if instance.expense_type == 'purchase' else 'other',
                payee_name=instance.payee_name,
                created_by=instance.created_by,
                status=Transaction.STATUS_PENDING,
            )
            if instance.created_by:
                Notification.objects.create(
                    user=instance.created_by,
                    title="Expense not posted",
                    message=f"Expense {instance.expense_number} not posted due to insufficient funds in selected account.",
                    notification_type='warning',
                )
            return
        txn = Transaction.objects.create(
            school=school,
            txn_type=Transaction.TYPE_PAYMENT,
            date=date,
            reference=reference,
            description=description,
            amount=amount,
            payee_type='supplier' if instance.expense_type == 'purchase' else 'other',
            payee_name=instance.payee_name,
            created_by=instance.created_by,
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
        JournalEntryLine.objects.create(entry=je, account=debit_account, description='Expense', debit=amount, credit=Decimal('0.00'))
        JournalEntryLine.objects.create(entry=je, account=payment_account, description='Expense', debit=Decimal('0.00'), credit=amount)
        je.validate_balanced()
        je.post(None)
        txn.status = Transaction.STATUS_POSTED
        txn.posted_by = None
        txn.posted_at = timezone.now()
        txn.save(update_fields=['status', 'posted_by', 'posted_at'])
