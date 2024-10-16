from django.urls import path
from .views import  LpoDetailView, ProDeView, delete_rawmaterial, purhcaseOrderDetails
from . import views

urlpatterns = [
    path('production-dashboard/', views.productionPage, name='productionPage'),
    path('suppliers/', views.supplierList, name='supplierList'),
    path('add-supplier/', views.addSupplier, name='addSupplier'),
    path('edit-supplier/<int:supplier_id>/', views.editSupplier, name='editSupplier'),
    path('delete-supplier/<int:supplier_id>/', views.deleteSupplier, name='deleteSupplier'),
    path('supplier_details/<int:supplier_id>/', views.supplier_details, name='supplier_details'),
    
    path('raw-materials/', views.rawmaterialsList, name='rawmaterialsList'),
    path('add-raw-materials/', views.addRawmaterial, name='addRawmaterial'),
    path('download-example-csv/', views.download_example_csv, name='download_example_csv'),
    path('download-supplier-csv,', views.download_supplier_csv, name="download_supplier_csv"),
    path('delete_rawmaterial/<int:raw_material_id>/', delete_rawmaterial, name='delete_rawmaterial'),
    path('raw-material/<int:pk>/', views.update_raw_material_quantity, name="update_raw_material_quantity"),
    path('rawamaterialsTable/', views.rawamaterialsTable, name="rawamaterialsTable"),
    path('debit_notes_list/', views.debit_notes_list, name="debit_notes_list"),
    path('debit_note_details/<int:debit_note_id>/', views.debit_note_details, name="debit_note_details"),
    path('replace_notes_list/', views.replace_notes_list, name="replace_notes_list"),
    path('replace_note_details/<int:replace_note_id>/', views.replace_note_details, name="replace_note_details"),
    path('process_replacements/<int:replace_note_id>/', views.process_replacements, name="process_replacements"),

    
    path('create_requisition/', views.create_requisition, name='create_requisition'),
    path('get_raw_materials/', views.get_raw_materials_by_supplier, name='get_raw_materials'),
    path('all_requisitions/', views.all_requisitions, name='all_requisitions'),
    path('requisition_details/<int:requisition_id>/', views.requisition_details, name='requisition_details'),
    path('delete_requisition/<int:requisition_id>/', views.delete_requisition, name='delete_requisition'),
    path('approve-requisition/<int:requisition_id>/', views.approve_requisition, name='approve_requisition'),
    path('reject-requisition/<int:requisition_id>/', views.reject_requisition, name='reject_requisition'),
    path('get_raw_materials_by_supplier/', views.get_raw_materials_by_supplier, name='get_raw_materials_by_supplier'),
    
    path('lpos_list/', views.lpo_list, name='lpos_list'),
    path('lpo<int:pk>/', views.lpo_verify, name='lpo_verify'),
    path('lpo/<int:pk>/', LpoDetailView.as_view(), name='lpo_detail'),
    # path('process_delivery/<int:requisition_id>/', views.process_delivery, name='process_delivery'),
    path('process_delivery/<int:requisition_id>/', ProDeView.as_view(), name='process_del'),
    path('pay_lpo/<int:lpo_id>/', views.pay_lpo, name='pay_lpo'),
    
    
    
    path('production_payment_vouchers/', views.production_payment_vouchers, name="production_payment_vouchers"),
    path('production_payment_voucher_detail/<str:voucher_number>/', views.production_payment_voucher_detail, name="production_payment_voucher_details"),
    
    path('goods-received-notes/', views.goods_recieved_notes, name='goods_received_note_list'),
    path('goods_received_note_detail/<int:note_id>', views.goods_received_note_detail, name='goods_received_note_detail'),
    path('goods-received-notes/<int:note_id>/handle-discrepancy/', views.handle_discrepancy, name='handle_discrepancy'),
    
    path('discrepancy_delivery_report_detail/<int:report_id>/', views.discrepancy_delivery_report_detail, name='discrepancy_delivery_report_detail'),
    path('discrepancy_delivery_report_list/', views.discrepancy_delivery_report_list, name='discrepancy_delivery_report_list'),
    
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
    path('write_off_inventory/<int:inventory_id>/', views.write_off_product, name="write_off_inventory"),
    path('all-stores/', views.all_stores, name="allStores"),
    path('add-store/', views.add_store, name="addStore"),
    path('edit-store/<int:store_id>', views.edit_store, name="editStore"),
    path('delete-store/<int:store_id>/', views.delete_store, name="deleteStore"),
    path('restock-requests/', views.restock_requests, name="restockRequests"),
    path('create-restock-request/', views.create_restock_request, name="createRestockRequest"),
    path('mark_restock_as_delivered/<int:restock_id>', views.mark_restock_as_delivered, name="restock_delivered"),
    
    path('manager_inventory_view/', views.manager_inventory_view, name="manager_inventory_view"),
    path('inventory_adjustments/<int:inventory_id>', views.inventory_adjustments, name="inventory_adjustments"),
    path('main_store_inventory_adjustments/', views.main_store_inventory_adjustments, name="main_store_inventory_adjustments"),
   

    path('approve-restock-request/<int:request_id>', views.approve_restock_requests, name="approve_restock_requests"),
    path('general-stores/', views.store_inventory_list, name="store_inventory_list"),
    path('bulk_stock_tansfer/', views.bulk_stock_transfer, name="bulk_stock_transfer"),
    path('complete_livara_ms_transfer/', views.mark_transfer_completed, name="mark_transfer_completed"),
    path('main_stock_transfers/', views.main_stock_transfer, name="main_stock_transfer"),
    path('livara_main_store_inventory', views.livara_main_store_inventory, name="livara_main_store_inventory"),
    
    path('reject-request/<int:request_id>/', views.reject_restock_request, name="reject_request"),
    path('finance-approval/<int:request_id>', views.finance_approve_request, name="finance_approval"),
    path('create_production_order/', views.create_production_order, name="create_production_order"),
    path('production-orders/', views.list_production_orders, name='productionList'),
    path('finance-approval/<int:pk>/', views.approve_production_order, name='approveProduction'),
    path('finance-production-orders/', views.finance_view_production_orders, name='financeProduction'),
    path('production-production-orders/', views.productions_view_production_orders, name='productionProduction'),
    path('start-progress/<int:pk>/', views.start_production_progress, name='startProgress'),
    path('finance-purchase-orders/', views.finance_view_purchase_orders, name='financePurchase'),
    path('orders/approve/<int:order_id>/', views.approve_order, name='approve_order'),
    path('orders/reject/<int:order_id>/', views.reject_order, name='reject_order'),
    
    path('approve-purchase-orders/<int:purchaseo_id>', views.approve_purchase_order, name='approvePurchaseOrder'),
    path('finance-restock-requests/', views.finance_restock_requests, name='financeRestockRequests'),
    
    path('create_store_sale/', views.create_store_sale, name='createStoreSale'),
    path('list_store_sales/', views.list_store_sales, name='listStoreSales'),
    path('test_sale/', views.create_store_test, name="SaleTest"),
    path('update_order_status/<int:store_sale_id>/', views.update_order_status, name='update_order_status'),
    path('finance_list_store_sales/', views.finance_list_store_sales, name="financeListStoreSales"),
    path('pay_order_status/<int:store_sale_id>/', views.pay_order_status, name='pay_order_status'),
    path('store_sale_order_details/<int:pk>/', views.store_sale_order_details, name='store_sale_order_details'),
    path('mark_transfer_completed/<int:transfer_id>/', views.mark_transfer_completed, name='mark_transfer_completed'),
    
    path('write_offs', views.write_offs, name="writeoffs"),
    path('manufacture_products_report', views.manufactured_products_report, name="manufactured_products_report"),
    path('raw_material_utilization_report/', views.raw_material_utilization_report, name='raw_material_utilization_report'),
    
    ## Store Manager View
    path('store_manager/', views.managers_store_inventory_view, name='managers_store_inventory_view'),
    
    ##finance
    path('outstanding_payables/',  views.outstanding_payables, name='outstanding_payables'),
    
]