from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, FormView, ListView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import Sum, Q, Exists, OuterRef
from django.utils import timezone
from decimal import Decimal

from core.utils import get_current_school
from core.models import AcademicYear
from .models import Account, Transaction, JournalEntry, JournalEntryLine, ensure_default_accounts_for_school, DEFAULT_ACCOUNTS
from .backfill import backfill_school_finance
from .forms import ReceiveDonationForm, MakePaymentForm, AccountForm


def user_can_create(user):
    return user.has_perm('finance.can_create_finance_transactions') or user.role in ['accountant', 'admin', 'superadmin']


def user_can_post(user):
    return user.has_perm('finance.can_post_finance_transactions') or user.role in ['accountant', 'admin', 'superadmin']


class FinanceAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return user_can_create(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        school = get_current_school(request)
        if school:
            ensure_default_accounts_for_school(school)
            # Ensure historical data and any missed postings are synchronized immediately
            backfill_school_finance(school, force=True)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['school_slug'] = self.kwargs.get('school_slug', '')
        return ctx


class FinanceDashboardView(FinanceAccessMixin, TemplateView):
    template_name = 'finance/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'dashboard'
        school = get_current_school(self.request)
        accounts = Account.objects.filter(is_active=True)
        if school:
            accounts = accounts.filter(school=school)
        cash_bank = accounts.filter(sub_type__in=[Account.SUBTYPE_CASH, Account.SUBTYPE_BANK]).order_by('code')
        ctx['cash_bank_accounts'] = cash_bank
        ctx['today'] = timezone.now().date()
        return ctx


class ChartOfAccountsView(FinanceAccessMixin, ListView):
    model = Account
    template_name = 'finance/accounts.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Account.objects.all()
        if school:
            qs = qs.filter(school=school)
        qs = qs.annotate(
            has_posted=Exists(
                JournalEntryLine.objects.filter(account=OuterRef('pk'), entry__posted=True)
            )
        ).order_by('code')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'accounts'
        # Totals for opening and current balances
        opening_total = Decimal('0.00')
        balance_total = Decimal('0.00')
        for acc in ctx.get('accounts', []):
            opening_total += (getattr(acc, 'opening_balance', Decimal('0.00')) or Decimal('0.00'))
            balance_total += (getattr(acc, 'current_balance', Decimal('0.00')) or Decimal('0.00'))
        ctx['opening_total'] = opening_total
        ctx['balance_total'] = balance_total
        return ctx


class AccountCreateView(FinanceAccessMixin, CreateView):
    model = Account
    template_name = 'finance/account_form.html'
    form_class = AccountForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.school = get_current_school(self.request)
        obj.save()
        messages.success(self.request, 'Account created')
        return redirect('finance:accounts', school_slug=self.kwargs.get('school_slug', ''))


class AccountUpdateView(FinanceAccessMixin, UpdateView):
    model = Account
    template_name = 'finance/account_form.html'
    form_class = AccountForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Account.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Account updated')
        return redirect('finance:accounts', school_slug=self.kwargs.get('school_slug', ''))


def get_account_by_code_or_name(school, code, name):
    qs = Account.objects.filter(code=code)
    if school:
        qs = qs.filter(school=school)
    acc = qs.first()
    if acc:
        return acc
    qs = Account.objects.filter(name=name)
    if school:
        qs = qs.filter(school=school)
    return qs.first()


    


class AccountDeleteView(FinanceAccessMixin, View):
    def post(self, request, *args, **kwargs):
        school = get_current_school(request)
        qs = Account.objects.all()
        if school:
            qs = qs.filter(school=school)
        account = get_object_or_404(qs, pk=kwargs.get('pk'))
        # Prevent deletion of default seeded accounts
        default_codes = {code for code, *_ in DEFAULT_ACCOUNTS}
        if account.code in default_codes:
            messages.error(request, 'Cannot delete a default system account')
            return redirect('finance:accounts', school_slug=kwargs.get('school_slug', ''))
        # Prevent deletion if there are related posted journal lines
        if account.journal_lines.filter(entry__posted=True).exists():
            messages.error(request, 'Cannot delete account with existing transactions')
            return redirect('finance:accounts', school_slug=kwargs.get('school_slug', ''))
        try:
            account.delete()
            messages.success(request, 'Account deleted')
        except Exception:
            messages.error(request, 'Unable to delete account')
        return redirect('finance:accounts', school_slug=kwargs.get('school_slug', ''))


class AccountBreakdownView(FinanceAccessMixin, View):
    def get(self, request, *args, **kwargs):
        school = get_current_school(request)
        qs = Account.objects.all()
        if school:
            qs = qs.filter(school=school)
        account = get_object_or_404(qs, pk=kwargs.get('pk'))

        lines_qs = (
            JournalEntryLine.objects
            .select_related('entry', 'account')
            .prefetch_related('entry__lines__account')
            .filter(account=account, entry__posted=True)
            .order_by('-entry__date', '-entry_id', '-id')
        )
        agg = lines_qs.aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))
        posted_count = lines_qs.count()
        last_date = lines_qs.values_list('entry__date', flat=True).first()

        items = []
        for ln in list(lines_qs[:20]):
            others = [ol for ol in ln.entry.lines.all() if ol.id != ln.id]
            counter = ", ".join(f"{ol.account.code} - {ol.account.name}" for ol in others)
            items.append({
                'date': ln.entry.date,
                'reference': ln.entry.reference,
                'memo': ln.entry.memo,
                'description': ln.description,
                'debit': ln.debit,
                'credit': ln.credit,
                'counter': counter,
            })

        ctx = {
            'account': account,
            'posted_count': posted_count,
            'total_debit': agg.get('total_debit') or Decimal('0.00'),
            'total_credit': agg.get('total_credit') or Decimal('0.00'),
            'last_date': last_date,
            'lines': items,
        }
        return render(request, 'finance/account_breakdown.html', ctx)


class ReceiveDonationView(FinanceAccessMixin, FormView):
    template_name = 'finance/donations.html'
    form_class = ReceiveDonationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        if not user_can_post(self.request.user):
            messages.error(self.request, 'You do not have permission to post transactions')
            return self.form_invalid(form)
        school = get_current_school(self.request)
        donor_name = form.cleaned_data['donor_name']
        amount = form.cleaned_data['amount']
        donation_type = form.cleaned_data['donation_type']
        deposit_account = form.cleaned_data['deposit_account']
        date = form.cleaned_data['date']
        notes = form.cleaned_data.get('notes') or ''
        income_acc = get_account_by_code_or_name(school, '4100', 'Donations – Restricted') if donation_type == 'restricted' else get_account_by_code_or_name(school, '4110', 'Donations – Unrestricted')
        with db_transaction.atomic():
            txn = Transaction.objects.create(
                school=school,
                txn_type=Transaction.TYPE_DONATION,
                date=date,
                reference='',
                description=f'Donation from {donor_name}',
                amount=amount,
                donor_name=donor_name,
                donation_type=donation_type,
                created_by=self.request.user,
                status=Transaction.STATUS_PENDING,
            )
            je = JournalEntry.objects.create(
                school=school,
                date=date,
                reference='',
                memo=notes or txn.description,
                transaction=txn,
                posted=False,
            )
            JournalEntryLine.objects.create(entry=je, account=deposit_account, description='Donation receipt', debit=amount, credit=Decimal('0.00'))
            JournalEntryLine.objects.create(entry=je, account=income_acc, description='Donation receipt', debit=Decimal('0.00'), credit=amount)
            je.validate_balanced()
            je.post(self.request.user)
            txn.status = Transaction.STATUS_POSTED
            txn.posted_by = self.request.user
            txn.posted_at = timezone.now()
            txn.save(update_fields=['status', 'posted_by', 'posted_at'])
        messages.success(self.request, 'Donation received and posted')
        return redirect('finance:dashboard', school_slug=self.kwargs.get('school_slug', ''))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'donations'
        return ctx


class MakePaymentView(FinanceAccessMixin, FormView):
    template_name = 'finance/payments.html'
    form_class = MakePaymentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        if not user_can_post(self.request.user):
            messages.error(self.request, 'You do not have permission to post transactions')
            return self.form_invalid(form)
        school = get_current_school(self.request)
        payee_type = form.cleaned_data['payee_type']
        amount = form.cleaned_data['amount']
        debit_account = form.cleaned_data['debit_account']
        payment_account = form.cleaned_data['payment_account']
        date = form.cleaned_data['date']
        description = form.cleaned_data.get('description') or ''
        payee_name = form.get_payee_display()
        if amount > payment_account.current_balance:
            messages.error(self.request, 'Insufficient funds in selected account')
            return self.form_invalid(form)
        with db_transaction.atomic():
            txn = Transaction.objects.create(
                school=school,
                txn_type=Transaction.TYPE_PAYMENT,
                date=date,
                reference='',
                description=description or f'Payment to {payee_name}',
                amount=amount,
                payee_type=payee_type,
                payee_name=payee_name,
                created_by=self.request.user,
                status=Transaction.STATUS_PENDING,
            )
            je = JournalEntry.objects.create(
                school=school,
                date=date,
                reference='',
                memo=txn.description,
                transaction=txn,
                posted=False,
            )
            JournalEntryLine.objects.create(entry=je, account=debit_account, description='Payment', debit=amount, credit=Decimal('0.00'))
            JournalEntryLine.objects.create(entry=je, account=payment_account, description='Payment', debit=Decimal('0.00'), credit=amount)
            je.validate_balanced()
            je.post(self.request.user)
            txn.status = Transaction.STATUS_POSTED
            txn.posted_by = self.request.user
            txn.posted_at = timezone.now()
            txn.save(update_fields=['status', 'posted_by', 'posted_at'])
        messages.success(self.request, 'Payment posted')
        return redirect('finance:dashboard', school_slug=self.kwargs.get('school_slug', ''))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'payments'
        return ctx


class GeneralLedgerView(FinanceAccessMixin, TemplateView):
    template_name = 'finance/ledger.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'ledger'
        school = get_current_school(self.request)
        date_from = self.request.GET.get('from')
        date_to = self.request.GET.get('to')
        lines_qs = (
            JournalEntryLine.objects
            .select_related('entry', 'account')
            .prefetch_related('entry__lines__account')
            .filter(entry__posted=True)
        )
        if school:
            lines_qs = lines_qs.filter(entry__school=school)
        if date_from:
            lines_qs = lines_qs.filter(entry__date__gte=date_from)
        if date_to:
            lines_qs = lines_qs.filter(entry__date__lte=date_to)
        lines_qs = lines_qs.order_by('account_id', 'entry__date', 'entry_id', 'id')

        running = {}
        lines = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        # Build a map of entry_id to its lines to show counter accounts per line
        lines_list = list(lines_qs)
        entry_map = {}
        for _ln in lines_list:
            entry_map.setdefault(_ln.entry_id, []).append(_ln)

        for ln in lines_list:
            acc = ln.account
            if acc.id not in running:
                running[acc.id] = acc.opening_balance_effect()
            d = (ln.debit or Decimal('0.00'))
            c = (ln.credit or Decimal('0.00'))
            running[acc.id] += d - c
            total_debit += d
            total_credit += c
            # Counterpart account names for this entry (exclude this line)
            others = [ol for ol in entry_map.get(ln.entry_id, []) if ol.id != ln.id]
            counter = ", ".join(f"{ol.account.code} - {ol.account.name}" for ol in others)
            lines.append({
                'date': ln.entry.date,
                'reference': ln.entry.reference,
                'account': acc,
                'debit': ln.debit,
                'credit': ln.credit,
                'description': ln.description,
                'counter': counter,
                'running_balance': running[acc.id],
            })

        ctx['lines'] = lines
        ctx['total_debit'] = total_debit
        ctx['total_credit'] = total_credit
        ctx['net_change'] = total_debit - total_credit
        ctx['date_from'] = date_from or ''
        ctx['date_to'] = date_to or ''
        return ctx


class ReportsView(FinanceAccessMixin, TemplateView):
    template_name = 'finance/reports.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'reports'
        school = get_current_school(self.request)
        date_from = self.request.GET.get('from')
        date_to = self.request.GET.get('to')
        academic_year_id = self.request.GET.get('academic_year')
        je_filter = Q(entry__posted=True)
        if school:
            je_filter &= Q(entry__school=school)
        if date_from:
            je_filter &= Q(entry__date__gte=date_from)
        if date_to:
            je_filter &= Q(entry__date__lte=date_to)
        if academic_year_id:
            je_filter &= Q(entry__transaction__academic_year_id=academic_year_id)
        lines = JournalEntryLine.objects.select_related('entry', 'account', 'entry__transaction').filter(je_filter)
        sums = lines.values('account_id', 'account__account_type', 'account__code', 'account__name').annotate(total_debit=Sum('debit'), total_credit=Sum('credit'))
        by_type = {'asset': Decimal('0.00'), 'liability': Decimal('0.00'), 'equity': Decimal('0.00'), 'income': Decimal('0.00'), 'expense': Decimal('0.00')}
        trial_rows = []
        for s in sums:
            debit = s['total_debit'] or Decimal('0.00')
            credit = s['total_credit'] or Decimal('0.00')
            trial_rows.append({'account_id': s['account_id'], 'code': s['account__code'], 'name': s['account__name'], 'debit': debit, 'credit': credit, 'type': s['account__account_type']})
            if s['account__account_type'] in by_type:
                if s['account__account_type'] in ['asset', 'expense']:
                    by_type[s['account__account_type']] += (debit - credit)
                else:
                    by_type[s['account__account_type']] += (credit - debit)
        income_total = by_type['income']
        expense_total = by_type['expense']
        net_income = income_total - expense_total
        assets_total = by_type['asset']
        liabilities_total = by_type['liability']
        equity_total = by_type['equity'] + net_income
        # Totals for Trial Balance table
        trial_total_debit = Decimal('0.00')
        trial_total_credit = Decimal('0.00')
        for r in trial_rows:
            trial_total_debit += (r.get('debit') or Decimal('0.00'))
            trial_total_credit += (r.get('credit') or Decimal('0.00'))
        ctx['date_from'] = date_from or ''
        ctx['date_to'] = date_to or ''
        ctx['trial_summaries'] = sums
        ctx['trial_rows'] = sorted(trial_rows, key=lambda r: (r['code'] or '', r['name'] or ''))
        ctx['trial_total_debit'] = trial_total_debit
        ctx['trial_total_credit'] = trial_total_credit
        ctx['net_income'] = net_income
        ctx['assets_total'] = assets_total
        ctx['liabilities_total'] = liabilities_total
        ctx['equity_total'] = equity_total
        ctx['academic_year_id'] = academic_year_id or ''
        # Academic years for filter dropdown
        years_qs = AcademicYear.objects.all()
        if school:
            years_qs = years_qs.filter(school=school)
        ctx['academic_years'] = years_qs.order_by('-start_date')
        return ctx


class ReclassifyDepositsView(FinanceAccessMixin, TemplateView):
    template_name = 'finance/reclassify.html'

    def _get_defaults(self, school):
        src = Account.objects.filter(school=school, code='1000').first()
        dest = Account.objects.filter(school=school, code='1010').first()
        return src, dest

    def _compute_eligible(self, school, source_acc, dest_acc, date_from, date_to):
        if not source_acc or not dest_acc:
            return Decimal('0.00')
        # Sum of fee deposit debits into source account within range
        fee_deposits = JournalEntryLine.objects.filter(
            entry__posted=True,
            entry__school=school,
            account=source_acc,
            entry__transaction__txn_type=Transaction.TYPE_FEE,
        )
        if date_from:
            fee_deposits = fee_deposits.filter(entry__date__gte=date_from)
        if date_to:
            fee_deposits = fee_deposits.filter(entry__date__lte=date_to)
        total_deposits = fee_deposits.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

        # Subtract any previous reclass JEs we created (tagged in memo)
        tag = f"REclass-FEE {source_acc.code}->{dest_acc.code}"
        prev_reclass = JournalEntryLine.objects.filter(
            entry__posted=True,
            entry__school=school,
            account=dest_acc,
            entry__transaction__isnull=True,
            entry__memo__icontains=tag,
        )
        if date_from:
            prev_reclass = prev_reclass.filter(entry__date__gte=date_from)
        if date_to:
            prev_reclass = prev_reclass.filter(entry__date__lte=date_to)
        total_reclass = prev_reclass.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

        eligible = total_deposits - total_reclass
        return eligible if eligible > 0 else Decimal('0.00')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'reports'
        school = get_current_school(self.request)
        date_from = self.request.GET.get('from') or ''
        date_to = self.request.GET.get('to') or ''
        # Accounts
        source_id = self.request.GET.get('source_id')
        dest_id = self.request.GET.get('dest_id')
        if school:
            accounts_qs = Account.objects.filter(school=school, sub_type__in=[Account.SUBTYPE_CASH, Account.SUBTYPE_BANK], is_active=True).order_by('code')
        else:
            accounts_qs = Account.objects.none()
        src, dest = self._get_defaults(school) if school else (None, None)
        if source_id:
            src = accounts_qs.filter(id=source_id).first() or src
        if dest_id:
            dest = accounts_qs.filter(id=dest_id).first() or dest

        eligible = self._compute_eligible(school, src, dest, date_from or None, date_to or None) if school else Decimal('0.00')

        ctx.update({
            'accounts': accounts_qs,
            'source_acc': src,
            'dest_acc': dest,
            'date_from': date_from,
            'date_to': date_to,
            'eligible_amount': eligible,
        })
        return ctx

    def post(self, request, *args, **kwargs):
        school = get_current_school(request)
        if not school:
            messages.error(request, 'No school selected')
            return redirect('finance:reports', school_slug=self.kwargs.get('school_slug', ''))
        date_from = request.POST.get('from') or None
        date_to = request.POST.get('to') or None
        source_id = request.POST.get('source_id')
        dest_id = request.POST.get('dest_id')
        accounts_qs = Account.objects.filter(school=school, sub_type__in=[Account.SUBTYPE_CASH, Account.SUBTYPE_BANK], is_active=True)
        source_acc = accounts_qs.filter(id=source_id).first()
        dest_acc = accounts_qs.filter(id=dest_id).first()
        if not source_acc or not dest_acc:
            messages.error(request, 'Invalid accounts')
            return redirect('finance:reclassify', school_slug=self.kwargs.get('school_slug', ''))

        amount = self._compute_eligible(school, source_acc, dest_acc, date_from, date_to)
        if amount <= 0:
            messages.info(request, 'Nothing to reclassify for the selected range and accounts')
            return redirect('finance:reclassify', school_slug=self.kwargs.get('school_slug', ''))

        # Create and post a reclass JE: Dr dest, Cr source
        tag = f"REclass-FEE {source_acc.code}->{dest_acc.code}"
        ref = f"RECLASS-FEE-{int(timezone.now().timestamp())}"
        with db_transaction.atomic():
            je = JournalEntry.objects.create(
                school=school,
                date=timezone.now().date(),
                reference=ref,
                memo=f"{tag} ({date_from or 'start'} to {date_to or 'end'})",
                transaction=None,
                posted=False,
            )
            JournalEntryLine.objects.create(entry=je, account=dest_acc, description='Reclass fee deposit', debit=amount, credit=Decimal('0.00'))
            JournalEntryLine.objects.create(entry=je, account=source_acc, description='Reclass fee deposit', debit=Decimal('0.00'), credit=amount)
            je.validate_balanced()
            je.post(self.request.user)
        messages.success(request, f'Reclassified {amount} from {source_acc.code} to {dest_acc.code}')
        return redirect('finance:reclassify', school_slug=self.kwargs.get('school_slug', ''))
