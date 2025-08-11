from django.core.management.base import BaseCommand
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
    help = 'Preview all store/factory data that would be deleted'

    def handle(self, *args, **options):
        # Count existing records
        counts = {
            # Store Sales
            'store_sales': StoreSale.objects.count(),
            'sale_items': SaleItem.objects.count(),
            'store_sale_receipts': StoreSaleReceipt.objects.count(),
            
            # Service Sales
            'service_sales': ServiceSale.objects.count(),
            'service_sale_items': ServiceSaleItem.objects.count(),
            'accessory_sale_items': AccessorySaleItem.objects.count(),
            'product_sale_items': ProductSaleItem.objects.count(),
            
            # Manufacturing and Production Orders
            'production_orders': ProductionOrder.objects.count(),
            'manufactured_products': ManufactureProduct.objects.count(),
            'manufactured_product_inventory': ManufacturedProductInventory.objects.count(),
            'manufactured_product_ingredients': ManufacturedProductIngredient.objects.count(),
            'production_batches': ProductionBatch.objects.count(),
            'write_offs': WriteOff.objects.count(),
            
            # Main Store Inventory
            'livara_main_store': LivaraMainStore.objects.count(),
            'livara_inventory_adjustments': LivaraInventoryAdjustment.objects.count(),
            'store_transfers': StoreTransfer.objects.count(),
            'store_transfer_items': StoreTransferItem.objects.count(),
            'store_write_offs': StoreWriteOff.objects.count(),
            
            # Store Inventory
            'store_inventory': StoreInventory.objects.count(),
            'inventory_adjustments': InventoryAdjustment.objects.count(),
            'store_inventory_adjustments': StoreInventoryAdjustment.objects.count(),
            
            # Restocking
            'restock_requests': RestockRequest.objects.count(),
            'restock_request_items': RestockRequestItem.objects.count(),
            'transfer_approvals': TransferApproval.objects.count(),
            
            # Accessories
            'accessory_inventory': AccessoryInventory.objects.count(),
            'accessory_inventory_adjustments': AccessoryInventoryAdjustment.objects.count(),
            'store_accessory_inventory': StoreAccessoryInventory.objects.count(),
            'main_store_accessory_requisitions': MainStoreAccessoryRequisition.objects.count(),
            'main_store_accessory_requisition_items': MainStoreAccessoryRequisitionItem.objects.count(),
            'internal_accessory_requests': InternalAccessoryRequest.objects.count(),
            'internal_accessory_request_items': InternalAccessoryRequestItem.objects.count(),
            
            # Commissions and Payments
            'staff_commissions': StaffCommission.objects.count(),
            'monthly_staff_commissions': MonthlyStaffCommission.objects.count(),
            'staff_product_commissions': StaffProductCommission.objects.count(),
            'payments': Payment.objects.count(),
            'service_sale_invoices': ServiceSaleInvoice.objects.count(),
        }

        total_records = sum(counts.values())

        self.stdout.write(
            self.style.WARNING(
                f'\n=== STORE/FACTORY DATA SUMMARY ===\n'
                f'\n--- SALES DATA ---\n'
                f'Store Sales: {counts["store_sales"]}\n'
                f'Sale Items: {counts["sale_items"]}\n'
                f'Store Sale Receipts: {counts["store_sale_receipts"]}\n'
                f'Service Sales: {counts["service_sales"]}\n'
                f'Service Sale Items: {counts["service_sale_items"]}\n'
                f'Accessory Sale Items: {counts["accessory_sale_items"]}\n'
                f'Product Sale Items: {counts["product_sale_items"]}\n'
                f'\n--- MANUFACTURING & PRODUCTION ---\n'
                f'Production Orders: {counts["production_orders"]}\n'
                f'Manufactured Products: {counts["manufactured_products"]}\n'
                f'Manufactured Product Inventory: {counts["manufactured_product_inventory"]}\n'
                f'Manufactured Product Ingredients: {counts["manufactured_product_ingredients"]}\n'
                f'Production Batches: {counts["production_batches"]}\n'
                f'Write Offs: {counts["write_offs"]}\n'
                f'\n--- MAIN STORE INVENTORY ---\n'
                f'Livara Main Store Items: {counts["livara_main_store"]}\n'
                f'Livara Inventory Adjustments: {counts["livara_inventory_adjustments"]}\n'
                f'Store Transfers: {counts["store_transfers"]}\n'
                f'Store Transfer Items: {counts["store_transfer_items"]}\n'
                f'Store Write Offs: {counts["store_write_offs"]}\n'
                f'\n--- STORE INVENTORY ---\n'
                f'Store Inventory: {counts["store_inventory"]}\n'
                f'Inventory Adjustments: {counts["inventory_adjustments"]}\n'
                f'Store Inventory Adjustments: {counts["store_inventory_adjustments"]}\n'
                f'\n--- RESTOCKING ---\n'
                f'Restock Requests: {counts["restock_requests"]}\n'
                f'Restock Request Items: {counts["restock_request_items"]}\n'
                f'Transfer Approvals: {counts["transfer_approvals"]}\n'
                f'\n--- ACCESSORIES ---\n'
                f'Accessory Inventory: {counts["accessory_inventory"]}\n'
                f'Accessory Inventory Adjustments: {counts["accessory_inventory_adjustments"]}\n'
                f'Store Accessory Inventory: {counts["store_accessory_inventory"]}\n'
                f'Main Store Accessory Requisitions: {counts["main_store_accessory_requisitions"]}\n'
                f'Main Store Accessory Requisition Items: {counts["main_store_accessory_requisition_items"]}\n'
                f'Internal Accessory Requests: {counts["internal_accessory_requests"]}\n'
                f'Internal Accessory Request Items: {counts["internal_accessory_request_items"]}\n'
                f'\n--- COMMISSIONS & PAYMENTS ---\n'
                f'Staff Commissions: {counts["staff_commissions"]}\n'
                f'Monthly Staff Commissions: {counts["monthly_staff_commissions"]}\n'
                f'Staff Product Commissions: {counts["staff_product_commissions"]}\n'
                f'Payments: {counts["payments"]}\n'
                f'Service Sale Invoices: {counts["service_sale_invoices"]}\n'
                f'\nTOTAL RECORDS: {total_records}\n'
            )
        )

        if total_records > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nTo delete all this store data, run:\n'
                    'python manage.py delete_all_store_data --confirm'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nNo store data found. Your system is already clean!'
                )
            ) 