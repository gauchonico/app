from django.core.management.base import BaseCommand
from django.db import transaction
from production.models import (
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
    help = 'Delete all store/factory data (sales, inventory, manufacturing, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all store data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will delete ALL store/factory data including:\n'
                    '- Store Sales & Service Sales\n'
                    '- Production Orders & Manufacturing Records\n'
                    '- Store Inventory & Transfers\n'
                    '- Accessory Data\n'
                    '- Staff Commissions\n'
                    '- All related transactions\n\n'
                    'To proceed, run the command with --confirm flag:\n'
                    'python manage.py delete_all_store_data --confirm'
                )
            )
            return

        # Count existing records for reporting
        total_records = (
            StoreSale.objects.count() + SaleItem.objects.count() + 
            ServiceSale.objects.count() + ServiceSaleItem.objects.count() +
            ProductionOrder.objects.count() + ManufactureProduct.objects.count() + 
            LivaraMainStore.objects.count() + StoreInventory.objects.count() + 
            AccessoryInventory.objects.count()
        )

        self.stdout.write(f"Found store/factory data to delete...")

        # Confirm deletion
        confirm = input("Are you sure you want to delete all store/factory data? Type 'DELETE' to confirm: ")
        if confirm != 'DELETE':
            self.stdout.write(self.style.ERROR('Deletion cancelled.'))
            return

        try:
            with transaction.atomic():
                deleted_counts = {}
                
                # Delete in reverse order of dependencies
                
                # 1. Delete commissions and payments first (they depend on sales)
                deleted_counts['staff_commissions'] = StaffCommission.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['staff_commissions']} staff commissions")
                
                deleted_counts['monthly_staff_commissions'] = MonthlyStaffCommission.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['monthly_staff_commissions']} monthly staff commissions")
                
                deleted_counts['staff_product_commissions'] = StaffProductCommission.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['staff_product_commissions']} staff product commissions")
                
                deleted_counts['payments'] = Payment.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['payments']} payments")
                
                deleted_counts['service_sale_invoices'] = ServiceSaleInvoice.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['service_sale_invoices']} service sale invoices")
                
                # 2. Delete sale items before sales
                deleted_counts['accessory_sale_items'] = AccessorySaleItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['accessory_sale_items']} accessory sale items")
                
                deleted_counts['product_sale_items'] = ProductSaleItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['product_sale_items']} product sale items")
                
                deleted_counts['service_sale_items'] = ServiceSaleItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['service_sale_items']} service sale items")
                
                deleted_counts['sale_items'] = SaleItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['sale_items']} sale items")
                
                # 3. Delete sales and receipts
                deleted_counts['store_sale_receipts'] = StoreSaleReceipt.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_sale_receipts']} store sale receipts")
                
                deleted_counts['service_sales'] = ServiceSale.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['service_sales']} service sales")
                
                deleted_counts['store_sales'] = StoreSale.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_sales']} store sales")
                
                # 4. Delete transfer items before transfers
                deleted_counts['store_transfer_items'] = StoreTransferItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_transfer_items']} store transfer items")
                
                deleted_counts['restock_request_items'] = RestockRequestItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['restock_request_items']} restock request items")
                
                deleted_counts['main_store_accessory_requisition_items'] = MainStoreAccessoryRequisitionItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['main_store_accessory_requisition_items']} main store accessory requisition items")
                
                deleted_counts['internal_accessory_request_items'] = InternalAccessoryRequestItem.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['internal_accessory_request_items']} internal accessory request items")
                
                # 5. Delete transfers and requests
                deleted_counts['transfer_approvals'] = TransferApproval.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['transfer_approvals']} transfer approvals")
                
                deleted_counts['store_transfers'] = StoreTransfer.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_transfers']} store transfers")
                
                deleted_counts['restock_requests'] = RestockRequest.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['restock_requests']} restock requests")
                
                deleted_counts['main_store_accessory_requisitions'] = MainStoreAccessoryRequisition.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['main_store_accessory_requisitions']} main store accessory requisitions")
                
                deleted_counts['internal_accessory_requests'] = InternalAccessoryRequest.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['internal_accessory_requests']} internal accessory requests")
                
                # 6. Delete adjustments and write-offs
                deleted_counts['livara_inventory_adjustments'] = LivaraInventoryAdjustment.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['livara_inventory_adjustments']} livara inventory adjustments")
                
                deleted_counts['inventory_adjustments'] = InventoryAdjustment.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['inventory_adjustments']} inventory adjustments")
                
                deleted_counts['store_inventory_adjustments'] = StoreInventoryAdjustment.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_inventory_adjustments']} store inventory adjustments")
                
                deleted_counts['accessory_inventory_adjustments'] = AccessoryInventoryAdjustment.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['accessory_inventory_adjustments']} accessory inventory adjustments")
                
                deleted_counts['store_write_offs'] = StoreWriteOff.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_write_offs']} store write offs")
                
                deleted_counts['write_offs'] = WriteOff.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['write_offs']} write offs")
                
                # 7. Delete manufactured product ingredients before products
                deleted_counts['manufactured_product_ingredients'] = ManufacturedProductIngredient.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['manufactured_product_ingredients']} manufactured product ingredients")
                
                # 8. Delete inventory items
                deleted_counts['store_accessory_inventory'] = StoreAccessoryInventory.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_accessory_inventory']} store accessory inventory")
                
                deleted_counts['store_inventory'] = StoreInventory.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['store_inventory']} store inventory")
                
                deleted_counts['livara_main_store'] = LivaraMainStore.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['livara_main_store']} livara main store items")
                
                deleted_counts['manufactured_product_inventory'] = ManufacturedProductInventory.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['manufactured_product_inventory']} manufactured product inventory")
                
                deleted_counts['accessory_inventory'] = AccessoryInventory.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['accessory_inventory']} accessory inventory")
                
                # 9. Delete manufacturing records (manufactured products before production orders since they reference orders)
                deleted_counts['manufactured_products'] = ManufactureProduct.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['manufactured_products']} manufactured products")
                
                deleted_counts['production_batches'] = ProductionBatch.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['production_batches']} production batches")
                
                # 10. Delete production orders last (since manufactured products reference them)
                deleted_counts['production_orders'] = ProductionOrder.objects.all().delete()[0]
                self.stdout.write(f"Deleted {deleted_counts['production_orders']} production orders")

                total_deleted = sum(deleted_counts.values())

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSuccessfully deleted all store/factory data:\n'
                        f'Total records deleted: {total_deleted}\n\n'
                        'Key deletions:\n'
                        f'- {deleted_counts["store_sales"]} Store Sales\n'
                        f'- {deleted_counts["service_sales"]} Service Sales\n'
                        f'- {deleted_counts["production_orders"]} Production Orders\n'
                        f'- {deleted_counts["manufactured_products"]} Manufactured Products\n'
                        f'- {deleted_counts["livara_main_store"]} Main Store Items\n'
                        f'- {deleted_counts["store_inventory"]} Store Inventory Items\n'
                        f'- {deleted_counts["accessory_inventory"]} Accessory Inventory\n'
                        f'- {deleted_counts["staff_commissions"]} Staff Commissions\n\n'
                        'Your store/factory system is now clean and ready for fresh data!'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error occurred while deleting data: {str(e)}')
            )
            raise 