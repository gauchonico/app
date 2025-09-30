from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Appointment, AppointmentFeedback
from .forms import AppointmentBookingForm, AppointmentSearchForm, AppointmentFeedbackForm
from production.models import Store, ServiceName, StoreInventory
from POSMagicApp.models import Customer


def customer_landing(request):
    """
    Landing page for customers (not logged in)
    """
    if request.user.is_authenticated:
        return redirect('customer_dashboard')
    
    return render(request, 'appointments/auth/customer_landing.html')


@login_required(login_url='/appointments/login/')
def customer_dashboard(request):
    """
    Customer dashboard with quick actions for appointments, products, and services
    """
    try:
        customer = request.user.customer
    except:
        messages.error(request, 'Customer profile not found. Please contact support.')
        return redirect('logout')
    
    # Get customer's recent appointments
    recent_appointments = Appointment.objects.filter(
        customer=customer
    ).order_by('-created_at')[:5]
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        customer=customer,
        appointment_date__gte=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).order_by('appointment_date', 'appointment_time')[:3]
    
    # Get all stores
    stores = Store.objects.all()
    
    # Get available services
    services = ServiceName.objects.all()[:6]
    
    # Get featured products
    featured_products = StoreInventory.objects.filter(
        quantity__gt=0
    ).select_related('product', 'store')[:6]
    
    # Statistics
    total_appointments = Appointment.objects.filter(customer=customer).count()
    upcoming_count = Appointment.objects.filter(
        customer=customer,
        appointment_date__gte=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).count()
    
    context = {
        'customer': customer,
        'recent_appointments': recent_appointments,
        'upcoming_appointments': upcoming_appointments,
        'stores': stores,
        'services': services,
        'featured_products': featured_products,
        'total_appointments': total_appointments,
        'upcoming_count': upcoming_count,
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/customer_dashboard.html', context)


@login_required(login_url='/login/')
def book_appointment(request):
    """
    Book a new appointment
    """
    try:
        customer = request.user.customer
    except:
        messages.error(request, 'Customer profile not found. Please contact support.')
        return redirect('logout')
    
    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST, user=request.user)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.customer = customer
            appointment.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(
                request, 
                f'Appointment booked successfully! Your appointment ID is {appointment.appointment_id}'
            )
            return redirect('appointment_details', appointment_id=appointment.id)
    else:
        form = AppointmentBookingForm(user=request.user)
    
    context = {
        'form': form,
        'customer': customer,
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/book_appointment.html', context)


@login_required(login_url='/login/')
def my_appointments(request):
    """
    View customer's appointments with filtering and search
    """
    try:
        customer = request.user.customer
    except:
        messages.error(request, 'Customer profile not found. Please contact support.')
        return redirect('logout')
    
    # Get search and filter parameters
    search_form = AppointmentSearchForm(request.GET)
    appointments = Appointment.objects.filter(customer=customer)
    
    # Apply filters
    if search_form.is_valid():
        search = search_form.cleaned_data.get('search')
        status = search_form.cleaned_data.get('status')
        store = search_form.cleaned_data.get('store')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if search:
            appointments = appointments.filter(
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search) |
                Q(appointment_id__icontains=search)
            )
        
        if status:
            appointments = appointments.filter(status=status)
        
        if store:
            if store == 'out_of_salon':
                appointments = appointments.filter(is_out_of_salon=True)
            else:
                appointments = appointments.filter(store=store)
        
        if date_from:
            appointments = appointments.filter(appointment_date__gte=date_from)
        
        if date_to:
            appointments = appointments.filter(appointment_date__lte=date_to)
    
    # Order appointments
    appointments = appointments.order_by('-appointment_date', '-appointment_time')
    
    # Pagination
    paginator = Paginator(appointments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'appointments': page_obj,
        'search_form': search_form,
        'customer': customer,
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/my_appointments.html', context)


@login_required(login_url='/login/')
def product_catalogue(request):
    """
    View product catalogue for customers
    """
    try:
        customer = request.user.customer
    except:
        messages.error(request, 'Customer profile not found. Please contact support.')
        return redirect('logout')
    
    # Get search parameters
    search_query = request.GET.get('search', '')
    store_filter = request.GET.get('store', '')
    
    # Get products
    products = StoreInventory.objects.filter(
        quantity__gt=0
    ).select_related('product', 'store')
    
    # Apply filters
    if search_query:
        products = products.filter(
            Q(product__product_name__icontains=search_query) |
            Q(product__description__icontains=search_query)
        )
    
    if store_filter:
        products = products.filter(store_id=store_filter)
    
    # Get stores for filter
    stores = Store.objects.all()
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'stores': stores,
        'search_query': search_query,
        'store_filter': store_filter,
        'customer': customer,
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/product_catalogue.html', context)


@login_required(login_url='/login/')
def service_catalogue(request):
    """
    View service catalogue for customers
    """
    try:
        customer = request.user.customer
    except:
        messages.error(request, 'Customer profile not found. Please contact support.')
        return redirect('logout')
    
    # Get search parameters
    search_query = request.GET.get('search', '')
    store_filter = request.GET.get('store', '')
    
    # Get services
    services = ServiceName.objects.all()
    
    # Apply search filter
    if search_query:
        services = services.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Get stores for filter
    stores = Store.objects.all()
    
    # Get service availability by store
    service_availability = {}
    if store_filter:
        store = get_object_or_404(Store, id=store_filter)
        available_services = store.store_services.values_list('service', flat=True)
        service_availability = {service.id: True for service in services.filter(id__in=available_services)}
    
    # Pagination
    paginator = Paginator(services, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'services': page_obj,
        'stores': stores,
        'search_query': search_query,
        'store_filter': store_filter,
        'service_availability': service_availability,
        'customer': customer,
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/service_catalogue.html', context)