from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.db.models import Q
from django.views import generic
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from payment.models import Transaction, StaffCommission
from cart.cart import Cart
from .models import *
from django.contrib.auth.models import User
from .forms import AddCustomerForm, AddProductForm, EditCustomerForm, EditProductForm, AddStaffForm, EditStaffForm

def index(request):
	return render(request, "pages/index.html")

def login_user(request):
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		user = authenticate(request, username=username, password=password)

		if user is not None:
			login(request, user)
			messages.success(request, "User logged in")
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
def pageOrderDetails(request, transaction_id):
	# Retrieve the transaction object from the database
	transaction = get_object_or_404(Transaction, pk=transaction_id)
	context ={
		'transaction': transaction,
	}

	return render(request, "pages/page-order-details.html", context)
def editOrderDetails(request, transaction_id):
	transaction = get_object_or_404(Transaction, pk=transaction_id)

## Customer ###

@login_required(login_url='/login/')
def pageCustomer(request):
	# get all customers
	customers = Customer.objects.all()
	context = {
		'customers': customers,
	}
	return render(request, "pages/page-customer.html", context)

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
 

def customer_details(request, customer_id):
	customer = get_object_or_404(Customer, pk=customer_id) # fetch customer by id
	transactions = Transaction.objects.filter(customer = customer)
	context = {
        'customer': customer,
		'transactions': transactions,
    }
	return render(request, "pages/customer-details.html", context)

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

def pageProductDetails(request, pk):
	product = Product.objects.get(id=pk)
	context = {'product': product}

	return render(request, "pages/page-product-details.html", context)

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

def productDetails (request):
	return render(request, "pages/product_details.html")

def deleteProduct(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully!')
    return redirect('DjangoHUDApp:pageProduct')



## Staff ###
@login_required(login_url='/login/')
def staff(request):
	all_staff = Staff.objects.all()
	context = {
        'all_staff': all_staff,
    }
	return render(request, "pages/page-staff.html", context)

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

