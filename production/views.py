from datetime import date, datetime, timedelta
from decimal import Decimal
import os
from django.db.models import Sum, F
from django.contrib.auth.models import Group
from django.views.decorators.http import require_POST
from django.db.models import Sum, F
from django.utils import timezone
from django.views.generic.edit import DeleteView
from django.views.generic import DetailView, FormView, ListView
import csv
from django.templatetags.static import static

from itertools import product
import json
from django import forms
from django.contrib import messages
from django.forms.formsets import BaseFormSet
from django.forms import ValidationError, formset_factory, inlineformset_factory, modelformset_factory
from django.http import FileResponse, Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from POSMagic import settings
from POSMagicApp.decorators import allowed_users
from POSMagicApp.models import Customer
from .utils import approve_restock_request, cost_per_unit
from .forms import AddSupplierForm, ApprovePurchaseForm, BulkUploadForm, BulkUploadRawMaterialForm, DeliveredRequisitionItemForm, EditSupplierForm, AddRawmaterialForm, CreatePurchaseOrderForm, GoodsReceivedNoteForm, LPOForm, ManufactureProductForm, ProductionForm, ProductionIngredientForm, ProductionIngredientFormSet, ProductionOrderForm, RawMaterialQuantityForm, ReplaceNoteForm, ReplaceNoteItemForm, ReplaceNoteItemFormSet, RequisitionForm, RequisitionItemForm, RestockRequestForm, RestockRequestItemForm, RestockRequestItemFormset, SaleOrderForm, StoreAlertForm, StoreForm, StoreTransferForm, StoreTransferItemForm, TestForm, TestItemForm, TestItemFormset, WriteOffForm
from .models import LPO, DebitNote, DiscrepancyDeliveryReport, GoodsReceivedNote, LivaraMainStore, ManufactureProduct, ManufacturedProductInventory, Notification, ProductionIngredient, Production, ProductionOrder, RawMaterial, RawMaterialInventory, ReplaceNote, ReplaceNoteItem, Requisition, RequisitionItem, RestockRequest, RestockRequestItem, SaleItem, Store, StoreAlerts, StoreInventory, StoreSale, StoreTransfer, StoreTransferItem, Supplier, PurchaseOrder, WriteOff

# Create your views here.
@login_required(login_url='/login/')
def productionPage(request):
    suppliers = Supplier.objects.count()
    rawmaterials = RawMaterial.objects.all()
    manufactured_products = ManufacturedProductInventory.objects.all()
    approved_orders_count = ProductionOrder.objects.filter(status='Approved').count()
    approved_rawmaterial_request_count = PurchaseOrder.objects.filter(status='approved').count()
    purchase_orders = LPO.objects.filter(status='verified').count()
    supplier_deliveries = GoodsReceivedNote.objects.count()
    below_reorder_count = RawMaterial.objects.annotate(current_stock=Sum('rawmaterialinventory__adjustment')).filter(current_stock__lt=F('reorder_point')).count()
    # Calculate total stock value
    total_stock_value = sum(material.stock_value for material in rawmaterials)
    context ={
        'rawmaterials': rawmaterials,
        'total_suppliers': suppliers,
        'manufactured_products': manufactured_products.count(),
        'approved_orders': approved_orders_count,
        'approved_rawmaterial_requests': approved_rawmaterial_request_count,
        'purchase_orders': purchase_orders,
        'supplier_deliveries': supplier_deliveries,
        'below_reorder_count': below_reorder_count,
        'total_stock_value': total_stock_value,
    }
    
    return render(request, "production_index.html", context)



@login_required(login_url='/login/')
def supplierList(request):
    suppliers = Supplier.objects.all()
    context ={
        'suppliers': suppliers,
    }
    return render(request, "suppliers_list.html", context)

@login_required(login_url='/login/')
def addSupplier(request):
    if request.method == 'POST':
        if 'bulk_upload' in request.POST:
            form = BulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['file']
                # Handle CSV file
                if file.name.endswith('.csv'):
                    data = file.read().decode('utf-8')
                    print("File Content:")
                    print(data)
                    csv_reader = csv.DictReader(data.splitlines())
                    # next(csv_reader)  # Skip header row if there's one

                    for row in csv_reader:
                        print("Row Data:")
                        print(row)
                        # Assuming your CSV file has columns for supplier details
                        # Adjust the indexing based on your CSV structure
                        try:
                            Supplier.objects.create(
                                name=row.get('name',''),
                                company_name=row.get('company',''),
                                email=row.get('email',''),
                                address=row.get('address', ''),
                                contact_number=row.get('contact',''),
                                # Add other fields as needed
                            )
                        except Exception as e:
                            print(f"Error creating supplier: {e}")
                            messages.error(request, f"Error processing row: {e}")
                            
                    messages.success(request, "Suppliers successfully added.")
                    return redirect('supplierList')
                else:
                    messages.error(request, "Invalid file format. Please upload a CSV file.")
        else:
            form = AddSupplierForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "New Supplier successfully added.")
                return redirect('supplierList')
    else:
        form = AddSupplierForm()
        bulk_form = BulkUploadForm()

    context = {
        'form': form,
        'bulk_form': bulk_form
    }
    return render(request, "add-supplier.html", context)

@login_required(login_url='/login/')
def editSupplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    if request.method == 'POST':
        form = EditSupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier Details have been updated successfully")
            return redirect('supplierList')
    else:
        form = EditSupplierForm(instance=supplier)
        context = {'form': form,'supplier': supplier}

    return render(request, "edit-supplier.html", context)

@login_required(login_url='/login/')
def deleteSupplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Delete related raw materials and their associated records
                raw_materials = RawMaterial.objects.filter(supplier=supplier)
                for raw_material in raw_materials:
                    PurchaseOrder.objects.filter(raw_material=raw_material).delete()
                    ProductionIngredient.objects.filter(raw_material=raw_material).delete()
                    RawMaterialInventory.objects.filter(raw_material=raw_material).delete()
                    raw_material.delete()
            supplier.delete()
            messages.success(request, "Supplier and related raw materials have been deleted successfully")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
        return redirect ('supplierList')
    return render(request, 'confirm_supplier_deletion.html')

def get_supplier_raw_material_breakdown():
    breakdown = RequisitionItem.objects.values(
        'requisition__supplier__name', 
        'raw_material__name'
    ).annotate(
        total_delivered=Sum('delivered_quantity')
    ).order_by('requisition__supplier__name', 'raw_material__name')
    
    return breakdown

def supplier_details (request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    rawmaterials = RawMaterial.objects.filter(supplier=supplier)
    requisitions = Requisition.objects.filter(supplier=supplier)
    # Get the breakdown of raw materials for the specific supplier
    breakdown = RequisitionItem.objects.filter(
        requisition__supplier=supplier
    ).values(
        'raw_material__name'
    ).annotate(
        total_delivered=Sum('delivered_quantity')
    ).order_by('raw_material__name')
    # Get the LPOs related to requisitions made to the supplier
    purchase_orders = LPO.objects.filter(requisition__supplier=supplier)
    
    context = {
        'supplier': supplier,
        'rawmaterials': rawmaterials,
        'requisitions': requisitions,
        'breakdown': breakdown,
        'purchase_orders': purchase_orders,
    }
    return render(request, "supplier_details.html", context)


@login_required(login_url='/login/')
def rawmaterialsList(request):
    rawmaterials = RawMaterial.objects.all()
    context = {
        'rawmaterials': rawmaterials,
    }
    return render(request, "raw-materials-list.html", context)

def rawamaterialsTable(request):
    rawmaterials = RawMaterial.objects.all()
    return render(request, 'raw-materials-table.html', {'rawmaterials': rawmaterials})

@login_required(login_url='/login/')
def addRawmaterial(request):
    if request.method == 'POST':
        if 'bulk_upload' in request.POST:
            form = BulkUploadRawMaterialForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['file']
                if file.name.endswith('.csv'):
                    data = file.read().decode('utf-8')
                    csv_reader = csv.DictReader(data.splitlines())

                    for row in csv_reader:
                        try:
                            supplier = Supplier.objects.get(name=row['supplier'])
                            RawMaterial.objects.create(
                                name=row['name'],
                                supplier=supplier,
                                quantity=int(row.get('quantity', 0)),
                                reorder_point=int(row.get('reorder_point', 0)),
                                unit_measurement=row.get('unit_measurement', '')
                            )
                        except Supplier.DoesNotExist:
                            messages.error(request, f"Supplier '{row['supplier']}' not found.")
                        except Exception as e:
                            print(f"Error processing row: {e}")
                            messages.error(request, f"Error processing row: {e}")

                    messages.success(request, "Raw Materials successfully added.")
                    return redirect('rawmaterialsList')
                else:
                    messages.error(request, "Invalid file format. Please upload a CSV file.")
        else:
            form = AddRawmaterialForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "New Raw Material Successfully added")
                return redirect('rawmaterialsList')
    else:
        form = AddRawmaterialForm()
        bulk_form = BulkUploadRawMaterialForm()

    context = {
        'form': form,
        'bulk_form': bulk_form
    }
    return render(request, "add-rawmaterial.html", context)

def update_raw_material_quantity(request, pk):
    raw_material = get_object_or_404(RawMaterial, pk=pk)

    if request.method == 'POST':
        form = RawMaterialQuantityForm(request.POST)
        if form.is_valid():
            new_quantity = form.cleaned_data['new_quantity']
            try:
                raw_material.set_quantity(new_quantity)
                messages.success(request, f"Quantity for {raw_material.name} updated successfully.")
                return redirect('rawmaterialsList')
            except ValueError as e:
                form.add_error(None, str(e))
    else:
        form = RawMaterialQuantityForm(initial={'new_quantity': raw_material.current_stock})

    return render(request, 'update_raw_material_quantity.html', {'form': form, 'raw_material': raw_material})

@login_required(login_url='/login/')
def download_example_csv(request):
    file_path = os.path.join(settings.BASE_DIR, 'POSMagicApp/static/files/raw_materials_upload.csv')
    return FileResponse(open(file_path, 'rb'), content_type='text/csv', as_attachment=True, filename='raw_materials_upload.csv')

def download_supplier_csv(request):
    file_path = os.path.join(settings.BASE_DIR, 'POSMagicApp/static/files/supplier_upload.csv')
    return FileResponse(open(file_path, 'rb'), content_type='text/csv', as_attachment=True, filename='supplier_upload.csv')

def storeManagement(request):
    return render(request, "store-management.html")

def delete_rawmaterial (request, raw_material_id):
    raw_material = get_object_or_404(RawMaterial, pk=raw_material_id)
    if request.method == 'POST':
        # Delete related records
        PurchaseOrder.objects.filter(raw_material=raw_material).delete()
        ProductionIngredient.objects.filter(raw_material=raw_material).delete()
        RawMaterialInventory.objects.filter(raw_material=raw_material).delete()
        
        # Delete the raw material
        raw_material.delete()
        messages.success(request, "Raw Material has been deleted successfully")
        return redirect('rawmaterialsList')
    return render (request, 'rawmaterial_confirm_delete.html', {'object': raw_material})
        

@login_required(login_url='/login/')
def storeRequests(request):
    porders = PurchaseOrder.objects.all().order_by('-created_at')
    store_alerts = StoreAlerts.objects.filter(handled=False)
    context = {
        'porders': porders,
        'store_alerts': store_alerts,
    }
    return render(request, "store-requests.html", context)

@login_required(login_url='/login/')
def editStoreAlerts(request, alert_id):
    store_alert = get_object_or_404(StoreAlerts, pk=alert_id)
    if request.method == 'POST':
        form = StoreAlertForm(request.POST, instance=store_alert)
        if form.is_valid():
            form.save()
            messages.success(request, "Store Alert has been handled successfully")
            return redirect('storeRequests')
    else:
        form = StoreAlertForm(instance=store_alert)

    context = {
        'form': form,
        'store_alert': store_alert,
    }
    # Check if this is an AJAX request (modal form submission)
    if request.is_ajax():
        return render(request, 'edit-store-alerts.html', context)  # Replace with your form template
    else:
        return render(request, 'store-requests.html', context)  # Fallback for direct access (optional)



def dispatchList(request):
    return render(request, "dispatch-list.html")

def storeProducts(request):
    return render(request, "store-products.html")

def productionProcess(request):
    return render(request, "production-process.html")

def purchaseOderList(request):
    return render(request, "purchase-order-list.html")

##############################################################
##############################################################
### Purchase Orders for raw materials #########################################################################
##############################################################
##############################################################
@login_required(login_url='/login/')
def createPurchaseOrder(request, rawmaterial_id):

    selected_rawmaterial = RawMaterial.objects.get(id=rawmaterial_id)
    if request.method == 'POST':
        form = CreatePurchaseOrderForm(request.POST)
        if form.is_valid():
            purchase_order = form.save()
            messages.success(request, "New Purchase Order Successfully added")
            return redirect (reverse('purchase_order_details', args=[purchase_order.id]))
        else:
            messages.error(request, "Failed to add new Purchase Order. Please check the form.")
            print(form.errors)
    else:
        form = CreatePurchaseOrderForm(initial={"raw_material": selected_rawmaterial})
        
    context = {'form': form}
    return render(request, "create-purchase-order.html", context)

@login_required(login_url='/login/')
def purhcaseOrderDetails (request, purchase_order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
    context = {
        'purchase_order':purchase_order,
    }
    return render (request, "purchase-order-details.html", context)


@login_required(login_url='/login/')
def editPurchaseOrderDetails(request, purchase_order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
    if request.method == 'POST':
        form = CreatePurchaseOrderForm(request.POST, instance=purchase_order)
        if form.is_valid():
            form.save()
            messages.success(request, "Purchase Order Details have been updated successfully")
            return redirect (reverse('purchase_order_details', args=[purchase_order.id]))
        else:
            messages.error(request, "Failed to update Purchase Order Details. Please check the form.")
            print(form.errors)
    else:
        form = CreatePurchaseOrderForm(instance=purchase_order)
        
    context = {'form': form}
    return render(request, "edit-purchase-order-details.html", context)

def approve_order(request, order_id):
    order = get_object_or_404(PurchaseOrder, id=order_id)
    if request.method == 'POST':
        order.status = 'approved'
        order.save()
        messages.success(request, 'Order approved successfully.')
    else:
        messages.error(request, 'Invalid request method.')
    return redirect('financePurchase')

def reject_order(request, order_id):
    order = get_object_or_404(PurchaseOrder, id=order_id)
    if request.method == 'POST':
        order.status = 'rejected'
        order.save()
        messages.success(request, 'Order rejected successfully.')
    else:
        messages.error(request, 'Invalid request method.')
    return redirect('financePurchase')

##############################################################
##############################################################

@login_required(login_url='/login/')
def productsList(request):
    products = Production.objects.all()
    context = {
        'products': products,

    }
    return render(request, "products-list.html", context)



@login_required(login_url='/login/')
def productDetails(request, product_id):
    product = Production.objects.get( pk=product_id)
    ingridients = ProductionIngredient.objects.filter(product=product_id)
    context = {
        'product': product,
        'ingredients': ingridients,
    }
    return render(request, "product-details.html", context)


@login_required(login_url='/login/')
def create_product(request):
    
    if request.method == 'POST':
        product_form = ProductionForm(request.POST)
        formset = ProductionIngredientFormSet(request.POST)

        if product_form.is_valid() and formset.is_valid():
            excluded_materials = ["Black jars 220 g", "Label Emerald Hair", "Black jars 50 g","Label for Product","Emerald Label Top 220 g","Emerald Label Side 220 g","Label Baby Opal Body butter top 220 g","Label Baby Opal Body Butter top 50 g","Label Chocolate Ruby Body Butter side 220 g","Label Chocolate Ruby Body Butter side 50 g","Label Chocolate Ruby Body butter top 220 g",
                                "Label Chocolate Ruby Body Butter top 50 g","Label Diamond Tones Body Butter side 220 g","Label Diamond Tones Body Butter side 50 g","Label Diamond Tones Body Butter top 220 g","Label Emerald Hair food Top 50 g","Label Emerald Hair food 220 g top","Label Emerald Hair food side 220 g","Label Emerald Hair food side 50 g","Label Jadeite Kids Baby Shampoo 250 ml",
                                "Label Jadeite Kids Baby Shampoo 500 ml","Label Jadeite kids detangler 500 ml","Label Jadeite Kids detangler 250 ml","Label Jadeite Kids Spritz Moisturiser 250 ml",
                                "Label Jadeite Kids Spritz Moisturiser 500 ml"
                                "Label Moonstone shine Body Butter side 50 g"
                                "Label Moonstone shine Body Butter top 220 g"
                                "Label Moonstone shine Body Butter Top 50 g"
                                "label Mugisha 220 g top"
                                "Label Mugisha Body Butter side 220 g"
                                "Label Mugisha Body Butter Top 50 g"
                                "Label Ruby glow Body Butter side 220 g"
                                "Label Ruby glow Body Butter side 50 g"
                                "Label Ruby glow Body Butter top 220 g"
                                "Label Ruby glow Body Butter Top 50 g"
                                "Label Sapphire 2in1 Leave in treatment 500 ml"
                                "Label Sapphire General Purpose Hair Shampoo 500 ml"
                                "Label Tanzanite Natural Hair Oil 100 ml"
                                "Label The Pearl Cleanser back 100 ml"
                                "Label The Pearl Cleanser back 200 ml"
                                "Label The Pearl Cleanser front 100 ml"
                                "Label The Pearl Cleanser front 200 ml"
                                "Conditioner bottles 500 ml"
                                "Conditioner bottles 250 ml"
                                "Cleanser bottles 200 ml"
                                "Cleanser bottles 100 ml"
                                "Ex.gloves"
                                "White jars"
                                "Tanzanite bottle"
                                "Conditioner Bottle Cap"
                                "Black Jar Cover 220g"
                                "Black Jar Cover 50g"
                                "White Jar Cover 250 ml"
                                "Security Seal"
                                "Label The Pearl Skin Toner back 200 ml"
                                "Label The Pearl Skin Toner front 200 ml"
                                "Label The Pearl Skin Toner front 100 ml"
                                "Label The Pearl Skin Toner back 100 ml"
                                "Label Diamond Tones Body Butter top 50 g"
                                "Label Baby Opal Body Butter side 50 g"
                                "Label Baby Opal Body Butter side 220 g"
                                "Cleanser bottle cap"
                                "Spray pumps"

                                ] 
            
            # Calculate total ingredient volume excluding the specified materials
            total_ingredient_volume = sum(
                form.cleaned_data.get('quantity_per_unit_product_volume', 0) 
                for form in formset if form.is_valid() and form.cleaned_data['raw_material'].name not in excluded_materials
            )
            product = product_form.save(commit=False)
            if int(total_ingredient_volume) != int(product.total_volume):
                messages.error(request, "Sum of ingredient quantities must equal product volume<br>Check your Formula Again")
                # Re-render the form with the error message instead of redirecting
                return render(request, 'create-product.html', {'product_form': product_form, 'formset': formset})
            else:
                product.save()
                formset.instance = product
                formset.save()
                messages.success(request, "You have successfully created A product")
                return redirect('productsList')  # Redirect to product list view after creation
        else:
            # Handle form validation errors (optional: display them in the template)
            messages.error(request, "There were errors in your form submission. Please correct them and try again.")
            pass
    else:
        product_form = ProductionForm()
        formset = ProductionIngredientFormSet()
    return render(request, 'create-product.html', {'product_form': product_form, 'formset': formset})


@login_required(login_url='/login/')
def testProduct(request, product_id):
    product = Production.objects.get(pk=product_id)
    raw_materials = RawMaterial.objects.all()  # Get all available raw materials

    if request.method == 'POST':
        formset = ProductionIngredientFormSet(request.POST, instance=product)
        if formset.is_valid():
            formset.save()
            return redirect('productDetailsPage', product_id=product_id)  # Redirect to product details
        else:
            # Handle formset validation errors (optional: display them in the template)
            pass
    else:
        formset = ProductionIngredientFormSet(instance=product)
    return render(request, 'test.html', {'product': product, 'raw_materials': raw_materials, 'formset': formset})


@login_required(login_url='/login/')
def edit_product(request, product_id):
    # Retrieve the product instance to edit
    product = get_object_or_404(Production, pk=product_id)
        
        # Create formset using inlineformset_factory
    IngredientFormSet = inlineformset_factory(Production, ProductionIngredient, form=ProductionIngredientForm, extra=5)

    if request.method == 'POST':
        # Populate the product_form with POST data and instance to edit
        product_form = ProductionForm(request.POST, instance=product)
        formset = IngredientFormSet(request.POST, instance=product)

        if product_form.is_valid() and formset.is_valid():
            # Save the product_form instance
            product = product_form.save()
            formset.instance = product # assign instace to formset
            # Save the formset instances
            formset.save()
            # Redirect to product list view after successful edit
            return redirect('productsList')
    else:
        # If it's not a POST request, populate forms with instance data
        product_form = ProductionForm(instance=product)
        formset = IngredientFormSet(instance=product)

    # Render the edit-product.html template with the forms
    return render(request, 'product-edit.html', {'product': product, 'product_form': product_form, 'formset': formset})


@login_required(login_url='/login/')
def manufacture_product(request, product_id):
    product = Production.objects.get(pk=product_id)
    
    # Handle case where product is not found
    if not product:
        return redirect('productsList')  # Redirect to product list on error

    if request.method == 'POST':
        form = ManufactureProductForm(request.POST, product=product)  # Create form instance with POST data
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            # labor_cost_per_unit = form.cleaned_data['labor_cost_per_unit']  # Access labor cost
            expiry_date = form.cleaned_data['expiry_date']
            production_order = form.cleaned_data['production_order']
            

            # Check for sufficient raw material stock (optional)
            sufficient_stock = True
            insufficient_ingredients = []  # List to collect insufficient stock errors
            with transaction.atomic():
                for ingredient in product.productioningredients.all():
                    quantity_needed = ingredient.quantity_per_unit_product_volume * quantity
                    base_quantity_needed = convert_to_base_unit(quantity_needed, ingredient.raw_material.unit_measurement)
                    
                    if ingredient.raw_material.current_stock < base_quantity_needed:
                        insufficient_ingredients.append(
                            f"Insufficient stock for {ingredient.raw_material.name}. "
                            f"Required: {quantity_needed}, Available: {ingredient.raw_material.current_stock}"
                        )
                        # sufficient_stock = False
                        # messages.error(request, f"Insufficient stock for {ingredient.raw_material.name}. Required: {quantity_needed}, Available: {ingredient.raw_material.current_stock}")
                        # break  # Exit loop if any ingredient has insufficient stock

                if not insufficient_ingredients:
                    #deduct raw materials
                    deduct_raw_materials(product, quantity)
                    manufacture_product = ManufactureProduct.objects.create(
                        product=product,
                        quantity=quantity,
                        notes=notes,  # Add notes to model creation
                        expiry_date = expiry_date,
                        production_order=production_order
                    )
                    manufacture_product.batch_number = manufacture_product.generate_batch_number()
                    manufacture_product.save()
                    #update manufactured product inventory
                    manufactured_product_inventory, created = ManufacturedProductInventory.objects.get_or_create(
                        product=product,
                        batch_number= manufacture_product.batch_number,
                        defaults={'quantity': quantity,'expiry_date':expiry_date}  # Update or create with quantity
                    )
                    if not created:
                        manufactured_product_inventory.quantity += quantity
                        manufactured_product_inventory.save()  # Update existing inventory
                    
                    cost_per = cost_per_unit(product)
                    # total_cost = (cost_per * quantity) + (labor_cost_per_unit * quantity)
                    total_cost = sum(cost_data['cost_per_unit'] for cost_data in cost_per)
                    
                    #update Production Order Status
                    if production_order:
                        production_order.status = 'Completed'
                        production_order.save()  # Update production order status to 'Manufactured'
                    
                    context ={
                        'cost_per': cost_per,
                        'total_cost': total_cost,
                    }

                    messages.success(request, f"Successfully manufactured {quantity} units of {product.product_name}")
                    return redirect('manufacturedProductList')  # Redirect to product list after success
                else:
                    # Display all insufficient stock errors at once
                    for error in insufficient_ingredients:
                        messages.error(request, error)
                    # Handle form validation errors
                    # messages.error(request, "Insufficient stock to manufacture the product. Please check the inventory and try again.")
        else:
                messages.error(request, "Please correct the errors in the form.")
    else:
        form = ManufactureProductForm(product=product)  # Create an empty form instance for GET requests

    return render(request, 'manufacture-product.html', {'product': product, 'form': form})

def manufactured_products_report(request):
    period = request.GET.get('period', 'month')  # 'month', 'week', 'day'
    
    if period == 'month':
        truncate_func = TruncMonth
    elif period == 'week':
        truncate_func = TruncWeek
    elif period == 'day':
        truncate_func = TruncDay
    else:
        truncate_func = TruncMonth
    
    now = timezone.now()
    start_date = now - timezone.timedelta(days=365)  # Last year
    manufactured_products = ManufactureProduct.objects.filter(
        manufactured_at__gte=start_date
    ).annotate(
        period=truncate_func('manufactured_at')
    ).values('period').annotate(
        total_quantity=Sum('quantity')
    ).order_by('period')
    
    context = {
        'manufactured_products': manufactured_products,
        'period': period
    }
    
    return render(request, 'manufactured_products_report.html', context)

def raw_material_utilization_report(request):
    # Get custom start and end dates from query parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Default to last month if no dates are provided
    if not start_date_str or not end_date_str:
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
    else:
        # Convert strings to date objects
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            # Handle invalid date formats
            start_date = timezone.now() - timedelta(days=30)
            end_date = timezone.now()

    # Aggregate data based on the specified date range
    utilization_data = ProductionIngredient.objects.filter(
        product__manufacturedproductinventory__last_updated__range=[start_date, end_date]
    ).values(
        'raw_material__name', 'raw_material__unit_measurement'
    ).annotate(
        total_quantity=Sum(F('quantity_per_unit_product_volume') * F('product__manufacturedproductinventory__quantity'))
    )
    
    context = {
        'raw_material_utilization': utilization_data,
        'start_date': start_date,
        'end_date': end_date
    }
    
    return render(request, 'raw_material_utilization_report.html', context)


def write_off_product(request, inventory_id):
    manufactured_product_inventory = get_object_or_404(ManufacturedProductInventory, pk=inventory_id)
    
    if request.method == 'POST':
        form = WriteOffForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']
            
            # Check if there is enough quantity in the inventory
            if manufactured_product_inventory.quantity >= quantity:
                with transaction.atomic():
                    # Update the inventory
                    manufactured_product_inventory.quantity -= quantity
                    manufactured_product_inventory.save()
                    
                    # Create the write-off record
                    WriteOff.objects.create(
                        manufactured_product_inventory=manufactured_product_inventory,
                        quantity=quantity,
                        reason=reason,
                        initiated_by=request.user
                    )
                    
                    messages.success(request, f"Successfully wrote off {quantity} units of {manufactured_product_inventory.product.product_name}")
                    return redirect('manufacturedProductList')  # Redirect to product list after success
            else:
                messages.error(request, "Not enough quantity in inventory to write off the requested amount.")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = WriteOffForm()

    return render(request, 'write-off-product.html', {'manufactured_product_inventory': manufactured_product_inventory, 'form': form})

def write_offs(request):
    """
    View to display a list of all write-offs.
    """
    write_offs = WriteOff.objects.all()  # Optimize query

    context = {
        'write_offs': write_offs,
    }
    return render(request, "production_writeoffs.html", context)

def convert_to_base_unit(quantity, unit_of_measurement):
    """ Convert quantity to base unit (liters for volume, kilograms for weight) """
    if unit_of_measurement == 'Kilograms':
        return quantity / 1000  # Convert kilograms to grams
    elif unit_of_measurement == 'Liters':
        return quantity / 1000  # Convert litres to milliliters
    elif unit_of_measurement == 'Litres':
        return quantity / 1000  # Convert litres to milliliters
    return quantity  # Return as is if already in base unit

def deduct_raw_materials(product, quantity):
    for ingredient in product.productioningredients.all():
        quantity_needed = ingredient.quantity_per_unit_product_volume * quantity
        base_quantity_needed = convert_to_base_unit(quantity_needed, ingredient.raw_material.unit_measurement)
        ingredient.raw_material.remove_stock(base_quantity_needed)

@login_required(login_url='/login/')
def factory_inventory(request):
    """
    View to display the manufactured product inventory.
    """
    inventory = ManufacturedProductInventory.objects.all().select_related('product')  # Optimize query

    context = {
        'inventory': inventory,
    }

    return render(request, 'manufactured-product-inventory.html', context)

@login_required(login_url='/login/')
def manufactured_products_list(request):
    """
    View to display a list of all manufactured products.
    """
    manufactured_products = ManufactureProduct.objects.all().order_by('-manufactured_at')  # Order by recent first
    for item in manufactured_products:
        cost_per = cost_per_unit(item.product)  # Call cost_per_unit function
        item.total_cost = cost_per * item.quantity

    context = {
        'manufactured_products': manufactured_products,
    }

    return render(request, 'manufactured-product-list.html', context)

@login_required(login_url='/login/')
def manufacturedproduct_detail(request, product_id):
    manufactured_product = get_object_or_404(ManufactureProduct, pk=product_id)
    product = manufactured_product.product
    quantity = manufactured_product.quantity
    ingredient_costs = cost_per_unit(product)
    
    # Calculate total cost considering quantity
    total_ingredient_cost = 0
    for ingredient_cost in cost_per_unit(product):
        total_ingredient_cost += ingredient_cost['cost_per_unit']
    
    cost_per_product = total_ingredient_cost
    total_production_cost = cost_per_product * quantity
    
    # Get the associated production order, if any
    production_order = manufactured_product.production_order if manufactured_product.production_order else None

    referer = request.META.get('HTTP_REFERER', '/')
    # Prepare data for ingredients used
    ingredients_used_data = []
    for ingredient_cost in ingredient_costs:
        ingredient_used_data = {
            'name': ingredient_cost['name'],
            'quantity': ingredient_cost['quantity'],
            'cost_per_unit': ingredient_cost['cost_per_unit'],
            'unit_measurement': ingredient_cost.get('unit_measurement', 'N/A'),
        }
        ingredients_used_data.append(ingredient_used_data)
    context = {
        'manufactured_product': manufactured_product,
        'quantity': quantity,
        'product': product,
        'ingredients_used': ingredients_used_data,
        # 'cost_per_product': cost_per_product,
        'cost_per_product': cost_per_product, #cost per bottle
        'ingredient_costs': ingredient_costs,
        'total_production_cost':total_production_cost,
        'production_order': production_order,
        'referer':referer,
    }
    return render(request, 'manufactured-product-details.html', context)

def get_raw_material_price(raw_material_name):
  """
  Retrieves the latest unit price for a raw material based on its name.
  """
  try:
    raw_material = RawMaterial.objects.get(name=raw_material_name)
    latest_purchase_order = raw_material.purchaseorder_set.order_by('-created_at').first()
    if latest_purchase_order:
        return latest_purchase_order.unit_price
    else:
        return 0  # Handle case where no purchase order exists (optional)
  except RawMaterial.DoesNotExist:
    return None  #

@login_required(login_url='/login/')
def product_inventory_details(request, inventory_id):

    inventory_item = get_object_or_404(ManufacturedProductInventory, pk=inventory_id)  # Assuming Production model represents product
    product = inventory_item.product



    context = {
        'inventory_item':inventory_item,
        'product':product,
    }
    return render (request, 'product-inventory-details.html', context)


def bulk_stock_transfer(request):
    initial_form_count = 1
    StockTransferItemFormSet = formset_factory(
        StoreTransferItemForm,
        extra=initial_form_count,
        min_num=initial_form_count,  # Minimum number of forms
        max_num=1000,
        )

    if request.method == 'POST':
        formset = StockTransferItemFormSet(request.POST, prefix='stock_item')
        transfer_form = StoreTransferForm(request.POST, prefix='transfer')
        
        print(f"Transfer Form Data: {transfer_form.data}")
        print(f"Formset Data: {formset.data}")

        if formset.is_valid() and transfer_form.is_valid():
            with transaction.atomic():
                transfer = transfer_form.save(commit=False)
                transfer.created_by = request.user
                transfer.save()
                
                for form in formset:
                    product_id = form.cleaned_data['product']
                    quantity = form.cleaned_data['quantity']

                    # Create StoreTransferItem
                    StoreTransferItem.objects.create(
                        transfer=transfer,
                        product=product_id,
                        quantity=quantity
                    )

                # Redirect after successful creation
                return redirect('main_stock_transfer')  # Adjust to your URL name for the transfer list view
    else:
        formset = StockTransferItemFormSet(prefix='stock_item')
        transfer_form = StoreTransferForm(prefix='transfer')

    context = {
        'formset': formset,
        'transfer_form':transfer_form,
    }

    return render(request, 'bulk_stock_transfer.html', context)

def main_stock_transfer (request):
    store_transfers = StoreTransfer.objects.all()
    context = {
        'store_transfers': store_transfers
    }
    return render(request, 'main_stock_transfers.html', context)

def mark_transfer_completed (request, transfer_id):
    transfer = get_object_or_404(StoreTransfer, pk=transfer_id)
    if transfer.status != 'completed':
        with transaction.atomic():
            transfer.status = 'completed'
            transfer.save()

            transfer_items = StoreTransferItem.objects.filter(transfer=transfer)
            for item in transfer_items:
                manufactured_product_inventory = item.product
                quantity = item.quantity
                batch_number = manufactured_product_inventory.batch_number
                expiry_date = manufactured_product_inventory.expiry_date

                # Update ManufacturedProductInventory
                if manufactured_product_inventory.quantity >= quantity:
                    manufactured_product_inventory.quantity -= quantity
                    manufactured_product_inventory.save()
                else:
                    # Handle the case where there isn't enough stock
                    raise ValueError(f"Not enough stock in manufacture inventory for {manufactured_product_inventory.product}")

                # Update LivaraMainStore
                livara_inventory, created = LivaraMainStore.objects.get_or_create(
                    product=manufactured_product_inventory,
                    batch_number=batch_number,
                    expiry_date=expiry_date,
                    defaults={'quantity': quantity}
                )
                
                if not created:
                    livara_inventory.quantity += quantity
                    livara_inventory.save()

    return redirect('main_stock_transfer')
def livara_main_store_inventory(request):
    main_store_inventory = LivaraMainStore.objects.all()
    context = {
        'main_store_inventory': main_store_inventory
    }
    return render(request, 'livara_main_store_inventory.html', context)

@login_required(login_url='/login/')
def all_stores(request):
    stores = Store.objects.all()
    context = {
        'stores': stores,
    }
    return render (request, 'all-stores.html', context)

@login_required(login_url='/login/')
def add_store(request):
    form = StoreForm
    if request.method == 'POST':
        form = StoreForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('allStores')
        else:
            form = StoreForm()  # Create an empty form for GET requests
    context = {
        'form': form,
    }
    return render(request, 'add-store.html', context)


@login_required(login_url='/login/')
def edit_store(request, store_id):
    store = get_object_or_404(Store, pk=store_id)  # Fetch store by ID
    if request.method == 'POST':
        form = StoreForm(request.POST, instance=store)  # Pre-populate the form
        if form.is_valid():
            form.save()
            return redirect('allStores')  # Redirect to 'allStores' view after update
    else:
        form = StoreForm(instance=store)  # Pre-populate the form with existing data

    context = {'form': form}
    return render(request, 'edit-store.html', context)


@login_required(login_url='/login/')
def delete_store(request, store_id):
    store = get_object_or_404(Store, pk=store_id)
    if request.method == 'POST':
        store.delete()
        return redirect('allStores')  # Redirect to 'allStores' view after deletion
    context = {'store': store}
    return render(request, 'delete-store.html', context)


@login_required(login_url='/login/')
def create_restock_request(request):

    RestockRequestItemFormset = inlineformset_factory(
        RestockRequest, RestockRequestItem,
        form=RestockRequestItemForm, extra=1, can_delete=True
    )

    if request.method == 'POST':
        form = RestockRequestForm(request.POST, prefix="restock")
        formset = RestockRequestItemFormset(request.POST, prefix="restock_item")

        if form.is_valid() and formset.is_valid():
            restock = form.save(commit=False)
            restock.requested_by = request.user  # Set the user who made the request
            restock.save()

            for item_form in formset:
                restock_item = item_form.save(commit=False)
                restock_item.restock_request = restock
                restock_item.save()

            messages.success(request, 'Restock request created successfully!')

            return redirect('restockRequests')  # Adjust this to your success URL name
        else:
            print(form.errors)
            print(formset.errors)
    else:
        form = RestockRequestForm(prefix="restock")
        formset = RestockRequestItemFormset(prefix="restock_item")

    context = {
        'form': form,
        'formset': formset,
    }
    
    return render(request, 'create-restock-requests.html', context)

@login_required(login_url='/login/')
def restock_requests (request):
    restock_requests = RestockRequest.objects.all().prefetch_related('items__product').order_by('-request_date')

    user_groups = request.user.groups.all()  # This retrieves all groups the user belongs to
    user_group = user_groups.first()

    context = {
        'restock_requests': restock_requests,
        'user_group': user_group,
    }
    
    return render(request, 'restock-requests.html', context)

@require_POST
@transaction.atomic
def mark_restock_as_delivered(request, restock_id):
    restock_request = get_object_or_404(RestockRequest, id=restock_id)

    # Ensure the request is still pending
    if restock_request.status != 'pending':
        messages.error(request, 'This restock request has already been processed.')
        return redirect('restockRequests')

    # Update the status to 'delivered'
    restock_request.status = 'delivered'
    restock_request.save()

    # Update the inventory in LivaraMainStore and StoreInventory
    for item in restock_request.items.all():
        livara_store_product = item.product
        livara_store_product.quantity -= item.quantity
        livara_store_product.save()

        # Update or create the store inventory record
        store_inventory, created = StoreInventory.objects.get_or_create(
            product=livara_store_product.product.product,  # Assuming this is the production product
            store=restock_request.store,
            defaults={'quantity': item.quantity}
        )
        if not created:
            store_inventory.quantity += item.quantity
            store_inventory.save()

    messages.success(request, 'Restock request marked as delivered and inventory updated successfully.')
    return redirect('restockRequests')


def approve_restock_requests(request, request_id):
    restock_request = get_object_or_404(RestockRequest, pk=request_id)

    if restock_request.status == "approved":  # Check if request is pending
        with transaction.atomic():
            approve_restock_request(request_id)  # Call your approval function

    # Redirect to the restock request list view after approval (or display a message)
    return redirect('restockRequests')

def finance_approve_request(request, request_id):
    restock_request = get_object_or_404(RestockRequest, pk=request_id)

    if restock_request.status == "pending":
        restock_request.status = "approved"
        restock_request.save()
    return redirect('restockRequests')

def reject_restock_request(request, request_id):
    restock_request = get_object_or_404(RestockRequest, pk=request_id)

    if restock_request.status in ("pending","approved"):
        restock_request.status = "rejected"
        restock_request.save()

    # Redirect to the restock request list view after rejection (or display a message)
    return redirect('restockRequests')


@login_required(login_url='/login/')
def store_inventory_list(request):
    stores = Store.objects.all()  # Get all stores
    # Get all store inventory objects (optional: filter or order)
    store_inventory = StoreInventory.objects.all().select_related('store', 'product')  # Optimize query

    context = {'store_inventory': store_inventory, 'stores':stores }
    return render(request, 'general-stores.html', context)

@login_required(login_url='/login/')
def managers_store_inventory_view (request):
    user = request.user
    managers = Group.objects.get(name='Managers')
    if user.groups.filter(name='Managers').exists():
        managed_stores = user.managed_stores.all()
    else:
        return HttpResponseForbidden("You do not have permission to view any store inventories.")
    store_inventories = StoreInventory.objects.filter(store__in=managed_stores)
    
    context = {
        'store_inventories':store_inventories,
        'managed_stores': managed_stores,
    }
    return render(request, 'store_manager.html', context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Storemanager','Production Manager'])
def create_production_order(request):
    if not request.user.groups.filter(name='Storemanager').exists():
        messages.error(request, "You don't have permission to create production orders.")
        return redirect('store_inventory_list')  # Redirect to homepage on permission error

    if request.method == 'POST':
        form = ProductionOrderForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            target_completion_date = form.cleaned_data['target_completion_date']

            # Check for sufficient raw materials (optional)
            # ... (implement logic to check raw material stock)

            production_order = ProductionOrder.objects.create(
                product=product,
                quantity=quantity,
                notes=notes,
                target_completion_date=target_completion_date,
                requested_by=request.user,
            )
            messages.success(request, f"Production order created for {quantity} units of {product.product_name}")
            return redirect('productionList')  # Redirect to production order list
    else:
        form = ProductionOrderForm()

    context = {'form': form}
    return render(request, 'create_production_order.html', context)

def list_production_orders(request):
    production_orders = ProductionOrder.objects.all().order_by('-created_at')  # Order by creation date descending

    context = {'production_orders': production_orders}
    return render(request, 'production_order_list.html', context)

def finance_view_production_orders(request):
    production_orders = ProductionOrder.objects.all().order_by('-created_at')  # Order by creation date descending
    context = {'production_orders': production_orders}
    return render(request, 'finance_production_order.html', context)

def finance_view_purchase_orders(request):
    statuses = ['pending','approved']
    purchase_orders = PurchaseOrder.objects.filter(status__in = statuses).order_by('-created_at')  # Order by creation date descending
    context = {'purchase_orders': purchase_orders}
    return render(request, 'finance_purchase_orders.html', context)

def approve_purchase_order(request, purchaseo_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=purchaseo_id)
    if request.method == 'POST':
        form = ApprovePurchaseForm(request.POST, instance=purchase_order)
        if form.is_valid():
            form.save()
            messages.success(request, "Purchase Order Details have been updated successfully")
            return redirect ('financePurchase')
        else:
            messages.error(request, "Failed to update Purchase Order Details. Please check the form.")
            print(form.errors)
    else:
        form = ApprovePurchaseForm(instance=purchase_order)
        
    context = {'form': form}
    return render(request, 'approve_purchase_order.html', context)

def productions_view_production_orders(request):
    production_orders = ProductionOrder.objects.filter(status__in=['Created','Approved', 'In Progress', 'Completed']).order_by('-created_at')  # Order by creation date descending
    context = {'production_orders': production_orders}
    return render(request, 'production_production_orders.html', context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Production Manager'])
def approve_production_order(request, pk):
    # if not request.user.groups.filter(name=['Production Manager']).exists():
    #     messages.error(request, "You don't have permission to create production orders.")
    #     return redirect('store_inventory_list')  # Redirect to homepage on permission error
    
    production_order = ProductionOrder.objects.get(pk=pk)
    if request.method == 'POST':
        approved_quantity = request.POST.get('approved_quantity')
        if approved_quantity:
            try:
                approved_quantity = int(approved_quantity)
                if approved_quantity <= 0:
                    messages.error(request, "Approved quantity must be a positive integer.")
                elif approved_quantity > production_order.quantity:
                    messages.error(request, "Approved quantity cannot be greater than requested quantity.")
                else:
                    production_order.approved_quantity = approved_quantity
                    production_order.status = 'Approved'
                    production_order.save()
                    messages.success(request, f"Production order approved for {approved_quantity} units.")
                    # Create notification
                    notification = Notification.objects.create(
                        recipient=production_order.requested_by,
                        verb='Your production order has been approved!',
                        description=f"Order #{production_order.pk} for '{production_order.product.product_name}' has been approved and is ready for production (approved quantity: {approved_quantity} units).",
                    )
                    return redirect('productionProduction')
            except ValueError:
                messages.error(request, "Invalid approved quantity. Please enter a number.")
    context = {'production_order': production_order}
    return render(request, 'approve_production_order.html', context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Production Manager'])
def start_production_progress(request, pk):
    production_order = ProductionOrder.objects.get(pk=pk)
    if production_order.status == 'Approved':
        production_order.status = 'In Progress'  # Update status to In Progress
        production_order.save()
        messages.success(request, f"Production progress started for order {production_order.pk}.")
    else:
        messages.error(request, "Order status must be 'Approved' to start progress.")
    return redirect('productionProduction')

@login_required(login_url='/login/')
@allowed_users(allowed_roles='Finance')
def finance_restock_requests(request):
    restock_requests = RestockRequest.objects.all()  # Order by creation date descending
    context = {'restock_requests': restock_requests}
    return render(request, 'finance_restock_requests.html', context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Storemanager'])
def create_store_sale(request):
    products = LivaraMainStore.objects.all()  # Eager loading
    products_data = [
    {'id': product.id, 'name': product.product.product_name }  # Access data through foreign key
    for product in products
    ]
    customers = Customer.objects.all()

    if request.method == 'POST':
        form = SaleOrderForm(request.POST)
        sale_items = form.sale_items
        
        if form.is_valid() and sale_items.is_valid():
            sale = form.save(commit=False) # Save without creating SaleItems yet
            
            for sale_item in form.sale_items:
                # Assuming sale_item is a dictionary with 'product' and 'quantity' keys
                product = LivaraMainStore.objects.get(pk=sale_item['product'])  # Fetch product object
                if product.quantity < sale_item['quantity']:
                    messages.error(request, f"Insufficient stock for {product.product.product_name}. Available stock: {product.quantity}")
                    continue  # Skip saving this item if insufficient stock
                
                today = date.today()
                if product.expiry_date is not None and product.expiry_date < today:
                    messages.error(request, f"Product {product.product.product_name} has expired on {product.expiry_date}.")
                    continue  # Skip saving this item if product has expired

                sale_item['product'] = product  # Update dictionary with product object
                sale.sale_items.append(sale_item)
                
            if sale.sale_items.count() > 0:    
                sale.save()  # Now save the sale with sale items
                messages.success(request, "Store sale created successfully!")
                return redirect('listStoreSales')  # Redirect to sale list view (replace 'list_store_sales' with your actual URL pattern name)
            else:
                messages.error(request, "No valid sale items. Please check product quantities and expiry dates.")
    else:
        form = SaleOrderForm()
        products = LivaraMainStore.objects.all()  # Assuming to list all products
        sale_items = form.sale_items
    
    context = {'form': form,'sale_items':sale_items, 'products_data': products_data,'customers': customers}
    return render(request, 'create_store_sale.html', context)

def list_store_sales(request):
    sale_orders = StoreSale.objects.all().order_by('-sale_date')  # Order by creation date descending
    today = date.today()
    for sale_order in sale_orders:
        if sale_order.sale_date:
            sale_order.due_date = sale_order.sale_date + timedelta(days=sale_order.PAYMENT_DURATION.days)
            remaining_days = 0 # to be worked on to show countdown.
            if remaining_days < 0:
                remaining_days = 0  # Set remaining days to 0 if past due date
            sale_order.remaining_days = remaining_days
    context = {'sale_orders': sale_orders}
    return render(request, 'list_store_sales.html', context)

# finance view of all direct store sales
def finance_list_store_sales(request):
    sale_orders = StoreSale.objects.all().order_by('-sale_date')  # Order by creation date descending
    today = date.today()
    for sale_order in sale_orders:
        if sale_order.sale_date:
            sale_order.due_date = sale_order.sale_date + timedelta(days=sale_order.PAYMENT_DURATION.days)
            remaining_days = 0 # to be worked on to show countdown.
            if remaining_days < 0:
                remaining_days = 0  # Set remaining days to 0 if past due date
            sale_order.remaining_days = remaining_days
    context = {'sale_orders': sale_orders}
    return render(request, 'finance_list_store_sales.html', context)

##################### Store Sale #################
def create_store_test(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        formset = TestItemFormset(request.POST, queryset=SaleItem.objects.none())

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                store_sale = form.save(commit=False)
                
                #Check inventory before saving
                sufficient_inventory = True
                for item_form in formset:
                    product = item_form.cleaned_data.get('product')
                    quantity = item_form.cleaned_data.get('quantity')
                    if product and quantity:
                        
                        if product.quantity < quantity:
                            sufficient_inventory = False
                            item_form.add_error('quantity', 'Insufficient quantity in store. Request for production.')
                            
                if sufficient_inventory:
                    store_sale.save()
                    for item_form in formset:
                        if form.cleaned_data:
                            sale_item = item_form.save(commit=False)
                            sale_item.sale = store_sale
                            sale_item.save()
                        
                        # Reduce the quantity in the LivaraMainStore inventory
                        product = sale_item.product
                        
                        product.quantity -= sale_item.quantity
                        product.save()
                        
                    return redirect('listStoreSales')
                else:
                # Add a general error message
                    messages.error(request, "Insufficient quantity in one or more items. Please adjust the quantities or request for production.")
        else:
            messages.error(request, "There was an error with your submission. Please check the form and try again.")
            
    else:
        form = TestForm()
        formset = TestItemFormset(queryset=SaleItem.objects.none())

    context = {'form': form, 'formset': formset}
    return render(request, 'testing.html', context)

# store manager mark order as delivered
def update_order_status(request, store_sale_id):
    if request.method == 'POST':
        order = StoreSale.objects.get(pk=store_sale_id)
        order.status = 'delivered'
        order.save()
        messages.success(request, 'Order status updated successfully!')
        # ... potentially add additional processing after updating status
        return redirect('listStoreSales')  # Redirect to your store sale list view
    else:
        return redirect('listStoreSales')  # Redirect if not a POST request
    
def pay_order_status(request, store_sale_id):
    if request.method == 'POST':
        order = StoreSale.objects.get(pk=store_sale_id)
        order.status = 'paid'
        order.save()
        # ... potentially add additional processing after updating status
        return redirect('listStoreSales')  # Redirect to your store sale list view
    else:
        return redirect('listStoreSales')  # Redirect if not a POST request

def store_sale_order_details(request, pk):
    sale_order = get_object_or_404(StoreSale, pk=pk)
    # Calculate the total order amount
    sale_items = SaleItem.objects.filter(sale=sale_order)
    total_order_amount = sum(item.quantity * item.unit_price for item in sale_items)

    referer = request.META.get('HTTP_REFERER')
    context = {
        'sale_order': sale_order,
        'referer': referer,
        'total_order_amount': total_order_amount,
    }
    return render(request,'store_sale_details.html', context)


################REQUISITIONS#########
def create_requisition(request):
    RequisitionItemFormSet = modelformset_factory(RequisitionItem, form=RequisitionItemForm, extra=1)

    if request.method == 'POST':
        requisition_form = RequisitionForm(request.POST)
        supplier_id = request.POST.get('supplier')  # Get the selected supplier ID from the POST data
        item_formset = RequisitionItemFormSet(request.POST, queryset=RequisitionItem.objects.none())
        
        # Set the supplier_id for each form in the formset
        for form in item_formset:
            form.fields['raw_material'].queryset = RawMaterial.objects.filter(supplier__id=supplier_id)

        if requisition_form.is_valid() and item_formset.is_valid():
            requisition = requisition_form.save()
            
            #save each form in the formset
            for form in item_formset:
                if form.cleaned_data and form.cleaned_data.get('quantity') and form.cleaned_data.get('raw_material'):
                    requisition_item = form.save(commit=False)
                    requisition_item.requisition = requisition
                    requisition_item.save()
            

            # Redirect to a success page or requisition detail page
            return redirect('requisition_details', requisition_id=requisition.id)
        else:
            print("Requisition form errors:", requisition_form.errors)
            print("Formset errors:", item_formset.errors)
            for form in item_formset:
                print("Form errors:", form.errors)
                # Print queryset IDs to match against submitted data
                available_ids = form.fields['raw_material'].queryset.values_list('id', flat=True)
                print("Submitted raw material IDs:", form.cleaned_data.get('raw_material'))
                print("Available raw material IDs:", available_ids)
                # Verify if the submitted ID exists in the available IDs
                if form.cleaned_data.get('raw_material') not in available_ids:
                    print(f"Error: Raw material ID {form.cleaned_data.get('raw_material')} not found in available choices.")
            print("POST data:", request.POST)

    else:
        requisition_form = RequisitionForm()
        item_formset = RequisitionItemFormSet(queryset=RequisitionItem.objects.none())

    return render(request, 'create_requisition.html', {
        'requisition_form': requisition_form,
        'item_formset': item_formset,
    })
    
def get_raw_materials_by_supplier(request):
    supplier_id = request.GET.get('supplier_id')
    raw_materials = RawMaterial.objects.filter(supplier__id=supplier_id)
    data = list(raw_materials.values('id', 'name'))
    return JsonResponse(data, safe=False)

def all_requisitions(request):
    requisitions = Requisition.objects.all().order_by('-created_at')
    user_is_production_manager = request.user.groups.filter(name='Production Manager').exists()
    context ={
        'requisitions': requisitions,
        'user_is_production_manager':user_is_production_manager
    }
    return render(request, 'all_requisitions.html', context)

def requisition_details(request, requisition_id):
    requisition = get_object_or_404(Requisition, pk=requisition_id)
    requisition_items = RequisitionItem.objects.filter(requisition=requisition)
    user_is_finance = request.user.groups.filter(name='Finance').exists()
    # Calculate total cost
    total_cost = sum(item.quantity * item.price_per_unit for item in requisition_items)
    context = {
        'requisition': requisition,
        'requisition_items': requisition_items,
        'total_cost':total_cost,
        'status': requisition.status,
        'user_is_finance': user_is_finance,
    }
    return render(request, 'requisition_details.html',context)

def delete_requisition(request, requisition_id):
    # Retrieve the Requisition object or raise 404 if not found
    requisition = get_object_or_404(Requisition, pk=requisition_id)
    
    # Check if the request method is POST to confirm deletion
    if request.method == 'POST':
        requisition.delete()
        messages.success(request, 'Request deleted successfully.')
        return redirect('all_requisitions')  # Redirect to the list of requisitions
    # Optionally render a confirmation page if needed
    return render(request, 'confirm_delete.html', {'requisition': requisition})
        

def approve_requisition(request, requisition_id):
    requisition = Requisition.objects.get(pk=requisition_id)
    requisition.status = 'approved'
    requisition.save()
    messages.success(request, 'Request approved successfully')
    return redirect('lpos_list')

################LPOS###########################
def lpo_list(request):
    lpos = LPO.objects.all().order_by('-created_at')
    context = {'lpos': lpos}
    return render(request, 'lpo_list.html', context)

def lpo_verify(request, pk):
    lpo = get_object_or_404(LPO, pk=pk)

    if lpo.status != 'pending':
        messages.error(request, "You can't verify this LPO.")
        return redirect('lpos_list')

    if request.method == 'POST':
        form = LPOForm(request.POST, request.FILES, instance=lpo)
        if form.is_valid():
            lpo = form.save(commit=False)
            lpo.status = 'verified'  # Update the status to 'verified'
            lpo.save()
            
            # Update the corresponding requisition status to 'checking'
            if lpo.requisition.status == 'approved':
                lpo.requisition.status = 'checking'
                lpo.requisition.save()
                
            messages.success(request, "LPO has been verified and is ready for delivery.")
            
            return redirect('lpos_list')
    else:
        form = LPOForm(instance=lpo)

    return render(request, 'lpo_verify.html', {'form': form, 'lpo': lpo})

def pay_lpo(request, lpo_id):
    lpo = get_object_or_404(LPO, id=lpo_id)

    # Check if the request method is POST
    if request.method == 'POST':
        amount_paid = request.POST.get('amount_paid', 0)
        try:
            amount_paid = Decimal(amount_paid)
            if amount_paid <= 0:
                messages.error(request, "Amount must be positive.")
                return redirect('pay_lpo', lpo_id=lpo.id)
            
            # Update LPO with the new payment
            lpo.amount_paid += amount_paid
            lpo.save()

            # Check if the balance has been cleared
            if lpo.outstanding_balance <= 0:
                messages.success(request, "Payment completed successfully.")
            else:
                messages.success(request, "Payment received. Outstanding balance updated.")

            return redirect('lpo_detail', lpo_id=lpo.id)  # Redirect to the PO details page

        except ValueError:
            messages.error(request, "Invalid amount.")
            return redirect('lpo_pay', lpo_id=lpo.id)
    
    return render(request, 'lpo_pay.html', {'lpo': lpo})

class LpoDetailView(DetailView):
    model = LPO
    template_name = 'lpo_detail.html'
    context_object_name = 'lpo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
# def process_delivery(request, requisition_id):
#     requisition = get_object_or_404(Requisition, id=requisition_id)
#     requisition_items = RequisitionItem.objects.filter(requisition=requisition)
    
#     # Define the formset factory
#     DeliveredRequisitionItemFormSet = modelformset_factory(
#         RequisitionItem,
#         form=DeliveredRequisitionItemForm,
#         extra=0  # No extra forms
#     )

#     if request.method == 'POST':
#         goods_received_form = GoodsReceivedNoteForm(request.POST)
#         formset = DeliveredRequisitionItemFormSet(request.POST, request.FILES, queryset=requisition.requisitionitem_set.all())

#         # Debugging Output
#         print(f"Formset POST Data: {request.POST}")
#         print(f"Formset TOTAL_FORMS: {request.POST.get('form-TOTAL_FORMS')}")
#         print(f"Formset INITIAL_FORMS: {request.POST.get('form-INITIAL_FORMS')}")
        
#         if goods_received_form.is_valid() and formset.is_valid():
#             goods_received_note = goods_received_form.save(commit=False)
#             goods_received_note.requisition = requisition
#             goods_received_note.lpo = requisition.lpo_set.first()  # Assuming the LPO is related to the requisition
#             goods_received_note.save()

#             # Process each item in the formset
#             for form in formset:
#                 delivered_quantity = form.cleaned_data.get('delivered_quantity')
#                 if delivered_quantity:
#                     item = form.instance
#                     # Update the delivered_quantity for the item
#                     item.delivered_quantity = delivered_quantity
#                     item.save()

#             messages.success(request, "Goods Received Note created successfully.")
#             return redirect('requisition_detail', requisition_id=requisition.id)
#     else:
#         goods_received_form = GoodsReceivedNoteForm()
#         formset = DeliveredRequisitionItemFormSet(queryset=requisition.requisitionitem_set.all())
        
#         # Debugging Output for GET
#         print(f"Formset Queryset on GET: {formset.queryset}")
#         print(f"Formset Forms: {formset.forms}")

#     return render(request, 'process_delivery.html', {
#         'goods_received_form': goods_received_form,
#         'formset': formset, 
#         'requisition': requisition,
#         'requisition_items': requisition_items
#     })
    
class ProDeView(FormView):
    template_name = 'process_delivery.html'
    form_class = GoodsReceivedNoteForm

    def get_requisition(self):
        """
        Get the Requisition object based on the URL parameter.
        """
        return get_object_or_404(Requisition, id=self.kwargs['requisition_id'])

    def get_formset(self, data=None, files=None):
        """
        Create and return a formset for DeliveredRequisitionItemForm.
        """
        DeliveredRequisitionItemFormSet = modelformset_factory(
            RequisitionItem,
            form=DeliveredRequisitionItemForm,
            extra=0
        )
        return DeliveredRequisitionItemFormSet(
            data=data, files=files, queryset=self.get_requisition().requisitionitem_set.all()
        )

    def get_context_data(self, **kwargs):
        """
        Add the formset and requisition to the context for rendering the template.
        """
        context = super().get_context_data(**kwargs)
        context['goods_received_form'] = self.get_form()
        context['requisition'] = self.get_requisition()
        context['formset'] = self.get_formset()
        context['requisition_items'] = self.get_requisition().requisitionitem_set.all()
        return context

    def form_valid(self, form):
        """
        Handle valid form submission: save GoodsReceivedNote, process formset, and update stock.
        """
        formset = self.get_formset(self.request.POST, self.request.FILES)
        
        if formset.is_valid():
            requisition = self.get_requisition()
            goods_received_note = form.save(commit=False)
            goods_received_note.requisition = requisition
            goods_received_note.lpo = requisition.lpo_set.first()  # Adjust if multiple LPOs are possible
            goods_received_note.save()
            
            print("GoodsReceivedNote saved successfully.")

            # Process each item in the formset
            with transaction.atomic():
                for item_form in formset:
                    if item_form.cleaned_data:
                        delivered_quantity = item_form.cleaned_data.get('delivered_quantity')
                        if delivered_quantity:
                            item = item_form.instance
                            item.delivered_quantity = delivered_quantity
                            item.save()
                            
                            print(f"RequisitionItem {item} saved with delivered quantity: {delivered_quantity}")
                            
                            # Update stock in RawMaterial
                            raw_material = item.raw_material
                            raw_material.add_stock(delivered_quantity)
                            raw_material.update_quantity()
                            
                            print(f"Updated stock for RawMaterial {raw_material.name}. Current stock: {raw_material.current_stock}")
                    
            # Update the requisition status to "delivered"
            requisition.status = 'delivered'
            requisition.save()
            print("Requisition status updated to 'delivered'.")

            messages.success(self.request, "Goods Received Note created successfully.")
            return redirect('requisition_details', requisition_id=requisition.id)
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        """
        Handle invalid form submission.
        """
        return self.render_to_response(self.get_context_data(form=form))
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: validate and process form and formset.
        """
        form = self.get_form()
        formset = self.get_formset(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form)
        else:
            # Provide detailed debugging information if needed
            for form in formset:
                if form.errors:
                    print(f"Formset errors: {form.errors}")
            return self.form_invalid(form)        

def goods_recieved_notes(request):
    goods_received_notes = GoodsReceivedNote.objects.all().order_by('-created_at')
    context = {'goods_received_notes': goods_received_notes}
    return render(request, 'goods_received_notes.html', context)

def goods_received_note_detail(request, note_id):
    
    note = get_object_or_404(GoodsReceivedNote, id=note_id)
    # Get the related requisition items
    requisition_items = RequisitionItem.objects.filter(requisition=note.requisition)
    # Check if a discrepancy report already exists
    report_exists = DiscrepancyDeliveryReport.objects.filter(goods_received_note=note).exists()
    
    # Calculate differences
    discrepancies_exist = False
    for item in requisition_items:
        item.difference = (item.quantity or 0) - (item.delivered_quantity or 0)
        if item.difference > 0:
            discrepancies_exist = True
            
    context = {
        'note': note,
        'discrepancies_exist': discrepancies_exist,
        'requisition_items':requisition_items,
        'report_exists':report_exists
        
        }
    return render(request, 'goods_received_note_detail.html', context)

def handle_discrepancy(request, note_id):
    note = get_object_or_404(GoodsReceivedNote, id=note_id)
    # Calculate discrepancies
    requisition_items = RequisitionItem.objects.filter(requisition=note.requisition)
    discrepancies = []
    total_deducted_amount = 0
    
    for item in requisition_items:
        difference = (item.quantity or 0) - (item.delivered_quantity or 0)
        if difference > 0:
            item.difference = difference
            discrepancies.append(item)
            total_deducted_amount += difference * item.price_per_unit
    
    if request.method == 'POST':
        action = request.POST.get('action')
        description = request.POST.get('description', '')

        if action in ['refund', 'replace']:
            with transaction.atomic():
                discrepancy_report = DiscrepancyDeliveryReport.objects.create(
                    
                    goods_received_note=note,
                    action_taken=action,
                    description=description
                )
                # Add logic to handle the specific action
                if action == 'refund':
                    # Create a DebitNote
                        debit_note = DebitNote.objects.create(
                            discrepancy_report=discrepancy_report,
                            total_deducted_amount=total_deducted_amount
                        )
                        messages.success(request, "Refund action recorded, Debit Note created.")
                        
                elif action == 'replace':
                    # Create a ReplaceNote and associated ReplaceNoteItems
                    replace_note = ReplaceNote.objects.create(
                        discrepancy_report=discrepancy_report,
                    )
                    for item in discrepancies:
                        ReplaceNoteItem.objects.create(
                            replace_note=replace_note,
                            raw_material=item.raw_material,
                            ordered_quantity=item.quantity,
                            delivered_quantity=item.delivered_quantity,
                            quantity_to_replace=item.difference,
                        )
                    messages.success(request, "Replacement action recorded, Replace Note created.")

            messages.success(request, f"Delivery Discrepancy action '{action}' has been recorded.")
            return redirect('discrepancy_delivery_report_list')
        else:
            messages.error(request, "Invalid action selected.")
    context = {
        'note': note,
        'discrepancies_exist': bool(discrepancies),
        'requisition_items': requisition_items,
        'discrepancies': discrepancies,
        'total_deducted_amount': total_deducted_amount
    }
    
    return render(request, 'goods_received_note_detail.html', context)
    

def discrepancy_delivery_report_detail(request, report_id):
    report = get_object_or_404(DiscrepancyDeliveryReport, pk=report_id)
    
    # Get the related goods received note and requisition items
    goods_received_note = report.goods_received_note
    
    
    context = {
        'report': report,
        'goods_received_note': goods_received_note,
        
    }
    
    return render(request, 'discrepancy_delivery_report_detail.html', context)

def discrepancy_delivery_report_list(request):
    reports = DiscrepancyDeliveryReport.objects.all().order_by('-date_reported')
    context = {'reports': reports}
    return render(request, 'discrepancy_delivery_report_list.html', context)

def debit_notes_list(request):
    debit_notes = DebitNote.objects.all().order_by('-date_created')
    context = {'debit_notes': debit_notes}
    return render(request, 'debit_notes_list.html', context)

def debit_note_details(request, debit_note_id):
    debit_note = get_object_or_404(DebitNote, id=debit_note_id)
    context = {
        'debit_note': debit_note,
    }
    return render (request, 'debit_note_details.html', context)

def replace_notes_list(request):
    replace_notes = ReplaceNote.objects.all().order_by('-date_created')
    context = {'replace_notes': replace_notes}
    return render(request, 'replace_notes_list.html', context)

def replace_note_details(request, replace_note_id):
    replace_note = get_object_or_404(ReplaceNote, id=replace_note_id)
    items = replace_note.items.all()
    
    # Debugging: Print the retrieved items and their attributes
    for item in items:
        print(f"Item: {item.raw_material.name}, Ordered: {item.ordered_quantity}, Delivered: {item.delivered_quantity}, To Replace: {item.quantity_to_replace}")
    context = {
        'replace_note': replace_note,
        'items': items,  # Use items instead of replace_note.items to avoid circular reference in templates.html. This can be solved by using a custom manager in models.py.
    }
    return render (request, 'replace_note_details.html', context)

def process_replacements(request, replace_note_id):
    replace_note = get_object_or_404(ReplaceNote, id=replace_note_id)
    
    if request.method == 'POST':
        form = ReplaceNoteForm(request.POST, instance=replace_note)
        formset = ReplaceNoteItemFormSet(request.POST, queryset=ReplaceNoteItem.objects.filter(replace_note=replace_note))
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Save ReplaceNote status
                form.save()
                
                # Process each item in the formset
                for item_form in formset:
                    if item_form.is_valid() and item_form.cleaned_data:
                        item = item_form.save(commit=False)
                        quantity_to_replace = item_form.cleaned_data.get('quantity_to_replace')
                        
                        if quantity_to_replace:
                            item.quantity_to_replace = quantity_to_replace
                            item.save()
                            
                            # Update stock in RawMaterial
                            raw_material = item.raw_material
                            raw_material.add_stock(quantity_to_replace)
                            raw_material.update_quantity()
                            
                            print(f"Updated stock for RawMaterial {raw_material.name}. Current stock: {raw_material.current_stock}")
                
                # Update the replace note status to "delivered"
                replace_note.status = 'delivered'
                replace_note.save()
                
                messages.success(request, "Replacement processed successfully.")
                return redirect('replace_note_details', replace_note_id=replace_note.id)
        else:
            print("Form errors:", form.errors)
            print("Formset errors:", [form.errors for form in formset.forms])
    else:
        form = ReplaceNoteForm(instance=replace_note)
        formset = ReplaceNoteItemFormSet(queryset=ReplaceNoteItem.objects.filter(replace_note=replace_note))
    
    context = {
        'replace_note_form': form,
        'replace_note': replace_note,
        'formset': formset,
    }
    return render(request, 'process_replacement.html', context)

def outstanding_payables(request):
    # Filter LPOs where the outstanding balance is greater than 0
    unpaid_pos = [lpo for lpo in LPO.objects.all() if lpo.outstanding_balance > 0]


    return render(request, 'outstanding_payables.html', {'unpaid_pos': unpaid_pos})