from django import forms
from .models import *
from django.forms import inlineformset_factory, modelformset_factory


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
            'supplier': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class':'form-control'}),
            'unit_measurement': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Kilograms | Pieces | Liters| Units Write units in full format'}),
            
        }
        
class RawMaterialQuantityForm(forms.ModelForm):
    new_quantity = forms.IntegerField(label="New Quantity")

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
        fields = ['product_name', 'total_volume']
        widgets = {
            'product_name': forms.TextInput(attrs={'class':'form-control'}),
            'total_volume': forms.NumberInput(attrs={'class':'form-control','placeholder':'unit volume'}),
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
    batch_number = forms.CharField(required=True, label="Batch Number", widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'e.g. EMR001'}))
    expiry_date = forms.DateField(required=True, label="Expiry Date", widget=forms.TextInput(attrs={'type':'date','class': 'form-control'}))
    labor_cost_per_unit = forms.DecimalField(required=True, label="Labor Cost per Unit", widget=forms.TextInput(attrs={'class': 'form-control'}))
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
        fields = ['notes']
        widgets = {
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
            
            'quantity': forms.NumberInput(attrs={'class':'form-control'}),
        }

RestockRequestItemFormset = forms.inlineformset_factory(
    RestockRequest, 
    RestockRequestItem, 
    form=RestockRequestItemForm, 
    extra=1, 
    can_delete=True
)


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
        fields = ['requisition_no', 'supplier']
        widgets = {
            'requisition_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Requisition Number'}),
            'supplier': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search':'true',
                'id':'supplier-select',
                'data-size':'5',
                'data-live-search-placeholder':'Search Suppliers',
                
            
            }),
        }
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['raw_material'].widget = forms.Select(choices=self.get_raw_material_choices())
            
        def get_raw_material_choices(self):
            choices = [(rm.id, f"{rm.name} ({rm.unit_measurement})") for rm in RawMaterial.objects.all()]
            return choices

class RequisitionItemForm(forms.ModelForm):
    class Meta:
        model = RequisitionItem
        fields = ['raw_material', 'quantity','price_per_unit']
        widgets = {
            'raw_material': forms.Select(attrs={'class': 'form-control','id':'id_raw_material'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Units Ordered'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price per Unit (Kg, Liter, Piece)'}),
        }
        
class LPOForm(forms.ModelForm):
    class Meta:
        model = LPO
        fields = ['invoice_document', 'payment_duration', 'payment_option']  # Exclude requisition
        widgets = {
            'invoice_document': forms.FileInput(attrs={'class': 'form-control'}),
            'payment_duration': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Days (e.g. 30)'}),
            'payment_option': forms.Select(attrs={'class': 'form-control'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Check that all required fields are filled
        invoice_document = cleaned_data.get('invoice_document')
        payment_duration = cleaned_data.get('payment_duration')
        payment_option = cleaned_data.get('payment_option')
        
        if not invoice_document:
            self.add_error('invoice_document', 'This field is required.')
        
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
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Carefully Inspect the delivered rawmaterials'}),
            'comment': forms.Textarea(attrs={'class': 'form-control','placeholder':'Give a detailed explanation of the state of the goods recieved'}),
        }
        
class DeliveredRequisitionItemForm(forms.ModelForm):
    class Meta:
        model = RequisitionItem
        fields = ['raw_material', 'price_per_unit', 'quantity', 'delivered_quantity']  # Include only the fields you want to render
        widgets = {
            'raw_material': forms.TextInput(attrs={'readonly': 'readonly'}),
            'price_per_unit': forms.TextInput(attrs={'readonly': 'readonly'}),
            'quantity': forms.TextInput(attrs={'readonly': 'readonly'}),
        }
# DeliveredRequisitionItemFormSet = modelformset_factory(
#     RequisitionItem,
#     form=DeliveredRequisitionItemForm,
#     extra=0,  # No extra forms
# )

