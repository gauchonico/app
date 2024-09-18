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
    path('services/', ServiceListView.as_view(), name='service_list'),
    
    ##Genereate Requisition
    path('requisition/new/', views.create_general_requisition, name='create_general_requisition'),
    path('requisition_list/', views.general_requisition_list, name='general_requisition_list'),
    path('requisition/<int:pk>', views.requisition_details, name='requisition_details'),
    path('requisition/<int:pk>/mark_as_delivered/', views.mark_requisition_as_delivered, name='mark_requisition_as_delivered'),
    path('salon-inventories/', views.salon_inventory_list, name='salon_inventory_list'),
]