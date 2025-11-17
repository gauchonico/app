from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views import View
from POSMagicApp.models import Customer
from .forms import CustomerRegistrationForm, CustomerLoginForm


class CustomerLoginView(View):
    """
    Customer login view
    """
    template_name = 'appointments/auth/customer_login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('customer_dashboard')
        
        form = CustomerLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Check if user has a customer profile
                try:
                    customer = user.customer
                    login(request, user)
                    messages.success(request, f'Welcome back, {customer.first_name}!')
                    return redirect('customer_dashboard')
                except Customer.DoesNotExist:
                    messages.error(request, 'No customer profile found. Please contact support.')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return render(request, self.template_name, {'form': form})


class CustomerRegistrationView(View):
    """
    Customer registration view
    """
    template_name = 'appointments/auth/customer_register.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('customer_dashboard')
        
        form = CustomerRegistrationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            # Create Django User
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            
            # Add user to "Customers" group (create if doesn't exist)
            customers_group, created = Group.objects.get_or_create(name='Customers')
            user.groups.add(customers_group)
            
            # Create Customer profile
            customer = Customer.objects.create(
                user=user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                type_of_customer='CLIENT',
                sex=form.cleaned_data.get('sex'),
                date_of_birth=form.cleaned_data.get('date_of_birth'),
                can_make_purchases=True
            )
            
            # Auto-login the user
            login(request, user)
            messages.success(request, f'Welcome to our salon, {customer.first_name}! Your account has been created successfully.')
            return redirect('customer_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return render(request, self.template_name, {'form': form})


@login_required
def customer_profile(request):
    """
    Customer profile view
    """
    try:
        customer = request.user.customer
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('customer_logout')
    
    context = {
        'customer': customer,
        'appSidebarHide': 1,
        'appHeaderHide': 1,
        'appContentFullHeight': 1,
        'appContentClass': "p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
    }
    
    return render(request, 'appointments/auth/customer_profile.html', context)


@login_required
def customer_logout(request):
    """
    Customer logout view
    """
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('customer_login')
