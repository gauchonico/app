from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Appointment, AppointmentFeedback
from production.models import Store, ServiceName, StoreService
from POSMagicApp.models import Customer, Staff


class AppointmentBookingForm(forms.ModelForm):
    """
    Form for customers to book appointments
    """
    # Custom fields for better UX
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': timezone.now().date().strftime('%Y-%m-%d')
        }),
        help_text="Select your preferred date"
    )
    
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control timepicker',
            'type': 'time'
        }),
        help_text="Select your preferred time"
    )
    
    services = forms.ModelMultipleChoiceField(
        queryset=ServiceName.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Select one or more services you need"
    )
    
    class Meta:
        model = Appointment
        fields = [
            'store', 'services', 'appointment_date', 'appointment_time',
            'customer_name', 'customer_phone', 'customer_email',
            'special_requests', 'duration_minutes', 'out_of_salon_address'
        ]
        widgets = {
            'store': forms.Select(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'special_requests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any special requests or notes...'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '30',
                'max': '480',
                'step': '30'
            }),
            'out_of_salon_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter the address where you would like the service...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make store field not required since it can be null for out-of-salon appointments
        self.fields['store'].required = False
        
        # Filter stores and add "Out of Salon" option
        store_choices = list(Store.objects.all().values_list('id', 'name'))
        store_choices.insert(0, ('out_of_salon', 'Out of Salon'))
        
        self.fields['store'].widget = forms.Select(attrs={'class': 'form-control'})
        self.fields['store'].choices = store_choices
        
        # Pre-populate customer info if user is logged in
        if user and hasattr(user, 'customer'):
            customer = user.customer
            self.fields['customer_name'].initial = f"{customer.first_name} {customer.last_name}"
            self.fields['customer_phone'].initial = customer.phone
            self.fields['customer_email'].initial = customer.email
    
    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date and date < timezone.now().date():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        return date
    
    def clean_appointment_time(self):
        time = self.cleaned_data.get('appointment_time')
        date = self.cleaned_data.get('appointment_date')
        
        if date and time:
            # Create timezone-aware datetime for comparison
            appointment_datetime = timezone.make_aware(datetime.combine(date, time))
            if appointment_datetime < timezone.now():
                raise forms.ValidationError("Appointment time cannot be in the past.")
            
            # Check if it's within business hours (9 AM to 6 PM)
            if time.hour < 9 or time.hour >= 18:
                raise forms.ValidationError("Appointments can only be booked between 9:00 AM and 6:00 PM.")
        
        return time
    
    def clean(self):
        cleaned_data = super().clean()
        services = cleaned_data.get('services')
        store = cleaned_data.get('store')
        out_of_salon_address = cleaned_data.get('out_of_salon_address')
        
        # Handle out-of-salon appointments
        if store == 'out_of_salon' or (isinstance(store, str) and store == 'out_of_salon'):
            if not out_of_salon_address:
                raise forms.ValidationError("Address is required for out-of-salon appointments.")
            cleaned_data['is_out_of_salon'] = True
            cleaned_data['store'] = None
        else:
            # Regular in-salon appointment
            cleaned_data['is_out_of_salon'] = False
            
            # Store is required for in-salon appointments
            if not store:
                raise forms.ValidationError("Please select a store or choose 'Out of Salon'.")
            
            # Check if all selected services are available at the selected store
            if services and store:
                try:
                    # Handle both Store object and ID
                    if isinstance(store, Store):
                        store_obj = store
                    else:
                        store_obj = Store.objects.get(id=store)
                    
                    available_services = store_obj.store_services.values_list('service', flat=True)
                    unavailable_services = services.exclude(id__in=available_services)
                    
                    if unavailable_services.exists():
                        service_names = [service.name for service in unavailable_services]
                        raise forms.ValidationError(
                            f"The following services are not available at {store_obj.name}: {', '.join(service_names)}"
                        )
                except Store.DoesNotExist:
                    raise forms.ValidationError("Selected store does not exist.")
        
        return cleaned_data


class AppointmentUpdateForm(forms.ModelForm):
    """
    Form for staff to update appointment details
    """
    class Meta:
        model = Appointment
        fields = [
            'status', 'assigned_staff', 'appointment_date', 'appointment_time',
            'duration_minutes', 'special_requests', 'estimated_cost', 'deposit_amount'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'assigned_staff': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
        }
    
    def __init__(self, *args, **kwargs):
        store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        
        # Filter staff to only those from the appointment's store
        if store:
            self.fields['assigned_staff'].queryset = Staff.objects.filter(store=store)
        elif self.instance and self.instance.store:
            self.fields['assigned_staff'].queryset = Staff.objects.filter(store=self.instance.store)


class AppointmentSearchForm(forms.Form):
    """
    Form for searching and filtering appointments
    """
    STATUS_CHOICES = [('', 'All Statuses')] + Appointment.STATUS_CHOICES
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by customer name, phone, or appointment ID...'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    store = forms.ModelChoiceField(
        queryset=Store.objects.all(),
        required=False,
        empty_label="All Stores",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class AppointmentFeedbackForm(forms.ModelForm):
    """
    Form for customers to submit feedback after appointments
    """
    class Meta:
        model = AppointmentFeedback
        fields = [
            'rating', 'service_quality', 'staff_friendliness', 
            'cleanliness', 'value_for_money', 'comments', 'would_recommend'
        ]
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'service_quality': forms.Select(attrs={'class': 'form-control'}),
            'staff_friendliness': forms.Select(attrs={'class': 'form-control'}),
            'cleanliness': forms.Select(attrs={'class': 'form-control'}),
            'value_for_money': forms.Select(attrs={'class': 'form-control'}),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about your experience...'
            }),
            'would_recommend': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to all rating fields
        for field_name in ['rating', 'service_quality', 'staff_friendliness', 'cleanliness', 'value_for_money']:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})


# Customer Authentication Forms
class CustomerLoginForm(forms.Form):
    """
    Customer login form
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class CustomerRegistrationForm(forms.Form):
    """
    Customer registration form
    """
    # User account fields
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        }),
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        }),
        help_text="Your password must contain at least 8 characters."
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        help_text="Enter the same password as before, for verification."
    )
    
    # Customer profile fields
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    phone = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    address = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address'
        })
    )
    sex = forms.ChoiceField(
        choices=Customer.SEX_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        
        if len(password1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        return password2
