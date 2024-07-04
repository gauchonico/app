import subprocess
import uuid
from django.http import Http404, HttpResponseRedirect, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.db.models import Q
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime


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
@allowed_users(allowed_roles=['Finance','Cashier'])
def pageCustomer(request):
	# get all customers
	customers = Customer.objects.all()
	context = {
		'customers': customers,
	}
	return render(request, "pages/page-customer.html", context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance'])
def createCustomer(request):
	if request.method == 'POST':
		form = AddCustomerForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "New Customer Successfully added")
			return redirect('DjangoHUDApp:pageCustomer')
	else:
		form = AddCustomerForm()
	context = {'form': form}
		
	return render(request, "pages/create-customer.html", context)
 

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['admin','Finance','Cashier'])
def customer_details(request, customer_id):
	customer = get_object_or_404(Customer, pk=customer_id) # fetch customer by id
	transactions = Transaction.objects.filter(customer = customer)
	context = {
        'customer': customer,
		'transactions': transactions,
    }
	return render(request, "pages/customer-details.html", context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['admin'])
def editCustomer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)  # Fetch customer by ID

    if request.method == 'POST':
        form = EditCustomerForm(request.POST, instance=customer)  # Pre-populate form with existing data
        if form.is_valid():
            form.save()
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


