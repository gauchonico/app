from django import forms
from .models import *

class AddProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'category', 'description', 'image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'A Breif description about the product or service.'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder':'15000'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    def clean_name(self):
        name = self.cleaned_data['name']
        if Product.objects.filter(name=name).exists():
            raise forms.ValidationError('Product already exists')
        return name

class EditProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'category', 'description', 'image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'A Breif description about the product or service.'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder':'15000'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AddCustomerForm(forms.ModelForm):

    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'address', 'phone', 'email', 'type_of_customer', 
            'date_of_birth', 'sex', 'is_minor', 'guardian', 'relationship_to_guardian',
            'kyc_verified', 'emergency_contact', 'notes', 'profile_image'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'First Name'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Last Name'}),
            'phone': forms.TextInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Address'}),
            'email': forms.EmailInput(attrs={'class':'form-control','placeholder':'email@email.com'}),
            'type_of_customer': forms.Select(attrs={'class':'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'sex': forms.Select(attrs={'class':'form-control'}),
            'guardian': forms.Select(attrs={'class':'form-control'}),
            'relationship_to_guardian': forms.Select(attrs={'class':'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class':'form-control','placeholder':'Emergency contact number'}),
            'notes': forms.Textarea(attrs={'class':'form-control','rows':3,'placeholder':'Additional notes...'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_minor': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'kyc_verified': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter guardian choices - prioritize verified customers but allow unverified if needed
        verified_customers = Customer.objects.filter(
            kyc_verified=True,
            can_make_purchases=True,
            is_minor=False
        ).order_by('first_name', 'last_name')
        
        # If no verified customers exist, show all adult customers who can make purchases
        if verified_customers.exists():
            self.fields['guardian'].queryset = verified_customers
        else:
            # Fallback to any adult customer who can make purchases
            self.fields['guardian'].queryset = Customer.objects.filter(
                is_minor=False,
                can_make_purchases=True
            ).order_by('first_name', 'last_name')
            
            # If still no customers, show all adult customers
            if not self.fields['guardian'].queryset.exists():
                self.fields['guardian'].queryset = Customer.objects.filter(
                    is_minor=False
                ).order_by('first_name', 'last_name')
        
        self.fields['guardian'].required = False
        
        # Add help text
        self.fields['sex'].help_text = "Required for clients"
        self.fields['guardian'].help_text = "Select a parent/guardian for minors"
        self.fields['kyc_verified'].help_text = "Has this customer completed KYC verification?"
        self.fields['is_minor'].help_text = "Check if this person is under 18 years old"
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if Customer.objects.filter(email=email).exists():
            raise forms.ValidationError('Customer with this email already exists')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate client type requirements
        type_of_customer = cleaned_data.get('type_of_customer')
        sex = cleaned_data.get('sex')
        
        if type_of_customer == 'CLIENT' and not sex:
            self.add_error('sex', 'Sex is required for clients.')
        
        # Validate minor requirements
        is_minor = cleaned_data.get('is_minor')
        guardian = cleaned_data.get('guardian')
        relationship = cleaned_data.get('relationship_to_guardian')
        
        if is_minor and not guardian:
            self.add_error('guardian', 'Guardian is required for minors.')
        
        if guardian and not relationship:
            self.add_error('relationship_to_guardian', 'Relationship to guardian is required.')
        
        if guardian and relationship == 'SELF':
            self.add_error('relationship_to_guardian', 'Cannot have "Self" relationship when guardian is specified.')
        
        return cleaned_data


#Refreshment Form

        
class EditCustomerForm(forms.ModelForm):

    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'address', 'phone', 'email', 'type_of_customer', 
            'date_of_birth', 'sex', 'is_minor', 'guardian', 'relationship_to_guardian',
            'kyc_verified', 'can_make_purchases', 'emergency_contact', 'notes', 'profile_image'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'First Name'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Last Name'}),
            'phone': forms.TextInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Address'}),
            'email': forms.EmailInput(attrs={'class':'form-control','placeholder':'email@email.com'}),
            'type_of_customer': forms.Select(attrs={'class':'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'sex': forms.Select(attrs={'class':'form-control'}),
            'guardian': forms.Select(attrs={'class':'form-control'}),
            'relationship_to_guardian': forms.Select(attrs={'class':'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class':'form-control','placeholder':'Emergency contact'}),
            'notes': forms.Textarea(attrs={'class':'form-control','rows':3,'placeholder':'Additional notes...'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_minor': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'kyc_verified': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'can_make_purchases': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter guardian choices - prioritize verified customers but allow unverified if needed
        verified_customers = Customer.objects.filter(
            kyc_verified=True,
            can_make_purchases=True,
            is_minor=False
        )
        
        # Exclude self from guardian list if editing existing customer
        if self.instance and self.instance.pk:
            verified_customers = verified_customers.exclude(id=self.instance.pk)
            fallback_customers = Customer.objects.filter(
                is_minor=False,
                can_make_purchases=True
            ).exclude(id=self.instance.pk)
            all_adults = Customer.objects.filter(
                is_minor=False
            ).exclude(id=self.instance.pk)
        else:
            fallback_customers = Customer.objects.filter(
                is_minor=False,
                can_make_purchases=True
            )
            all_adults = Customer.objects.filter(
                is_minor=False
            )
        
        # Apply the same fallback logic as AddCustomerForm
        if verified_customers.exists():
            self.fields['guardian'].queryset = verified_customers.order_by('first_name', 'last_name')
        elif fallback_customers.exists():
            self.fields['guardian'].queryset = fallback_customers.order_by('first_name', 'last_name')
        else:
            self.fields['guardian'].queryset = all_adults.order_by('first_name', 'last_name')
        
        self.fields['guardian'].required = False
        
        # Add help text
        self.fields['can_make_purchases'].help_text = "Can this customer authorize purchases?"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Same validation as AddCustomerForm
        type_of_customer = cleaned_data.get('type_of_customer')
        sex = cleaned_data.get('sex')
        
        if type_of_customer == 'CLIENT' and not sex:
            self.add_error('sex', 'Sex is required for clients.')
        
        is_minor = cleaned_data.get('is_minor')
        guardian = cleaned_data.get('guardian')
        relationship = cleaned_data.get('relationship_to_guardian')
        
        if is_minor and not guardian:
            self.add_error('guardian', 'Guardian is required for minors.')
        
        if guardian and not relationship:
            self.add_error('relationship_to_guardian', 'Relationship to guardian is required.')
        
        if guardian and relationship == 'SELF':
            self.add_error('relationship_to_guardian', 'Cannot have "Self" relationship when guardian is specified.')
        
        return cleaned_data


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

class AddStaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['first_name', 'last_name','store', 'address', 'phone','specialization','nin_no']
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Jane'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Naki'}),
            'phone': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'store': forms.Select(attrs={'class':'form-control','placeholder':'Choose Branch'}),
            'specialization': forms.Select(attrs={'class':'form-control'}),
            'nin_no': forms.TextInput(attrs={'class':'form-control','placeholder':'CM960******'}),
        }

class EditStaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['first_name', 'last_name','store', 'address', 'phone','specialization','nin_no']
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Jane'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Naki'}),
            'phone': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'store': forms.Select(attrs={'class':'form-control','placeholder':'Choose Branch'}),
            'specialization': forms.Select(attrs={'class':'form-control'}),
            'nin_no': forms.TextInput(attrs={'class':'form-control','placeholder':'CM960******'}),
        }
        
class GenerateReceiptForm(forms.Form):
    confirmation = forms.BooleanField(label='Confirm Receipt Creation', required=True)