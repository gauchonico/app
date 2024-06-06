from django.contrib import admin
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
admin.site.register(RawMaterial)
admin.site.register(PurchaseOrder)
admin.site.register(StoreAlerts)
admin.site.register(Transaction)
admin.site.register(ProductionBatch)
admin.site.register(Production)
admin.site.register(ProductionIngredient)
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

