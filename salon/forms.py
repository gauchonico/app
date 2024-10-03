from django import forms

from production.models import LivaraMainStore 
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


class SalonRestockRequestForm(forms.ModelForm):
    class Meta:
        model = SalonRestockRequest
        fields = ['comments']
        widgets = {
            'comments': forms.TextInput(attrs={'class':'form-control'}),
            'salon': forms.Select(attrs={'class':'form-control'}),

        }
    def clean_salon(self):
        cleaned_salon = self.cleaned_data['salon']
        user = self.context['request'].user
        # Check if user has a salon branch
        if user.salon_branch:
            if cleaned_salon != user.salon_branch:
                raise forms.ValidationError(
                    "You can only create requests for your assigned branch."
                )
        else:
            raise forms.ValidationError(
                "User does not have an assigned salon branch."
            )
        return cleaned_salon
class SalonRestockRequestItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=LivaraMainStore.objects.all())

    class Meta:
        model = SalonRestockRequestItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
        }

SalonRestockRequestItemFormset = forms.inlineformset_factory(
    SalonRestockRequest, 
    SalonRestockRequestItem, 
    form=SalonRestockRequestItemForm, 
    extra=1, 
    can_delete=True
)