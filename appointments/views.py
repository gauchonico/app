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
    
    context = {
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/auth/customer_landing.html', context)


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
        # 'appSidebarHide': 1,
        # 'appHeaderHide': 1,
        # 'appContentFullHeight': 1,
        # 'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
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
        
        # Debug: Print POST data
        print("POST Data:", request.POST)
        print("Form errors:", form.errors)
        print("Form is valid:", form.is_valid())
        
        if form.is_valid():
            print("Form cleaned data:", form.cleaned_data)
            try:
                appointment = form.save(commit=False)
                appointment.customer = customer
                
                # Handle is_out_of_salon flag from cleaned_data
                if 'is_out_of_salon' in form.cleaned_data:
                    appointment.is_out_of_salon = form.cleaned_data['is_out_of_salon']
                
                print("About to save appointment...")
                appointment.save()
                print("Appointment saved with ID:", appointment.id)
                
                form.save_m2m()  # Save many-to-many relationships
                print("M2M saved")
                
                messages.success(
                    request, 
                    f'Appointment booked successfully! Your appointment ID is {appointment.appointment_id}'
                )
                return redirect('appointment_details', appointment_id=appointment.id)
            except Exception as e:
                print("Error saving appointment:", str(e))
                import traceback
                traceback.print_exc()
                messages.error(request, f"Error saving appointment: {str(e)}")
        else:
            # Show form errors
            print("Form validation failed. Errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            # Also show non-field errors
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, f"Error: {error}")
    else:
        form = AppointmentBookingForm(user=request.user)
    
    context = {
        'form': form,
        'customer': customer,
        # 'appSidebarHide': 1,
        # 'appHeaderHide': 1,
        # 'appContentFullHeight': 1,
        # 'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
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
        # 'appSidebarHide': 1,
        # 'appHeaderHide': 1,
        # 'appContentFullHeight': 1,
        # 'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/my_appointments.html', context)


@login_required(login_url='/login/')
def all_appointments(request):
    """
    View all appointments for managers and finance staff with advanced filters and analytics
    """
    # Check permissions - only managers and finance can access
    user_groups = request.user.groups.all()
    group_names = [group.name for group in user_groups]
    
    allowed_groups = ['Branch Manager','Storemanager', 'Finance', 'Admin']
    if not any(group in group_names for group in allowed_groups):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('production_dashboard')
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    payment_status_filter = request.GET.get('payment_status', '').strip()
    store_filter = request.GET.get('store', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    show_latest = request.GET.get('show_latest', '').strip()
    
    # Base queryset with related data
    appointments = Appointment.objects.select_related('customer', 'store').prefetch_related('services', 'assigned_staff')
    
    # Apply filters
    if search_query:
        appointments = appointments.filter(
            Q(appointment_id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(customer_email__icontains=search_query)
        )
    
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    if payment_status_filter:
        appointments = appointments.filter(payment_status=payment_status_filter)
    
    if store_filter:
        if store_filter == 'out_of_salon':
            appointments = appointments.filter(is_out_of_salon=True)
        else:
            appointments = appointments.filter(store_id=store_filter)
    
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            appointments = appointments.filter(appointment_date__gte=date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            appointments = appointments.filter(appointment_date__lte=date_to_obj)
        except:
            pass
    
    # Latest filter
    if show_latest:
        appointments = appointments.order_by('-created_at')
    else:
        appointments = appointments.order_by('-appointment_date', '-appointment_time')
    
    # Calculate statistics
    from django.db.models import Sum, Count, Q, Avg
    total_appointments = appointments.count()
    
    # Status breakdown
    status_stats = {
        'pending': appointments.filter(status='pending').count(),
        'confirmed': appointments.filter(status='confirmed').count(),
        'in_progress': appointments.filter(status='in_progress').count(),
        'completed': appointments.filter(status='completed').count(),
        'cancelled': appointments.filter(status='cancelled').count(),
        'no_show': appointments.filter(status='no_show').count(),
    }
    
    # Financial stats
    total_estimated = appointments.aggregate(total=Sum('estimated_cost'))['total'] or 0
    total_deposits = appointments.aggregate(total=Sum('deposit_amount'))['total'] or 0
    completed_revenue = appointments.filter(status='completed').aggregate(total=Sum('estimated_cost'))['total'] or 0
    
    # Payment status breakdown
    payment_stats = {
        'not_required': appointments.filter(payment_status='not_required').count(),
        'pending': appointments.filter(payment_status='pending').count(),
        'paid': appointments.filter(payment_status='paid').count(),
        'refunded': appointments.filter(payment_status='refunded').count(),
    }
    
    # Today's appointments
    today = timezone.now().date()
    today_appointments = appointments.filter(appointment_date=today).count()
    
    # Upcoming appointments (next 7 days)
    from datetime import timedelta
    next_week = today + timedelta(days=7)
    upcoming_appointments = appointments.filter(
        appointment_date__gte=today,
        appointment_date__lte=next_week,
        status__in=['pending', 'confirmed']
    ).count()
    
    # Store breakdown
    store_stats = appointments.values('store__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Out of salon count
    out_of_salon_count = appointments.filter(is_out_of_salon=True).count()
    
    # Pagination
    paginator = Paginator(appointments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all stores for filter dropdown
    stores = Store.objects.all()
    
    context = {
        'appointments': page_obj,
        'stores': stores,
        'total_appointments': total_appointments,
        'status_stats': status_stats,
        'payment_stats': payment_stats,
        'total_estimated': total_estimated,
        'total_deposits': total_deposits,
        'completed_revenue': completed_revenue,
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
        'store_stats': store_stats,
        'out_of_salon_count': out_of_salon_count,
        # Filter values for preserving state
        'filter_search': search_query,
        'filter_status': status_filter,
        'filter_payment_status': payment_status_filter,
        'filter_store': store_filter,
        'filter_date_from': date_from,
        'filter_date_to': date_to,
        'filter_show_latest': show_latest,
        # Status choices
        'status_choices': Appointment.STATUS_CHOICES,
        'payment_status_choices': Appointment.PAYMENT_STATUS_CHOICES,
    }
    
    return render(request, 'appointments/all_appointments.html', context)

@login_required(login_url='/login/')
def store_appointments(request):
    """
    View for store managers to see appointments for their specific store
    """
    # Get the store managed by the current user
    store = get_object_or_404(Store, manager=request.user)
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_filter = request.GET.get('date', '').strip()
    
    # Base queryset with related data, filtered by store
    appointments = Appointment.objects.filter(store=store).select_related(
        'customer'
    ).prefetch_related(
        'services', 'assigned_staff'
    ).order_by('-appointment_date', '-appointment_time')
    
    # Apply filters
    if search_query:
        appointments = appointments.filter(
            Q(appointment_id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(customer_email__icontains=search_query)
        )
    
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    if date_filter:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            appointments = appointments.filter(appointment_date=date_obj)
        except:
            pass
    
    # Calculate basic statistics
    total_appointments = appointments.count()
    today_appointments = appointments.filter(appointment_date=timezone.now().date()).count()
    
    # Status breakdown
    status_stats = {
        'pending': appointments.filter(status='pending').count(),
        'confirmed': appointments.filter(status='confirmed').count(),
        'in_progress': appointments.filter(status='in_progress').count(),
        'completed': appointments.filter(status='completed').count(),
        'cancelled': appointments.filter(status='cancelled').count(),
    }
    
    # Pagination
    paginator = Paginator(appointments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'appointments': page_obj,
        'store': store,
        'total_appointments': total_appointments,
        'today_appointments': today_appointments,
        'status_stats': status_stats,
        # Filter values for preserving state
        'filter_search': search_query,
        'filter_status': status_filter,
        'filter_date': date_filter,
        # Status choices
        'status_choices': Appointment.STATUS_CHOICES,
    }
    
    return render(request, 'appointments/store_appointments.html', context)

@login_required(login_url='/login/')
def appointment_details(request, appointment_id):
    """
    View appointment details
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if user is the customer who booked
    try:
        customer = request.user.customer
        if appointment.customer != customer:
            messages.error(request, 'You do not have permission to view this appointment.')
            return redirect('customer_dashboard')
    except:
        messages.error(request, 'Customer profile not found.')
        return redirect('customer_dashboard')
    
    # Calculate estimated cost if not set
    if appointment.estimated_cost == 0:
        total_cost = 0
        for service in appointment.services.all():
            if appointment.store:
                try:
                    store_service = appointment.store.store_services.get(service=service)
                    total_cost += store_service.service.price
                except:
                    total_cost += service.price
            else:
                total_cost += service.price
        appointment.estimated_cost = total_cost
        appointment.save()
    
    context = {
        'appointment': appointment,
        'customer': customer,
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/appointment_details.html', context)

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