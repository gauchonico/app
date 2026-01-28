from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import SalesRevenue
from accounts.services import AccountingService
from accounts.signals import get_admin_user
from production.models import StoreSale


class Command(BaseCommand):
    help = "Backfill missing accounting journal entries for existing StoreSales"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Optional ISO date (YYYY-MM-DD). Only backfill sales on or after this date.",
        )

    def handle(self, *args, **options):
        since = options.get("since")
        qs = StoreSale.objects.filter(status="invoiced", total_amount__gt=0)

        if since:
            try:
                from datetime import datetime

                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                qs = qs.filter(order_date__date__gte=since_date)
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid --since date format: {since}. Expected YYYY-MM-DD."))
                return

        admin_user = get_admin_user()
        if not admin_user:
            self.stderr.write(self.style.ERROR("No admin (superuser) found. Cannot create journal entries."))
            return

        total = qs.count()
        created_count = 0

        self.stdout.write(self.style.NOTICE(f"Found {total} invoiced StoreSales to inspect."))

        with transaction.atomic():
            for sale in qs.select_related("customer"):
                # Skip if a SalesRevenue record already exists (journal already created)
                if SalesRevenue.objects.filter(store_sale=sale).exists():
                    continue

                je = AccountingService.create_sales_journal_entry(sale, admin_user)
                if je is not None:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created sales JE {je.id} for StoreSale {sale.order_number} (ID: {sale.id})"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. Created {created_count} new sales journal entries out of {total} invoiced StoreSales."
            )
        )
