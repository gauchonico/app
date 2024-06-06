from django.urls import resolve

def mark_active_link(menu, current_path_name):
    for item in menu:
        item['is_active'] = item.get('name', '') == current_path_name

        if 'children' in item:
            item['children'] = mark_active_link(item['children'], current_path_name)

            if any(child.get('is_active', False) for child in item['children']):
                item['is_active'] = True

    return menu

def sidebar_menu(request):
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
        'url': '/production/suppliers/',
        'icon': 'bi bi-truck-flatbed',
        'text': 'Suppliers',
        'name': 'supplierList'
    },{
         'url': '/production/products-list/',
         'icon': 'bi bi-upc-scan',
         'text': 'Products',
         'name': 'productsList'
    },{
        'url': '/production/production-production-orders/',
        'icon': 'bi bi-node-plus-fill',
        'text': 'Production Orders',
        'name': 'productionProduction'
    },{
        'url': '/production/manufactured-product-list/',
        'icon': 'bi bi-speedometer',
        'text': 'Production Center',
        'name': 'manufacturedProductList'
    },{
        'url': '/production/factory-inventory/',
        'icon': 'bi bi-box-fill',
        'text': 'Production Inventory',
        'name': 'factoryInventory'
    },{
        'icon': 'bi bi-inboxes-fill',
        'text': 'Store Management',
        'children': [{
             'url': '/production/store-requests',
             'icon': 'bi bi-inboxes-fill',
             'text': 'Store Requests',
             'name':'storeRequests'
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
        'url': '/production/all-stores/',
        'icon': 'bi bi-shop',
        'text': 'All Stores',
        'name': 'allStores'
    },{
        'url': '/production/restock-requests/',
        'icon': 'bi bi-recycle',
        'text': 'Restock Requests',
        'name': 'restockRequests',
    },{
        'url': '/production/general-stores/',
        'icon': 'bi bi-boxes',
        'text': 'General Stores',
        'name': 'store_inventory_list',
    },{
         'text': 'FINANCE',
         'is_header': 1
    },{
        'url': '/production/finance-production-orders/',
        'icon': 'bi bi-bounding-box-circles',
        'text': 'Production Orders',
        'name': 'financeProduction',
    },{
         'url': '/production/finance-purchase-orders/',
         'icon': 'bi bi-box-seam',
         'text': 'Raw-material P.O',
         'name': 'financePurchase'
    },{
         'url': '/production/finance-restock-requests/',
         'icon': 'bi bi-receipt',
         'text': 'Restock Requests',
         'name': 'financeRestockRequests',
    }]
	
	resolved_path = resolve(request.path_info)

	current_path_name = resolved_path.url_name
	
	sidebar_menu = mark_active_link(sidebar_menu, current_path_name)

	return {'sidebar_menu': sidebar_menu}