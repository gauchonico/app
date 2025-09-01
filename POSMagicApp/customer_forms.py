from django import forms
from django.core.exceptions import ValidationError
from .models import Customer
from datetime import date, timedelta

class EnhancedCustomerForm(forms.ModelForm):
    """Enhanced customer form with support for dependents and better categorization"""
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'address', 'phone', 'email', 
            'type_of_customer', 'date_of_birth', 'sex', 'is_minor',
            'guardian', 'relationship_to_guardian', 'kyc_verified', 
            'can_make_purchases', 'emergency_contact', 'notes', 'profile_image'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0700000000'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'type_of_customer': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'guardian': forms.Select(attrs={'class': 'form-control'}),
            'relationship_to_guardian': forms.Select(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter guardian choices to only show verified customers who can make purchases
        self.fields['guardian'].queryset = Customer.objects.filter(
            kyc_verified=True,
            can_make_purchases=True,
            is_minor=False
        ).exclude(id=self.instance.id if self.instance.pk else None)
        
        # Make certain fields required based on customer type
        self.setup_conditional_requirements()
        
        # Add help text
        self.fields['guardian'].help_text = "Select a parent/guardian for minors or dependents"
        self.fields['kyc_verified'].help_text = "Has this customer completed KYC verification?"
        self.fields['sex'].help_text = "Required for client categorization"
    
    def setup_conditional_requirements(self):
        """Set up conditional field requirements"""
        # Sex is required for clients
        if self.data.get('type_of_customer') == 'CLIENT':
            self.fields['sex'].required = True
        
        # Guardian is required for minors
        if self.data.get('is_minor') == 'on' or self.data.get('is_minor') is True:
            self.fields['guardian'].required = True
            self.fields['relationship_to_guardian'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate age and minor status
        date_of_birth = cleaned_data.get('date_of_birth')
        is_minor = cleaned_data.get('is_minor')
        
        if date_of_birth:
            age = self.calculate_age(date_of_birth)
            
            # Auto-set minor status based on age
            if age < 18:
                cleaned_data['is_minor'] = True
            elif age >= 18 and is_minor:
                # Warning: person is over 18 but marked as minor
                self.add_error('is_minor', 'Person is over 18 years old but marked as minor.')
        
        # Validate guardian requirements
        guardian = cleaned_data.get('guardian')
        is_minor = cleaned_data.get('is_minor')
        relationship = cleaned_data.get('relationship_to_guardian')
        
        if is_minor and not guardian:
            self.add_error('guardian', 'Guardian is required for minors.')
        
        if guardian and relationship == 'SELF':
            self.add_error('relationship_to_guardian', 'Cannot have "Self" relationship when guardian is specified.')
        
        # Validate guardian authorization
        if guardian and not guardian.can_make_purchases:
            self.add_error('guardian', 'Selected guardian cannot make purchases.')
        
        # Client type validation
        type_of_customer = cleaned_data.get('type_of_customer')
        sex = cleaned_data.get('sex')
        
        if type_of_customer == 'CLIENT' and not sex:
            self.add_error('sex', 'Sex is required for client categorization.')
        
        return cleaned_data
    
    def calculate_age(self, birth_date):
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


class AddDependentForm(forms.ModelForm):
    """Form specifically for adding dependents to an existing customer account"""
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'sex',
            'relationship_to_guardian', 'emergency_contact', 'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Child\'s First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Child\'s Last Name'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'relationship_to_guardian': forms.Select(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes about the child...'}),
        }
    
    def __init__(self, guardian, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guardian = guardian
        
        # Pre-fill some fields
        self.fields['relationship_to_guardian'].initial = 'CHILD'
        
        # Set field requirements
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['date_of_birth'].required = True
        self.fields['sex'].required = True
        self.fields['relationship_to_guardian'].required = True
        
        # Filter relationship choices (exclude SELF and PARENT)
        relationship_choices = [
            choice for choice in Customer.RELATIONSHIP_CHOICES 
            if choice[0] not in ['SELF', 'PARENT']
        ]
        self.fields['relationship_to_guardian'].choices = relationship_choices
    
    def save(self, commit=True):
        dependent = super().save(commit=False)
        
        # Set the guardian and other dependent-specific fields
        dependent.guardian = self.guardian
        dependent.type_of_customer = 'CLIENT'  # Dependents are always clients
        dependent.is_minor = True  # Assume dependents are minors
        dependent.kyc_verified = False  # Dependents don't have KYC
        dependent.can_make_purchases = False  # Dependents can't make purchases
        
        # Inherit some fields from guardian
        dependent.address = self.guardian.address
        dependent.phone = self.guardian.phone  # Use guardian's phone
        dependent.email = self.guardian.email  # Use guardian's email
        
        if commit:
            dependent.save()
        
        return dependent


class CustomerSearchForm(forms.Form):
    """Form for searching customers with various criteria"""
    
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, phone, or email...'
        })
    )
    
    customer_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Customer.TYPE_OF_CUSTOMER),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    has_dependents = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('yes', 'Has Dependents'),
            ('no', 'No Dependents'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    kyc_status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('verified', 'KYC Verified'),
            ('pending', 'KYC Pending'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
