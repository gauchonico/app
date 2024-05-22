from django.urls import path
from .views import purhcaseOrderDetails
from . import views

urlpatterns = [
    path('production-dashboard/', views.productionPage, name='productionPage'),
    path('suppliers/', views.supplierList, name='supplierList'),
    path('add-supplier/', views.addSupplier, name='addSupplier'),
    path('edit-supplier/<int:supplier_id>/', views.editSupplier, name='editSupplier'),
    path('delete-supplier/<int:supplier_id>/', views.deleteSupplier, name='deleteSupplier'),
    path('raw-materials/', views.rawmaterialsList, name='rawmaterialsList'),
    path('add-raw-materials/', views.addRawmaterial, name='addRawmaterial'),
    path('store-management/', views.storeManagement, name='storeManagement'),
    path('dispatch-list/', views.dispatchList, name='dispatchList'),
    path('store-products/', views.storeProducts, name='storeProducts'),
    path('production-process/', views.productionProcess, name='productionProcess'),
    path('store-requests/', views.storeRequests, name='storeRequests'),
    path('purchase-order-list/', views.purchaseOderList, name='purchaseOderList'),
    path('create-purchase-order/<int:rawmaterial_id>/', views.createPurchaseOrder, name='createPurchaseOrder'),
    path('purhcase_order/<int:purchase_order_id>', views.purhcaseOrderDetails, name='purchase_order_details'),
    path('edit-purchase-order/<int:purchase_order_id>/', views.editPurchaseOrderDetails, name='edit_purchase_order_details'),
    path('products-list/', views.productsList, name='productsList'),
    path('product-details/<int:product_id>/', views.productDetails, name='productDetailsPage'),
    path('create-product/', views.create_product, name='createProduct'),
    path('test-product/<int:product_id>', views.testProduct, name='testProduct'),
    path('edit-product/<int:product_id>/', views.edit_product, name='editProduct'),
    path('manufacture-product/<int:product_id>/', views.manufacture_product, name='manufactureProduct'),
    path('manufactured-product-list/', views.manufactured_products_list, name='manufacturedProductList'),
    path('factory-inventory/', views.factory_inventory, name='factoryInventory'),
    path('manufactured-product-details/<int:product_id>/', views.manufacturedproduct_detail, name="manufacturedProductDetails"),
    path('product-inventory-details/<int:inventory_id>/', views.product_inventory_details, name="productInventoryDetails"),
]