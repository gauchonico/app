from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.services import AccountingService
from accounts.signals import get_admin_user
from production.models import StaffCommission, StaffProductCommission


class Command(BaseCommand):
    help = "Backfill missing commission journal entries for StaffCommission and StaffProductCommission"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD). Only backfill commissions "
                "created on or after this date."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Do not create any journal entries; just list which commissions "
                "would get JEs."
            ),
        )

    def handle(self, *args, **options):
        from datetime import datetime

        since = options.get("since")
        dry_run = options.get("dry_run", False)

        service_qs = StaffCommission.objects.filter(accounting_records__isnull=True)
        product_qs = StaffProductCommission.objects.filter(accounting_records__isnull=True)

        if since:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                service_qs = service_qs.filter(created_at__date__gte=since_date)
                product_qs = product_qs.filter(created_at__date__gte=since_date)
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(
                        f"Invalid --since date format: {since}. Expected YYYY-MM-DD."
                    )
                )
                return

        admin_user = get_admin_user()
        if not admin_user:
            self.stderr.write(
                self.style.ERROR(
                    "No admin (superuser) found. Cannot create journal entries."
                )
            )
            return

        total_service = service_qs.count()
        total_product = product_qs.count()
        created_count = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Found {total_service} service commissions and {total_product} product "
                f"commissions without accounting records."
            )
        )

        with transaction.atomic():
            # Service commissions
            for comm in service_qs.select_related("staff", "service_sale_item__service__service"):
                if dry_run:
                    created_count += 1
                    self.stdout.write(
                        self.style.NOTICE(
                            "[DRY-RUN] Would create JE for service commission ID {cid} "
                            "(staff: {staff}, amount: {amt})".format(
                                cid=comm.id,
                                staff=comm.staff.first_name,
                                amt=comm.commission_amount,
                            )
                        )
                    )
                    continue

                je = AccountingService.create_service_commission_journal_entry(
                    comm, admin_user
                )
                if je is not None:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Created JE {je_id} for service commission ID {cid} (staff: {staff})".format(
                                je_id=je.entry_number or je.id,
                                cid=comm.id,
                                staff=comm.staff.first_name,
                            )
                        )
                    )

            # Product commissions
            for pcomm in product_qs.select_related(
                "staff", "product_sale_item__product__product"
            ):
                if dry_run:
                    created_count += 1
                    self.stdout.write(
                        self.style.NOTICE(
                            "[DRY-RUN] Would create JE for product commission ID {cid} "
                            "(staff: {staff}, amount: {amt})".format(
                                cid=pcomm.id,
                                staff=pcomm.staff.first_name,
                                amt=pcomm.commission_amount,
                            )
                        )
                    )
                    continue

                je = AccountingService.create_product_commission_journal_entry(
                    pcomm, admin_user
                )
                if je is not None:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Created JE {je_id} for product commission ID {cid} (staff: {staff})".format(
                                je_id=je.entry_number or je.id,
                                cid=pcomm.id,
                                staff=pcomm.staff.first_name,
                            )
                        )
                    )

        summary_prefix = "DRY-RUN complete." if dry_run else "Backfill complete."
        self.stdout.write(
            self.style.SUCCESS(
                summary_prefix + " Processed {created} commission lines out of "
                "{total_service} service and {total_product} product commissions "
                "without accounting records.".format(
                    created=created_count,
                    total_service=total_service,
                    total_product=total_product,
                )
            )
        )
