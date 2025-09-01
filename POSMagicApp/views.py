import subprocess
import uuid
from django.http import Http404, HttpResponseRedirect, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.db.models import Q
from django.conf import settings
import io
# from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime

# Import loyalty views
from .loyalty_views import (
    loyalty_settings_view, loyalty_reports_view, points_redemption_view,
    manual_points_adjustment_view, customer_loyalty_details, get_customer_points_ajax
)

from django.views import generic
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .decorators import unauthenticated_user, allowed_users
from payment.models import Receipt, Transaction, StaffCommission
from cart.cart import Cart
from .models import *
from django.contrib.auth.models import User
from django.db import transaction
from .forms import AddCustomerForm, AddProductForm, EditCustomerForm, EditProductForm, AddStaffForm, EditStaffForm, GenerateReceiptForm


def index(request):
	return render(request, "pages/index.html")
@unauthenticated_user
def login_user(request):
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		user = authenticate(request, username=username, password=password)

		if user is not None:
			login(request, user)
			messages.success(request, "User logged in")

			# Redirect based on user group membership
			if user.groups.filter(name='Finance').exists():
				return redirect('restockRequests') # Redirect to Finance dashboard
			elif user.groups.filter(name='Storemanager').exists():
				return redirect('store_inventory_list')  # Redirect to Store Manager dashboard
			elif user.groups.filter(name='Cashier').exists():
				return redirect('DjangoHUDApp:customerOrder')  # Redirect to Cashier dashboard
			else:
				# Handle case where user doesn't belong to any relevant group
				return redirect('DjangoHUDApp:index')

			
		else:
			messages.error(request, "Invalid username or password")
			return redirect('DjangoHUDApp:login')
            
	else:
		context = {
		"appSidebarHide": 1,
		"appHeaderHide": 1,
		"appContentClass": 'p-0'
	}
	return render(request, "pages/login.html", context)

def logout_user(request):
	logout(request)
	messages.success(request, "User logged out")
	return redirect('DjangoHUDApp:login')

def register_user(request):
	context = {
		"appSidebarHide": 1,
		"appHeaderHide": 1,
		"appContentClass": 'p-0'
	}
	return render(request, "pages/register.html", context)

@login_required
@allowed_users(allowed_roles=['Finance','Cashier'])
def pageOrderDetails(request, transaction_id):
	# Retrieve the transaction object from the database
	transaction = get_object_or_404(Transaction, pk=transaction_id)
	context ={
		'transaction': transaction,
	}

	return render(request, "pages/page-order-details.html", context)

def update_transaction_status(request, transaction_id):
    try:
        transaction = Transaction.objects.get(pk=transaction_id)
        if transaction.status == 'pending':
            transaction.status = 'paid'
            transaction.save()
            # Success message or redirect to confirmation page (optional)
            return redirect('DjangoHUDApp:pageOrder')  # Redirect example
    except Transaction.DoesNotExist:
        # Handle transaction not found error (optional)
        pass

def generate_pdf(request, transaction_id):
    try:
        transaction = Transaction.objects.get(pk=transaction_id)
        context = {'transaction': transaction}
        html_string = render_to_string('page-order-details.html', context)

        # Use wkhtmltopdf command (adjust paths if needed)
        pdf_filename = f'receipt-{transaction_id}.pdf'
        subprocess.run(['wkhtmltopdf', '-quiet', '-O', 'portrait', 'your_receipt_template.html', pdf_filename])

        # Read generated PDF content
        with open(pdf_filename, 'rb') as f:
            pdf_content = f.read()

        # Remove the temporary PDF file (optional)
        # os.remove(pdf_filename)  # Uncomment if needed

        # Set appropriate content type and filename
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response.headers['Content-Disposition'] = f'attachment; filename={pdf_filename}'

        return response
    except Transaction.DoesNotExist:
        return HttpResponse('Transaction not found.')
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return HttpResponse('Failed to generate PDF.')


## Customer ###

@login_required(login_url='/login/')
# @allowed_users(allowed_roles=['Finance','Cashier','Managers','Branch Manager','Store Managers'])
def pageCustomer(request):
	"""Enhanced customer page with analytics and filtering"""
	from django.db.models import Count, Q
	
	# Get filter parameters
	customer_type = request.GET.get('type', '')
	search_query = request.GET.get('search', '').strip()
	has_dependents = request.GET.get('dependents', '')
	kyc_status = request.GET.get('kyc', '')
	
	# Base queryset with related data
	customers = Customer.objects.select_related('guardian').prefetch_related('dependents')
	
	# Apply filters
	if customer_type:
		customers = customers.filter(type_of_customer=customer_type)
	
	if search_query:
		customers = customers.filter(
			Q(first_name__icontains=search_query) |
			Q(last_name__icontains=search_query) |
			Q(phone__icontains=search_query) |
			Q(email__icontains=search_query)
		)
	
	if has_dependents == 'yes':
		customers = customers.filter(dependents__isnull=False).distinct()
	elif has_dependents == 'no':
		customers = customers.filter(dependents__isnull=True)
	
	if kyc_status == 'verified':
		customers = customers.filter(kyc_verified=True)
	elif kyc_status == 'pending':
		customers = customers.filter(kyc_verified=False)
	
	# Annotate with additional data
	customers = customers.annotate(
		dependents_count=Count('dependents'),
		total_sales=Count('service_sales'),
	).order_by('-id')
	
	# Customer analytics
	analytics = {
		'total_customers': Customer.objects.count(),
		'total_clients': Customer.objects.filter(type_of_customer='CLIENT').count(),
		'total_wholesalers': Customer.objects.filter(type_of_customer='WHOLESALE').count(),
		'total_retailers': Customer.objects.filter(type_of_customer='RETAIL').count(),
		'kyc_verified': Customer.objects.filter(kyc_verified=True).count(),
		'minors': Customer.objects.filter(is_minor=True).count(),
		'with_dependents': Customer.objects.filter(dependents__isnull=False).distinct().count(),
	}
	
	context = {
		'customers': customers,
		'analytics': analytics,
		'customer_type': customer_type,
		'search_query': search_query,
		'has_dependents': has_dependents,
		'kyc_status': kyc_status,
		'customer_types': Customer.TYPE_OF_CUSTOMER,
	}
	return render(request, "pages/page-customer.html", context)

@login_required(login_url='/login/')
def add_dependent(request, customer_id):
	"""Add a dependent to an existing customer account"""
	from .forms import AddDependentForm
	from django.shortcuts import get_object_or_404, redirect
	from django.contrib import messages
	
	guardian = get_object_or_404(Customer, id=customer_id)
	
	# Check if the customer can be a guardian
	if guardian.is_minor or not guardian.kyc_verified:
		messages.error(request, 'This customer cannot be a guardian. Must be an adult with verified KYC.')
		return redirect('customerDetails', customer_id=customer_id)
	
	if request.method == 'POST':
		form = AddDependentForm(guardian, request.POST)
		if form.is_valid():
			dependent = form.save()
			messages.success(request, f'Successfully added {dependent.name} as a dependent.')
			return redirect('customerDetails', customer_id=customer_id)
	else:
		form = AddDependentForm(guardian)
	
	context = {
		'form': form,
		'guardian': guardian,
	}
	return render(request, "pages/add-dependent.html", context)

@login_required(login_url='/login/')
def customer_family_view(request, customer_id):
	"""View showing customer and all their dependents"""
	from django.shortcuts import get_object_or_404
	
	customer = get_object_or_404(Customer, id=customer_id)
	
	# Get the main account holder
	main_account = customer.account_holder
	
	# Get all family members (main account + dependents)
	family_members = Customer.objects.filter(
		Q(id=main_account.id) | Q(guardian=main_account)
	).select_related('guardian').order_by('is_minor', 'first_name')
	
	context = {
		'customer': customer,
		'main_account': main_account,
		'family_members': family_members,
	}
	return render(request, "pages/customer-family.html", context)

@login_required(login_url='/login/')
def createCustomer(request):
	if request.method == 'POST':
		form = AddCustomerForm(request.POST, request.FILES)  # Include FILES for image uploads
		if form.is_valid():
			customer = form.save()
			messages.success(request, f"New Customer {customer.name} Successfully added")
			return redirect('DjangoHUDApp:pageCustomer')
	else:
		form = AddCustomerForm()
	context = {'form': form}
		
	return render(request, "pages/create-customer.html", context)
 

@login_required(login_url='/login/')
def customer_details(request, customer_id):
	customer = get_object_or_404(Customer, pk=customer_id) # fetch customer by id
	transactions = Transaction.objects.filter(customer = customer)
	context = {
        'customer': customer,
		'transactions': transactions,
    }
	return render(request, "pages/customer-details.html", context)

@login_required(login_url='/login/')
def editCustomer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)  # Fetch customer by ID

    if request.method == 'POST':
        form = EditCustomerForm(request.POST, request.FILES, instance=customer)  # Include FILES for image uploads
        if form.is_valid():
            form.save()
            messages.success(request, f'Customer {customer.name} updated successfully!')
            return redirect('DjangoHUDApp:pageCustomer')  # Redirect to customer list after successful edit
    else:
        form = EditCustomerForm(instance=customer)  # Create form with existing customer data

    context = {'form': form, 'customer': customer}
    return render(request, 'pages/edit_customer.html', context)

def deleteCustomer (request, customer_id):
	customer = get_object_or_404(Customer, pk=customer_id)  # Fetch customer by ID
	customer.delete()
	messages.success(request, "Customer deleted")
	return redirect('DjangoHUDApp:pageCustomer')


## Product ##
@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Cashier'])
def pageProduct(request):
	# Get all products
	all_products = Product.objects.all()

	#Get products by category
	babershop_products = Product.objects.filter(category='BABERSHOP')
	kidshair_products = Product.objects.filter(category='KIDS_HAIR')
	nail_products = Product.objects.filter(category='NAIL_ART')
	prod_products = Product.objects.filter(category='PRODUCTS')
	dreadlock_products = Product.objects.filter(category='DREADLOCKS')
	cart = Cart(request)
	cart_products = cart.get_prods()

	context = {
		'cart': cart,
        'cart_products': cart_products,
		'all_products':all_products,
		'babershop_products':babershop_products,
		'kidshair_products':kidshair_products,
		'nail_products':nail_products,
		'prod_products':prod_products,
		'dreadlock_products':dreadlock_products,
	}
	return render(request, "pages/page-product.html", context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Cashier'])
def pageProductDetails(request, pk):
	product = Product.objects.get(id=pk)
	context = {'product': product}

	return render(request, "pages/page-product-details.html", context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance'])
def createProduct(request):

	if request.method == 'POST':
		form = AddProductForm(request.POST, request.FILES)
		if form.is_valid():
			form.save()
			messages.success(request, "Product Successfully created")
			return redirect('DjangoHUDApp:pageProduct')
	else:
		form = AddProductForm()
	context ={"form": form}

	return render(request, "pages/create-product.html", context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance'])
def editProduct(request, product_id):
    product = get_object_or_404(Product, pk=product_id)  # Fetch product by ID

    if request.method == 'POST':
        form = EditProductForm(request.POST, request.FILES, instance=product)  # Pre-populate form with existing data
        if form.is_valid():
            form.save()
            return redirect('DjangoHUDApp:pageProduct')  # Redirect to product list after successful edit
    else:
        form = EditProductForm(instance=product)  # Create form with existing product data

    context = {'form': form, 'product': product}
    return render(request, 'pages/edit_product.html', context)

@login_required(login_url='/login/')
def productDetails (request):
	return render(request, "pages/product_details.html")

def deleteProduct(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully!')
    return redirect('DjangoHUDApp:pageProduct')



## Staff ###
@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance'])
def staff(request):
	all_staff = Staff.objects.all()
	context = {
        'all_staff': all_staff,
    }
	return render(request, "pages/page-staff.html", context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance'])
def createStaff(request):
	if request.method == 'POST':
		form = AddStaffForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "Staff created successfully")
			return redirect('DjangoHUDApp:staff')
	else:
		form = AddStaffForm()
	context ={"form": form}
	return render(request, "pages/create-staff.html", context)

@login_required(login_url='/login/')
def editStaff(request, staff_id):
	staff = get_object_or_404(Staff, pk=staff_id)  # Fetch staff by user ID (primary key)
	
	if request.method == 'POST':
		form = EditStaffForm(request.POST, instance=staff)  # Pre-populate form with existing data
		if form.is_valid():
			form.save()
			messages.success(request, "Staff Details have been updated successfully")
			return redirect('DjangoHUDApp:staff')  # Redirect to staff list after successful edit
	else:
		form = EditStaffForm(instance=staff)  # Create form with existing staff data

	context = {'form': form, 'staff': staff}
	return render(request, 'pages/edit-staff.html', context)

def deleteStaff(request, staff_id):
	staff = get_object_or_404(Staff, pk=staff_id)
	staff.delete()
	messages.success(request, "Staff deleted successfully")
	return redirect('DjangoHUDApp:staff')

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance'])
def staff_commissions_view(request):
	staff = request.GET.get('staff')  # Get staff member filter (optional)
	start_date = request.GET.get('start_date')  # Get start date filter (optional)
	end_date = request.GET.get('end_date')  # Get end date filter (optional)
	status = request.GET.get('status') # Get status filter
	

	commissions = StaffCommission.objects.all()  # Start with all commissions

	# Apply filters based on provided parameters
	filters = Q()
	if staff:
		filters &= Q(staff__id=staff)  # Filter by staff ID
	if start_date and end_date:
		filters &= Q(date__range=(start_date, end_date))  # Filter by date range
	if status:
		filters &= Q(transaction__status=status)  # Filter by transaction status

	commissions = commissions.filter(filters)

	context = {
		'staff_commissions': commissions,
		'staff_choices': Staff.objects.all(),
		'status_choices': Transaction.STATUS_CHOICES,  # List of all staff members for dropdown (optional)
	}

	return render (request, 'pages/staff-commissions.html',context)

def generate_staff_commissions_pdf(request):
    
    # Get date range from request parameters
	start_date = request.GET.get('start_date')
	end_date = request.GET.get('end_date')

	# Validate date range
	

	# if start_date and end_date:
	# 	try:
	# 		start_date = datetime.date(start_date, '%Y-%m-%d')
	# 		end_date = datetime.date(end_date, '%Y-%m-%d').date()
	# 		date_filter &= Q(date__range=(start_date, end_date))
	# 	except ValueError:
	# 		pass  # Handle invalid date format
    
	# Retrieve all staff commissions (consider filtering based on needs)
	commissions = StaffCommission.objects.all().select_related('staff', 'transaction').order_by('staff__id')

	date_filter = Q()
	if start_date and end_date:
		date_filter &= Q(date__range=(start_date, end_date))
	commissions = commissions.filter(date_filter)

	# Group commissions by staff
	commissions_by_staff = {}
	for commission in commissions:
		staff = commission.staff
		if staff not in commissions_by_staff:
			commissions_by_staff[staff] = []
		commissions_by_staff[staff].append(commission)

	# Create a PDF document
	response = HttpResponse(content_type='application/pdf')
	response['Content-Disposition'] = 'attachment; filename="staff_commissions.pdf"'

	# Create a canvas
	p = canvas.Canvas(response, pagesize=letter)
	width, height = letter

	# Set initial position and styles
	font_size = 10
	line_height = 14
	x_margin = 40
	y_position = height - 50

	for staff, commissions in commissions_by_staff.items():
		# Start a new page for each staff member
		p.setFont("Helvetica-Bold", font_size + 2)
		p.drawString(x_margin, y_position, f"Staff Name: {staff.first_name} {staff.last_name}")
		p.setFont("Helvetica", font_size)
		y_position -= 20
		p.drawString(x_margin, y_position, "-" * 100)  # Line separator
		y_position -= 20

		# Add header
		for commission in commissions:
            # Display commission details
			p.drawString(x_margin, y_position, f"Transaction ID: {commission.transaction.id}")
			p.drawString(x_margin + 150, y_position, f"Commission Amount: {commission.commission_amount}")
			p.drawString(x_margin + 300, y_position, f"Transaction Status: {commission.transaction.get_status_display()}")
			p.drawString(x_margin + 450, y_position, f"Date: {commission.date}")
			y_position -= line_height  # Adjust line spacing

            # Check if we need to move to a new page
			if y_position < 50:
				p.showPage()
				p.setFont("Helvetica", font_size)
				y_position = height - 50
		
	p.showPage()
	p.save()

	return response

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Cashier'])
def posCustomerOrder(request):
	cart = Cart(request)  # Create a Cart instance
	
	cart_products = cart.get_prods()  # Get products from cart

	products = Product.objects.all()
	
	#Get products by category
	babershop_products = Product.objects.filter(category='BABERSHOP')
	kidshair_products = Product.objects.filter(category='KIDS_HAIR')
	nail_products = Product.objects.filter(category='NAIL_ART')
	prod_products = Product.objects.filter(category='PRODUCTS')
	dreadlock_products = Product.objects.filter(category='DREADLOCKS')
	
	if request.method == 'POST':
		try: 
			product_id = int(request.POST.get('product_id'))
			product_qty = int(request.POST.get('product_qty'))
		except (ValueError, TypeError):
			return JsonResponse({'error': 'Invalid Prodcut Id'})
		
		try:
			product = get_object_or_404(Product, id=product_id)
		except Http404:
			return JsonResponse({'error': 'Product Not found'})
		
		cart.add(product=product, quantity=product_qty)
		cart_products = list(cart.cart.items())
		total_cart = cart.__len__()

	context = {
		'cart_products': cart_products,
		"products": products,
		'babershop_products':babershop_products,
		'kidshair_products':kidshair_products,
		'nail_products':nail_products,
		'prod_products':prod_products,
		'dreadlock_products':dreadlock_products,
		"appSidebarHide": 1, 
		"appHeaderHide": 1, 
		"appContentFullHeight": 1,
		"appContentClass": "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
		"total_cart": total_cart if request.method == 'POST' else 0,
	}
	return render(request, "pages/pos_customer_order.html", context)



@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Cashier'])
def transactionList(request):
	transactions = Transaction.objects.all()
	context = {
		'transactions': transactions,
	}
	return render(request, "pages/page-order.html", context)

def error404(request):
	context = {
		"appSidebarHide": 1,
		"appHeaderHide": 1,
		"appContentClass": 'p-0'
	}
	return render(request, "pages/page-error.html", context)

def handler404(request, exception = None):
	return redirect('/404/')

def generate_receipt(request, customer_id):
    orders = Transaction.objects.filter(customer_id=customer_id, status='pending')  # Filter pending transactions
    total_pay = sum(order.total_amount for order in orders)
    if len(orders) == 0:
        return redirect('DjangoHUDApp:posCustomerOrder')  # Redirect to POS page if no pending orders found
    context = {'orders': orders,'form': GenerateReceiptForm(),'total_pay': total_pay }
    
    if request.method == 'POST':
        form = GenerateReceiptForm(request.POST)
        if form.is_valid():
            with transaction.atomic():  # Wrap database operations in an atomic transaction
                receipt_number = str(uuid.uuid4())[:5].upper()  # Generate 5-character alphanumeric string
                # Create receipt object (assuming Receipt model exists)
                customer = Customer.objects.get(pk=customer_id)
                receipt = Receipt.objects.create(customer=customer,total_amount=total_pay,receipt_number=receipt_number)
                for order in orders:
                    receipt.transactions.add(order) #Add transaction to order
                    order.status = 'paid'
                    order.save()
            return render(request, 'pages/receipt.html', context)
        else:
            # Handle form validation errors (optional)
            pass

    return render(request, 'pages/receipt.html', context)

def view_receipt(request):
    receipts = Receipt.objects.all().order_by('-created_at')  # Get all receipts ordered by creation date (descending)
    context = {'receipts': receipts}
    return render (request, 'pages/receipts.html',context)

def customer_receipt(request,receipt_id):
    
    receipt = get_object_or_404(Receipt, pk=receipt_id)  # Retrieve receipt by ID (404 if not found)
    total_bill = sum(transaction.total_amount for transaction in receipt.transactions.all())
    context = {'receipt': receipt,'total_bill':total_bill}
    return render (request, 'pages/customer_receipt.html',context)

@login_required(login_url='/login/')
def search_customers(request):
    """AJAX endpoint for searching customers"""
    from django.db.models import Q
    from datetime import date
    
    query = request.GET.get('q', '').strip()
    guardian_only = request.GET.get('guardian_only', 'false').lower() == 'true'
    exclude_id = request.GET.get('exclude_id', '')
    
    if len(query) < 2:
        return JsonResponse({'customers': []})
    
    # Base queryset
    customers = Customer.objects.all()
    
    # Exclude specific customer (for edit forms)
    if exclude_id:
        try:
            exclude_id = int(exclude_id)
            customers = customers.exclude(id=exclude_id)
        except (ValueError, TypeError):
            pass
    
    # Filter for guardian search
    if guardian_only:
        customers = customers.filter(is_minor=False)
    
    # Search by name or phone
    customers = customers.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query)
    )
    
    # Limit results
    customers = customers[:10]
    
    # Prepare response data
    customer_data = []
    for customer in customers:
        age = None
        if customer.date_of_birth:
            today = date.today()
            age = today.year - customer.date_of_birth.year
            if (today.month, today.day) < (customer.date_of_birth.month, customer.date_of_birth.day):
                age -= 1
        
        customer_data.append({
            'id': customer.id,
            'name': f"{customer.first_name} {customer.last_name}",
            'phone': customer.phone,
            'email': customer.email or '',
            'type_display': customer.get_type_of_customer_display(),
            'kyc_verified': customer.kyc_verified,
            'age': age,
            'is_minor': customer.is_minor,
            'can_make_purchases': customer.can_make_purchases,
        })
    
    return JsonResponse({'customers': customer_data})

@login_required(login_url='/login/')
def debug_customer_image(request, customer_id):
    """Debug view to check customer image details"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    debug_info = {
        'customer_name': customer.name,
        'profile_image_field': str(customer.profile_image),
        'profile_image_url': customer.profile_image.url if customer.profile_image else 'No image',
        'profile_image_bool': bool(customer.profile_image),
        'profile_image_empty_check': customer.profile_image != '',
        'settings_debug': settings.DEBUG,
    }
    
    return JsonResponse(debug_info)

@login_required(login_url='/login/')
def customer_family_view(request, customer_id):
    """View to display customer family relationships"""
    from django.shortcuts import get_object_or_404
    from django.db.models import Q
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Get the main account holder (either the customer or their guardian)
    main_account = customer.account_holder
    
    # Get all family members (main account + all dependents)
    family_members = Customer.objects.filter(
        Q(id=main_account.id) | Q(guardian=main_account)
    ).select_related('guardian').order_by('is_minor', 'first_name')
    
    # Get family statistics
    total_members = family_members.count()
    adults = family_members.filter(is_minor=False).count()
    minors = family_members.filter(is_minor=True).count()
    verified_members = family_members.filter(kyc_verified=True).count()
    
    context = {
        'customer': customer,
        'main_account': main_account,
        'family_members': family_members,
        'family_stats': {
            'total_members': total_members,
            'adults': adults,
            'minors': minors,
            'verified_members': verified_members,
        }
    }
    
    return render(request, "pages/customer-family.html", context)

@login_required(login_url='/login/')
def add_dependent(request, customer_id):
    """View to add a dependent to an existing customer account"""
    from .forms import AddDependentForm
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    
    guardian = get_object_or_404(Customer, id=customer_id)
    
    # Validate that this customer can be a guardian
    if guardian.is_minor or not guardian.kyc_verified:
        messages.error(request, 'This customer cannot be a guardian. Must be an adult with verified KYC.')
        return redirect('DjangoHUDApp:customer_details', customer_id=customer_id)
    
    if request.method == 'POST':
        form = AddDependentForm(guardian, request.POST)
        if form.is_valid():
            dependent = form.save()
            messages.success(request, f'Successfully added {dependent.name} as a dependent.')
            return redirect('DjangoHUDApp:customer_details', customer_id=customer_id)
    else:
        form = AddDependentForm(guardian)
    
    context = {
        'form': form,
        'guardian': guardian,
        'existing_dependents': guardian.get_all_dependents()
    }
    
    return render(request, "pages/add-dependent.html", context)


