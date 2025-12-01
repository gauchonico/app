from django.urls import path
from . import views, views_auth

urlpatterns = [
    # Customer Authentication
    path('login/', views_auth.CustomerLoginView.as_view(), name='customer_login'),
    path('register/', views_auth.CustomerRegistrationView.as_view(), name='customer_register'),
    path('profile/', views_auth.customer_profile, name='customer_profile'),
    path('logout/', views_auth.customer_logout, name='customer_logout'),
    
    # Customer Landing & Dashboard
    path('welcome/', views.customer_landing, name='customer_landing'),
    path('', views.customer_dashboard, name='customer_dashboard'),
    
    # Appointment Management
    path('book/', views.book_appointment, name='book_appointment'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('appointment/<int:appointment_id>/', views.appointment_details, name='appointment_details'),
    # path('appointment/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    # path('appointment/<int:appointment_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    
    # Catalogues
    path('products/', views.product_catalogue, name='product_catalogue'),
    path('services/', views.service_catalogue, name='service_catalogue'),
    
    # Admin/Staff Views
    path('all-appointments/', views.all_appointments, name='all_appointments'),
    path('store-appointments/', views.store_appointments, name='store_appointments'),
    
    # AJAX endpoints
    # path('api/available-times/', views.get_available_times, name='get_available_times'),
]
