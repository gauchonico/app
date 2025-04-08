from django import views
from django.urls import path
from .views import *
from . import views
from .views import ServiceListView


urlpatterns = [
    path('salon-dashboard/', views.salon, name='salon'),
    path('products/add/', SalonProductCreateView.as_view(), name='salonproduct_create'),
    path('products/<int:pk>/edit/', SalonProductUpdateView.as_view(), name='salonproduct_edit'),
    path('products/<int:pk>/delete/', SalonProductDeleteView.as_view(), name='salonproduct_delete'),
    path('services/add/', ServiceCreateView.as_view(), name='service_create'),
    path('services/<int:pk>/edit/', ServiceUpdateView.as_view(), name='service_edit'),
    path('services/<int:pk>/delete/', ServiceDeleteView.as_view(), name='service_delete'),
    path('products/', SalonProductListView.as_view(), name='salonproduct_list'),
    path('services/', ServiceListView.as_view(), name='service_listunused'),
    
    ##Genereate Requisition
    path('requisition/new/', views.create_general_requisition, name='create_general_requisition'),
    path('requisition_list/', views.general_requisition_list, name='general_requisition_list'),
    path('salon_requisition/<int:pk>', views.requisition_details, name='salon_requisition_details'),
    path('salon_requisition/<int:pk>/mark_as_delivered/', views.mark_requisition_as_delivered, name='mark_requisition_as_delivered'),
    path('salon-inventories/', views.salon_inventory_list, name='salon_inventory_list'),
    
    #Restock requests
    path('create_salon_restock_requests/', views.create_salon_restock_requests, name="create_salon_restock_requests"),
    # path('mark_restock_as_delivered/<int:restock_id>', views.mark_restock_as_delivered, name="restock_delivered"),
    # path('approve-restock-request/<int:request_id>', views.approve_restock_requests, name="approve_restock_requests"),
    path('all_salon_restock_requests/', views.view_salon_restock_requests, name='view_salon_restock_requests'),
    path('salon_restock_request/<int:restock_request_id>/deliver/', views.deliver_salon_restock_request, name='deliver_salon_restock_request'),
    path('restock_request_details/<str:salon_restock_req_no>/', views.restock_request_details, name='restock_request_details'),
    path('branch_inventory/', views.branch_inventory, name='branch_inventory'),
]