from django.core.management.base import BaseCommand
from decimal import Decimal

from accounts.models import ChartOfAccounts
from production.models import Supplier


class Command(BaseCommand):
    help = "Create ChartOfAccounts payables sub-accounts for each supplier and optionally link them."

    def add_arguments(self, parser):
        parser.add_argument(
            '--code-prefix',
            type=str,
            default='2001',
            help='Base code prefix for supplier AP accounts (e.g. 2001 -> 2001001, 2001002, ...).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created/updated without writing to the database.',
        )

    def handle(self, *args, **options):
        code_prefix = options['code_prefix']
        dry_run = options['dry_run']

        self.stdout.write(self.style.MIGRATE_HEADING("Creating supplier AP accounts"))

        # Ensure control account 2000 exists
        control_account, _ = ChartOfAccounts.objects.get_or_create(
            account_code='2000',
            defaults={
                'account_name': 'Accounts Payable - Suppliers',
                'account_type': 'liability',
                'account_category': 'current_liability',
                'is_active': True,
            },
        )

        created = 0
        linked = 0

        for supplier in Supplier.objects.all().order_by('name'):
            if supplier.payables_account:
                self.stdout.write(f"Supplier {supplier.name}: already linked to {supplier.payables_account.account_code}")
                continue

            # Generate a code based on prefix + incremental number
            # e.g. prefix 2001 -> 2001001, 2001002, ...
            base_qs = ChartOfAccounts.objects.filter(account_code__startswith=code_prefix)
            last = base_qs.order_by('-account_code').first()
            if last:
                last_code = last.account_code
                try:
                    seq = int(last_code[len(code_prefix):] or '0') + 1
                except ValueError:
                    seq = 1
            else:
                seq = 1

            new_code = f"{code_prefix}{seq:03d}"
            account_name = f"Accounts Payable - {supplier.name}"

            self.stdout.write(f"Supplier {supplier.name}: -> {new_code} {account_name}")

            if dry_run:
                continue

            ap_account = ChartOfAccounts.objects.create(
                account_code=new_code,
                account_name=account_name,
                account_type='liability',
                account_category='current_liability',
                parent_account=control_account,
                is_active=True,
            )
            created += 1

            supplier.payables_account = ap_account
            supplier.save(update_fields=['payables_account'])
            linked += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete - no changes saved."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created {created} supplier AP accounts and linked {linked} suppliers."))