from django.urls import path

from . import views


app_name = 'DjangoHUDApp'
urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path('page/order', views.transactionList, name='pageOrder'),
    path('page/order-details/<int:transaction_id>', views.pageOrderDetails, name='pageOrderDetails'),
    path('pay-transaction/<int:transaction_id>/', views.update_transaction_status, name='mark_transaction'),
    path('generate-reciept/<int:transaction_id>/', views.generate_pdf, name='generateReciept'),
    path('page/customers', views.pageCustomer, name='pageCustomer'),
    path('page/create-customer', views.createCustomer, name='createCustomer'),
    path('customer/<int:customer_id>/', views.customer_details, name='customer_details'),
    path('edit-customer/<int:customer_id>/', views.editCustomer, name='editCustomer'),
    path('delete-customer/<int:customer_id>/', views.deleteCustomer, name='deleteCustomer'),
    path('page/products', views.pageProduct, name='pageProduct'),
    path('page/create-product', views.createProduct, name='createProduct'),
    path('page/edit-product/<int:product_id>/', views.editProduct, name='editProduct'),
    path('delete-product/<int:product_id>/', views.deleteProduct, name='deleteProduct'),
    path('product-details/', views.productDetails,name='productDetails'),
    path('staff', views.staff, name='staff'),
    path('page/create-staff', views.createStaff, name='createStaff'),
    path('page/edit-staff/<int:staff_id>/', views.editStaff, name='editStaff'),
    path('delete-staff/<int:staff_id>/', views.deleteStaff, name='deleteStaff'),
    path('staff-commissions/', views.staff_commissions_view, name='StaffCommissionsView'),
    path('page/product-details/<int:pk>/', views.pageProductDetails, name='pageProductDetails'),
    path('404/', views.error404, name='error404'),
    path('customer-order/', views.posCustomerOrder, name='customerOrder'),
]