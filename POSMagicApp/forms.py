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
        fields = ['first_name', 'last_name', 'address', 'phone', 'email','type_of_customer','date_of_birth','profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Jane'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Naki'}),
            'phone': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Ntinda'}),
            'email': forms.TextInput(attrs={'class':'form-control','placeholder':'email@email.com'}),
            'type_of_customer': forms.Select(attrs={'class':'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class':'form-control','placeholder':'1990-01-01'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    def email(self):
        email = self.cleaned_data['email']
        if Customer.objects.filter(email=email).exists():
            raise forms.ValidationError('Customer already exists')
        
class EditCustomerForm(forms.ModelForm):

    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'address', 'phone', 'email','type_of_customer','date_of_birth']
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Jane'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Naki'}),
            'phone': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Ntinda'}),
            'email': forms.TextInput(attrs={'class':'form-control','placeholder':'email@email.com'}),
            'type_of_customer': forms.Select(attrs={'class':'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class':'form-control','placeholder':'1990-01-01'}),
        }

class AddStaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['first_name', 'last_name','branch', 'address', 'phone','specialization','nin_no']
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Jane'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Naki'}),
            'phone': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'branch': forms.Select(attrs={'class':'form-control','placeholder':'Choose Branch'}),
            'specialization': forms.Select(attrs={'class':'form-control'}),
            'nin_no': forms.TextInput(attrs={'class':'form-control','placeholder':'CM960******'}),
        }

class EditStaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['first_name', 'last_name','branch', 'address', 'phone','specialization','nin_no']
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Jane'}),
            'last_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Naki'}),
            'phone': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'branch': forms.Select(attrs={'class':'form-control','placeholder':'Choose Branch'}),
            'specialization': forms.Select(attrs={'class':'form-control'}),
            'nin_no': forms.TextInput(attrs={'class':'form-control','placeholder':'CM960******'}),
        }