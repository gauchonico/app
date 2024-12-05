from django.contrib import admin

from salon.models import *
from .models import *
from payment.models import *
from production.models import *

# Register your models here.
admin.site.register(Staff)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Branch)
admin.site.register(Ordern)
admin.site.register(OrderItem)
admin.site.register(Supplier)
# admin.site.register(RawMaterial)
admin.site.register(PurchaseOrder)
admin.site.register(StoreAlerts)
admin.site.register(Transaction)
admin.site.register(ProductionBatch)
# admin.site.register(Production)
# admin.site.register(ProductionIngredient)
admin.site.register(ManufactureProduct)
admin.site.register(ManufacturedProductInventory)
admin.site.register(CommissionRate)
admin.site.register(StaffCommission)
admin.site.register(Store)
admin.site.register(StoreInventory)
admin.site.register(StockTransfer)
admin.site.register(RestockRequest)
admin.site.register(ProductionOrder)
admin.site.register(Notification)
admin.site.register(Receipt)
admin.site.register(SaleItem)
admin.site.register(StoreSale)
admin.site.register(StoreTransfer)
admin.site.register(StoreTransferItem)
admin.site.register(LivaraMainStore)
admin.site.register(WriteOff)
admin.site.register(RestockRequestItem)
class ProductionIngredientInline(admin.TabularInline):
    model = ProductionIngredient
    extra = 1

class ProductionAdmin(admin.ModelAdmin):
    inlines = [ProductionIngredientInline]
    list_display = ['product_name', 'total_volume']
    search_fields = ['product_name']

admin.site.register(Production, ProductionAdmin)

class ProductionIngredientAdmin(admin.ModelAdmin):
    list_display = ['product', 'raw_material', 'quantity_per_unit_product_volume']
    search_fields = ['product__product_name', 'raw_material__name']

admin.site.register(ProductionIngredient, ProductionIngredientAdmin)
admin.site.register(Requisition)
admin.site.register(RequisitionItem)
admin.site.register(LPO)
admin.site.register(GoodsReceivedNote)
admin.site.register(DiscrepancyDeliveryReport)
admin.site.register(UnitOfMeasurement)
admin.site.register(ReplaceNote)
admin.site.register(ReplaceNoteItem)
admin.site.register(DebitNote)
admin.site.register(SalonBranch)
admin.site.register(BranchInventory)
admin.site.register(SalonProduct)
admin.site.register(Sale)
admin.site.register(GeneralRequisition)
admin.site.register(PaymentVoucher)
admin.site.register(SalonRestockRequest)
admin.site.register(SalonRestockRequestItem)
admin.site.register(ServiceName)
admin.site.register(StoreService)
admin.site.register(Accessory)
admin.site.register(AccessoryInventory)
admin.site.register(MainStoreAccessoryRequisition)
admin.site.register(MainStoreAccessoryRequisitionItem)
admin.site.register(InternalAccessoryRequest)
admin.site.register(InternalAccessoryRequestItem)
admin.site.register(StoreAccessoryInventory)
admin.site.register(ServiceSale)
admin.site.register(ServiceSaleInvoice)
admin.site.register(AccessoryInventoryAdjustment)
admin.site.register(AccessorySaleItem)
admin.site.register(ServiceSaleItem)
admin.site.register(ProductSaleItem)
@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'reorder_point', 'unit_measurement')
    filter_horizontal = ('suppliers',)  # Use a widget that allows selecting multiple suppliers


