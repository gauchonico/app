from django.core.management.base import BaseCommand
from django.db import transaction
from production.models import (
    # Requisition Data
    Requisition, RequisitionItem, RequisitionExpenseItem, 
    LPO, PaymentVoucher, GoodsReceivedNote, 
    ReplaceNote, ReplaceNoteItem, DebitNote,
    DiscrepancyDeliveryReport,
    
    # Store Sales and Service Sales
    StoreSale, SaleItem, StoreSaleReceipt,
    ServiceSale, ServiceSaleItem, AccessorySaleItem, ProductSaleItem,
    
    # Manufacturing and Production
    ProductionOrder, ManufactureProduct, ManufacturedProductInventory, ManufacturedProductIngredient,
    ProductionBatch, WriteOff,
    
    # Store Inventory and Transfers
    LivaraMainStore, LivaraInventoryAdjustment, StoreTransfer, StoreTransferItem,
    StoreInventory, InventoryAdjustment, StoreWriteOff,
    
    # Restocking
    RestockRequest, RestockRequestItem, TransferApproval,
    
    # Accessories
    AccessoryInventory, AccessoryInventoryAdjustment, StoreAccessoryInventory,
    MainStoreAccessoryRequisition, MainStoreAccessoryRequisitionItem,
    InternalAccessoryRequest, InternalAccessoryRequestItem,
    
    # Commissions and Payments
    StaffCommission, MonthlyStaffCommission, StaffProductCommission,
    Payment, ServiceSaleInvoice,
    
    # Store Inventory Adjustments
    StoreInventoryAdjustment,
)

class Command(BaseCommand):
    help = 'Clean the entire system - delete all requisitions, store data, and manufacturing records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete ALL system data',
        )
        parser.add_argument(
            '--only-requisitions',
            action='store_true',
            help='Only delete requisition data',
        )
        parser.add_argument(
            '--only-store',
            action='store_true',
            help='Only delete store/factory data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will COMPLETELY CLEAN your system by deleting:\n\n'
                    '=== REQUISITION DATA ===\n'
                    '- Requisitions & Items\n'
                    '- LPOs & Payment Vouchers\n'
                    '- Goods Received Notes\n'
                    '- Replace Notes & Debit Notes\n'
                    '- Discrepancy Reports\n\n'
                    '=== STORE/FACTORY DATA ===\n'
                    '- Store Sales & Service Sales\n'
                    '- Production Orders & Manufacturing\n'
                    '- Store Inventory & Transfers\n'
                    '- Accessory Data & Staff Commissions\n'
                    '- All related transactions\n\n'
                    'Options:\n'
                    '  --only-requisitions  Clean only requisition data\n'
                    '  --only-store        Clean only store/factory data\n'
                    '  --confirm           Clean everything\n\n'
                    'To proceed, run with --confirm flag:\n'
                    'python manage.py clean_system --confirm'
                )
            )
            return

        # Determine what to clean
        clean_requisitions = not options['only_store']
        clean_store = not options['only_requisitions']

        if options['only_requisitions']:
            self.stdout.write("Cleaning ONLY requisition data...")
        elif options['only_store']:
            self.stdout.write("Cleaning ONLY store/factory data...")
        else:
            self.stdout.write("Cleaning ALL system data...")

        # Count total records
        requisition_count = 0
        store_count = 0
        
        if clean_requisitions:
            requisition_count = (
                Requisition.objects.count() + LPO.objects.count() + 
                PaymentVoucher.objects.count() + GoodsReceivedNote.objects.count()
            )
        
        if clean_store:
            store_count = (
                StoreSale.objects.count() + ServiceSale.objects.count() +
                ProductionOrder.objects.count() + ManufactureProduct.objects.count() +
                LivaraMainStore.objects.count() + StoreInventory.objects.count()
            )

        total_estimated = requisition_count + store_count
        self.stdout.write(f"Estimated records to delete: {total_estimated}")

        # Final confirmation
        if clean_requisitions and clean_store:
            confirm_text = "CLEAN ALL"
            warning = "This will delete ALL your business data!"
        elif clean_requisitions:
            confirm_text = "CLEAN REQUISITIONS"
            warning = "This will delete all requisition and procurement data!"
        else:
            confirm_text = "CLEAN STORE"
            warning = "This will delete all store, sales, and manufacturing data!"

        self.stdout.write(self.style.ERROR(f"\n{warning}"))
        confirm = input(f"Type '{confirm_text}' to confirm: ")
        if confirm != confirm_text:
            self.stdout.write(self.style.ERROR('Cleaning cancelled.'))
            return

        try:
            with transaction.atomic():
                deleted_counts = {}
                total_deleted = 0

                if clean_requisitions:
                    self.stdout.write(self.style.WARNING("\n=== CLEANING REQUISITION DATA ==="))
                    
                    # Delete requisition data in dependency order
                    deleted_counts['replace_note_items'] = ReplaceNoteItem.objects.all().delete()[0]
                    deleted_counts['replace_notes'] = ReplaceNote.objects.all().delete()[0]
                    deleted_counts['debit_notes'] = DebitNote.objects.all().delete()[0]
                    deleted_counts['discrepancy_reports'] = DiscrepancyDeliveryReport.objects.all().delete()[0]
                    deleted_counts['goods_received_notes'] = GoodsReceivedNote.objects.all().delete()[0]
                    deleted_counts['payment_vouchers'] = PaymentVoucher.objects.all().delete()[0]
                    deleted_counts['lpos'] = LPO.objects.all().delete()[0]
                    deleted_counts['requisition_expenses'] = RequisitionExpenseItem.objects.all().delete()[0]
                    deleted_counts['requisition_items'] = RequisitionItem.objects.all().delete()[0]
                    deleted_counts['requisitions'] = Requisition.objects.all().delete()[0]
                    
                    req_total = sum([deleted_counts[k] for k in deleted_counts if k.startswith(('req', 'lpo', 'payment', 'goods', 'replace', 'debit', 'discrepancy'))])
                    self.stdout.write(f"✓ Deleted {req_total} requisition-related records")

                if clean_store:
                    self.stdout.write(self.style.WARNING("\n=== CLEANING STORE/FACTORY DATA ==="))
                    
                    # Delete store data in dependency order
                    store_deletions = [
                        ('staff_commissions', StaffCommission),
                        ('monthly_staff_commissions', MonthlyStaffCommission),
                        ('staff_product_commissions', StaffProductCommission),
                        ('payments', Payment),
                        ('service_sale_invoices', ServiceSaleInvoice),
                        ('accessory_sale_items', AccessorySaleItem),
                        ('product_sale_items', ProductSaleItem),
                        ('service_sale_items', ServiceSaleItem),
                        ('sale_items', SaleItem),
                        ('store_sale_receipts', StoreSaleReceipt),
                        ('service_sales', ServiceSale),
                        ('store_sales', StoreSale),
                        ('store_transfer_items', StoreTransferItem),
                        ('restock_request_items', RestockRequestItem),
                        ('main_store_accessory_requisition_items', MainStoreAccessoryRequisitionItem),
                        ('internal_accessory_request_items', InternalAccessoryRequestItem),
                        ('transfer_approvals', TransferApproval),
                        ('store_transfers', StoreTransfer),
                        ('restock_requests', RestockRequest),
                        ('main_store_accessory_requisitions', MainStoreAccessoryRequisition),
                        ('internal_accessory_requests', InternalAccessoryRequest),
                        ('livara_inventory_adjustments', LivaraInventoryAdjustment),
                        ('inventory_adjustments', InventoryAdjustment),
                        ('store_inventory_adjustments', StoreInventoryAdjustment),
                        ('accessory_inventory_adjustments', AccessoryInventoryAdjustment),
                        ('store_write_offs', StoreWriteOff),
                        ('write_offs', WriteOff),
                        ('manufactured_product_ingredients', ManufacturedProductIngredient),
                        ('store_accessory_inventory', StoreAccessoryInventory),
                        ('store_inventory', StoreInventory),
                        ('livara_main_store', LivaraMainStore),
                        ('manufactured_product_inventory', ManufacturedProductInventory),
                        ('accessory_inventory', AccessoryInventory),
                        ('manufactured_products', ManufactureProduct),
                        ('production_batches', ProductionBatch),
                        ('production_orders', ProductionOrder),
                    ]
                    
                    for name, model in store_deletions:
                        deleted_counts[name] = model.objects.all().delete()[0]
                    
                    store_total = sum([deleted_counts[k] for k in deleted_counts if not k.startswith(('req', 'lpo', 'payment', 'goods', 'replace', 'debit', 'discrepancy'))])
                    self.stdout.write(f"✓ Deleted {store_total} store/factory records")

                total_deleted = sum(deleted_counts.values())

                # Success message
                success_msg = f'\n🎉 SYSTEM SUCCESSFULLY CLEANED! 🎉\n\nTotal records deleted: {total_deleted:,}\n\n'
                
                if clean_requisitions:
                    success_msg += f'REQUISITION DATA CLEANED:\n'
                    success_msg += f'- {deleted_counts.get("requisitions", 0)} Requisitions\n'
                    success_msg += f'- {deleted_counts.get("lpos", 0)} LPOs\n'
                    success_msg += f'- {deleted_counts.get("payment_vouchers", 0)} Payment Vouchers\n\n'
                
                if clean_store:
                    success_msg += f'STORE/FACTORY DATA CLEANED:\n'
                    success_msg += f'- {deleted_counts.get("store_sales", 0)} Store Sales\n'
                    success_msg += f'- {deleted_counts.get("service_sales", 0)} Service Sales\n'
                    success_msg += f'- {deleted_counts.get("production_orders", 0)} Production Orders\n'
                    success_msg += f'- {deleted_counts.get("manufactured_products", 0)} Manufactured Products\n'
                    success_msg += f'- {deleted_counts.get("livara_main_store", 0)} Main Store Items\n'
                    success_msg += f'- {deleted_counts.get("store_inventory", 0)} Store Inventory\n'
                    success_msg += f'- {deleted_counts.get("staff_commissions", 0)} Staff Commissions\n\n'

                success_msg += 'Your system is now completely clean and ready for fresh data! 🚀'
                
                self.stdout.write(self.style.SUCCESS(success_msg))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error occurred while cleaning system: {str(e)}')
            )
            raise 