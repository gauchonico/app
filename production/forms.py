from django import forms

from POSMagicApp.models import Customer, Staff
from accounts.models import ChartOfAccounts
from .models import *
from django.forms import BaseModelFormSet, ModelForm, ValidationError, inlineformset_factory, modelformset_factory
import os
import csv


class AddSupplierForm(forms.ModelForm):
    raw_material = forms.ChoiceField(choices=[(rm.pk, rm.name) for rm in RawMaterial.objects.all()], required=False)
    class Meta:
        model = Supplier
        fields = [
            'name', 'company_name', 'address', 'contact_number', 'email',
            'quality_rating', 'payment_terms', 'credit_limit', 'is_active',
            'reliability_score', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control','placeholder':'John'}),
            'company_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Tusuubila Ltd.'}),
            'contact_number': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Mbarara'}),
            'email': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'raw_material': forms.Select(attrs={'class':'form-control'}),
            'quality_rating': forms.Select(attrs={'class':'form-select'}),
            'payment_terms': forms.Select(attrs={'class':'form-select'}),
            'credit_limit': forms.NumberInput(attrs={'class':'form-control','placeholder':'0.00'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'reliability_score': forms.NumberInput(attrs={'class':'form-control','min':'0','max':'10','step':'0.1','placeholder':'5.0'}),
            'notes': forms.Textarea(attrs={'class':'form-control','rows':'3','placeholder':'Additional notes about the supplier...'}),
        }

class BulkUploadForm(forms.Form):
    file = forms.FileField()

class EditSupplierForm(forms.ModelForm):
    raw_material = forms.ChoiceField(choices=[(rm.pk, rm.name) for rm in RawMaterial.objects.all()], required=False)
    class Meta:
        model = Supplier
        fields = [
            'name', 'company_name', 'address', 'contact_number', 'email',
            'quality_rating', 'payment_terms', 'credit_limit', 'is_active',
            'reliability_score', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control','placeholder':'John'}),
            'company_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Tusuubila Ltd.'}),
            'contact_number': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Mbarara'}),
            'email': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'raw_material': forms.Select(attrs={'class':'form-control'}),
            'quality_rating': forms.Select(attrs={'class':'form-select'}),
            'payment_terms': forms.Select(attrs={'class':'form-select'}),
            'credit_limit': forms.NumberInput(attrs={'class':'form-control','placeholder':'0.00'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'reliability_score': forms.NumberInput(attrs={'class':'form-control','min':'0','max':'10','step':'0.1','placeholder':'5.0'}),
            'notes': forms.Textarea(attrs={'class':'form-control','rows':'3','placeholder':'Additional notes about the supplier...'}),
        }

class AddRawmaterialForm(forms.ModelForm):
    class Meta:
        model = RawMaterial
        fields = ['name', 'suppliers', 'quantity', 'reorder_point','unit_measurement']
        widgets ={
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'e.g. Shea Butter, Bottle Tops'}),
            'suppliers': forms.SelectMultiple(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class':'form-control'}),
            'unit_measurement': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Kilograms | Pieces | Liters| Units Write units in full format'}),
            
        }
        
    def clean_suppliers(self):
        suppliers = self.cleaned_data['suppliers']
        if not suppliers:
            raise forms.ValidationError('Please select at least one supplier.')
        return suppliers
        
class RawMaterialQuantityForm(forms.ModelForm):
    new_quantity = forms.DecimalField(label="New Quantity",max_digits=11, decimal_places=5)

    class Meta:
        model = RawMaterial
        fields = ['new_quantity']
        widgets ={
            'new_quantity': forms.NumberInput(attrs={'class':'form-control'}),
        }

    def clean_new_quantity(self):
        new_quantity = self.cleaned_data.get('new_quantity')
        if new_quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return new_quantity
    
class ReorderPointForm(forms.ModelForm):
    class Meta:
        model = RawMaterial
        fields = ['reorder_point']

class RawMaterialPriceForm(forms.ModelForm):
    class Meta:
        model = RawMaterialPrice
        fields = ['raw_material', 'supplier', 'price', 'effective_date']
        widgets = {
            'effective_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-select'
            }),
            'raw_material': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Select a raw material...'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Select a supplier...',
                'disabled': True
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01', 
                'min': '0.01'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make supplier field not required initially
        self.fields['supplier'].required = False

class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ['threshold_price', 'is_above']
        widgets = {
            'threshold_price': forms.NumberInput(attrs={'step': '0.01'}),
        }

class BulkUploadRawMaterialForm(forms.Form):
    file = forms.FileField()
class CreatePurchaseOrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'raw_material' in self.initial:
            raw = self.initial['raw_material']
            # Find all raw materials supplied by the chosen supplier
            
            self.fields['supplier'].queryset = Supplier.objects.filter(raw_materials=raw)
        # Filter supplier queryset if a raw material is preselected

    class Meta:
        model = PurchaseOrder
        fields = ['supplier','raw_material','quantity','fullfilled_qty','unit_price','total_cost','order_number','status']
        widgets ={
            'supplier': forms.Select(attrs={'class':'form-control'}),
            'raw_material': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'fullfilled_qty': forms.NumberInput(attrs={'class':'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class':'form-control'}),
            'total_cost': forms.NumberInput(attrs={'class':'form-control'}),
            'order_number': forms.TextInput(attrs={'class':'form-control'}),
            'status': forms.Select(attrs={'class':'form-control'}),
        }

class StoreAlertForm(forms.ModelForm):
    class Meta:
        model = StoreAlerts
        fields = ['handled','handled_at']
        widgets = {
            'handled': forms.CheckboxInput(),  # Render handled field as a checkbox
            'handled_at': forms.DateInput(), # Render as date input field
        }
class ProductionForm(forms.ModelForm):
    class Meta:
        model = Production
        fields = ['product_name', 'total_volume','unit_of_measure','price','wholesale_price']
        widgets = {
            'product_name': forms.TextInput(attrs={'class':'form-control'}),
            'total_volume': forms.NumberInput(attrs={'class':'form-control','placeholder':'unit volume'}),
            'unit_of_measure': forms.Select(attrs={'class':'form-control','placeholder':'unit of measure'}),
            'price': forms.NumberInput(attrs={'class':'form-control','placeholder':'Proposed price for Product'}),  # Render as number input field
            'wholesale_price': forms.NumberInput(attrs={'class':'form-control','placeholder':'Wholesale price for Product'}),  # Render as number input field
        }
        labels = {
            'total_volume':'Unit Volume',
        }

ProductionIngredientFormSet = inlineformset_factory(
    Production,
    ProductionIngredient,
    fields=['raw_material', 'quantity_per_unit_product_volume'],
    extra=1,  # Number of extra forms
    can_delete=True,  # Allow deleting ingredients
    widgets= {
        'raw_material': forms.Select(attrs={'class': 'form-control, form-select'}),
        'quantity_per_unit_product_volume': forms.NumberInput(attrs={'class': 'form-control', 'placeholder':'0'}),
    }
)

##Form to csv upload for product pricing
class PriceGroupCSVForm(forms.Form):
    price_group = forms.ModelChoiceField(queryset=PriceGroup.objects.all(), label="Select Price Group")
    file = forms.FileField(label="Upload CSV")

class ApprovePurchaseForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['status','supplier','raw_material','quantity','unit_price','total_cost','order_number']  # Only include the 'status' field
        widgets = {
        'status': forms.Select(attrs={'class':'form-control','disabled': False}),
        'supplier': forms.TextInput(attrs={'class':'form-control','disabled': True}),
        'raw_material': forms.TextInput(attrs={'class':'form-control','disabled': True}),
        'quantity': forms.NumberInput(attrs={'class':'form-control','disabled': True}),
        'unit_price': forms.NumberInput(attrs={'class':'form-control','disabled': True}),
        'total_cost': forms.NumberInput(attrs={'class':'form-control','disabled': True}),
        'order_number': forms.TextInput(attrs={'class':'form-control','disabled': True}),
        
        }

    def clean_status(self):
        data = self.cleaned_data['status']
        if data != 'Approved':
            raise forms.ValidationError('Order status can only be set to "Approved" on this page.')
        return data


class ProductionIngredientForm(forms.ModelForm):
    class Meta:
        model = ProductionIngredient
        fields = ['raw_material', 'quantity_per_unit_product_volume']
        widgets = {
        'raw_material': forms.Select(attrs={'class': 'form-control'}),
        'quantity_per_unit_product_volume': forms.NumberInput(attrs={'class': 'form-control', 'placeholder':'0'}),
        }

class ManufactureProductForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, label="Quantity to Manufacture", widget=forms.NumberInput(attrs={'class': 'form-control','placeholder': 'e.g. 3'}))
    notes = forms.CharField(required=False, label="Manufacturing Notes", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    expiry_date = forms.DateField(required=True, label="Expiry Date", widget=forms.TextInput(attrs={'type':'date','class': 'form-control'}))
    production_order = forms.ModelChoiceField(queryset=ProductionOrder.objects.none(), required=False, label="Production Order", widget=forms.Select(attrs={'class': 'form-control'}))
    
    # Quality Control Fields
    qc_required = forms.BooleanField(
        required=False, 
        initial=True,
        label="Quality Control Required", 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    qc_sample_quantity = forms.IntegerField(
        min_value=0, 
        initial=1,
        label="Sample Bottles for QC", 
        widget=forms.NumberInput(attrs={'class': 'form-control','placeholder': 'e.g. 2'}),
        help_text="Number of sample bottles to allocate for quality control testing"
    )
    auto_create_qc_test = forms.BooleanField(
        required=False, 
        initial=True,
        label="Auto-create QC Test", 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Automatically create quality control test after manufacturing"
    )
    
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if product:
            # Show only in-progress production orders for this product
            self.fields['production_order'].queryset = ProductionOrder.objects.filter(
                product=product, 
                status='In Progress'
            ).order_by('-created_at')
            
    def clean(self):
        cleaned_data = super().clean()
        production_order = cleaned_data.get('production_order')
        quantity = cleaned_data.get('quantity')
        qc_required = cleaned_data.get('qc_required')
        qc_sample_quantity = cleaned_data.get('qc_sample_quantity')
        
        # If production order is selected, ensure quantity matches approved quantity
        if production_order and quantity:
            if quantity != production_order.approved_quantity:
                raise forms.ValidationError(f"Quantity must match the approved quantity ({production_order.approved_quantity}) for this production order.")
        
        # Validate QC sample quantity
        if qc_required and qc_sample_quantity > quantity:
            raise forms.ValidationError("Sample quantity for QC cannot exceed total manufacturing quantity.")
            
        if qc_required and qc_sample_quantity <= 0:
            raise forms.ValidationError("Sample quantity must be greater than 0 when QC is required.")
        
        return cleaned_data

class WriteOffForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, label="Quantity to Write Off", widget=forms.NumberInput(attrs={'class': 'form-control','placeholder': 'e.g. 3'}))
    reason = forms.CharField(required=True, label="Reason for Write Off", widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'e.g. Expired'}))


################### Quality Control Forms ###################

class QualityControlTestForm(forms.ModelForm):
    class Meta:
        model = QualityControlTest
        fields = [
            'test_name', 'sample_quantity', 'scheduled_test_date', 
            'assigned_tester', 'priority', 'testing_notes'
        ]
        widgets = {
            'test_name': forms.TextInput(attrs={'class': 'form-control'}),
            'sample_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'scheduled_test_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'assigned_tester': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'testing_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter assigned_tester to show only active users
        from django.contrib.auth.models import User
        self.fields['assigned_tester'].queryset = User.objects.filter(is_active=True)


class QualityTestParameterForm(forms.ModelForm):
    class Meta:
        model = QualityTestParameter
        fields = [
            'parameter_name', 'parameter_type', 'measurement_unit',
            'target_value', 'min_acceptable', 'max_acceptable',
            'measured_value', 'result_status', 'test_method', 'notes'
        ]
        widgets = {
            'parameter_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parameter_type': forms.Select(attrs={'class': 'form-control'}),
            'measurement_unit': forms.Select(attrs={'class': 'form-control'}),
            'target_value': forms.TextInput(attrs={'class': 'form-control'}),
            'min_acceptable': forms.TextInput(attrs={'class': 'form-control'}),
            'max_acceptable': forms.TextInput(attrs={'class': 'form-control'}),
            'measured_value': forms.TextInput(attrs={'class': 'form-control'}),
            'result_status': forms.Select(attrs={'class': 'form-control'}),
            'test_method': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class QualityControlActionForm(forms.ModelForm):
    class Meta:
        model = QualityControlAction
        fields = [
            'action_type', 'action_reason', 'quantity_affected',
            'follow_up_required', 'follow_up_date', 'follow_up_notes'
        ]
        widgets = {
            'action_type': forms.Select(attrs={'class': 'form-control'}),
            'action_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'quantity_affected': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'follow_up_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'follow_up_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class QualityTestResultForm(forms.ModelForm):
    """Form for updating quality test results"""
    class Meta:
        model = QualityControlTest
        fields = [
            'status', 'overall_result', 'pass_percentage', 'actual_test_date',
            'testing_duration_hours', 'testing_notes', 'failure_reasons', 
            'recommendations'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'overall_result': forms.Select(attrs={'class': 'form-control'}),
            'pass_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'actual_test_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'testing_duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.25'}),
            'testing_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'failure_reasons': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set actual_test_date to now if not set
        if not self.instance.actual_test_date:
            from django.utils import timezone
            self.fields['actual_test_date'].initial = timezone.now()


# Formset for managing multiple test parameters
QualityTestParameterFormSet = forms.inlineformset_factory(
    QualityControlTest,
    QualityTestParameter,
    form=QualityTestParameterForm,
    extra=3,
    can_delete=True,
    fields=['parameter_name', 'parameter_type', 'measurement_unit', 'target_value', 'min_acceptable', 'max_acceptable']
)
    

#######################################################

class StoreTransferForm(forms.ModelForm):
    class Meta:
        model = StoreTransfer
        fields = ['notes', 'delivery_document']
        widgets = {
            'delivery_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls',
                'help_text': 'Upload delivery note, invoice, or any supporting document'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Notes about the Transfer',
                'rows': 4
            }),
        }
    
    def clean_delivery_document(self):
        document = self.cleaned_data.get('delivery_document')
        if document:
            # Check file size (max 10MB)
            if document.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB.")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.xlsx', '.xls']
            file_extension = os.path.splitext(document.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
                )
        
        return document

class StoreTransferItemForm(forms.ModelForm):
    class Meta:
        model = StoreTransferItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control',
                'data-live-search': 'true'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Enter quantity'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to only show products with available inventory
        self.fields['product'].queryset = ManufacturedProductInventory.objects.filter(
            quantity__gt=0
        ).select_related('product').order_by('product__product_name')
        
        # Add custom labels
        self.fields['product'].label = "Product"
        self.fields['quantity'].label = "Transfer Quantity"
        
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        product = self.cleaned_data.get('product')
        
        if quantity and product:
            if quantity <= 0:
                raise forms.ValidationError("Quantity must be greater than 0.")
            
            if quantity > product.quantity:
                raise forms.ValidationError(
                    f"Transfer quantity ({quantity}) cannot exceed available inventory ({product.quantity})"
                )
        
        return quantity

class StoreTransferItemFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = StoreTransferItem.objects.none()
    
    def clean(self):
        super().clean()
        
        # Check if at least one item is provided
        if not any(form.cleaned_data and not form.cleaned_data.get('DELETE', False) 
                  for form in self.forms):
            raise forms.ValidationError("At least one item must be added to the transfer.")
        
        # Check for duplicate products
        products = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                product = form.cleaned_data.get('product')
                if product in products:
                    raise forms.ValidationError(f"Product '{product}' is already in the transfer.")
                products.append(product)

# Create formset factory
StoreTransferItemFormSet = forms.modelformset_factory(
    StoreTransferItem,
    form=StoreTransferItemForm,
    formset=StoreTransferItemFormSet,
    extra=1,
    can_delete=True
)
        
class TransferApprovalForm(forms.ModelForm):
    class Meta:
        model = RestockRequest
        fields = ['status']  # You might want to include other fields as needed

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for item in self.instance.items.all():
            initial_value = item.approved_quantity or 0  # Use 0 as default if no approved_quantity exists
            self.fields[f'approve_quantity_for{item.product.product.product}'] = forms.IntegerField(initial=initial_value, required=True)
        
class LivaraMainStoreDeliveredQuantityForm(forms.ModelForm):
    class Meta:
        model = StoreTransferItem
        fields = ['delivered_quantity']  # Only include delivered quantity
        widgets ={
            'delivered_quantity': forms.NumberInput(attrs={'class':'form-control', 'placeholder':'e.g. 3'}),
        }
        
        
#######################################################

class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control'}),
            'location': forms.TextInput(attrs={'class':'form-control'}),
        }

class RestockRequestForm(forms.ModelForm):
    class Meta:
        model = RestockRequest
        fields = ['store', 'comments']
        widgets = {
            'comments': forms.TextInput(attrs={'class':'form-control'}),
            'store': forms.Select(attrs={'class':'form-control'}),

        }
class RestockRequestItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=LivaraMainStore.objects.all())

    class Meta:
        model = RestockRequestItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
        }

RestockRequestItemFormset = forms.inlineformset_factory(
    RestockRequest, 
    RestockRequestItem, 
    form=RestockRequestItemForm, 
    extra=1, 
    can_delete=True
)

class RestockApprovalItemForm(forms.ModelForm):
    class Meta:
        model = RestockRequestItem
        fields = ['product','quantity','approved_quantity']  # You might want to include other fields as needed
        widgets ={
            'product': forms.Select(attrs={'readonly': 'readonly'}),
            'quantity': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'approved_quantity': forms.NumberInput(attrs={'class':'form-control'}),
        }
        
class DeliveryRestockRequestForm(forms.ModelForm):
    class Meta:
        model = RestockRequestItem
        fields = ('product','quantity','approved_quantity','delivered_quantity',)
        widgets = {
            'product': forms.Select(attrs={'readonly': 'readonly'}),
            'quantity': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'approved_quantity': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'delivered_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    


class ProductionOrderForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = ['product','quantity','notes','target_completion_date']
        widgets = {
            'product': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'notes': forms.Textarea(attrs={
                'class':'form-control',
                'rows': 2,  # Reduce number of rows
                'style': 'resize:none;'  # Prevent manual resizing
            }),
            'target_completion_date': forms.DateInput(attrs={'type':'date','class':'form-control'}),
        }
class BaseProductionOrderFormSet(BaseModelFormSet):
    def clean(self):
        """Checks if any products are selected multiple times"""
        super().clean()
        products = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                product = form.cleaned_data.get('product')
                if product in products:
                    raise forms.ValidationError("Each product can only be ordered once per submission.")
                products.append(product)

# Create the formset
ProductionOrderFormSet = modelformset_factory(
    ProductionOrder,
    form=ProductionOrderForm,
    formset=BaseProductionOrderFormSet,
    extra=1,
    can_delete=True
)
    
class SaleOrderForm(forms.ModelForm):
    class Meta:
        model = StoreSale
        fields = ['customer', 'withhold_tax']

    sale_items = forms.inlineformset_factory(
        parent_model=StoreSale,
        model=SaleItem,
        fk_name='sale',
        fields=['product', 'quantity', 'chosen_price'],
        extra=1,  # Add one empty form initially
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sale_items = self.sale_items(self.instance)  # Initialize formset with instance

    def save(self, commit=True):
        instance = super().save(commit=commit)
        self.sale_items.save(commit=commit)
        return instance
    

    

######## Form for creating store sale #################################
class TestForm(forms.ModelForm):
    total_items = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = StoreSale
        fields = ['customer', 'tax_code', 'description', 'billing_address', 'withhold_tax']
        widgets = {
            'customer': forms.Select(attrs={'class':'form-control'}),
            'tax_code': forms.Select(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control', 'rows': 3, 'placeholder': 'Sale description or special notes...'}),
            'billing_address': forms.Textarea(attrs={'class':'form-control', 'rows': 3, 'placeholder': 'Customer billing address...'}),
            'withhold_tax': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super(TestForm, self).__init__(*args, **kwargs)
        if self.instance.pk:  # Check if the instance already exists
            self.fields['total_items'].initial = self.instance.saleitem_set.count()
        
        # Auto-populate billing address when customer is selected
        if self.instance.pk and self.instance.customer and not self.instance.billing_address:
            customer = self.instance.customer
            self.fields['billing_address'].initial = f"{customer.address}\nPhone: {customer.phone}\nEmail: {customer.email}"
        
    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        # Auto-populate billing address from customer if not provided
        if not instance.billing_address and instance.customer:
            customer = instance.customer
            instance.billing_address = f"{customer.address}\nPhone: {customer.phone}\nEmail: {customer.email}"
            if commit:
                instance.save()
        
        return instance
    
##Form to select store in salons store inventory adjustment view
class StoreSelectionForm(forms.Form):
    store = forms.ModelChoiceField(
        queryset=Store.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,  # Optional if you want to show all stores when none is selected
        label="Select Store"
    )
        
class TestItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=LivaraMainStore.objects.filter(quantity__gt=0),
        required=False,  # Make it not required for empty forms
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    price_group = forms.ModelChoiceField(
        queryset=PriceGroup.objects.filter(is_active=True),  # Filter only active pricing groups
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    chosen_price = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}), required=False)
    
    class Meta:
        model = SaleItem
        fields = '__all__'
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Units Ordered'}),
            'price_group': forms.Select(attrs={'class': 'form-control'}),
            'chosen_price': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make quantity not required for empty forms
        self.fields['quantity'].required = False
        
    def clean(self):
        """Update the chosen_price based on the selected pricing group."""
        cleaned_data = super().clean()
        product_instance = cleaned_data.get('product')
        price_group = cleaned_data.get('price_group')
        quantity = cleaned_data.get('quantity')

        # If this is an empty form (no product or quantity), skip validation
        if not product_instance or not quantity:
            return cleaned_data

        # Validate that both product and quantity are provided
        if product_instance and not quantity:
            self.add_error('quantity', 'Quantity is required when a product is selected.')
            return cleaned_data
        
        if quantity and not product_instance:
            self.add_error('product', 'Product is required when quantity is provided.')
            return cleaned_data

        if product_instance:
            # Navigate relationships to get the Product instance
            production_instance = product_instance.product.product

            if price_group:
                # Fetch the price from the selected price group
                product_price = ProductPrice.objects.filter(
                    product=production_instance, price_group=price_group
                ).first()
                if product_price:
                    cleaned_data['chosen_price'] = product_price.price
                else:
                    self.add_error('price_group', f"No price configured for {production_instance.product_name} in the selected price group '{price_group.name}'. Please contact Finance to set up pricing.")
            else:
                # No price group selected - this is now an error
                self.add_error('price_group', f"Price group is required for {production_instance.product_name}. Please select a pricing group.")

        return cleaned_data

    def save(self, commit=False):
        """Save the chosen price and total price."""
        instance = super().save(commit=False)
        product_instance = instance.product  # This is a LivaraMainStore instance

        if product_instance:
            # Navigate relationships to get the Product instance
            production_instance = product_instance.product.product

            if instance.price_group:
                product_price = ProductPrice.objects.filter(
                    product=production_instance, price_group=instance.price_group
                ).first()
                if product_price:
                    instance.chosen_price = product_price.price
                else:
                    # No price configured in the selected group - this should be handled by form validation
                    raise ValueError(f"No price configured for {production_instance.product_name} in price group '{instance.price_group.name}'")
            else:
                # No price group selected - this should be handled by form validation
                raise ValueError(f"Price group is required for {production_instance.product_name}")

            # Calculate the total price
            instance.total_price = instance.quantity * instance.chosen_price

        if commit:
            instance.save()
        return instance

        
TestItemFormset = inlineformset_factory(
    parent_model = StoreSale,
    model = SaleItem, 
    form = TestItemForm,
    extra=1, 
    can_delete=True,
    validate_min=False,  # Allow empty forms
    validate_max=False,  # Allow unlimited forms
)

class RequisitionForm(forms.ModelForm):
    class Meta:
        model = Requisition
        fields = ['supplier', 'price_list_document', 'amounts_are_tax_inclusive', 'default_tax_code']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'price_list_document': forms.FileInput(attrs={'class': 'form-control'}),
            'amounts_are_tax_inclusive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_tax_code': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to only active tax codes
        self.fields['default_tax_code'].queryset = TaxCode.objects.filter(is_active=True)
        self.fields['default_tax_code'].empty_label = "Select default tax code (optional)"

class RequisitionItemForm(forms.ModelForm):
    use_manual_price = forms.BooleanField(
        required=False, 
        label="Use Manual Price",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = RequisitionItem
        fields = [
            'raw_material', 'quantity', 'price_per_unit', 'pricing_source', 
            'manual_price_reason', 'tax_code'
        ]
        widgets = {
            'raw_material': forms.Select(attrs={'class': 'form-select raw-material-field'}, choices=[('', 'Select Raw Material')]),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pricing_source': forms.Select(attrs={'class': 'form-select'}),
            'manual_price_reason': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_code': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        supplier = kwargs.pop('supplier', None)
        super().__init__(*args, **kwargs)
        
        # Always show all raw materials initially, let JavaScript handle filtering
        self.fields['raw_material'].queryset = RawMaterial.objects.all()
        self.fields['raw_material'].empty_label = "Select Raw Material"
        
        # Filter to only active tax codes
        self.fields['tax_code'].queryset = TaxCode.objects.filter(is_active=True)
        self.fields['tax_code'].empty_label = "Select tax code"
        
        # Make manual_price_reason not required
        self.fields['manual_price_reason'].required = False

    def clean(self):
        cleaned_data = super().clean()
        use_manual_price = cleaned_data.get('use_manual_price')
        
        if use_manual_price:
            cleaned_data['pricing_source'] = 'manual'
            if not cleaned_data.get('manual_price_reason'):
                cleaned_data['manual_price_reason'] = "Manual price adjustment"
        else:
            cleaned_data['pricing_source'] = 'system'
        
        return cleaned_data

class RequisitionExpenseItemForm(forms.ModelForm):
    class Meta:
        model = RequisitionExpenseItem
        fields = ['expense_account', 'amount', 'description']
        widgets = {
            'expense_account': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to only active expense accounts
        from accounts.models import ChartOfAccounts
        self.fields['expense_account'].queryset = ChartOfAccounts.objects.filter(
            account_type='expense', 
            is_active=True
        )

# Create formsets
_RequisitionItemFormSet = inlineformset_factory(
    Requisition, 
    RequisitionItem, 
    form=RequisitionItemForm,
    extra=1, 
    can_delete=True,
    fields=[
        'raw_material', 'quantity', 'price_per_unit', 'use_manual_price', 
        'manual_price_reason', 'tax_code'
    ]
)

RequisitionExpenseItemFormSet = inlineformset_factory(
    Requisition, 
    RequisitionExpenseItem, 
    form=RequisitionExpenseItemForm,
    extra=1, 
    can_delete=True,
    fields=['expense_account', 'amount', 'description']
)
        
class LPOForm(forms.ModelForm):
    class Meta:
        model = LPO
        fields = ['invoice_document','quotation_document', 'payment_duration', 'payment_option']  # Exclude requisition
        widgets = {
            'invoice_document': forms.FileInput(attrs={'class': 'form-control'}),
            'quotation_document': forms.FileInput(attrs={'class':'form-control'}),
            'payment_duration': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Days (e.g. 30)'}),
            'payment_option': forms.Select(attrs={'class': 'form-control'}),
        }
        
        labels = {
            'payment_duration': 'Payment Duration (Days)',
            'payment_option': 'Payment Option',
            'invoice_document':'Proforma Invoice',
            'quotation_document':'Price List'
        }
        
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Check that all required fields are filled
        invoice_document = cleaned_data.get('invoice_document')
        payment_duration = cleaned_data.get('payment_duration')
        quotation_document = cleaned_data.get('quotation_document')
        payment_option = cleaned_data.get('payment_option')
        
        if not invoice_document:
            self.add_error('invoice_document', 'This field is required.')
            
        if not quotation_document:
            self.add_error('quotation_document', 'This field is required.')
        
        if not payment_duration:
            self.add_error('payment_duration', 'This field is required.')
        
        if not payment_option:
            self.add_error('payment_option', 'This field is required.')
        
        return cleaned_data
    
class GoodsReceivedNoteForm(forms.ModelForm):
    class Meta:
        model = GoodsReceivedNote
        fields = ['reason', 'comment']  # Include other fields as necessary
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control', 'placeholder':'Carefully Inspect the delivered rawmaterials'}),
            'comment': forms.Textarea(attrs={'class': 'form-control','placeholder':'Give a detailed explanation of the state of the goods recieved'}),
        }
        
class DeliveredRequisitionItemForm(forms.ModelForm):
    class Meta:
        model = RequisitionItem
        fields = ['raw_material', 'price_per_unit', 'quantity', 'delivered_quantity']  # Include only the fields you want to render
        widgets = {
            'raw_material': forms.Select(attrs={'readonly': 'readonly'}),
            'quantity': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'price_per_unit': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'delivered_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
# DeliveredRequisitionItemFormSet = modelformset_factory(
#     RequisitionItem,
#     form=DeliveredRequisitionItemForm,
#     extra=0,  # No extra forms
# )

class ReplaceNoteForm(forms.ModelForm):
    class Meta:
        model = ReplaceNote
        fields = ['status']  # Include any fields you want to edit in the ReplaceNote
        widgets = {
            
            'status': forms.Select(attrs={'class': 'form-control'})
        }
        
class ReplaceNoteItemForm(forms.ModelForm):
    class Meta:
        model = ReplaceNoteItem
        fields = ['raw_material', 'ordered_quantity', 'delivered_quantity', 'quantity_to_replace']
        widgets = {
            'raw_material': forms.Select(),
            'ordered_quantity': forms.NumberInput(attrs={'step': 'any'}),
            'delivered_quantity': forms.NumberInput(attrs={'step': 'any'}),
            'quantity_to_replace': forms.NumberInput(attrs={'step': 'any'}),
        }
ReplaceNoteItemFormSet = modelformset_factory(
    ReplaceNoteItem,
    extra=0,  # You can adjust this to show a certain number of empty forms
    fields=('raw_material', 'ordered_quantity', 'delivered_quantity', 'quantity_to_replace'),
    can_delete=False
)


class NewAccessoryForm(forms.ModelForm):
    class Meta:
        model = Accessory
        fields = ['name', 'description', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control','placeholder':'A brief description of the accessory'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class MainStoreAccessoryRequisitionForm(forms.ModelForm):
    class Meta:
        model = MainStoreAccessoryRequisition
        fields = ['comments']
        widgets = {
            'comments': forms.Textarea(attrs={'class': 'form-control','placeholder':'Provide any details of this requsition e.g supplier, details etc.'}),
        }
        

class MainStoreAccessoryRequisitionItemForm(forms.ModelForm):
    class Meta:
        model = MainStoreAccessoryRequisitionItem
        fields = ['accessory', 'quantity_requested','price']
        widgets = {
            'accessory': forms.Select(attrs={'class': 'form-control'}),
            'quantity_requested': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_quantity_requested(self):
        quantity = self.cleaned_data['quantity_requested']
        if quantity <= 0:
            raise ValidationError('Quantity requested must be a positive integer.')
        return quantity

MainStoreAccessoryRequisitionItemFormSet = modelformset_factory(
    MainStoreAccessoryRequisitionItem,
    form=MainStoreAccessoryRequisitionItemForm,
    extra=1,  # Show one empty form by default
    can_delete=True  # Allow deleting individual items
)


class InternalAccessoryRequestForm(forms.ModelForm):
    class Meta:
        model = InternalAccessoryRequest
        fields = ['comments','store']
        widgets= {
            'comments': forms.Textarea(attrs={'class': 'form-control','placeholder':'Provide any details of this requsition e.g. supplier, details etc.'}),
        }

    def __init__(self, *args, **kwargs):
        # Retrieve the user from kwargs
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter store queryset to only include the store managed by the logged-in user
        if self.user:
            managed_stores = Store.objects.filter(manager=self.user)
            self.fields['store'].queryset = managed_stores
            
        # Automatically select the store if user manages only one store
            if managed_stores.count() == 1:
                self.fields['store'].initial = managed_stores.first()
            
    def save(self, commit=True):
        request = super().save(commit=False)
        request.save()


        return request
InternalAccessoryRequestItemFormSet = modelformset_factory(
    InternalAccessoryRequestItem,
    fields=('accessory', 'quantity_requested'),
    widgets= {
        'accessory': forms.Select(attrs={'class': 'form-control'}),
        'quantity_requested': forms.NumberInput(attrs={'class': 'form-control'})
    },
    extra=1  # Add an extra form initially
)

class ApproveRejectRequestForm(forms.ModelForm):
    class Meta:
        model = InternalAccessoryRequest
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow 'approved' and 'rejected' statuses
        self.fields['status'].choices = [
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ]
class MarkAsDeliveredForm(forms.ModelForm):
    class Meta:
        model = InternalAccessoryRequest
        fields = ['status']
        widgets = {
            'status': forms.HiddenInput()  # Hide the field since we are auto-marking it as 'delivered'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].initial = 'delivered'  # Set status to 'delivered' by default
        

class ServiceSaleForm(forms.ModelForm):
    class Meta:
        model = ServiceSale
        fields = ['store', 'customer','payment_mode']
        widgets = {
            'store':forms.Select(attrs={'class':'form-control'}),
            'customer': forms.Select(attrs={'class':'form-control'}),
            'payment_mode': forms.Select(attrs={'class':'form-control'}),  # Use a select box for payment mode options  # TODO: Populate payment mode options from a predefined list in the model  # TODO: Add validation for payment mode selection  # TODO: Handle case where user doesn't manage any stores and display an appropriate message  # TODO: Handle case where user doesn't have access to the selected store and display an appropriate message   # TODO: Add validation for

            
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['store'].queryset = Store.objects.filter(manager=user)
            if self.fields['store'].queryset.count() == 1:
                self.fields['store'].initial = self.fields['store'].queryset.first()

                
class ServiceSaleItemForm(ModelForm):
    class Meta:
        model = ServiceSaleItem
        fields = ['service','staff','quantity','sale']
        widgets ={
            'sale': forms.HiddenInput(),
            'service':forms.Select(attrs={'class':'form-control'}),
            'staff':forms.SelectMultiple(attrs={'class':'form-control'}),
            'quantity':forms.NumberInput(attrs={'class':'form-control'})
        }
    def __init__(self, *args, **kwargs):
        store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        if store:
            # Apply the store filter to the queryset for the 'service' field
            self.fields['service'].queryset = StoreService.objects.filter(store=store)
    

class AccessorySaleItemForm(ModelForm):
    class Meta:
        model = AccessorySaleItem
        fields = ['accessory','quantity','price','sale']
        widgets ={
            'sale': forms.HiddenInput(),
            'accessory':forms.Select(attrs={'class':'form-control'}),
            'price':forms.NumberInput(attrs={'class':'form-control'}),
            'quantity':forms.NumberInput(attrs={'class':'form-control'})
        }
    def __init__(self, *args, **kwargs):
        store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        if store:
            self.fields['accessory'].queryset = StoreAccessoryInventory.objects.filter(store=store)

class ProductSaleItemForm(ModelForm):
    staff = forms.ModelChoiceField(
        queryset=Staff.objects.all(),
        required=False,
        empty_label="No staff commission",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = ProductSaleItem
        fields = ['product','quantity','price_group','sale','staff']
        widgets ={
            'sale': forms.HiddenInput(),
            'product':forms.Select(attrs={'class':'form-control'}),
            'quantity':forms.NumberInput(attrs={'class':'form-control'}),
            'price_group': forms.Select(attrs={'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'})
        }
    def __init__(self, *args, **kwargs):
        store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        if store:
            self.fields['product'].queryset = StoreInventory.objects.filter(store=store)
            
class IncidentWriteOffForm(ModelForm):
    class Meta:
        model = IncidentWriteOff
        fields = ['raw_material','quantity','reason']
        widgets ={
            'raw_material': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'reason': forms.Textarea(attrs={'class':'form-control'}),
            'total_cost': forms.NumberInput(attrs={'class':'form-control'})
        }
        
class IncidentWriteOffForm(forms.ModelForm):
    class Meta:
        model = IncidentWriteOff
        fields = ('raw_material', 'quantity', 'reason')
        widgets ={
            'raw_material': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'reason': forms.Textarea(attrs={'class':'form-control'}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        raw_material = self.cleaned_data['raw_material']
        if quantity > raw_material.current_stock:
            raise forms.ValidationError(f"Insufficient stock. Available stock for {raw_material} is {raw_material.current_stock}")
        return quantity

class RawMaterialUploadForm(forms.Form):
    csv_file = forms.FileField()

class BulkUploadRawMaterialPriceForm(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV File",
        help_text="Upload a CSV file with raw material price data. Download the template for the correct format.",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # Check file size (max 5MB)
            if csv_file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5MB.")
            
            # Check file extension
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError("Please upload a CSV file.")
            
            # Check file content
            try:
                decoded_file = csv_file.read().decode('utf-8')
                csv_file.seek(0)  # Reset file pointer
                
                # Check if file has content
                if not decoded_file.strip():
                    raise forms.ValidationError("The CSV file is empty.")
                
                # Check if file has headers
                lines = decoded_file.splitlines()
                if len(lines) < 2:
                    raise forms.ValidationError("The CSV file must have at least a header row and one data row.")
                
                # Check required headers
                reader = csv.DictReader(lines)
                required_headers = ['raw_material_name', 'supplier_name', 'price']
                missing_headers = [header for header in required_headers if header not in reader.fieldnames]
                
                if missing_headers:
                    raise forms.ValidationError(f"Missing required headers: {', '.join(missing_headers)}")
                    
            except UnicodeDecodeError:
                raise forms.ValidationError("The file must be encoded in UTF-8.")
            except Exception as e:
                raise forms.ValidationError(f"Error reading CSV file: {str(e)}")
        
        return csv_file

class PaymentForm(forms.Form):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('visa', 'Visa'),
        ('mixed', 'Mixed'),
    ]

    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    amount = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total Amount'}), required=False)
    cash_amount = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cash Amount'}), required=False)
    mobile_money_amount = forms.DecimalField(label='MTM MOMO',widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Momo Pay'}), required=False)
    airtel_money_amount = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Airtel Money Amount'}), required=False)
    visa_amount = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Visa Amount'}), required=False)
    remarks = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Remarks'}), required=False)

    def __init__(self, *args, sale_balance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sale_balance = sale_balance  # Pass the sale's balance for validation
        
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        amount = cleaned_data.get('amount')
        cash_amount = cleaned_data.get('cash_amount') or 0
        mobile_money_amount = cleaned_data.get('mobile_money_amount') or 0
        airtel_money_amount = cleaned_data.get('airtel_money_amount') or 0
        visa_amount = cleaned_data.get('visa_amount') or 0

        # Validate mixed payments
        # if payment_method == 'mixed':
        #     if not any([cash_amount, mobile_money_amount, visa_amount]):
        #         raise forms.ValidationError("Please enter at least one amount for mixed payments.")
        # elif payment_method in ['cash', 'mobile_money', 'visa'] and not amount:
        #     raise forms.ValidationError(f"Please enter the amount for {payment_method} payment.")
        
        # Mixed payment validation
        if payment_method == 'mixed':
            total_mixed = cash_amount + mobile_money_amount + airtel_money_amount + visa_amount
            if total_mixed > self.sale_balance:
                raise forms.ValidationError(
                    f"Total mixed payment ({total_mixed}) exceeds the remaining balance ({self.sale_balance})."
                )
        elif payment_method in ['cash', 'mobile_money', 'airtel_money', 'visa']:
            amount = cleaned_data.get('amount') or 0
            if amount > self.sale_balance:
                raise forms.ValidationError(
                    f"Payment amount ({amount}) exceeds the remaining balance ({self.sale_balance})."
                )

        return cleaned_data

class PriceGroupForm(forms.ModelForm):
    class Meta:
        model = PriceGroup
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            })
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].widget.attrs['class'] = 'form-check-input'
        self.fields['is_active'].label_attrs = {'class': 'form-check-label'}
        
##Livara Mainstore Writeoff
class StoreWriteOffForm(forms.ModelForm):
    confirm_quantity = forms.IntegerField(
        help_text="Please confirm the quantity to write off"
    )

    class Meta:
        model = StoreWriteOff
        fields = ['main_store_product', 'quantity', 'reason', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter main store products to only show those with stock
        self.fields['main_store_product'].queryset = LivaraMainStore.objects.filter(quantity__gt=0)
        
        # Add Bootstrap classes and custom styling
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })
        
        # Custom label for main_store_product
        self.fields['main_store_product'].label = "Select Product"
        self.fields['confirm_quantity'].label = "Confirm Quantity"

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        confirm_quantity = cleaned_data.get('confirm_quantity')
        main_store_product = cleaned_data.get('main_store_product')

        if quantity and confirm_quantity:
            if quantity != confirm_quantity:
                raise forms.ValidationError("Quantities do not match. Please confirm the correct quantity.")

        if main_store_product and quantity:
            if quantity > main_store_product.quantity:
                raise forms.ValidationError(
                    f"Cannot write off more than available stock. Current stock: {main_store_product.quantity}"
                )

        return cleaned_data

class ServiceNameForm(forms.ModelForm):
    class Meta:
        model = ServiceName
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'})
        }

class StoreServiceForm(forms.ModelForm):
    class Meta:
        model = StoreService
        fields = ['store', 'service', 'commission_rate']
        widgets = {
            'store': forms.Select(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
            'commission_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '1'
            })
        }

    def clean_commission_rate(self):
        rate = self.cleaned_data['commission_rate']
        if rate <= 0 or rate >= 1:
            raise forms.ValidationError("Commission rate must be between 0 and 1 (e.g., 0.10 for 10%)")
        return rate

class StoreSalePaymentForm(forms.ModelForm):
    """Form for recording customer payments for store sales"""
    
    class Meta:
        model = StoreSalePayment
        fields = [
            'amount_paid', 'payment_method', 'payment_status', 
            'revenue_account', 'bank_account', 'transaction_id', 'notes'
        ]
        widgets = {
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter amount paid'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'payment_status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'revenue_account': forms.Select(attrs={
                'class': 'form-control'
            }),
            'bank_account': forms.Select(attrs={
                'class': 'form-control'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Transaction ID (optional)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Payment notes (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        receipt = kwargs.pop('receipt', None)
        super().__init__(*args, **kwargs)
        
        # Store receipt for validation
        self.receipt = receipt
        
        # Filter Chart of Accounts for appropriate accounts
        if receipt:
            # Set default amount to remaining balance
            remaining_balance = receipt.total_due - sum(
                payment.amount_paid for payment in receipt.payments.filter(payment_status='completed')
            )
            self.fields['amount_paid'].initial = remaining_balance
        
        # Filter revenue accounts (income accounts)
        try:
            self.fields['revenue_account'].queryset = ChartOfAccounts.objects.filter(
                account_type__in=['income', 'revenue']
            ).order_by('account_name')
        except:
            # Fallback if ChartOfAccounts is not available
            self.fields['revenue_account'].queryset = ChartOfAccounts.objects.all().order_by('account_name')
        
        # Filter bank accounts (asset accounts)
        try:
            self.fields['bank_account'].queryset = ChartOfAccounts.objects.filter(
                account_type__in=['asset', 'bank', 'cash']
            ).order_by('account_name')
        except:
            # Fallback if ChartOfAccounts is not available
            self.fields['bank_account'].queryset = ChartOfAccounts.objects.all().order_by('account_name')
    
    def clean_amount_paid(self):
        amount_paid = self.cleaned_data.get('amount_paid')
        receipt = getattr(self, 'receipt', None)
        
        if receipt and amount_paid:
            # Check if amount exceeds remaining balance
            total_paid = sum(
                payment.amount_paid for payment in receipt.payments.filter(payment_status='completed')
            )
            remaining_balance = receipt.total_due - total_paid
            
            if amount_paid > remaining_balance:
                raise forms.ValidationError(
                    f"Amount paid (UGX {amount_paid:,.0f}) cannot exceed remaining balance (UGX {remaining_balance:,.0f})"
                )
        
        return amount_paid

class ReceiptForm(forms.ModelForm):
    """Form for creating receipts from invoices with Chart of Accounts integration"""
    
    class Meta:
        model = StoreSaleReceipt
        fields = ['customer_name', 'customer_phone', 'customer_email', 'total_due', 'payment_method', 
                 'receiving_account', 'accounts_receivable_account', 'notes']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'total_due': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'receiving_account': forms.Select(attrs={'class': 'form-control'}),
            'accounts_receivable_account': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set payment method choices from StoreSalePayment model
        self.fields['payment_method'].choices = StoreSalePayment.PAYMENT_METHOD_CHOICES
        
        # Filter Chart of Accounts for appropriate accounts
        try:
            # Filter receiving accounts (asset accounts - cash, bank, etc.)
            self.fields['receiving_account'].queryset = ChartOfAccounts.objects.filter(
                account_type='asset'
            ).order_by('account_name')
            
            # Filter accounts receivable accounts
            self.fields['accounts_receivable_account'].queryset = ChartOfAccounts.objects.filter(
                account_type='asset'
            ).order_by('account_name')
            
            # Set default accounts if available
            if not self.instance.pk:  # Only for new receipts
                # Set default receiving account (Cash)
                try:
                    default_receiving = ChartOfAccounts.objects.filter(
                        account_name__icontains='cash',
                        account_type='asset'
                    ).first()
                    if default_receiving:
                        self.fields['receiving_account'].initial = default_receiving
                except:
                    pass
                
                # Set default accounts receivable
                try:
                    default_receivable = ChartOfAccounts.objects.filter(
                        account_name__icontains='receivable',
                        account_type='asset'
                    ).first()
                    if default_receivable:
                        self.fields['accounts_receivable_account'].initial = default_receivable
                except:
                    pass
                    
        except Exception as e:
            # Fallback if ChartOfAccounts is not available
            self.fields['receiving_account'].queryset = ChartOfAccounts.objects.all().order_by('account_name')
            self.fields['accounts_receivable_account'].queryset = ChartOfAccounts.objects.all().order_by('account_name')
    
    def clean_total_due(self):
        total_due = self.cleaned_data.get('total_due')
        if total_due <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return total_due

class CreditNoteForm(forms.ModelForm):
    """Form for creating credit notes with Chart of Accounts integration"""
    
    class Meta:
        model = CreditNote
        fields = ['credit_note_type', 'customer_name', 'customer_phone', 'customer_email', 
                 'subtotal', 'tax_amount', 'reason', 'accounts_receivable_account', 
                 'sales_return_account', 'reference_number', 'notes']
        widgets = {
            'credit_note_type': forms.Select(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'accounts_receivable_account': forms.Select(attrs={'class': 'form-control'}),
            'sales_return_account': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter Chart of Accounts for appropriate accounts
        try:
            # Filter accounts receivable accounts (asset accounts)
            self.fields['accounts_receivable_account'].queryset = ChartOfAccounts.objects.filter(
                account_type='asset'
            ).order_by('account_name')
            
            # Filter sales return accounts (revenue accounts)
            self.fields['sales_return_account'].queryset = ChartOfAccounts.objects.filter(
                account_type='revenue'
            ).order_by('account_name')
            
            # Set default accounts if available
            if not self.instance.pk:  # Only for new credit notes
                # Set default accounts receivable
                try:
                    default_receivable = ChartOfAccounts.objects.filter(
                        account_name__icontains='receivable',
                        account_type='asset'
                    ).first()
                    if default_receivable:
                        self.fields['accounts_receivable_account'].initial = default_receivable
                except:
                    pass
                
                # Set default sales return account
                try:
                    default_sales_return = ChartOfAccounts.objects.filter(
                        account_name__icontains='return',
                        account_type='revenue'
                    ).first()
                    if default_sales_return:
                        self.fields['sales_return_account'].initial = default_sales_return
                except:
                    pass
                    
        except Exception as e:
            # Fallback if ChartOfAccounts is not available
            self.fields['accounts_receivable_account'].queryset = ChartOfAccounts.objects.all().order_by('account_name')
            self.fields['sales_return_account'].queryset = ChartOfAccounts.objects.all().order_by('account_name')
    
    def clean_subtotal(self):
        subtotal = self.cleaned_data.get('subtotal')
        if subtotal <= 0:
            raise forms.ValidationError("Subtotal must be greater than zero.")
        return subtotal
    
    def clean_tax_amount(self):
        tax_amount = self.cleaned_data.get('tax_amount')
        if tax_amount < 0:
            raise forms.ValidationError("Tax amount cannot be negative.")
        return tax_amount