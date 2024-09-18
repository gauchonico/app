from django import forms 
from .models import *
from django.forms import formset_factory

class SalonProductForm(forms.ModelForm):
    class Meta:
        model = SalonProduct
        fields = ['name', 'supplier', 'description', 'price', 'commission_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'commission_rate': forms.Select(choices=SalonProduct.COMMISSION_CHOICES, attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            }
        
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'commission_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'commission_rate': forms.Select(choices=Service.COMMISSION_CHOICES, attrs={'class': 'form-control'}),
    
        }

class GeneralRequisitionForm(forms.ModelForm):
    class Meta:
        model = GeneralRequisition
        fields = ['branch', 'supplier']
        widgets ={
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
        }

class GeneralRequisitionItemForm(forms.ModelForm):
    class Meta:
        model = GeneralRequisitionItem
        fields = ['product', 'quantity','price']
        widgets ={
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control','placeholder': 'Price per Unit'}),
        }
        
GeneralRequisitionItemFormSet = formset_factory(GeneralRequisitionItemForm, extra=1)