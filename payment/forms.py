from django import forms
from .models import *

class OrderDetailsForm(forms.ModelForm):
    class Meta:
        model = order_details
        fields = ['customer', 'is_delivery','staff', 'branch', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Details about the order'}),
            'is_delivery': forms.CheckboxInput(attrs={'class': 'form-switch form-check checkbox form-check-input'}),
        }