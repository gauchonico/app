from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import JournalEntry, JournalEntryLine, ChartOfAccounts, Department
from production.models import StoreProductSale


# ── Account resolution maps ───────────────────────────────────────────────────

STORE_CASH_CODES = {
    'mutaasa': '3004',
    'bugolobi': '3001',
    'ntinda': '3002',
    'kyanja': '3003',
}

PAYMENT_METHOD_CODES = {
    'mobile_money': '10100',
    'airtel_money': '101001',
    'visa': '1020',
    'bank_transfer': '1020',
}

PRODUCT_REVENUE_CODE = '4100'


def resolve_cash_account(store, payment_method):
    """Return the correct ChartOfAccounts entry for this store + payment method."""
    if payment_method == 'cash' or payment_method == 'mixed':
        store_key = (store.name or '').strip().lower()
        for key, code in STORE_CASH_CODES.items():
            if key in store_key:
                account = ChartOfAccounts.objects.filter(account_code=code).first()
                if account:
                    return account
        # Fallback
        return ChartOfAccounts.objects.filter(account_code='1000').first()

    code = PAYMENT_METHOD_CODES.get(payment_method)
    if code:
        return ChartOfAccounts.objects.filter(account_code=code).first()

    return ChartOfAccounts.objects.filter(account_code='1000').first()


class Command(BaseCommand):
    help = (
        'Backfill journal entries for paid StoreProductSale records '
        'that were created before the post_save signal existed.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be posted without writing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved\n'))

        # ── Find all paid sales with no journal entry ─────────────────────────
        paid_sales = StoreProductSale.objects.filter(
            paid_status='paid'
        ).select_related('store', 'customer', 'cash_drawer_session__user')

        already_posted_refs = set(
            JournalEntry.objects.filter(
                reference__startswith='ProductSale-'
            ).values_list('reference', flat=True)
        )

        missing_sales = [
            s for s in paid_sales
            if f"ProductSale-{s.id}" not in already_posted_refs
        ]

        if not missing_sales:
            self.stdout.write(self.style.SUCCESS('Nothing to backfill — all paid sales already have journal entries.'))
            return

        self.stdout.write(f"Found {len(missing_sales)} sale(s) missing journal entries:\n")

        # ── Resolve shared accounts once ──────────────────────────────────────
        revenue_account = ChartOfAccounts.objects.filter(
            account_code=PRODUCT_REVENUE_CODE
        ).first()

        if not revenue_account:
            self.stdout.write(
                self.style.ERROR(f'Revenue account {PRODUCT_REVENUE_CODE} not found. Aborting.')
            )
            return

        store_dept = Department.objects.filter(code='STORE').first()

        # Fallback system user
        system_user = (
            User.objects.filter(is_superuser=True).first()
        )

        # ── Process each sale ─────────────────────────────────────────────────
        success = 0
        errors = 0

        for sale in missing_sales:
            store = sale.store
            cash_account = resolve_cash_account(store, sale.payment_mode)

            if not cash_account:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Sale #{sale.id} ({store.name} / {sale.payment_mode}): "
                        f"cash account not found — skipping."
                    )
                )
                errors += 1
                continue

            # Resolve user: prefer the cash drawer session user
            user = None
            if sale.cash_drawer_session and sale.cash_drawer_session.user:
                user = sale.cash_drawer_session.user
            if not user:
                user = system_user

            self.stdout.write(
                f"  → Sale #{sale.id} | {store.name} | "
                f"{sale.payment_mode} | {sale.total_amount} | {sale.sale_date.date()}\n"
                f"       DR {cash_account.account_code} {cash_account.account_name}\n"
                f"       CR {revenue_account.account_code} {revenue_account.account_name}\n"
                f"       User: {user}"
            )

            if not dry_run:
                try:
                    with transaction.atomic():
                        je = JournalEntry.objects.create(
                            date=sale.sale_date.date(),
                            reference=f"ProductSale-{sale.id}",
                            description=(
                                f"Product sale {sale.product_sale_number} — "
                                f"{sale.customer.first_name} {sale.customer.last_name} "
                                f"at {store.name}"
                            ),
                            entry_type='sales',
                            department=store_dept,
                            created_by=user,
                            is_posted=True,
                            posted_at=timezone.now(),
                        )

                        # DR Cash / Mobile Money / Bank
                        JournalEntryLine.objects.create(
                            journal_entry=je,
                            account=cash_account,
                            entry_type='debit',
                            amount=sale.total_amount,
                            description=(
                                f"Cash received via {sale.payment_mode} — "
                                f"{sale.product_sale_number}"
                            ),
                        )

                        # CR 4100 Product Sales Revenue
                        JournalEntryLine.objects.create(
                            journal_entry=je,
                            account=revenue_account,
                            entry_type='credit',
                            amount=sale.total_amount,
                            description=(
                                f"Product sales revenue — {sale.product_sale_number} "
                                f"at {store.name}"
                            ),
                        )

                        self.stdout.write(
                            self.style.SUCCESS(f"       ✓ Posted as {je.entry_number}")
                        )
                        success += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"       ✗ Failed: {e}")
                    )
                    errors += 1
            else:
                success += 1

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('\n' + '─' * 50)
        action = 'Would post' if dry_run else 'Posted'
        self.stdout.write(self.style.SUCCESS(
            f"Done.\n"
            f"  {action}  : {success} journal entries\n"
            f"  Errors   : {errors}"
        ))
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nDRY RUN — re-run without --dry-run to apply.')
            )