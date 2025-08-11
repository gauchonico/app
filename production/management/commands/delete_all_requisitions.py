from django.core.management.base import BaseCommand
from django.db import transaction
from production.models import (
    Requisition, RequisitionItem, RequisitionExpenseItem, 
    LPO, PaymentVoucher, GoodsReceivedNote, 
    ReplaceNote, ReplaceNoteItem, DebitNote,
    DiscrepancyDeliveryReport
)

class Command(BaseCommand):
    help = 'Delete all requisitions and related data (LPOs, payments, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all requisition data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will delete ALL requisition data including:\n'
                    '- Requisitions\n'
                    '- Requisition Items\n'
                    '- Requisition Expense Items\n'
                    '- LPOs\n'
                    '- Payment Vouchers\n'
                    '- Goods Received Notes\n'
                    '- Replace Notes\n'
                    '- Debit Notes\n'
                    '- Discrepancy Reports\n\n'
                    'To proceed, run the command with --confirm flag:\n'
                    'python manage.py delete_all_requisitions --confirm'
                )
            )
            return

        # Count existing records
        counts = {
            'requisitions': Requisition.objects.count(),
            'requisition_items': RequisitionItem.objects.count(),
            'requisition_expenses': RequisitionExpenseItem.objects.count(),
            'lpos': LPO.objects.count(),
            'payment_vouchers': PaymentVoucher.objects.count(),
            'goods_received_notes': GoodsReceivedNote.objects.count(),
            'replace_notes': ReplaceNote.objects.count(),
            'replace_note_items': ReplaceNoteItem.objects.count(),
            'debit_notes': DebitNote.objects.count(),
            'discrepancy_reports': DiscrepancyDeliveryReport.objects.count(),
        }

        self.stdout.write(f"Found {counts['requisitions']} requisitions and related data to delete...")

        # Confirm deletion
        confirm = input("Are you sure you want to delete all this data? Type 'DELETE' to confirm: ")
        if confirm != 'DELETE':
            self.stdout.write(self.style.ERROR('Deletion cancelled.'))
            return

        try:
            with transaction.atomic():
                # Delete in reverse order of dependencies
                deleted_counts = {}
                
                # Delete replace note items first
                deleted_counts['replace_note_items'] = ReplaceNoteItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['replace_note_items']} replace note items")
                
                # Delete replace notes
                deleted_counts['replace_notes'] = ReplaceNote.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['replace_notes']} replace notes")
                
                # Delete debit notes
                deleted_counts['debit_notes'] = DebitNote.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['debit_notes']} debit notes")
                
                # Delete discrepancy reports
                deleted_counts['discrepancy_reports'] = DiscrepancyDeliveryReport.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['discrepancy_reports']} discrepancy reports")
                
                # Delete goods received notes
                deleted_counts['goods_received_notes'] = GoodsReceivedNote.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['goods_received_notes']} goods received notes")
                
                # Delete payment vouchers
                deleted_counts['payment_vouchers'] = PaymentVoucher.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['payment_vouchers']} payment vouchers")
                
                # Delete LPOs
                deleted_counts['lpos'] = LPO.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['lpos']} LPOs")
                
                # Delete requisition expense items
                deleted_counts['requisition_expenses'] = RequisitionExpenseItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['requisition_expenses']} requisition expense items")
                
                # Delete requisition items
                deleted_counts['requisition_items'] = RequisitionItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['requisition_items']} requisition items")
                
                # Delete requisitions
                deleted_counts['requisitions'] = Requisition.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['requisitions']} requisitions")

            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully deleted all requisition data:\n'
                    f'- {deleted_counts["requisitions"]} Requisitions\n'
                    f'- {deleted_counts["requisition_items"]} Requisition Items\n'
                    f'- {deleted_counts["requisition_expenses"]} Requisition Expense Items\n'
                    f'- {deleted_counts["lpos"]} LPOs\n'
                    f'- {deleted_counts["payment_vouchers"]} Payment Vouchers\n'
                    f'- {deleted_counts["goods_received_notes"]} Goods Received Notes\n'
                    f'- {deleted_counts["replace_notes"]} Replace Notes\n'
                    f'- {deleted_counts["replace_note_items"]} Replace Note Items\n'
                    f'- {deleted_counts["debit_notes"]} Debit Notes\n'
                    f'- {deleted_counts["discrepancy_reports"]} Discrepancy Reports\n\n'
                    'Your system is now clean and ready for fresh requisitions!'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error occurred while deleting data: {str(e)}')
            )
            raise 