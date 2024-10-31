from django import forms

from POSMagicApp.models import Customer
from .models import *
from django.forms import ValidationError, inlineformset_factory, modelformset_factory


class AddSupplierForm(forms.ModelForm):
    raw_material = forms.ChoiceField(choices=[(rm.pk, rm.name) for rm in RawMaterial.objects.all()], required=False)
    class Meta:
        model = Supplier
        fields = ['name', 'company_name', 'address', 'contact_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control','placeholder':'John'}),
            'company_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Tusuubila Ltd.'}),
            'contact_number': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Mbarara'}),
            'email': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'raw_material': forms.Select(attrs={'class':'form-control'}),
        }

class BulkUploadForm(forms.Form):
    file = forms.FileField()

class EditSupplierForm(forms.ModelForm):
    raw_material = forms.ChoiceField(choices=[(rm.pk, rm.name) for rm in RawMaterial.objects.all()], required=False)
    class Meta:
        model = Supplier
        fields = ['name', 'company_name', 'address', 'contact_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control','placeholder':'John'}),
            'company_name': forms.TextInput(attrs={'class':'form-control','placeholder':'Tusuubila Ltd.'}),
            'contact_number': forms.NumberInput(attrs={'class':'form-control','placeholder':'0700000000'}),
            'address': forms.TextInput(attrs={'class':'form-control','placeholder':'Mbarara'}),
            'email': forms.TextInput(attrs={'class':'form-control','placeholder':'email@mylivara.com'}),
            'raw_material': forms.Select(attrs={'class':'form-control'}),
        }

class AddRawmaterialForm(forms.ModelForm):
    class Meta:
        model = RawMaterial
        fields = ['name', 'supplier', 'quantity', 'reorder_point','unit_measurement']
        widgets ={
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Shea Butter'}),
            'supplier': forms.Select(attrs={'class':'form-control select2'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class':'form-control'}),
            'unit_measurement': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Kilograms | Pieces | Liters| Units Write units in full format'}),
            
        }
        
class RawMaterialQuantityForm(forms.ModelForm):
    new_quantity = forms.DecimalField(label="New Quantity")

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
        fields = ['product_name', 'total_volume','unit_of_measure','price']
        widgets = {
            'product_name': forms.TextInput(attrs={'class':'form-control'}),
            'total_volume': forms.NumberInput(attrs={'class':'form-control','placeholder':'unit volume'}),
            'unit_of_measure': forms.Select(attrs={'class':'form-control','placeholder':'unit of measure'}),
            'price': forms.NumberInput(attrs={'class':'form-control','placeholder':'Proposed price for Product'}),  # Render as number input field
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
    
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if product:
            self.fields['production_order'].queryset = ProductionOrder.objects.filter(product=product, status='In Progress')
            

class WriteOffForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, label="Quantity to Write Off", widget=forms.NumberInput(attrs={'class': 'form-control','placeholder': 'e.g. 3'}))
    reason = forms.CharField(required=True, label="Reason for Write Off", widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'e.g. Expired'}))
    

#######################################################

class StoreTransferForm(forms.ModelForm):
    class Meta:
        model = StoreTransfer
        fields = ['notes','delivery_document']
        widgets = {
            'delivery_document': forms.FileInput(attrs={'class':'form-control-file'}),
            'notes': forms.Textarea(attrs={'class':'form-control', 'placeholder':'Notes about the Transfer'}),
        }

class StoreTransferItemForm(forms.ModelForm):
    class Meta:
        model = StoreTransferItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Example: Limit queryset to active ManufacturedProductInventory instances
        self.fields['product'].queryset = ManufacturedProductInventory.objects.all()
        
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
            'notes': forms.Textarea(attrs={'class':'form-control'}),
            'target_completion_date': forms.DateInput(attrs={'type':'date','class':'form-control'}),
        }
    
class SaleOrderForm(forms.ModelForm):
    class Meta:
        model = StoreSale
        fields = ['customer', 'withhold_tax', 'vat']

    sale_items = forms.inlineformset_factory(
        parent_model=StoreSale,
        model=SaleItem,
        fk_name='sale',
        fields=['product', 'quantity', 'unit_price'],
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
        fields = ['customer','withhold_tax','vat','due_date']
        widgets = {
            'customer': forms.Select(attrs={'class':'form-control'}),
            'withhold_tax': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'vat': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'due_date': forms.DateInput(attrs={'class':'form-control', 'placeholder':"No. of days untill payment"}),
            
        }
    def __init__(self, *args, **kwargs):
        super(TestForm, self).__init__(*args, **kwargs)
        # Get all customers
        self.fields['customer'].queryset = Customer.objects.all()
        
class TestItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=LivaraMainStore.objects.all())
    class Meta:
        model = SaleItem
        fields = '__all__'
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Units Ordered'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cost Per Unit'}),
        }
        
TestItemFormset = inlineformset_factory(
    parent_model = StoreSale,
    model = SaleItem, 
    form = TestItemForm,
    extra=1, 
    can_delete=True,
)

class RequisitionForm(forms.ModelForm):
    class Meta:
        model = Requisition
        fields = ['supplier','price_list_document']
        widgets = {
            'supplier': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search':'true',
                'id':'supplier-select',
                'data-size':'5',
                'data-live-search-placeholder':'Search Suppliers',
                
            
            }),
            'price_list_document': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels ={  
            'price_list_document':'Upload Supplier Price List *',
        }
class RequisitionItemForm(forms.ModelForm):
    class Meta:
        model = RequisitionItem
        fields = ['raw_material', 'quantity','price_per_unit']
        widgets = {
            'raw_material': forms.Select(attrs={'class': 'form-control','id':'id_raw_material'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Units Ordered'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price per Unit (Kg, Liter, Piece)'}),
        }
    def __init__(self, *args, **kwargs):
        supplier_id = kwargs.pop('supplier_id', None)
        super().__init__(*args, **kwargs)
        if supplier_id:
            self.fields['raw_material'].queryset = RawMaterial.objects.filter(supplier__id=supplier_id)
        else:
            self.fields['raw_material'].queryset = RawMaterial.objects.none()
        
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
        fields = ['store', 'service', 'customer', 'staff']
        widgets = {
            'service': forms.Select(attrs={'class':'form-control'}),
            'staff': forms.SelectMultiple(attrs={'class':'form-control'}),
            'service':forms.Select(attrs={'class':'form-control'}),
            'customer': forms.Select(attrs={'class':'form-control'}),

            
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Get the user from kwargs
        super(ServiceSaleForm, self).__init__(*args, **kwargs)

        if user:
            # Filter stores to those managed by the logged-in user
            self.fields['store'].queryset = Store.objects.filter(manager=user)

            # If the user manages only one store, pre-select it
            managed_stores = Store.objects.filter(manager=user)
            if managed_stores.count() == 1:
                self.fields['store'].initial = managed_stores.first()
        
class ServiceSaleAccessoryForm(forms.ModelForm):
    class Meta:
        model = ServiceSaleAccessory
        fields = ['accessory', 'quantity']
        widgets = {
            'accessory': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
        }

class ServiceSaleProductForm(forms.ModelForm):
    class Meta:
        model = ServiceSaleProduct
        fields = ['product', 'quantity', 'price']
        widgets = {
            'product': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'price': forms.NumberInput(attrs={'class':'form-control'}),
        }
        
# Formset for ServiceSaleAccessory (related to ServiceSale)
ServiceSaleAccessoryFormSet = inlineformset_factory(
    ServiceSale,
    ServiceSaleAccessory,
    form=ServiceSaleAccessoryForm,
    extra=1,  # Number of empty forms to display
    can_delete=True  # Allow deletion of accessories
)

# Formset for ServiceSaleProduct (related to ServiceSale)
ServiceSaleProductFormSet = inlineformset_factory(
    ServiceSale,
    ServiceSaleProduct,
    form=ServiceSaleProductForm,
    extra=1,  # Number of empty forms to display
    can_delete=True  # Allow deletion of products
)