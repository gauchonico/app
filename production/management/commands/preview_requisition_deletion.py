from django.core.management.base import BaseCommand
from production.models import (
    Requisition, RequisitionItem, RequisitionExpenseItem, 
    LPO, PaymentVoucher, GoodsReceivedNote, 
    ReplaceNote, ReplaceNoteItem, DebitNote,
    DiscrepancyDeliveryReport
)

class Command(BaseCommand):
    help = 'Preview all requisition data that would be deleted'

    def handle(self, *args, **options):
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

        total_records = sum(counts.values())

        self.stdout.write(
            self.style.WARNING(
                f'\n=== REQUISITION DATA SUMMARY ===\n'
                f'Requisitions: {counts["requisitions"]}\n'
                f'Requisition Items: {counts["requisition_items"]}\n'
                f'Requisition Expense Items: {counts["requisition_expenses"]}\n'
                f'LPOs: {counts["lpos"]}\n'
                f'Payment Vouchers: {counts["payment_vouchers"]}\n'
                f'Goods Received Notes: {counts["goods_received_notes"]}\n'
                f'Replace Notes: {counts["replace_notes"]}\n'
                f'Replace Note Items: {counts["replace_note_items"]}\n'
                f'Debit Notes: {counts["debit_notes"]}\n'
                f'Discrepancy Reports: {counts["discrepancy_reports"]}\n'
                f'\nTOTAL RECORDS: {total_records}\n'
            )
        )

        if total_records > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nTo delete all this data, run:\n'
                    'python manage.py delete_all_requisitions --confirm'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nNo requisition data found. Your system is already clean!'
                )
            ) 