from urllib import request
from django.urls import resolve
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe

from production.models import LPO, DiscrepancyDeliveryReport, InternalAccessoryRequest, LivaraMainStore, MainStoreAccessoryRequisition, PaymentVoucher, ProductionOrder, ReplaceNote, Requisition, RestockRequest, StoreSale, StoreTransfer
from salon.models import SalonRestockRequest


def get_created_production_orders_count():
    return ProductionOrder.objects.filter(status='Created').count()

def get_pending_livara_store_orders():
    return StoreTransfer.objects.filter(status='Pending').count()

def get_new_restock_requests_count():
    return SalonRestockRequest.objects.filter(status='pending').count()

def get_new_requisitions_count():
    return Requisition.objects.filter(status='created').count()

def get_new_lpo_count():
    return LPO.objects.filter(status='pending').count()

def get_outstanding_payables_count():
    return LPO.objects.filter(is_paid=False).count()

def get_verified_requsitions():
    return Requisition.objects.filter(status='approved').count()

def get_replace_notes():
    return ReplaceNote.objects.filter(status='pending').count()

def get_discrepancy_reports():
    return DiscrepancyDeliveryReport.objects.filter(status='refund').count()

def get_production_payment_voucher_count():
    return PaymentVoucher.objects.all().count()

def get_accessories_orders_count ():
    return MainStoreAccessoryRequisition.objects.filter(status='pending').count()

def get_internal_requisition_count():
    return InternalAccessoryRequest.objects.filter(status='pending').count()

def get_store_sales_order_count():
    return StoreSale.objects.filter(status='ordered').count()


def mark_active_link(menu, current_path_name):
    for item in menu:
        item['is_active'] = item.get('name', '') == current_path_name

        if 'children' in item:
            item['children'] = mark_active_link(item['children'], current_path_name)

            if any(child.get('is_active', False) for child in item['children']):
                item['is_active'] = True

    return menu


def sidebar_menu(request):
    created_production_orders_count = get_created_production_orders_count()  # Get the count of created production orders
    new_accessory_requests = get_accessories_orders_count()
    created_livara_store_orders = get_pending_livara_store_orders()
    restock_requests_count= get_new_restock_requests_count()
    requisitions_count = get_new_requisitions_count()
    lpo_count = get_new_lpo_count()
    internal_requisition_count = get_internal_requisition_count()
    verified_requsitions = get_verified_requsitions()
    replace_notes = get_replace_notes()
    get_outstanding_po_payables = get_outstanding_payables_count()
    production_payment_vouchers = get_production_payment_voucher_count()
    store_sales_order_count = get_store_sales_order_count()
    # Calculate total notifications for dropdowns
    production_logistics_total = (
        requisitions_count + 
        lpo_count + 
        get_outstanding_po_payables + 
        production_payment_vouchers
    )
    
    inventory_total = (
        created_livara_store_orders + 
        new_accessory_requests + 
        internal_requisition_count
    )
    
    sales_total = store_sales_order_count
    
    sidebar_menu = [{
            'text': 'Navigation',
            'is_header': 1
        },{
            'url': '/',
            'icon': 'bi bi-house-door',
            'text': 'Home',
            'name': 'index'
        },{
            'url': '/page/order',
            'icon': 'bi bi-cart',
            'text': 'Orders',
            'name': 'pageOrder'
        },{
            'url': '/page/customers',
            'icon': 'bi bi-person-check',
            'text': 'Customers',
            'name': 'pageCustomer'
        },{
            'url': '/page/reciepts',
            'icon': 'bi bi-app-indicator',
            'text': 'Reciepts',
            'name': 'view_receipt'
        },{
            'url': '/page/products',
            'icon': 'bi bi-app-indicator',
            'text': 'Products',
            'name': 'pageProduct'
        },{
            'url': '/staff',
            'icon': 'bi bi-person',
            'text': 'Staff',
            'name': 'staff'
        },{
            'url': '/customer-order',
            'icon': 'bi bi-laptop',
            'text': 'POS',
            'name': 'customerOrder'
        },{
            'text': 'PRODUCTION',
            'is_header': 1
        },{
            'url': '/production/production-dashboard/',
            'icon': 'bi bi-pie-chart-fill',
            'text': 'Dashboard',
            'name': 'productionPage'
        },{
            'url': '/production/raw-materials/',
            'icon': 'bi bi-egg-fried',
            'text': 'Raw Materials',
            'name': 'rawmaterialsList'
        },{
            'url': '/production/suppliers/',
            'icon': 'bi bi-truck-flatbed',
            'text': 'Suppliers',
            'name': 'supplierList'
        },{
            'url': '/production/products-list/',
            'icon': 'bi bi-upc-scan',
            'text': 'Products / Manufacture',
            'name': 'productsList'
        },{
            'url': '/production/production-production-orders/',
            'icon': 'bi bi-node-plus-fill',
            'text': mark_safe(
                f'Production Orders <span class="badge rounded-circle bg-danger">{created_production_orders_count}</span>' 
                if created_production_orders_count > 0 else 'Production Orders'),
            'name': 'productionProduction'
        },#{
        #     'url': '/production/store-requests',
        #     'icon': 'bi bi-inboxes-fill',
        #     'text': 'Store Requests',
        #     'name':'storeRequests'
        {
            'url': '/production/manufactured-product-list/',
            'icon': 'bi bi-speedometer',
            'text': 'Production Reports',
            'name': 'manufacturedProductList'
        },{
            'url': '/production/factory-inventory/',
            'icon': 'bi bi-box-fill',
            'text': 'URI Inventory',
            'name': 'factoryInventory'
        },{
            'url': '/production/production-orders/',
            'icon': 'bi bi-inboxes-fill',
            'text': 'Production Orders',
            'name': 'productionList'
        },{
            'url': '/production/create_production_order/',
            'icon': 'bi bi-node-plus-fill',
            'text': 'Create Prodcution Order',
            'name': 'create_production_order'
        },{
            'icon': 'bi bi-inboxes-fill',
            'text': 'Production Logistics',
            'children': [{
                'url': '/production/all_requisitions',
                'icon': 'bi bi-inboxes-fill',
                'text': 'Requisitions',
                'name':'all_requisitions'
            },{
                'url': '/production/lpos_list/',
                'icon': 'bi bi-egg-fried',
                'text': mark_safe(f'LPOrders <span class="badge rounded-circle bg-danger">{lpo_count}</span>'
                        if lpo_count > 0 else 'LPOrders'
                        ),
                'name': 'lpos_list' 
            },{
                'url': '/production/goods-received-notes/',
                'icon': 'bi bi-receipt',
                'text': 'Goods Received Note List',
                'name': 'goods_received_note_list'
            },{
                'url': '/production/discrepancy_delivery_report_list/',
                'icon': 'bi bi-box-fill',
                'text': 'Discrepancy Delivery Report List',
                'name': 'discrepancy_delivery_report_list'
            },{
                    'url': '/production/debit_notes_list/',
                    'icon': 'bi bi-receipt',
                    'text': 'Debit Notes',
                    'name': 'debit_notes_list'
            },{
                'url': '/production/replace_notes_list/',
                'icon': 'bi bi-receipt',
                'text': mark_safe(
                    f'Replace Notes<span class="badge rounded-circle bg-danger">{replace_notes}</span>'
                    if replace_notes>0 else 'Replacing Notes'
                    ),
                'name':'replace_notes_list'
            }]
        },{
            'text': 'STORES',
            'is_header': 1
        },{
            'icon': 'bi bi-node-plus-fill',
            'text': 'Production Orders',
            'children': [{
                'url': '/production/production-orders/',
                'icon': 'bi bi-reciept',
                'text': 'Production Orders',
                'name': 'productionList'
            },{
                'url': '/production/create_production_order/',
                'icon': 'bi bi-node-plus-fill',
                'text': 'Create Prodcution Order',
                'name': 'create_production_order'
            }]
        },{
            'url': '/production/list_store_sales',
            'icon': 'bi bi-speedometer',
            'text': 'All Store Sales',
            'name':'listStoreSales'
        },{
            'url': '/production/all-stores/',
            'icon': 'bi bi-shop',
            'text': 'All Stores',
            'name': 'allStores'
        },{
            'url': '/production/main_store_inventory_adjustments/',
            'icon': 'bi bi-folder',
            'text': 'Stores Data',
            'name':'main_store_inventory_adjustments',
        },{
            'url': '/production/general-stores/',
            'icon': 'bi bi-boxes',
            'text': 'General Stores',
            'name': 'store_inventory_list',
        },{
            'url':'/production/accessory_store/',
            'icon': 'fa-solid fa-gem',
            'text': 'Main Accessory Inventory',
            'name': 'accessory_store',
        },{
            'url': '/production/all_internal_requests/',
            'icon': 'bi bi-folder-fill',
            'text': mark_safe(f'Store Accessory Requests <span class="badge rounded-circle bg-danger">{internal_requisition_count}</span>'
                        if internal_requisition_count > 0 else 'Store Accessory Requests'
                        ),
            'name': 'all_internal_requests',
        },{
            'url':'/production/particular_store_inventory/',
            'icon': 'bi bi-folder-fill',
            'text': 'Accessory Inventory',
            'name': 'particular_store_inventory',
        },{
            'url': '/production/store_internal_requests/',
            'icon': 'bi bi-folder',
            'text': 'Accessory Requests',
            'name':'store_internal_requests'
        },{
            'url': '/production/all_stores_inventory_view/',
            'icon': 'bi bi-folder-fill',
            'text': 'All Store Accessories',
            'name':'all_stores_inventory_view'
        },{
            'url': '/production/main_stock_transfers/',
            'icon': 'bi bi-truck',
            'text': mark_safe (
                f'Main Store Transfers <span class="badge rounded-circle bg-danger">{created_livara_store_orders}</span>'
                if created_livara_store_orders > 0 else 'Main Store'
            ),
            'name':'main_stock_transfers'
        },{
            'url': '/production/livara_main_store_inventory',
            'icon': 'bi bi-folder',
            'text': 'Livara Main Store',
            'name':'livara_main_store_inventory'
        },{
            'url': '/production/write_offs',
            'icon': 'bi bi-box-seam',
            'text': 'Production Store Writeoffs',
            'name': 'writeoffs',
        },{
            'url':'/production/incident_write_off_list',
            'icon':'bi bi-box-seam',
            'text': 'Rawmaterial Writeoffs',
            'name': 'incident_write_off_list',
        },{
            'url':'/production/main_store_writeoff_list/',
            'icon':'bi bi-list-task',
            'text':'Main Store Offsets',
            'name':'main_store_writeoff_list',
                    
        },{
            'url': '/production/restock-requests/',
            'icon':'bi bi-folder-fill',
            'text':'Store Restock Requests',
            'name':'restockRequests'
        },{
            'url': '/production/manufacture_products_report',
            'icon': 'bi bi-folder-fill',
            'text': 'Manufacture Products Report',
            'name':'manufacture_products_report',
        },{
            'url': '/production/raw_material_utilization_report/',
            'icon': 'bi bi-folder',
            'text': 'Raw Material Utilization Report',
            'name': 'raw_material_utilization_report',
        },{
            'url': '/production/raw_material_date_report/',
            'icon': 'bi bi-folder',
            'text': 'Raw Material Date Report',
            'name': 'raw_material_date_report',
        },{
            'url':'/production/manager_inventory_view/',
            'icon': 'bi bi-folder-fill',
            'text': 'Manager Inventory',
            'name':'manager_inventory_view',    
        },{
            'url': '/production/store_sale_list/',
            'icon': 'bi bi-folder',
            'text': 'Store Sales',
            'name':'store_sale_list',
        },{
            'url': '/production/store_sale_service_invoice_list/',
            'icon': 'bi bi-folder',
            'text': 'Store Sales Invoices',
            'name':'store_sale_service_invoice_list',
        },{
            'text': 'FINANCE',
            'is_header': 1
        },{
            'url':'/accounts/accounts-dashboard/',
            'icon': 'bi bi-receipt',
            'text': 'Accounts',
            'name': 'accounts_dashboard',
        },{
            'url':'/accounts/chart-of-accounts/',
            'icon': 'bi bi-receipt',
            'text': 'Chart of Accounts',
            'name': 'chart_of_accounts_list',
        },{
            'url':'/accounts/departments/',
            'icon': 'bi bi-receipt',
            'text': 'Departments',
            'name': 'department_list',
        },{
            'url':'/accounts/budgets/',
            'icon': 'bi bi-receipt',
            'text': 'Budgets',
            'name': 'budget_list',
        },{
            'url':'/accounts/journal-entries/',
            'icon': 'bi bi-receipt',
            'text': 'Journal Entries',
            'name': 'journal_entry_list',
        },{
            'url':'/accounts/trial-balance/',
            'icon': 'bi bi-receipt',
            'text': 'Trial Balance',
            'name': 'trial_balance',
        },{
            'url':'/accounts/ledger-entries/',
            'icon': 'bi bi-receipt',
            'text': 'Ledger Entries',
            'name': 'ledger_entry_list',
        },{
            'url':'/accounts/ledger-entries/',
            'url':'/production/price-groups/',
            'icon': 'bi bi-folder-fill',
            'text': 'Pricing Groups',
            'name': 'view_pricing_groups',
        },{
            'url': '/production/product_location_report/',
            'icon': 'bi bi-bounding-box-circles',
            'text': 'Product by Location Report',
            'name': 'product_location_report',
        },{
            'url': '/production/finance-production-orders/',
            'icon': 'bi bi-bounding-box-circles',
            'text': 'Production Orders',
            'name': 'financeProduction',
        },{
            'url': '/production/finance_list_store_sales/',
            'icon': 'bi bi-bounding-box-circles',
            'text': 'Direct Store Orders',
            'name': 'financeListStoreSales',
        },{
            'url': '/production/finance-purchase-orders/',
            'icon': 'bi bi-box-seam',
            'text': 'Raw-material P.O',
            'name': 'financePurchase'
        },
        {
            'url': '/production/services/',
            'icon': 'bi bi-receipt',
            'text': 'Services',
            'name': 'service_list',
        },{
            'url': '/production/finance-restock-requests/',
            'icon': 'bi bi-receipt',
            'text': 'Restock Requests',
            'name': 'financeRestockRequests',
        },{
            'url': '/production/outstanding_payables',
            'icon': 'bi bi-box-seam',
            'text': mark_safe(f'Outstanding Payables<span class="badge rounded-circle bg-danger">{get_outstanding_po_payables}</span>'
                                if get_outstanding_po_payables>0 else 'Outstanding Payables'
                                ),
            'name': 'outstanding_payables',
        },{
            'url':'/production/production_payment_vouchers/',
            'icon':'bi bi-receipt',
            'text': 'Production Payment Vouchers',
            'name': 'production_payment_vouchers',
        },{
            'url':'/production/main_store_accessory_requisitions_list/',
            'icon':'bi bi-receipt',
            'text': mark_safe(f'Salon Accessories<span class="badge rounded-circle bg-danger">{new_accessory_requests}</span>'
                    if new_accessory_requests>0 else 'Salon Accessories'    
                    ),
            'name': 'main_store_accessory_requisitions_list',
    
            },{
            'text': 'MANAGERS',
            'is_header': 1
        },{
            'url': '/production/store_manager/',
            'icon': 'bi bi-bounding-box-circles',
            'text': 'My Inventory',
            'name': 'managers_store_inventory_view',
        },{
            'url': '/production/store_services_view/',
            'icon': 'bi bi-bounding-box-circles',
            'text': 'Our Services',
            'name': 'store_services_view',
        },{
            'url':'/production/branch_staff_view/',
            'icon': 'bi bi-person',
            'text': 'Branch Staff',
            'name': 'branch_staff_view',
        },{
            'text': 'Salon Manager',
            'is_header': 1
        },{
            'url': '/salon/salon-dashboard/',
            'icon': 'bi bi-bounding-box-circles',
            'text': 'Salon',
            'name': 'salon',
        },{
            'url':'/salon/branch_inventory/',
            'icon':'bi bi-bounding-box-circles',
            'text':'Branch Inventory',
            'name':'branch_inventory',    
        },{
            'url': '/salon/all_salon_restock_requests/',
            'icon': 'bi bi-recycle',
            'text': mark_safe (
                f'Salon Requests <span class="badge rounded-circle bg-danger">{restock_requests_count}</span>'
                if restock_requests_count > 0 else 'Salon Requests' 
            ),
            'name': 'view_salon_restock_requests',
        },{
        
            
    }
        # ... your existing menu definition ...
    ]

    resolved_path = resolve(request.path_info)
    current_path_name = resolved_path.url_name
    
    # Check for superuser first
    if request.user.is_superuser:
        # Show all menus for superuser
        sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
        return {'sidebar_menu': sidebar_menu}

    # Check user group and modify menu accordingly
    user_groups = request.user.groups.all()
    if user_groups:
        group_names = [group.name for group in user_groups]
        if 'Cashier' in group_names:
            # Show cashier menus (if applicable)
            sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
            sidebar_menu = [item for item in sidebar_menu if item.get('name', '') in ['pageOrder','pageCustomer','pageProduct','customerOrder','store_inventory_list','view_receipt']]  # Replace with your cashier menu names
        elif 'Storemanager' in group_names:
            # Show store manager menus
            sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
            sidebar_menu = [item for item in sidebar_menu if item.get('name', '') in ['allStores','view_pricing_groups','factoryInventory','pageCustomer']]  # Replace with your store manager menu names
            sidebar_menu.append({
                'icon': 'bi bi-box-fill',
                'text': mark_safe(f'Inventory<span class="badge rounded-circle bg-danger">{inventory_total}</span>'
                                if inventory_total > 0 else 'Inventory'
                                ),
                'children': [
                    {
                    'url': '/production/production-production-orders/',
                    'icon': 'bi bi-node-plus-fill',
                    'text': mark_safe(
                        f'Product Orders <span class="badge rounded-circle bg-danger">{created_production_orders_count}</span>' 
                        if created_production_orders_count > 0 else 'Product Orders'),
                    'name': 'productionProduction'
                },
                    # {
                    #     'url': '/production/create_production_order/',
                    #     'icon': 'bi bi-node-plus-fill',
                    #     'text': 'Product Order',
                    #     'name': 'create_production_order'
                    # },
                    {
                    'url': '/production/livara_main_store_inventory',
                    'icon': 'bi bi-box-fill',
                    'text': 'Inventory Items',
                    'name': 'livara_main_store_inventory'
                    },{
                        'url':'/production/write_offs',
                        'icon': 'bi bi-box-fill',
                        'text': 'Inventory Write Offs',
                        'name': 'write_offs'
                    },{
                        'url': '/production/main_stock_transfers/',
                        'icon': 'bi bi-truck',
                        'text': mark_safe (
                            f'Inventory Transfers <span class="badge rounded-circle bg-danger">{created_livara_store_orders}</span>'
                            if created_livara_store_orders > 0 else 'Inventory Transfers'
                        ),
                        'name':'main_stock_transfers'
                    },
                        ]
            })
            sidebar_menu.append({
                'icon': 'bi bi-box-fill',
                'text': 'Accessory Inventory',
                'children': [
                    {
                    'url':'/production/main_store_accessory_requisitions_list/',
                    'icon':'bi bi-receipt',
                    'text': mark_safe(f'Accessory Requests<span class="badge rounded-circle bg-danger">{new_accessory_requests}</span>'
                            if new_accessory_requests>0 else 'Accessory Requests'    
                            ),
                    'name': 'main_store_accessory_requisitions_list',
            
                    },
                    {
                        'url':'/production/accessory_store/',
                        'icon': 'bi bi-box-fill',
                        'text': 'Accessories Items',
                        'name': 'accessory_store'
                    },{
                        'url': '/production/all_internal_requests/',
                        'icon': 'bi bi-folder-fill',
                        'text': mark_safe(f'Branch Accessory Requests <span class="badge rounded-circle bg-danger">{internal_requisition_count}</span>'
                                    if internal_requisition_count > 0 else 'Branch Accessory Requests'
                                    ),
                        'name': 'all_internal_requests',
                    }
                        ]
            })
            sidebar_menu.append({
                'icon': 'bi bi-receipt',
                'text': 'Manage Sales',
                'children': [
                    {
                    'url': '/production/list_store_sales',
                    'icon': 'bi bi-speedometer',
                    'text': mark_safe(f'All Store Sales<span class="badge rounded-circle bg-danger">{store_sales_order_count}</span>'
                                    if store_sales_order_count > 0 else 'All Store Sales'
                                    ),
                    'name':'listStoreSales'
                    },
                    {
                    'url': '/production/store_sale_list_receipts',
                    'icon': 'bi bi-speedometer',
                    'text': 'Receipts',
                    'name':'store_sale_list_receipts'
                    }
                    ]
            })
            sidebar_menu.append({
                'icon': 'bi bi-box-seam',
                'text': 'Reports',
                'children': [{
                    'url': '/production/write_offs',
                    'icon': 'bi bi-box-seam',
                    'text': 'Production Store Writeoffs',
                    'name': 'writeoffs',
                },{
                    'url': '/production/product_location_report/',
                    'icon': 'bi bi-bounding-box-circles',
                    'text': 'Product by Location Report',
                    'name': 'product_location_report',
                },{
                    'url':'/production/main_store_writeoff_list/',
                    'icon':'bi bi-list-task',
                    'text':'Main Store Offsets',
                    'name':'main_store_writeoff_list',
                    
                }]
            })
        elif 'Branch Manager' in group_names:
            # Show branch manager menus
            sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
            sidebar_menu = [item for item in sidebar_menu if item.get('name', '') in ['manager_inventory_view','view_pricing_groups','restockRequests','store_services_view','branch_staff_view','particular_store_inventory','store_internal_requests','store_sale_list','store_sale_service_invoice_list','pageCustomer']]  # Replace with your branch manager menu names
            sidebar_menu.append({
                'icon':'bi bi-boxex-fill',
                'text': 'Inventory',
                'children': [{
                    
                    'url': '/production/manager_inventory_view/',
                    'icon': 'bi bi-box-fill',
                    'text': 'Store Inventory',
                    'name': 'manager_inventory_view'
                    }]
            })
            sidebar_menu.append({
                'icon':'bi bi-boxex-fill',
                'text': 'Sales',
                'children': [
                    {
                    'url': '/production/finance_store_sale_list/',
                    'icon': 'bi bi-folder',
                    'text': 'Salon Sales',
                    'name':'finance_store_sale_list',
                },{
                        'url':'/production/payments/',
                        'icon':'bi bi-credit-card',
                        'text':'Receipt Payments',
                        'name':'payment_list'
                    }]
            })
            sidebar_menu.append({
                'icon': 'bi bi-receipt',
                'text': 'Staff Commissions',
                'children': [{
                    'url': '/production/monthly-commissions/',
                    'icon': 'bi bi-receipt',
                    'text': 'Monthly Commissions',
                    'name': 'monthly_commission_list',
                }]
            })
        elif 'Finance' in group_names:
            # Show finance menus
            sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
            sidebar_menu = [item for item in sidebar_menu if item.get('name', '') in ['financeProduction','supplierList','productsList','rawmaterialsList','pageCustomer','discrepancy_delivery_report_list','goods_received_note_list']]
            sidebar_menu.append({
            
                'icon': 'bi bi-receipt',
                'text': 'Services',
                'children': [{
                    'url': '/production/services/',
                    'icon': 'bi bi-receipt',
                    'text': 'Services',
                    'name': 'service_list',
                }]
                
            })
            sidebar_menu.append({
                'icon': 'bi bi-inboxes-fill',
                'text': mark_safe(f'Production Logistics<span class="badge rounded-circle bg-danger">{production_logistics_total}</span>'
                                if production_logistics_total > 0 else 'Production Logistics'
                                ),
                'children': [{
                    'url': '/production/all_requisitions',
                    'icon': 'bi bi-inboxes-fill',
                    'text': mark_safe(
                        f'Requisitions <span class="badge rounded-circle bg-danger">{requisitions_count}</span>' 
                        if requisitions_count > 0 else 'Requisitions'),
                    'name': 'all_requisitions'
                },{
                    'url': '/production/lpos_list/',
                    'icon': 'bi bi-egg-fried',
                    'text': mark_safe(f'Purchase Orders <span class="badge rounded-circle bg-danger">{lpo_count}</span>'
                            if lpo_count > 0 else 'Purchase Orders'
                            ),
                    'name': 'lpos_list'
                },{
                'url': '/production/goods-received-notes/',
                'icon': 'bi bi-receipt',
                'text': 'Goods Received Note List',
                'name': 'goods_received_note_list'
            },{
                    'url': '/production/discrepancy_delivery_report_list/',
                    'icon': 'bi bi-box-fill',
                    'text': 'Discrepancy Delivery Report List',
                    'name': 'discrepancy_delivery_report_list'
                },{
                    'url': '/production/debit_notes_list/',
                    'icon': 'bi bi-receipt',
                    'text': 'Debit Notes',
                    'name': 'debit_notes_list'
                },{
                'url': '/production/replace_notes_list/',
                'icon': 'bi bi-receipt',
                'text': 'Replace Notes',
                'name':'replace_notes_list'
                },{
            
                'url': '/production/outstanding_payables',
                'icon': 'bi bi-box-seam',
                'text': mark_safe(f'Outstanding Payables<span class="badge rounded-circle bg-danger">{get_outstanding_po_payables}</span>'
                                if get_outstanding_po_payables>0 else 'Outstanding Payables'
                                ),
                'name': 'outstanding_payables',
           
                },{
                'url':'/production/production_payment_vouchers/',
                'icon':'bi bi-receipt',
                'text': mark_safe (f'Payment Vouchers<span class="badge rounded-circle bg-danger">{production_payment_vouchers}</span>'
                                    if production_payment_vouchers>0 else 'Payment Vouchers'
                                ),
                'name': 'production_payment_vouchers',
                }],
                
            })
            sidebar_menu.append({
                'icon': 'bi bi-box-seam',
                'text': mark_safe(f'Sales<span class="badge rounded-circle bg-danger">{sales_total}</span>'
                                if sales_total > 0 else 'Sales'
                                ),
                'children': [{
                    'url': '/production/finance_list_store_sales/',
                    'icon': 'bi bi-bounding-box-circles',
                    'text': 'Direct Store Sales',
                    'name': 'financeListStoreSales',
                },{
                    'url': '/production/store_sale_list_receipts',
                    'icon': 'bi bi-speedometer',
                    'text': 'Direct Store Sale Receipts',
                    'name':'store_sale_list_receipts'
                    },
                {
                    'url': '/production/finance_store_sale_list/',
                    'icon': 'bi bi-folder',
                    'text': 'Salon Sales',
                    'name':'finance_store_sale_list',
                },{
                    'url':'/production/all_payment_receipts_view',
                    'icon':'bi bi-receipt',
                    'text':'Salon Sale Receipts',
                    'name':'all_payment_receipts_view',
                },{
                        'url':'/production/payments/',
                        'icon':'bi bi-credit-card',
                        'text':'Receipt Payments',
                        'name':'payment_list'
                    },{
                        'url':'/accounts/process-pending-sales/',
                        'icon':'bi bi-receipt',
                        'text':'Process Pending Sales',
                        'name':'process_pending_sales'
                    }]
            })
            sidebar_menu.append({
                'icon': 'bi bi-box-seam',
                'text': mark_safe(f'Inventory<span class="badge rounded-circle bg-danger">{inventory_total}</span>'
                                if inventory_total > 0 else 'Inventory'
                                ),
                'children': [{
                    'url': '/production/livara_main_store_inventory',
                    'icon': 'bi bi-box-fill',
                    'text': 'Main Store Inventory',
                    'name': 'livara_main_store_inventory'
                    
            },{
            'url': '/production/factory-inventory/',
            'icon': 'bi bi-box-fill',
            'text': 'URI Inventory',
            'name': 'factoryInventory'
        },{
                    'url':'/production/accessory_store/',
                    'icon': 'fa-solid fa-gem',
                    'text': 'Accessory Inventory',
                    'name': 'accessory_store',
                },{
                        'url': '/production/main_store_inventory_adjustments/',
                        'icon': 'bi bi-folder',
                        'text': 'Saloon Inventory',
                        'name':'main_store_inventory_adjustments',
                    },{
                    'url': '/production/main_stock_transfers/',
                    'icon': 'bi bi-truck',
                    'text': mark_safe (
                        f'Inventory Transfers <span class="badge rounded-circle bg-danger">{created_livara_store_orders}</span>'
                        if created_livara_store_orders > 0 else 'Inventory Transfers'
                    ),
                    'name':'main_stock_transfers'
                },{
            'url':'/production/main_store_accessory_requisitions_list/',
            'icon':'bi bi-receipt',
            'text': mark_safe(f'Accessories Requests<span class="badge rounded-circle bg-danger">{new_accessory_requests}</span>'
                    if new_accessory_requests>0 else 'Accessories Requests'    
                    ),
            'name': 'main_store_accessory_requisitions_list',
    
            },]
            })
            sidebar_menu.append({
                'icon': 'bi bi-box-seam',
                'text': 'Reports',
                'children': [{
                    'url':'/production/price-groups/',
                    'icon': 'bi bi-folder-fill',
                    'text': 'Pricing Groups',
                    'name': 'view_pricing_groups',
                },{
                    'url': '/production/raw_material_date_report/',
                    'icon': 'bi bi-folder',
                    'text': 'Raw Material Date Report',
                    'name': 'raw_material_date_report',
                },{
                    'url':'/production/incident_write_off_list',
                    'icon':'bi bi-box-seam',
                    'text': 'Rawmaterial Writeoffs',
                    'name': 'incident_write_off_list',
                },{
                    'url': '/production/write_offs',
                    'icon': 'bi bi-box-seam',
                    'text': 'URI Store Writeoffs',
                    'name': 'writeoffs',
                },{
                    'url': '/production/product_location_report/',
                    'icon': 'bi bi-bounding-box-circles',
                    'text': 'Product by Location Report',
                    'name': 'product_location_report',
                },{
                    'url':'/production/main_store_writeoff_list/',
                    'icon':'bi bi-list-task',
                    'text':'Main Store Offsets',
                    'name':'main_store_writeoff_list',
                            
                }]
            })
            sidebar_menu.append({
                'icon': 'bi bi-receipt',
                'text': 'Staff Commissions',
                'children': [{
                    'url': '/production/monthly-commissions/',
                    'icon': 'bi bi-receipt',
                    'text': 'Monthly Commissions',
                    'name': 'monthly_commission_list',
                }]
            })
            sidebar_menu.append({
                'icon': 'bi bi-receipt',
                'text': 'Accounts',
                'children': [{
                    'url': '/accounts/accounting_dashboard/',
                    'icon': 'bi bi-receipt',
                    'text': 'Accounts',
                    'name': 'accounting_dashboard',
                },{
                    'url': '/accounts/chart-of-accounts/',
                    'icon': 'bi bi-receipt',
                    'text': 'Chart of Accounts',
                    'name': 'chart_of_accounts_list',
                },{
                    'url': '/accounts/departments/',
                    'icon': 'bi bi-receipt',
                    'text': 'Departments',
                    'name': 'department_list',
                },{
                    'url': '/accounts/budgets/',
                    'icon': 'bi bi-receipt',
                    'text': 'Budgets',
                    'name': 'budget_list',
                },{
                    'url': '/accounts/journal-entries/',
                    'icon': 'bi bi-receipt',
                    'text': 'Journal Entries',
                    'name': 'journal_entry_list',
                },{
                    'url': '/accounts/trial-balance/',
                    'icon': 'bi bi-receipt',
                    'text': 'Trial Balance',
                    'name': 'trial_balance',
                },{
                    'url': '/accounts/ledger-entries/',
                    'icon': 'bi bi-receipt',
                    'text': 'Ledger Entries',
                    'name': 'ledger_entries',
                }]
            })
        elif 'Production Manager' in group_names:
            # Show production manager menus
            sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
            sidebar_menu = [item for item in sidebar_menu if item.get('name', '') in ['productionPage', 'supplierList', 'productsList', 'productionProduction', 'manufacturedProductList', 'factoryInventory','storeRequests']]
            sidebar_menu.append({
                'icon': 'bi bi-inboxes-fill',
                'text': mark_safe(f'Production Logistics<span class="badge rounded-circle bg-danger">{production_logistics_total}</span>'
                                if production_logistics_total > 0 else 'Production Logistics'
                                ),
                'children': [{
                    'url': '/production/all_requisitions',
                    'icon': 'bi bi-inboxes-fill',
                    'text': mark_safe(
                        f'Requisitions <span class="badge rounded-circle bg-danger">{verified_requsitions}</span>' 
                        if verified_requsitions > 0 else 'Requisitions'),
                    'name': 'all_requisitions'
                },{
                    'url': '/production/goods-received-notes/',
                    'icon': 'bi bi-receipt',
                    'text': 'Goods Received Note List',
                    'name': 'goods_received_note_list'
                },{
                    'url': '/production/debit_notes_list/',
                    'icon': 'bi bi-receipt',
                    'text': 'Debit Notes',
                    'name': 'debit_notes_list'
                },
                {
                'url': '/production/replace_notes_list/',
                'icon': 'bi bi-receipt',
                'text': mark_safe(
                    f'Replace Notes<span class="badge rounded-circle bg-danger">{replace_notes}</span>'
                    if replace_notes>0 else 'Replace Notes'
                    ),
                'name':'replace_notes_list'
                }]
            })
            sidebar_menu.append({
                'icon': 'bi bi-folder',
                'text':'Production Reports',
                'children': [{
                    'url': '/production/manufacture_products_report',
                    'icon': 'bi bi-folder-fill',
                    'text': 'Manufacture Products Report',
                    'name':'manufacture_products_report',
                },{
                    'url': '/production/raw_material_utilization_report/',
                    'icon': 'bi bi-folder',
                    'text': 'Raw Material Utilization Report',
                    'name': 'raw_material_utilization_report',
                },{
                    'url': '/production/raw_material_date_report/',
                    'icon': 'bi bi-folder',
                    'text': 'Raw Material Date Report',
                    'name': 'raw_material_date_report',
                },{
                    'url': '/production/write_offs',
                    'icon': 'bi bi-box-seam',
                    'text': 'Production Store Writeoffs',
                    'name': 'writeoffs',
                },{
                    'url':'/production/incident_write_off_list',
                    'icon':'bi bi-box-seam',
                    'text': 'Rawmaterial Writeoffs',
                    'name': 'incident_write_off_list'
                    },{
                    'url': '/accounts/manufacturing-report/',
                    'icon': 'bi bi-folder',
                    'text': 'Manufacturing Report',
                    'name': 'manufacturing_report',
                    },{
                        'url': '/production/main_stock_transfers/',
                        'icon': 'bi bi-truck',
                        'text': 'Inventory Transfer',
                        'name': 'main_stock_transfer',
                    }]
            })
            sidebar_menu.append({
                'icon': 'bi bi-folder',
                'text':'Rawmaterials Unit',
                'children': [{
                    'url': '/production/raw-materials/',
                    'text': 'All Rawmaterials',
                    'name':'rawmaterialsList',
                },{
                    'url': '/production/raw-material-prices/add/',
                    'text': 'Raw Material Price',
                    'name':'add_raw_material_price',
                    },{
                        'url': '/production/price-comparison/',
                        'text': 'Price Comparison',
                        'name':'price_comparison',
                    }]
            })
        elif 'Saloon Managers' in group_names:
            sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
            sidebar_menu = [item for item in sidebar_menu if item.get('name', '') in ['salon','pageCustomer','branch_inventory']]
            # Add store management menu if user has permission
            
            sidebar_menu.append({
                'icon': 'bi bi-inboxes-fill',
                'text': 'Saloon Management',
                'children': [{
            'url': '/salon/all_salon_restock_requests/',
            'icon': 'bi bi-recycle',
            'text': mark_safe (
                f'Restock Requests <span class="badge rounded-circle bg-danger">{restock_requests_count}</span>'
                if restock_requests_count > 0 else 'Restock Requests' 
            ),
            'name': 'view_salon_restock_requests',
        },{
                'url': '/production/raw-materials/',
                'icon': 'bi bi-egg-fried',
                'text': 'Raw Materials',
                'name': 'rawmaterialsList'
            },{
                'url': '/production/store-products',
                'text': 'Store Products',
                'name':'storeProducts'
            },{
                'url': '/production/dispatch-list',
                'icon': 'bi bi-inboxes-fill',
                'text': 'Dispatch',
                'name': 'dispatchList'
            }
                        # ... store management children
                    ]
                })
    else:
        sidebar_menu = [item for item in sidebar_menu if item.get('name', '') in ['index']]

        sidebar_menu = mark_active_link(sidebar_menu, current_path_name)
    return {'sidebar_menu': sidebar_menu}