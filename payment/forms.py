from django import forms
from .models import *

class OrderDetailsForm(forms.ModelForm):
    commission_rate = forms.ModelChoiceField(queryset=CommissionRate.objects.all())
    class Meta:
        model = order_details
        fields = ['customer', 'is_delivery','staff', 'branch', 'notes','commission_rate']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'commission_rate': forms.Select(attrs ={'class':'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Details about the order'}),
            'is_delivery': forms.CheckboxInput(attrs={'class': 'form-switch form-check checkbox form-check-input'}),
        }