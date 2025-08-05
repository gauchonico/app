from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from io import StringIO, TextIOWrapper
from uuid import uuid4
from django.db.models import OuterRef, Subquery
import os
from django.db import IntegrityError, models
from django.views.decorators.http import require_http_methods
from urllib import error
from django.db.models import Sum, F, Q, Case, When, Count, Value, CharField, Max, Avg
from django.contrib.auth.models import Group
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum, F
from django.utils import timezone
from django.views.generic.edit import DeleteView
from django.views.generic import DetailView, FormView, ListView
import csv
from django.templatetags.static import static
import logging
from POSMagicApp.decorators import unauthenticated_user, allowed_users

from itertools import chain, product
from django.db.models.functions import Coalesce, TruncDate
import json
from django import forms
from django.contrib import messages
from django.forms.formsets import BaseFormSet
from django.forms import DecimalField, ValidationError, formset_factory, inlineformset_factory, modelformset_factory
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay, TruncYear
from POSMagic import settings
from POSMagicApp.decorators import allowed_users
from POSMagicApp.models import Branch, Customer, Staff
from .utils import approve_restock_request, cost_per_unit
from django.core.exceptions import ObjectDoesNotExist
from .forms import AccessorySaleItemForm, AddSupplierForm, ApprovePurchaseForm, ApproveRejectRequestForm, DeliveryRestockRequestForm, IncidentWriteOffForm, PaymentForm, PriceGroupCSVForm, PriceGroupForm, ProductSaleItemForm, ProductionOrderFormSet, RawMaterialUploadForm, ReorderPointForm, RestockApprovalItemForm, BulkUploadForm, BulkUploadRawMaterialForm, BulkUploadRawMaterialPriceForm, DeliveredRequisitionItemForm, EditSupplierForm, AddRawmaterialForm, CreatePurchaseOrderForm, GoodsReceivedNoteForm, InternalAccessoryRequestForm, LPOForm, LivaraMainStoreDeliveredQuantityForm, MainStoreAccessoryRequisitionForm,MainStoreAccessoryRequisitionItemFormSet, ManufactureProductForm, MarkAsDeliveredForm, NewAccessoryForm, ProductionForm,RawMaterialPriceForm, PriceAlertForm, ProductionIngredientForm, ProductionIngredientFormSet, ProductionOrderForm, RawMaterialQuantityForm, ReplaceNoteForm, ReplaceNoteItemForm, ReplaceNoteItemFormSet, RequisitionForm, RequisitionItemForm, RestockRequestForm, RestockRequestItemForm, RestockRequestItemFormset, SaleOrderForm, ServiceNameForm, ServiceSaleForm, ServiceSaleItemForm, StoreAlertForm, StoreForm, StoreSelectionForm, StoreServiceForm, StoreTransferForm,InternalAccessoryRequestItemFormSet, StoreTransferItemForm, StoreWriteOffForm, TestForm, TestItemForm, TestItemFormset, TransferApprovalForm, WriteOffForm
from .models import LPO, Accessory, AccessoryInventory, AccessoryInventoryAdjustment, AccessorySaleItem,RawMaterialPrice, PriceAlert, DebitNote, DiscrepancyDeliveryReport, GoodsReceivedNote, IncidentWriteOff, InternalAccessoryRequest, InternalAccessoryRequestItem, InventoryAdjustment, LivaraInventoryAdjustment, LivaraMainStore, MainStoreAccessoryRequisition, MainStoreAccessoryRequisitionItem, ManufactureProduct, ManufacturedProductIngredient, ManufacturedProductInventory, MonthlyStaffCommission, Notification, Payment, PaymentVoucher, PriceGroup, ProductPrice, ProductSaleItem, ProductionIngredient, Production, ProductionOrder, RawMaterial, RawMaterialInventory, ReplaceNote, ReplaceNoteItem, Requisition, RequisitionItem, RestockRequest, RestockRequestItem, SaleItem, ServiceName, ServiceSale, ServiceSaleInvoice, ServiceSaleItem, StaffCommission, StaffProductCommission, Store, StoreAccessoryInventory, StoreAlerts, StoreInventory, StoreInventoryAdjustment, StoreSale, StoreSaleReceipt, StoreService, StoreTransfer, StoreTransferItem, StoreWriteOff, Supplier, PurchaseOrder, TransferApproval, WriteOff

logger = logging.getLogger(__name__)
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
    total_stock_value = sum(material.quantity for material in rawmaterials)
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
    rawmaterials = RawMaterial.objects.filter(suppliers=supplier)
    requisitions = Requisition.objects.filter(supplier=supplier)
    
    # Get the breakdown of raw materials for the specific supplier with last delivery date
    breakdown = RequisitionItem.objects.filter(
        requisition__supplier=supplier
    ).values(
        'raw_material__name'
    ).annotate(
        total_delivered=Sum('delivered_quantity'),
        last_delivery=Max('requisition__updated_at')
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
    # Add suppliers to each raw material object for easier access in the template
    for rawmaterial in rawmaterials:
        rawmaterial.suppliers_list = rawmaterial.suppliers.all()
    context = {
        'rawmaterials': rawmaterials,
        
    }

    return render(request, "raw-materials-list.html", context)

def upload_raw_materials(request):
    if request.method == "POST" and request.FILES["csv_file"]:
        csv_file = request.FILES["csv_file"]

        # Ensure it's a CSV file
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Please upload a CSV file.")

        # Parse the CSV file
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        csv_reader = csv.reader(decoded_file)
        
        # Skip the header row if it exists
        next(csv_reader, None)
        updated_count = 0  # To keep track of how many records were updated

        for row in csv_reader:
            # Assuming each row has 'RawMaterial name' and 'Comma separated list of supplier names'
            rawmaterial_name = row[0].strip()
            suppliers_names = row[1].strip().split(',')

            # Find the raw material by name, or create if not found
            rawmaterial, created = RawMaterial.objects.get_or_create(name=rawmaterial_name)

            # For each supplier, add them to the raw material's suppliers
            for supplier_name in suppliers_names:
                supplier_name = supplier_name.strip()
                supplier = Supplier.objects.filter(name=supplier_name).first()
                if supplier:
                    rawmaterial.suppliers.add(supplier)
            
            rawmaterial.save()

        return redirect("rawmaterialsList")
    
    form = RawMaterialUploadForm()
    return render(request, 'upload_raw_materials.html', {'form': form})

def rawamaterialsTable(request):
    rawmaterials = RawMaterial.objects.all()
    # Add suppliers to each raw material object for easier access in the template
    for rawmaterial in rawmaterials:
        rawmaterial.suppliers_list = rawmaterial.suppliers.all()
    return render(request, 'raw-materials-table.html', {'rawmaterials': rawmaterials})

@login_required(login_url='/login/')
def addRawmaterial(request):
    form = AddRawmaterialForm() 
    bulk_form = BulkUploadRawMaterialForm()
    if request.method == 'POST':
        if 'bulk_upload' in request.POST:
            bulk_form = BulkUploadRawMaterialForm(request.POST, request.FILES)
            if bulk_form.is_valid():
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
def update_reorder_point(request, pk):
    raw_material = get_object_or_404(RawMaterial, pk=pk)

    if request.method == 'POST':
        form = ReorderPointForm(request.POST, instance=raw_material)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reorder point updated successfully.')
            return redirect('rawmaterialsList')  # Replace with your list view URL
    else:
        form = ReorderPointForm(instance=raw_material)

    return render(request, 'update_reorder_point.html', {'form': form, 'raw_material': raw_material})

@login_required(login_url='/login/')
def create_incident_write_off(request):
    if request.method == 'POST':
        form = IncidentWriteOffForm(request.POST)
        if form.is_valid():
            write_off = form.save(commit=False)
            write_off.written_off_by = request.user  # Add logged-in user
            write_off.save()
            messages.success(request, f"Incident report writeoff has been initiated")
            return redirect('incident_write_off_list')  # Redirect to a list view
    else:
        # Check if raw_material parameter is provided
        raw_material_id = request.GET.get('raw_material')
        if raw_material_id:
            try:
                raw_material = RawMaterial.objects.get(id=raw_material_id)
                form = IncidentWriteOffForm(initial={'raw_material': raw_material})
            except RawMaterial.DoesNotExist:
                form = IncidentWriteOffForm()
        else:
            form = IncidentWriteOffForm()
    return render(request, 'incident_write_off_form.html', {'form': form})

@login_required(login_url='/login/')
def approve_incident_write_off(request, pk):
    try:
        write_off = get_object_or_404(IncidentWriteOff, pk=pk)
        
        if write_off.status == 'pending':
            with transaction.atomic():
                # Update the write-off status
                write_off.status = 'approved'
                write_off.save()

                # Deduct from raw material inventory
                raw_material = write_off.raw_material
                
                # Create inventory adjustment record
                RawMaterialInventory.objects.create(
                    raw_material=raw_material,
                    adjustment=-write_off.quantity  # Negative for deductions
                )
                
                messages.success(request, f"Write-off for {raw_material.name} has been approved successfully.")
        else:
            messages.warning(request, f"This write-off is already {write_off.status}.")
            
    except Exception as e:
        messages.error(request, f"Error approving write-off: {str(e)}")
    
    return redirect('incident_write_off_list')

def calculate_incident_write_off_loss(write_off):
    """Helper function to calculate financial loss for an incident write-off"""
    total_loss = Decimal('0.00')
    price_per_unit = Decimal('0.00')
    price_source = "No requisition history found"
    
    try:
        # Get the most recent requisition item for this raw material
        latest_requisition_item = RequisitionItem.objects.filter(
            raw_material=write_off.raw_material,
            price_per_unit__gt=0  # Only consider items with valid prices
        ).order_by('-requisition__created_at').first()
        
        if latest_requisition_item:
            price_per_unit = latest_requisition_item.price_per_unit
            total_loss = write_off.quantity * price_per_unit
            price_source = f"Latest requisition: {latest_requisition_item.requisition.requisition_no}"
        else:
            # Try to get from RawMaterialPrice if no requisition history
            latest_price = RawMaterialPrice.objects.filter(
                raw_material=write_off.raw_material,
                is_current=True
            ).order_by('-effective_date').first()
            
            if latest_price:
                price_per_unit = latest_price.price
                total_loss = write_off.quantity * price_per_unit
                price_source = f"Market price: {latest_price.supplier.name}"
            else:
                price_source = "No pricing information available"
                
    except Exception as e:
        price_source = f"Error calculating price: {str(e)}"
    
    return {
        'total_loss': total_loss,
        'price_per_unit': price_per_unit,
        'price_source': price_source,
    }

@login_required(login_url='/login/')
def incident_write_off_list(request):
    write_offs = IncidentWriteOff.objects.all().order_by('-date')
    
    # Calculate financial loss for each write-off
    write_offs_with_loss = []
    total_company_loss = Decimal('0.00')
    
    for write_off in write_offs:
        loss_data = calculate_incident_write_off_loss(write_off)
        write_off.total_loss = loss_data['total_loss']
        write_off.price_per_unit = loss_data['price_per_unit']
        write_off.price_source = loss_data['price_source']
        write_offs_with_loss.append(write_off)
        total_company_loss += loss_data['total_loss']
    
    context = {
        'write_offs': write_offs_with_loss,
        'total_company_loss': total_company_loss,
    }
    return render(request, "incident_write_off_list.html", context)

@login_required(login_url='/login/')
def incident_write_off_detail(request, write_off_id):
    write_off = get_object_or_404(IncidentWriteOff, pk=write_off_id)
    
    # Calculate financial loss using helper function
    loss_data = calculate_incident_write_off_loss(write_off)
    
    context = {
        'write_off': write_off,
        'total_loss': loss_data['total_loss'],
        'price_per_unit': loss_data['price_per_unit'],
        'price_source': loss_data['price_source'],
    }
    return render(request, "incident_write_off_detail.html", context)

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

#PRICE GROUPS 
#Create Price Group
@login_required(login_url='/login/')
def create_price_group(request):
    """Create a new price group."""
    if request.method == 'POST':
        form = PriceGroupForm(request.POST)
        if form.is_valid():
            price_group = form.save()
            messages.success(request, f"Price group '{price_group.name}' created successfully!")
            return redirect('view_pricing_groups')
    else:
        form = PriceGroupForm()

    context = {
        'form': form,
    }
    return render(request, 'create_price_group.html', context)
@login_required(login_url='/login/')
def view_pricing_groups(request):
    pricing_groups = PriceGroup.objects.all()
    if request.method == 'POST':
        # Handle CSV Upload
        csv_form = PriceGroupCSVForm(request.POST, request.FILES)
        if csv_form.is_valid():
            price_group = csv_form.cleaned_data['price_group']
            csv_file = csv_form.cleaned_data['file']
            try:
                handle_csv_upload(csv_file, price_group)
                messages.success(request, f"Prices updated for {price_group.name} successfully!")
            except Exception as e:
                messages.error(request, f"Error processing CSV: {e}")
            return redirect('view_pricing_groups')
    else:
        csv_form = PriceGroupCSVForm()

    context = {
        'pricing_groups': pricing_groups,
        'csv_form': csv_form,
    }
    return render(request, 'view-pricing-groups.html', context)

def toggle_price_group(request, pk):
    """Activate or deactivate a price group."""
    if request.method == 'POST':
        price_group = get_object_or_404(PriceGroup, pk=pk)
        price_group.is_active = not price_group.is_active
        price_group.save()
        return JsonResponse({'success': True, 'is_active': price_group.is_active})
    return JsonResponse({'success': False})

def price_group_details(request, pk):
    """View details of a specific price group."""
    price_group = get_object_or_404(PriceGroup, pk=pk)
    product_prices = ProductPrice.objects.filter(price_group=price_group)

    context = {
        'price_group': price_group,
        'product_prices': product_prices,
    }
    return render(request, 'price_group_details.html', context)

def handle_csv_upload(csv_file, price_group):
    """Handle the uploaded CSV to bulk update or add product prices."""
    try:
        # Read the file content
        decoded_file = csv_file.read().decode('utf-8-sig')  # Handle BOM if present
        csv_reader = csv.DictReader(StringIO(decoded_file))
        
        # Validate CSV headers
        required_headers = {'product_name', 'price'}
        headers = set(csv_reader.fieldnames) if csv_reader.fieldnames else set()
        
        if not required_headers.issubset(headers):
            missing = required_headers - headers
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        success_count = 0
        errors = []

        with transaction.atomic():
            for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 to account for header row
                try:
                    # Validate row data
                    product_name = row.get('product_name', '').strip()
                    price = row.get('price', '').strip()

                    if not product_name:
                        errors.append(f"Row {row_num}: Product name is empty")
                        continue

                    if not price:
                        errors.append(f"Row {row_num}: Price is empty")
                        continue

                    try:
                        price = float(price)
                        if price < 0:
                            errors.append(f"Row {row_num}: Price cannot be negative")
                            continue
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid price format - {price}")
                        continue

                    # Try to find the product
                    try:
                        product = Production.objects.get(product_name=product_name)
                    except Production.DoesNotExist:
                        errors.append(f"Row {row_num}: Product not found - {product_name}")
                        continue

                    # Create or update price
                    ProductPrice.objects.update_or_create(
                        product=product,
                        price_group=price_group,
                        defaults={'price': price}
                    )
                    success_count += 1

                except Exception as e:
                    errors.append(f"Row {row_num}: Unexpected error - {str(e)}")

        # If there were any errors, raise them
        if errors:
            error_message = "\n".join(errors)
            if success_count > 0:
                error_message = f"Partially successful: {success_count} prices updated.\nErrors:\n{error_message}"
            raise ValueError(error_message)

        return success_count

    except Exception as e:
        raise ValueError(f"Error processing CSV: {str(e)}")
    
# Create Services
@login_required
def create_service(request):
    if request.method == 'POST':
        form = ServiceNameForm(request.POST)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service "{service.name}" created successfully!')
            return redirect('service_list')
    else:
        form = ServiceNameForm()
    
    context = {
        'form': form,
        'title': 'Create New Service',
        'button_text': 'Create Service'
    }
            
    return render(request, 'services/service_form.html', context)

@login_required
def upload_store_services(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please upload a CSV file')
            return redirect('upload_store_services')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File must be a CSV')
            return redirect('upload_store_services')

        # Process CSV file
        try:
            decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_rows = []
            
            with transaction.atomic():
                for row_number, row in enumerate(reader, start=2):  # Start at 2 to account for header row
                    try:
                        # Get or create service
                        service, created = ServiceName.objects.get_or_create(
                            name=row['service_name'],
                            defaults={'price': float(row['price'])}
                        )
                        
                        # If service exists but price is different, update it
                        if not created and service.price != float(row['price']):
                            service.price = float(row['price'])
                            service.save()

                        # Get store
                        try:
                            store = Store.objects.get(name=row['store_name'])
                        except Store.DoesNotExist:
                            error_rows.append(f"Row {row_number}: Store '{row['store_name']}' not found")
                            continue

                        # Create store service
                        store_service, created = StoreService.objects.get_or_create(
                            store=store,
                            service=service,
                            defaults={'commission_rate': float(row['commission_rate'])}
                        )

                        # If store service exists but commission rate is different, update it
                        if not created and store_service.commission_rate != float(row['commission_rate']):
                            store_service.commission_rate = float(row['commission_rate'])
                            store_service.save()

                        success_count += 1

                    except Exception as e:
                        error_rows.append(f"Row {row_number}: {str(e)}")

            if error_rows:
                messages.warning(request, f"Processed with {len(error_rows)} errors. {success_count} services were created/updated successfully.")
                for error in error_rows:
                    messages.error(request, error)
            else:
                messages.success(request, f"Successfully processed {success_count} services")

        except Exception as e:
            messages.error(request, f"Error processing CSV file: {str(e)}")
            
    return render(request, 'services/bulk_service_upload.html')

@login_required
def download_service_template(request):
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="store_services_template.csv"'

    # Create the CSV writer
    writer = csv.writer(response)
    
    # Write the header row
    writer.writerow(['store_name', 'service_name', 'price', 'commission_rate'])
    
    # Write a sample row
    writer.writerow(['Store Name', 'Hair Cut', '2000', '0.10'])

    return response

@login_required
def service_list(request):
    services = ServiceName.objects.all().order_by('name')
    return render(request, 'services/service_list.html', {'services': services})

@login_required
def assign_service_to_store(request):
    if request.method == 'POST':
        form = StoreServiceForm(request.POST)
        if form.is_valid():
            store_service = form.save()
            messages.success(request, f'Service "{store_service.service.name}" assigned to {store_service.store.name} successfully!')
            return redirect('store_service_list_detail')  # Fixed the redirect
    else:
        form = StoreServiceForm()
    
    context = {
        'form': form,
        'title': 'Assign Service to Store',
        'button_text': 'Assign Service'
    }
    return render(request, 'services/assign_service.html', context)

@login_required
def store_service_list_detail(request):
    store_services = StoreService.objects.all().select_related('store', 'service')
    return render(request, 'services/store_service_list_detail.html', {
        'store_services': store_services
    })

@login_required
def edit_store_service(request, pk):
    service = get_object_or_404(ServiceName, pk=pk)
    if request.method == 'POST':
        form = ServiceNameForm(request.POST, instance=service)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service "{service.name}" updated successfully!')
            return redirect('service_list')
    else:
        form = ServiceNameForm(instance=service)
    
    context = {
        'form': form,
        'title': f'Edit Service: {service.name}',
        'button_text': 'Update Service'
    }
    
    return render(request, 'services/service_form.html', context)

@login_required
def delete_service(request, pk):
    service = get_object_or_404(ServiceName, pk=pk)
    if request.method == 'POST':
        service_name = service.name
        service.delete()
        messages.success(request, f'Service "{service_name}" deleted successfully!')
        return redirect('service_list')
    
    context = {
        'service': service,
        'title': 'Delete Service'
    }
    return render(request, 'services/service_confirm_delete.html', context)


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

@require_POST
@login_required(login_url='/login/')
def delete_ingredient(request, ingredient_id):
    """Delete a specific ingredient from a product"""
    try:
        ingredient = ProductionIngredient.objects.get(id=ingredient_id)
        ingredient_name = ingredient.raw_material.name
        ingredient.delete()
        return JsonResponse({
            'success': True,
            'message': f'Ingredient "{ingredient_name}" deleted successfully'
        })
    except ProductionIngredient.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Ingredient not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required(login_url='/login/')
def bulk_upload_raw_material_prices(request):
    """Bulk upload raw material prices from CSV file"""
    if request.method == 'POST':
        form = BulkUploadRawMaterialPriceForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            try:
                # Decode the file content
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                
                success_count = 0
                error_count = 0
                errors = []
                
                for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                    try:
                        # Get raw material by name
                        raw_material_name = row.get('raw_material_name', '').strip()
                        if not raw_material_name:
                            errors.append(f"Row {row_num}: Raw material name is required")
                            error_count += 1
                            continue
                            
                        try:
                            raw_material = RawMaterial.objects.get(name__iexact=raw_material_name)
                        except RawMaterial.DoesNotExist:
                            errors.append(f"Row {row_num}: Raw material '{raw_material_name}' not found")
                            error_count += 1
                            continue
                        
                        # Get supplier by name
                        supplier_name = row.get('supplier_name', '').strip()
                        if not supplier_name:
                            errors.append(f"Row {row_num}: Supplier name is required")
                            error_count += 1
                            continue
                            
                        try:
                            supplier = Supplier.objects.get(name__iexact=supplier_name)
                        except Supplier.DoesNotExist:
                            errors.append(f"Row {row_num}: Supplier '{supplier_name}' not found")
                            error_count += 1
                            continue
                        
                        # Parse price
                        price_str = row.get('price', '').strip()
                        if not price_str:
                            errors.append(f"Row {row_num}: Price is required")
                            error_count += 1
                            continue
                            
                        try:
                            price = Decimal(price_str)
                            if price <= 0:
                                raise ValueError("Price must be positive")
                        except (ValueError, InvalidOperation):
                            errors.append(f"Row {row_num}: Invalid price '{price_str}'")
                            error_count += 1
                            continue
                        
                        # Parse effective date (optional, default to now)
                        effective_date_str = row.get('effective_date', '').strip()
                        if effective_date_str:
                            try:
                                effective_date = datetime.strptime(effective_date_str, '%Y-%m-%d')
                                effective_date = timezone.make_aware(effective_date)
                            except ValueError:
                                errors.append(f"Row {row_num}: Invalid date format '{effective_date_str}'. Use YYYY-MM-DD")
                                error_count += 1
                                continue
                        else:
                            effective_date = timezone.now()
                        
                        # Check if is_current should be set
                        is_current_str = row.get('is_current', 'true').strip().lower()
                        is_current = is_current_str in ['true', '1', 'yes', 'y']
                        
                        # Create the price record
                        price_record = RawMaterialPrice.objects.create(
                            raw_material=raw_material,
                            supplier=supplier,
                            price=price,
                            effective_date=effective_date,
                            is_current=is_current
                        )
                        
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
                
                # Prepare response message
                if success_count > 0:
                    messages.success(request, f"Successfully uploaded {success_count} price records.")
                
                if error_count > 0:
                    error_message = f"Failed to upload {error_count} records. "
                    if len(errors) <= 5:
                        error_message += "Errors: " + "; ".join(errors)
                    else:
                        error_message += f"First 5 errors: {'; '.join(errors[:5])}... (and {len(errors) - 5} more)"
                    messages.error(request, error_message)
                
                return redirect('bulk_upload_raw_material_prices')
                
            except Exception as e:
                messages.error(request, f"Error processing CSV file: {str(e)}")
    else:
        form = BulkUploadRawMaterialPriceForm()
    
    return render(request, 'bulk_upload_raw_material_prices.html', {'form': form})

@login_required(login_url='/login/')
def download_raw_material_price_template(request):
    """Download CSV template for raw material price bulk upload"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="raw_material_price_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['raw_material_name', 'supplier_name', 'price', 'effective_date', 'is_current'])
    
    # Add some example rows
    writer.writerow(['Sugar', 'ABC Suppliers', '150.00', '2024-01-15', 'true'])
    writer.writerow(['Flour', 'XYZ Company', '200.50', '2024-01-15', 'true'])
    writer.writerow(['Salt', 'ABC Suppliers', '25.00', '2024-01-15', 'false'])
    
    return response

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
            ingredient_usage = []
            with transaction.atomic():
                for ingredient in product.productioningredients.all():
                    quantity_needed = ingredient.quantity_per_unit_product_volume * quantity
                    base_quantity_needed = convert_to_base_unit(quantity_needed, ingredient.raw_material.unit_measurement)
                    
                    if ingredient.raw_material.current_stock < base_quantity_needed:
                        insufficient_ingredients.append(
                            f"Insufficient stock for {ingredient.raw_material.name}. "
                            f"Required: {quantity_needed}, Available: {ingredient.raw_material.current_stock}"
                        )
                        sufficient_stock = False
                    else:
                        ingredient_usage.append({
                            'ingredient': ingredient,
                            'quantity_used': quantity_needed,
                        })

                if sufficient_stock:
                    # Deduct raw materials
                    deduct_raw_materials(product, quantity)
                    
                    # Create ManufactureProduct instance
                    manufacture_product = ManufactureProduct.objects.create(
                        product=product,
                        quantity=quantity,
                        notes=notes,
                        expiry_date=expiry_date,
                        production_order=production_order
                    )
                    manufacture_product.batch_number = manufacture_product.generate_batch_number()
                    manufacture_product.save()
                    
                    # Update manufactured product inventory
                    manufactured_product_inventory, created = ManufacturedProductInventory.objects.get_or_create(
                        product=product,
                        batch_number=manufacture_product.batch_number,
                        defaults={'quantity': Decimal(str(quantity)), 'expiry_date': expiry_date}
                    )
                    if not created:
                        manufactured_product_inventory.quantity += quantity
                        manufactured_product_inventory.save()

                    # Calculate cost per ingredient
                    cost_per = cost_per_unit(product)
                    total_cost = sum(cost_data['cost_per_unit'] for cost_data in cost_per)
                    
                    # Log used ingredients if using ManufacturedProductIngredient model
                    for usage in ingredient_usage:
                        ManufacturedProductIngredient.objects.create(
                            manufactured_product=manufacture_product,
                            raw_material=usage['ingredient'].raw_material,
                            quantity_used=usage['quantity_used']
                        )
                    
                    # Update Production Order Status
                    if production_order:
                        production_order.status = 'Completed'
                        production_order.save()

                    context = {
                        'cost_per': cost_per,
                        'total_cost': total_cost,
                    }

                    messages.success(request, f"Successfully manufactured {quantity} units of {product.product_name}")
                    return redirect('manufacturedProductList')
                else:
                    # Display all insufficient stock errors at once
                    for error in insufficient_ingredients:
                        messages.error(request, error)
        else:
                messages.error(request, "Please correct the errors in the form.")
    else:
        form = ManufactureProductForm(product=product)  # Create an empty form instance for GET requests
        
        # Auto-populate quantity if production order is selected via GET parameter
        production_order_id = request.GET.get('production_order')
        if production_order_id:
            try:
                production_order = ProductionOrder.objects.get(id=production_order_id, product=product, status='In-progre')
                form.initial['production_order'] = production_order
                form.initial['quantity'] = production_order.approved_quantity
            except ProductionOrder.DoesNotExist:
                pass

    return render(request, 'manufacture-product.html', {'product': product, 'form': form})

def manufactured_products_report(request):
    period = request.GET.get('period', 'month')  # 'month', 'week', 'day'
    
    if period == 'month':
        truncate_func = TruncMonth
        date_range = timezone.now() - timezone.timedelta(days=365)
    elif period == 'week':
        truncate_func = TruncWeek
        date_range = timezone.now() - timezone.timedelta(weeks=52)  # Last year in weeks
    elif period == 'day':
        truncate_func = TruncDay
        date_range = timezone.now() - timezone.timedelta(days=30)
    elif period == 'year':
        truncate_func = TruncYear
        date_range = timezone.now() - timezone.timedelta(days=365 * 5)
    else:
        truncate_func = TruncMonth
    
    # Query the ManufactureProduct model and group by period and product
    manufactured_products = (
        ManufactureProduct.objects.filter(manufactured_at__gte=date_range)
        .annotate(period=truncate_func('manufactured_at'))
        .values('period', 'product__product_name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('period', 'product__product_name')
    )
    
    context = {
        'manufactured_products': manufactured_products,
        'period': period
    }
    
    return render(request, 'manufactured_products_report.html', context)

def raw_material_utilization_report(request):
    selected_date_str = request.GET.get('date')
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date() if selected_date_str else timezone.now().date()
    
    
    # Get usage adjustments grouped by raw material and period
    raw_material_usage = (
        RawMaterialInventory.objects.filter(last_updated__date=(selected_date))
        .values('raw_material__name', 'raw_material__unit_measurement')
        .annotate(
            initial_stock=Sum(F('raw_material__quantity') - F('adjustment')),  # Stock before usage
            total_usage=Sum('adjustment'),  # Total adjustment within period
            final_stock=F('raw_material__quantity')  # Latest stock after adjustments
        )
        .order_by('raw_material__name', )
    )
    
    # Organize data by raw material
    grouped_data = {}
    for entry in raw_material_usage:
        raw_material_name = entry['raw_material__name']
        if raw_material_name not in grouped_data:
            grouped_data[raw_material_name] = []
        grouped_data[raw_material_name].append(entry)
    
    context = {
        'grouped_data': grouped_data,
        'selected_date': selected_date,
    }
    
    return render(request, 'raw_material_utilization_report.html', context)

from django.db.models import Sum, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from django.utils import timezone
from django.shortcuts import render
from decimal import Decimal

def raw_material_utilization_reports(request):
    # Get period and date parameters
    start_date_str = request.GET.get('start_date', timezone.now().strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', start_date_str)  # Default to the same day if not provided

    # Parse the start and end dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    # Determine truncation function based on selected period
    period = request.GET.get('period', 'day')
    if period == 'day':
        truncate_func = TruncDay
    elif period == 'week':
        truncate_func = TruncWeek
    elif period == 'month':
        truncate_func = TruncMonth
    elif period == 'year':
        truncate_func = TruncYear
    else:
        truncate_func = None  # No truncation for custom date ranges without grouping

    # Filter usage within the specified date range
    usage_queryset = ManufacturedProductIngredient.objects.filter(
        manufactured_product__manufactured_at__range=(start_date, end_date)
    )

    # Apply truncation if a period is specified
    if truncate_func:
        usage_queryset = usage_queryset.annotate(period=truncate_func('manufactured_product__manufactured_at'))
    else:
        usage_queryset = usage_queryset.annotate(period=F('manufactured_product__manufactured_at'))


    # Get raw material usage data within the specified date range
    raw_material_usage = (
        ManufacturedProductIngredient.objects.filter(
            manufactured_product__manufactured_at__range=(start_date, end_date)
        )
        .annotate(period=truncate_func('manufactured_product__manufactured_at'))
        .values('raw_material__id', 'raw_material__name', 'manufactured_product__product__product_name', 'period')
        .annotate(
            total_usage=Sum('quantity_used')
        )
        .order_by('raw_material__name', 'manufactured_product__product__product_name', 'period')
    )

    # Calculate opening and closing stocks for each raw material
    grouped_data = {}
    for entry in raw_material_usage:
        raw_material = RawMaterial.objects.get(id=entry['raw_material__id'])
        period_start = entry['period']

        # Opening stock as of the beginning of the selected day/period
        opening_stock = (
            RawMaterialInventory.objects.filter(raw_material=raw_material, last_updated__lt=period_start)
            .aggregate(opening_stock=Sum('adjustment'))['opening_stock'] or Decimal(0)
        )

        # Total usage within the period
        total_usage = entry['total_usage'] or Decimal(0)

        # Calculate closing stock as opening stock minus total usage
        closing_stock = opening_stock - total_usage

        # Organize data for the report
        key = f"{entry['raw_material__name']} - {entry['manufactured_product__product__product_name']} - {period_start}"
        grouped_data[key] = {
            'raw_material': entry['raw_material__name'],
            'product': entry['manufactured_product__product__product_name'],
            'period': period_start,
            'opening_stock': opening_stock,
            'total_usage': total_usage,
            'closing_stock': closing_stock,
        }

    # Pass the data to the template
    context = {
        'grouped_data': grouped_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'raw_material_utilization_reports.html', context)


def raw_material_date_report(request):
    # Retrieve selected date range from the form, default to today if not provided
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    if from_date_str and to_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    else:
        # Default to today if no dates provided
        from_date = to_date = timezone.now().date()

    # Query for raw materials with separate additions and deductions, and closing stock calculations
    raw_materials = RawMaterial.objects.annotate(
        # Calculate stock up to the from_date, renamed to 'previous_stock' to avoid conflict
        previous_stock=Sum(
            'rawmaterialinventory__adjustment',
            filter=Q(rawmaterialinventory__last_updated__lt=from_date), 
            default=0
        ),
        # Calculate additions during the date range
        additions=Coalesce(Sum(
            'rawmaterialinventory__adjustment',
            filter=Q(rawmaterialinventory__adjustment__gt=0) & 
                   Q(rawmaterialinventory__last_updated__date__gte=from_date) &
                   Q(rawmaterialinventory__last_updated__date__lte=to_date)
        ),Decimal(0)),
        # Calculate deductions during the date range (including incident write-offs)
        deductions=Coalesce(Sum(
            'rawmaterialinventory__adjustment',
            filter=Q(rawmaterialinventory__adjustment__lt=0) & 
                   Q(rawmaterialinventory__last_updated__date__gte=from_date) &
                   Q(rawmaterialinventory__last_updated__date__lte=to_date)
        ),Decimal(0) )
    ).annotate(
        # Calculate closing stock based on previous_stock, additions, and deductions
        closing_stock=F('previous_stock') + (F('additions')) + (F('deductions'))
    )
    
    # Get requisitions delivered during the date range (for additions)
    requisitions_delivered = Requisition.objects.filter(
        status='delivered',
        updated_at__date__gte=from_date,
        updated_at__date__lte=to_date
    ).prefetch_related('requisitionitem_set__raw_material')
    
    # Get manufacturing records during the date range (for deductions)
    manufacturing_records = ManufactureProduct.objects.filter(
        manufactured_at__date__gte=from_date,
        manufactured_at__date__lte=to_date
    ).prefetch_related('used_ingredients__raw_material')
    
    # Get incident write-offs during the date range (for deductions)
    incident_write_offs = IncidentWriteOff.objects.filter(
        date__gte=from_date,
        date__lte=to_date,
        status='approved'
    ).select_related('raw_material', 'written_off_by')
    
    # Create a mapping of raw material to its related transactions
    raw_material_transactions = {}
    
    for material in raw_materials:
        material_transactions = {
            'additions': [],
            'deductions': []
        }
        
        # Find requisitions that added this material
        requisition_additions = {}
        for requisition in requisitions_delivered:
            for item in requisition.requisitionitem_set.all():
                if item.raw_material == material:
                    # Use requisition ID as key to prevent duplicates
                    if requisition.id not in requisition_additions:
                        requisition_additions[requisition.id] = {
                            'type': 'requisition',
                            'id': requisition.id,
                            'number': requisition.requisition_no,
                            'quantity': item.delivered_quantity,
                            'date': requisition.updated_at,
                            'supplier': requisition.supplier.name
                        }
                    else:
                        # If same requisition has this material multiple times, sum the quantities
                        requisition_additions[requisition.id]['quantity'] += item.delivered_quantity
        
        # Add unique requisition additions to the list
        material_transactions['additions'].extend(requisition_additions.values())
        
        # Find manufacturing records that consumed this material
        manufacturing_deductions = {}
        for manufacturing in manufacturing_records:
            for ingredient in manufacturing.used_ingredients.all():
                if ingredient.raw_material == material:
                    # Use manufacturing ID as key to prevent duplicates
                    if manufacturing.id not in manufacturing_deductions:
                        manufacturing_deductions[manufacturing.id] = {
                            'type': 'manufacturing',
                            'id': manufacturing.id,
                            'batch_number': manufacturing.batch_number,
                            'quantity': ingredient.quantity_used,
                            'date': manufacturing.manufactured_at,
                            'product': manufacturing.product.product_name
                        }
                    else:
                        # If same manufacturing record uses this material multiple times, sum the quantities
                        manufacturing_deductions[manufacturing.id]['quantity'] += ingredient.quantity_used
        
        # Add unique manufacturing deductions to the list
        material_transactions['deductions'].extend(manufacturing_deductions.values())
        
        # Find incident write-offs for this material
        for write_off in incident_write_offs:
            if write_off.raw_material == material:
                material_transactions['deductions'].append({
                    'type': 'incident_write_off',
                    'id': write_off.id,
                    'quantity': write_off.quantity,
                    'date': write_off.date,
                    'reason': write_off.reason,
                    'written_off_by': write_off.written_off_by.get_full_name() if write_off.written_off_by else 'Unknown'
                })
        
        raw_material_transactions[material.id] = material_transactions
    
    # Now we need to manually adjust the deductions and closing stock to include incident write-offs
    # since they are not included in the RawMaterialInventory calculations
    for material in raw_materials:
        # Calculate total incident write-off deductions for this material during the date range
        incident_deductions = sum(
            write_off.quantity 
            for write_off in incident_write_offs 
            if write_off.raw_material == material
        )
        
        # Add incident write-off deductions to the material's deductions
        material.deductions -= incident_deductions  # Subtract because deductions are negative
        
        # Recalculate closing stock
        material.closing_stock = material.previous_stock + material.additions + material.deductions
    
    context = {
        'raw_materials': raw_materials,
        'from_date': from_date,
        'to_date': to_date,
        'raw_material_transactions': raw_material_transactions,
    }
    return render(request, 'raw_material_date_report.html', context)

def raw_material_additions_detail(request):
    """Detailed view of all additions for a specific raw material during a date range"""
    raw_material_id = request.GET.get('material_id')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    if not raw_material_id:
        messages.error(request, 'Raw material ID is required')
        return redirect('raw_material_date_report')
    
    try:
        raw_material = RawMaterial.objects.get(id=raw_material_id)
    except RawMaterial.DoesNotExist:
        messages.error(request, 'Raw material not found')
        return redirect('raw_material_date_report')
    
    if from_date_str and to_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    else:
        from_date = to_date = timezone.now().date()
    
    # Get all additions for this material during the date range
    additions = []
    
    # Get requisitions that added this material
    requisitions_delivered = Requisition.objects.filter(
        status='delivered',
        updated_at__date__gte=from_date,
        updated_at__date__lte=to_date,
        requisitionitem__raw_material=raw_material
    ).prefetch_related('requisitionitem_set')
    
    # Group by requisition to avoid duplicates
    requisition_totals = {}
    for requisition in requisitions_delivered:
        total_quantity = 0
        for item in requisition.requisitionitem_set.all():
            if item.raw_material == raw_material:
                total_quantity += item.delivered_quantity
        
        if total_quantity > 0:  # Only add if there was actual delivery
            requisition_totals[requisition.id] = {
                'requisition': requisition,
                'total_quantity': total_quantity
            }
    
    # Add unique requisitions to additions list
    for req_id, req_data in requisition_totals.items():
        requisition = req_data['requisition']
        additions.append({
            'type': 'requisition',
            'date': requisition.updated_at,
            'reference': requisition.id,  # Use integer id for URL
            'reference_display': requisition.requisition_no,  # Use string for display
            'quantity': req_data['total_quantity'],
            'supplier': requisition.supplier.name,
            'description': f'Delivered from {requisition.supplier.name}'
        })
    
    # # Get inventory adjustments that added this material
    # inventory_additions = RawMaterialInventory.objects.filter(
    #     raw_material=raw_material,
    #     adjustment__gt=0,
    #     last_updated__date__gte=from_date,
    #     last_updated__date__lte=to_date
    # ).order_by('last_updated')
    
    # for adjustment in inventory_additions:
    #     additions.append({
    #         'type': 'inventory_adjustment',
    #         'date': adjustment.last_updated,
    #         'reference': f'Adjustment #{adjustment.id}',
    #         'quantity': adjustment.adjustment,
    #         'description': 'Manual inventory adjustment'
    #     })
    
    # Sort all additions by date
    additions.sort(key=lambda x: x['date'], reverse=True)
    
    context = {
        'raw_material': raw_material,
        'additions': additions,
        'from_date': from_date,
        'to_date': to_date,
        'total_additions': sum(item['quantity'] for item in additions)
    }
    return render(request, 'raw_material_additions_detail.html', context)

def raw_material_deductions_detail(request):
    """Detailed view of all deductions for a specific raw material during a date range"""
    
    raw_material_id = request.GET.get('material_id')
    if not raw_material_id:
        messages.error(request, 'Raw material ID is required')
        return redirect('raw_material_date_report')
    
    try:
        raw_material = RawMaterial.objects.get(id=raw_material_id)
    except RawMaterial.DoesNotExist:
        messages.error(request, 'Raw material not found')
        return redirect('raw_material_date_report')
    
    # Get date parameters from request
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    if from_date_str and to_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    else:
        from_date = to_date = timezone.now().date()
    
    # Get all deductions for this material during the date range
    deductions = []
    
    # Get manufacturing records that consumed this material
    manufacturing_records = ManufactureProduct.objects.filter(
        manufactured_at__date__gte=from_date,
        manufactured_at__date__lte=to_date,
        used_ingredients__raw_material=raw_material
    ).distinct().prefetch_related('used_ingredients')
    
    for manufacturing in manufacturing_records:
        # Get the exact quantity of this raw material used in this manufacturing process
        # from the ManufacturedProductIngredient records
        ingredient_record = manufacturing.used_ingredients.filter(raw_material=raw_material).first()
        
        if ingredient_record:
            # The quantity_used is stored in base unit (grams, milliliters, etc.)
            # Convert to display unit if needed (Kilograms, Litres)
            quantity_used = ingredient_record.quantity_used
            
            # Convert to display unit based on raw material's unit of measurement
            unit_of_measurement = raw_material.unit_measurement
            if unit_of_measurement in ['Kilograms', 'Litres', 'Liters']:
                # Convert from base unit (grams/ml) to display unit (kg/l)
                quantity_used = quantity_used / 1000
            
            deductions.append({
                'type': 'manufacturing',
                'date': manufacturing.manufactured_at,
                'reference': manufacturing.id,
                'reference_display': manufacturing.batch_number,
                'quantity': quantity_used,  # Now in display units
                'description': f'Used in manufacturing {manufacturing.product.product_name}',
                'product': manufacturing.product.product_name
            })
    
    # Get incident write-offs for this material
    incident_write_offs = IncidentWriteOff.objects.filter(
        raw_material=raw_material,
        date__gte=from_date,
        date__lte=to_date,
        status='approved'
    ).select_related('written_off_by')
    
    for write_off in incident_write_offs:
        deductions.append({
            'type': 'incident_write_off',
            'date': timezone.make_aware(datetime.combine(write_off.date, datetime.min.time())),
            'reference': write_off.id,  # Use integer id for URL
            'reference_display': f'Write-off #{write_off.id}',  # Use formatted string for display
            'quantity': write_off.quantity,
            'description': write_off.reason,
            'written_off_by': write_off.written_off_by.get_full_name() if write_off.written_off_by else 'Unknown'
        })
    
    # Get inventory adjustments that deducted this material
    # inventory_deductions = RawMaterialInventory.objects.filter(
    #     raw_material=raw_material,
    #     adjustment__lt=0,
    #     last_updated__date__gte=from_date,
    #     last_updated__date__lte=to_date
    # ).order_by('last_updated')
    
    # for adjustment in inventory_deductions:
    #     deductions.append({
    #         'type': 'inventory_adjustment',
    #         'date': adjustment.last_updated,
    #         'reference': adjustment.id,  # Use integer id for consistency
    #         'reference_display': f'Adjustment #{adjustment.id}',  # Use formatted string for display
    #         'quantity': abs(adjustment.adjustment),  # Make positive for display
    #         'description': 'Manual inventory adjustment'
    #     })
    
    # Sort all deductions by date
    deductions.sort(key=lambda x: x['date'], reverse=True)
    
    context = {
        'raw_material': raw_material,
        'deductions': deductions,
        'from_date': from_date,
        'to_date': to_date,
        'total_deductions': sum(item['quantity'] for item in deductions)
    }
    return render(request, 'raw_material_deductions_detail.html', context)

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
    View to display the manufactured product inventory with comprehensive statistics.
    """
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Sum, Count
    
    # Get all inventory with related data
    inventory = ManufacturedProductInventory.objects.all().select_related('product')
    
    # Calculate comprehensive statistics
    total_products = inventory.count()
    total_quantity = sum(item.quantity for item in inventory)
    total_value = sum(item.quantity * (getattr(item.product, 'price', 0) or 0) for item in inventory)
    
    # Stock level analysis
    low_stock_items = inventory.filter(quantity__lt=10).count()
    out_of_stock_items = inventory.filter(quantity=0).count()
    high_stock_items = inventory.filter(quantity__gt=50).count()
    
    # Expiry analysis
    today = timezone.now().date()
    expiring_soon = inventory.filter(expiry_date__lte=today + timedelta(days=30)).count()
    expired_items = inventory.filter(expiry_date__lt=today).count()
    
    # Batch analysis
    unique_batches = inventory.values('batch_number').distinct().count()
    recent_batches = inventory.filter(
        last_updated__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Get monthly production trends (last 6 months)
    monthly_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        
        # Count new inventory items for this month
        month_production = inventory.filter(
            last_updated__gte=month_start,
            last_updated__lte=month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%B %Y'),
            'production': month_production
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    # Get top products by quantity
    top_products = inventory.order_by('-quantity')[:5]
    
    # Get low stock products
    low_stock_products = inventory.filter(quantity__lt=10).order_by('quantity')[:5]
    
    # Get expiring products
    expiring_products = inventory.filter(
        expiry_date__lte=today + timedelta(days=30)
    ).order_by('expiry_date')[:5]
    
    # Get recent inventory updates
    recent_updates = inventory.order_by('-last_updated')[:10]
    
    # Get batch distribution
    batch_distribution = inventory.values('batch_number').annotate(
        total_quantity=Sum('quantity'),
        product_count=Count('product', distinct=True)
    ).order_by('-total_quantity')[:5]
    
    # Calculate inventory status breakdown
    inventory_status = {
        'In Stock': inventory.filter(quantity__gt=10).count(),
        'Low Stock': inventory.filter(quantity__range=(1, 10)).count(),
        'Out of Stock': inventory.filter(quantity=0).count(),
    }
    
    # Get production efficiency data
    production_efficiency = {
        'High Stock': inventory.filter(quantity__gt=50).count(),
        'Medium Stock': inventory.filter(quantity__range=(11, 50)).count(),
        'Low Stock': inventory.filter(quantity__range=(1, 10)).count(),
        'No Stock': inventory.filter(quantity=0).count(),
    }
    
    # Get recent transfers to main store
    recent_transfers = StoreTransfer.objects.filter(
        date__gte=timezone.now() - timedelta(days=30)
    ).select_related('product').order_by('-date')[:10]
    
    context = {
        'inventory': inventory,
        'total_products': total_products,
        'total_quantity': total_quantity,
        'total_value': total_value,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'high_stock_items': high_stock_items,
        'expiring_soon': expiring_soon,
        'expired_items': expired_items,
        'unique_batches': unique_batches,
        'recent_batches': recent_batches,
        'monthly_data': monthly_data,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'expiring_products': expiring_products,
        'recent_updates': recent_updates,
        'batch_distribution': batch_distribution,
        'inventory_status': inventory_status,
        'production_efficiency': production_efficiency,
        'recent_transfers': recent_transfers,
        'today': today,
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
     # Initialize total cost to 0
    total_ingredient_cost = 0
    ingredients_used_data = []
    
    for ingredient_cost in ingredient_costs:
        # Calculate total quantity of each ingredient needed for the given quantity of product
        total_quantity_needed = ingredient_cost['quantity'] * quantity
        total_cost_for_ingredient = ingredient_cost['cost_per_unit'] * total_quantity_needed
        
        # Add to the running total of ingredient costs
        total_ingredient_cost += total_cost_for_ingredient
        
        # Collect detailed ingredient usage data
        ingredients_used_data.append({
            'name': ingredient_cost['name'],
            'quantity': total_quantity_needed,
            'cost_per_unit': ingredient_cost['cost_per_unit'],
            'total_cost': total_cost_for_ingredient,
            'unit_measurement': ingredient_cost.get('unit_measurement', 'N/A'),
        })
    
    # Calculate the cost per unit of product and the total production cost
    cost_per_product = total_ingredient_cost / quantity if quantity > 0 else 0
    total_production_cost = total_ingredient_cost  # This is for the whole production batch

    
    # Get the associated production order, if any
    production_order = manufactured_product.production_order

    referer = request.META.get('HTTP_REFERER', '/')

    context = {
        'manufactured_product': manufactured_product,
        'quantity': quantity,
        'product': product,
        'ingredients_used': ingredients_used_data,
        'cost_per_product': cost_per_product,
        'total_production_cost': total_production_cost,
        'production_order': production_order,
        'referer': referer,
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
        transfer_form = StoreTransferForm(request.POST, request.FILES, prefix='transfer')

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
                return redirect('main_stock_transfer')  
    else:
        formset = StockTransferItemFormSet(prefix='stock_item')
        transfer_form = StoreTransferForm(prefix='transfer')

    context = {
        'formset': formset,
        'transfer_form':transfer_form,
    }

    return render(request, 'bulk_stock_transfer.html', context)


def main_stock_transfer (request):
    from django.db.models import Sum, Count
    
    # Get all store transfers with related data
    store_transfers = StoreTransfer.objects.select_related('created_by').prefetch_related('items__product').order_by('-date')
    
    # Calculate comprehensive statistics
    total_transfers = store_transfers.count()
    pending_transfers = store_transfers.filter(status='Pending').count()
    completed_transfers = store_transfers.filter(status='Completed').count()
    approved_transfers = store_transfers.filter(status='Approved').count()
    
    # Calculate total quantities transferred
    total_items_transferred = sum(
        transfer.items.aggregate(total=Sum('quantity'))['total'] or 0 
        for transfer in store_transfers.filter(status='Completed')
    )
    
    # Get recent transfers (last 7 days)
    from datetime import timedelta
    recent_transfers = store_transfers.filter(
        date__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Get transfers by status for chart
    status_breakdown = {
        'Pending': pending_transfers,
        'Approved': approved_transfers,
        'Completed': completed_transfers,
    }
    
    # Get monthly transfer trends (last 6 months)
    monthly_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        
        month_transfers = store_transfers.filter(
            date__gte=month_start,
            date__lte=month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%B %Y'),
            'transfers': month_transfers
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    # Get top transferred products
    top_products = StoreTransferItem.objects.filter(
        transfer__status='Completed'
    ).values(
        'product__product__product_name'
    ).annotate(
        total_quantity=Sum('quantity'),
        transfer_count=Count('transfer', distinct=True)
    ).order_by('-total_quantity')[:5]
    
    user_is_production_manager = request.user.groups.filter(name='Production Manager').exists()
    
    context = {
        'store_transfers': store_transfers,
        'user_is_production_manager': user_is_production_manager,
        'total_transfers': total_transfers,
        'pending_transfers': pending_transfers,
        'completed_transfers': completed_transfers,
        'approved_transfers': approved_transfers,
        'total_items_transferred': total_items_transferred,
        'recent_transfers': recent_transfers,
        'status_breakdown': status_breakdown,
        'monthly_data': monthly_data,
        'top_products': top_products,
    }
    return render(request, 'main_stock_transfers.html', context)

def mark_transfer_completed (request, transfer_id):
    transfer = get_object_or_404(StoreTransfer, pk=transfer_id)
    
    # Ensure we only allow marking as completed if the status is not already completed
    if transfer.status == 'Completed':
        return redirect('main_stock_transfer')
    # Get transfer items for the selected transfer
    transfer_items = StoreTransferItem.objects.filter(transfer=transfer)

    # Create a formset for delivered quantities
    LivaraMainStoreQuantityFormSet = modelformset_factory(StoreTransferItem, form=LivaraMainStoreDeliveredQuantityForm, extra=0)
    if request.method == 'POST':
        formset = LivaraMainStoreQuantityFormSet(request.POST, queryset=transfer_items)

        if formset.is_valid():
            with transaction.atomic():
                transfer.status = 'Completed'
                transfer.save()

                for form, item in zip(formset.forms, transfer_items):
                    delivered_quantity = form.cleaned_data['delivered_quantity']
                    manufactured_product_inventory = item.product
                    batch_number = manufactured_product_inventory.batch_number
                    expiry_date = manufactured_product_inventory.expiry_date

                    # Update ManufacturedProductInventory
                    if manufactured_product_inventory.quantity >= delivered_quantity:
                        manufactured_product_inventory.quantity -= delivered_quantity
                        manufactured_product_inventory.save()
                    else:
                        raise ValueError(f"Not enough stock in manufacture inventory for {manufactured_product_inventory.product}")

                    # Update LivaraMainStore
                    livara_inventory, created = LivaraMainStore.objects.get_or_create(
                        product=manufactured_product_inventory,
                        batch_number=batch_number,
                        expiry_date=expiry_date,
                        defaults={'quantity': delivered_quantity}
                    )
                    
                    if not created:
                        livara_inventory.quantity += delivered_quantity
                        livara_inventory.save()
                    # Create an audit trail record for LivaraMainStore adjustment
                    
                    LivaraInventoryAdjustment.objects.create(
                        store_inventory=livara_inventory,
                        adjusted_quantity=delivered_quantity,  # Assuming a positive quantity indicates an increase
                        adjustment_reason="Stock Transfer Completed",
                        adjusted_by=request.user  # Assuming the logged-in user is responsible
                    )

            return redirect('main_stock_transfer')
        else:
            print(formset.errors)
    else:
        formset = LivaraMainStoreQuantityFormSet(queryset=transfer_items)

    context = {
        'formset': formset,
        'transfer': transfer,
        'transfer_items': transfer_items,
    }

    return render(request, 'mark_transfer_completed.html', context)

def detailed_inventory_report(request):
    selected_date = request.GET.get('date', datetime.now().date())
    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date() if isinstance(selected_date, str) else selected_date

    # Calculate the previous day's end
    previous_day = selected_date - timedelta(days=1)
    # Fetch all products in the main store
    products = LivaraMainStore.objects.values('product__product__product_name','batch_number','product__expiry_date').distinct()

    # Prepare report data
    report_data = []

    for product in products:
        product_name = product['product__product__product_name']
        batch_number = product['batch_number']
        expiry_date = product['product__expiry_date']
        
        #get current stock in Livaramainstore
        current_stock = LivaraMainStore.objects.filter(
            product__product__product_name=product_name,
            batch_number=batch_number
        ).aggregate(total=Sum('quantity'))['total'] or 0

        # Get all adjustments for the selected date
        todays_adjustments = LivaraInventoryAdjustment.objects.filter(
            store_inventory__product__product__product_name=product_name,
            store_inventory__product__batch_number=batch_number,
            adjustment_date__date=selected_date
        ).aggregate(
            total_adjustments=Sum('adjusted_quantity')
        )['total_adjustments'] or 0

        # Opening stock is current stock minus today's adjustments
        opening_stock = current_stock - todays_adjustments

        # Get positive and negative adjustments separately for display
        positive_adjustments = LivaraInventoryAdjustment.objects.filter(
            store_inventory__product__product__product_name=product_name,
            store_inventory__product__batch_number=batch_number,
            adjustment_date__date=selected_date,
            adjusted_quantity__gt=0
        ).aggregate(
            total=Sum('adjusted_quantity')
        )['total'] or 0

        negative_adjustments = LivaraInventoryAdjustment.objects.filter(
            store_inventory__product__product__product_name=product_name,
            store_inventory__product__batch_number=batch_number,
            adjustment_date__date=selected_date,
            adjusted_quantity__lt=0
        ).aggregate(
            total=Sum('adjusted_quantity')
        )['total'] or 0
        # Calculate closing stock
        adjs = (positive_adjustments - negative_adjustments)
        closing_stock = opening_stock + positive_adjustments + negative_adjustments
        
        # Add debug information
        print(f"\nProduct: {product_name}")
        print(f"Current Stock: {current_stock}")
        
        # Only append products with activity or stock
        if opening_stock != 0 or positive_adjustments != 0 or negative_adjustments != 0 or closing_stock != 0:
            report_data.append({
                'product_name': product_name,
                'batch_number': batch_number,
                'opening_stock': opening_stock,
                'positive_adjustments': positive_adjustments,
                'negative_adjustments': negative_adjustments,
                'closing_stock': closing_stock
            })

    context = {
        'selected_date': selected_date,
        'report_data': report_data
    }

    return render(request, 'detailed_inventory_report.html', context)

def product_adjustments(request, product_name, batch_number, date):
    # Convert date string to date object
    selected_date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # Get all adjustments for the product on the specified date
    adjustments = LivaraInventoryAdjustment.objects.filter(
        store_inventory__product__product__product_name=product_name,
        store_inventory__product__batch_number=batch_number,
        adjustment_date__date=selected_date
    ).order_by('adjustment_date')

    context = {
        'product_name': product_name,
        'batch_number': batch_number,
        'selected_date': selected_date,
        'adjustments': adjustments,
    }
    
    return render(request, 'product_adjustments.html', context)

def livara_main_store_inventory(request):
    main_store_inventory = LivaraMainStore.objects.all()
    context = {
        'main_store_inventory': main_store_inventory
    }
    return render(request, 'livara_main_store_inventory.html', context)

#Mainstore WriteOff List and creation
@login_required
def create_main_store_writeoff(request):
    if request.method == 'POST':
        form = StoreWriteOffForm(request.POST)
        if form.is_valid():
            writeoff = form.save(commit=False)
            writeoff.initiated_by = request.user
            writeoff.save()
            
            messages.success(request, 'Write-off recorded successfully. Awaiting approval.')
            return redirect('main_store_writeoff_list')  # Redirect to the list view
    else:
        form = StoreWriteOffForm()
    
    return render(request, 'store_writeoff_form.html', {'form': form})

@login_required
def main_store_writeoff_list(request):
    writeoffs = StoreWriteOff.objects.all().order_by('-date')
    return render(request, 'store_writeoff_list.html',{'writeoffs': writeoffs})

#approve livaramainstore wiriteoffs
def is_finance(user):
    return user.groups.filter(name='Finance').exists()

@require_POST
@user_passes_test(is_finance)
def approve_mainstore_writeoff(request):
    try:
        writeoff_id = request.POST.get('writeoff_id')
        if not writeoff_id:
            return JsonResponse({
                'success': False,
                'message': 'Write-off ID is required'
            })

        writeoff = get_object_or_404(StoreWriteOff, id=writeoff_id)
        
        # Check if already approved
        if writeoff.approved:
            return JsonResponse({
                'success': False,
                'message': 'Write-off has already been approved'
            })

        # Use boolean True instead of string 'true'
        writeoff.approved = True
        writeoff.approved_by = request.user
        writeoff.approved_at = timezone.now()
        writeoff.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Write-off approved successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error approving write-off: {str(e)}'
        })




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

@login_required
def manager_inventory_view(request):
    # Get the store for the logged-in user
    user_store = None
    
    # Check if user is a store manager and get their store
    if request.user.groups.filter(name='Branch Manager').exists():
        try:
            user_store = Store.objects.get(manager=request.user)
        except Store.DoesNotExist:
            pass
    
    # If no store, show error
    if not user_store:
        messages.error(request, "You are not associated with any store. Please contact your administrator.")
        return redirect('store_inventory_list')
    
    # Get inventory for the manager's store
    inventory = StoreInventory.objects.filter(store=user_store).select_related('product')
    
    # Calculate comprehensive statistics
    total_products = inventory.count()
    total_quantity = sum(item.quantity for item in inventory)
    low_stock_items = inventory.filter(quantity__lt=10).count()
    out_of_stock_items = inventory.filter(quantity=0).count()
    high_stock_items = inventory.filter(quantity__gt=50).count()
    
    # Calculate total inventory value (assuming product has a price field)
    total_value = sum(item.quantity * (getattr(item.product, 'price', 0) or 0) for item in inventory)
    
    # Get recent adjustments (last 30 days)
    from datetime import timedelta
    recent_adjustments = InventoryAdjustment.objects.filter(
        store_inventory__store=user_store,
        adjustment_date__gte=timezone.now().date() - timedelta(days=30)
    ).select_related('store_inventory__product', 'adjusted_by').order_by('-adjustment_date')[:10]
    
    # Get monthly inventory trends (last 6 months)
    monthly_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        
        # Count adjustments for this month
        month_adjustments = InventoryAdjustment.objects.filter(
            store_inventory__store=user_store,
            adjustment_date__gte=month_start.date(),
            adjustment_date__lte=month_end.date()
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%B %Y'),
            'adjustments': month_adjustments
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    # Get top products by quantity
    top_products = inventory.order_by('-quantity')[:5]
    
    # Get low stock products
    low_stock_products = inventory.filter(quantity__lt=10).order_by('quantity')[:5]
    
    # Get recent inventory changes
    recent_changes = InventoryAdjustment.objects.filter(
        store_inventory__store=user_store
    ).select_related('store_inventory__product', 'adjusted_by').order_by('-adjustment_date')[:10]
    
    # Calculate stock status breakdown
    stock_status = {
        'In Stock': inventory.filter(quantity__gt=10).count(),
        'Low Stock': inventory.filter(quantity__range=(1, 10)).count(),
        'Out of Stock': inventory.filter(quantity=0).count(),
    }
    
    context = {
        'inventory': inventory,
        'user_store': user_store,
        'total_products': total_products,
        'total_quantity': total_quantity,
        'total_value': total_value,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'high_stock_items': high_stock_items,
        'recent_adjustments': recent_adjustments,
        'monthly_data': monthly_data,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'recent_changes': recent_changes,
        'stock_status': stock_status,
    }
    
    return render(request, 'manager_inventory.html', context)

@login_required
def main_store_inventory_adjustments(request):
    form = StoreSelectionForm(request.GET or None )
    # Base queryset for store inventory
    store_inventory = StoreInventory.objects.select_related('store', 'product')
    # store_inventory = StoreInventory.objects.all()
    # adjustments = InventoryAdjustment.objects.filter(store_inventory__store__in=store_inventory.values('store'))
    # all_adjustments = InventoryAdjustment.objects.select_related('store_inventory')
    
    # Filter store inventory by the selected store if a store is chosen
    selected_store = None
    if form.is_valid() and form.cleaned_data.get('store'):
        selected_store = form.cleaned_data['store']
        store_inventory = store_inventory.filter(store=selected_store)

    # Fetch adjustments related to the filtered store inventory
    adjustments = InventoryAdjustment.objects.filter(
        store_inventory__in=store_inventory
    ).select_related('store_inventory__store', 'adjusted_by')

    # Group adjustments by store inventory for better organization in the template
    grouped_adjustments = defaultdict(list)
    for adjustment in adjustments:
        grouped_adjustments[adjustment.store_inventory_id].append(adjustment)

    context = {
        'store_inventory': store_inventory,
        'adjustments': adjustments,
        'adjustments': grouped_adjustments,  # Grouped adjustments for easier display
        'form': form,  # Store selection form
        'selected_store': selected_store,  # Track selected store for UI
    }

    return render(request, 'main_store_inventory_adjustments.html', context)


@login_required(login_url='/login/')
def create_restock_request(request):
    # Get the store for the logged-in user
    user_store = None
    
    # Check if user is a store manager and get their store
    if request.user.groups.filter(name='Branch Manager').exists():
        try:
            user_store = Store.objects.get(manager=request.user)
        except Store.DoesNotExist:
            pass
    
    # If still no store, show error
    if not user_store:
        messages.error(request, "You are not associated with any store. Please contact your administrator.")
        return redirect('restockRequests')

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
            restock.store = user_store  # Automatically set the store
            restock.save()

            for item_form in formset:
                if item_form.cleaned_data:  # Only save if there is valid data
                    restock_item = item_form.save(commit=False)
                    restock_item.restock_request = restock
                    restock_item.save()

            messages.success(request, 'Restock request created successfully!')

            return redirect('restockRequests')  # Adjust this to your success URL name
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        # Pre-populate the form with the user's store
        form = RestockRequestForm(prefix="restock", initial={'store': user_store})
        formset = RestockRequestItemFormset(prefix="restock_item")

    context = {
        'form': form,
        'formset': formset,
        'user_store': user_store,  # Pass store info to template
    }
    
    return render(request, 'create-restock-requests.html', context)

@login_required(login_url='/login/')
def restock_requests (request):
    # Get all restock requests with related data
    restock_requests = RestockRequest.objects.select_related('store', 'requested_by').prefetch_related('items__product').order_by('-request_date')

    # Calculate comprehensive statistics
    total_requests = restock_requests.count()
    pending_requests = restock_requests.filter(status='pending').count()
    approved_requests = restock_requests.filter(status='approved').count()
    delivered_requests = restock_requests.filter(status='delivered').count()
    rejected_requests = restock_requests.filter(status='rejected').count()

    # Calculate total quantities requested
    total_items_requested = sum(
        request.items.aggregate(total=Sum('quantity'))['total'] or 0
        for request in restock_requests
    )

    # Get recent requests (last 7 days)
    from datetime import timedelta
    recent_requests = restock_requests.filter(
        request_date__gte=timezone.now() - timedelta(days=7)
    ).count()

    # Get requests by status for chart
    status_breakdown = {
        'Pending': pending_requests,
        'Approved': approved_requests,
        'Delivered': delivered_requests,
        'Rejected': rejected_requests,
    }

    # Get monthly request trends (last 6 months)
    monthly_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)

        month_requests = restock_requests.filter(
            request_date__gte=month_start,
            request_date__lte=month_end
        ).count()

        monthly_data.append({
            'month': month_start.strftime('%B %Y'),
            'requests': month_requests
        })

    monthly_data.reverse()  # Show oldest to newest

    # Get top requesting stores
    top_stores = restock_requests.values(
        'store__name'
    ).annotate(
        total_requests=Count('id'),
        total_quantity=Sum('items__quantity')
    ).order_by('-total_requests')[:5]

    # Get top requested products
    top_products = RestockRequestItem.objects.values(
        'product__product__product__product_name'
    ).annotate(
        total_quantity=Sum('quantity'),
        request_count=Count('restock_request', distinct=True)
    ).order_by('-total_quantity')[:5]

    # Get recent activity
    recent_activity = restock_requests.filter(
        request_date__gte=timezone.now() - timedelta(days=7)
    ).select_related('store', 'requested_by')[:10]

    user_groups = request.user.groups.all()
    user_group = user_groups.first()

    context = {
        'restock_requests': restock_requests,
        'user_group': user_group,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'delivered_requests': delivered_requests,
        'rejected_requests': rejected_requests,
        'total_items_requested': total_items_requested,
        'recent_requests': recent_requests,
        'status_breakdown': status_breakdown,
        'monthly_data': monthly_data,
        'top_stores': top_stores,
        'top_products': top_products,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'restock-requests.html', context)

def restock_request_detail(request, restock_id):
    restock_request = get_object_or_404(RestockRequest, pk=restock_id)

    if request.method == 'POST':
        form = TransferApprovalForm(request.POST, instance=restock_request)
        if form.is_valid():
            form.save()
            # Redirect to a success page or back to the list of requests
            return redirect('restockRequests')  # Replace with your list view URL
    else:
        form = TransferApprovalForm(instance=restock_request)

    context = {
        'restock_request': restock_request,
        'form': form,
    }
    return render(request, 'restock_request_detail.html', context)

@login_required
def approve_store_transfer(request, pk):
    restock_request = get_object_or_404(RestockRequest, pk=pk)

    # Check if the user has permission to approve requests
    # You might want to implement your own permission check here

    RestockRequestItemFormset = modelformset_factory(
        RestockRequestItem,
        form = RestockApprovalItemForm,
        extra=0,  # No extra forms
        can_delete=False  # No deletion of items allowed during approval
    )

    if request.method == 'POST':
        print(request.POST)
        formset = RestockRequestItemFormset(request.POST, instance=restock_request)

        if formset.is_valid():
            for item_form in formset:
                restock_item = item_form.save(commit=False)
                restock_item.save()  # Save the approved quantities

            # Update the request status to 'approved'
            restock_request.status = 'approved'
            restock_request.save()

            messages.success(request, 'Restock request approved successfully!')
            return redirect('restockRequests')  # Adjust this to your success URL name
    else:
        formset = RestockRequestItemFormset(instance=restock_request)
        
    print(formset.errors)
    print(formset.non_form_errors())

    context = {
        'restock_request': restock_request,
        'formset': formset,
    }

    return render(request, 'approve_store_transfer.html', context)

class ApproveStoreTransferView(FormView):
    template_name = 'approve_store_transfer.html'
    form_class = RestockRequestForm  # If you have a main form; otherwise, set this to None

    def get_object(self):
        """
        Get the RestockRequest object based on the URL parameter.
        """
        return get_object_or_404(RestockRequest, pk=self.kwargs['pk'])

    def get_formset(self, data=None):
        restock_request = self.get_object()
    
        RestockRequestItemFormset = inlineformset_factory(
        RestockRequest,
        RestockRequestItem,
        form = RestockApprovalItemForm,
        fields=('id','approved_quantity',),  # Only include approved_quantity
        extra=0,
        can_delete=False
    )
        return RestockRequestItemFormset(data=data, instance=restock_request)


    def get_context_data(self, **kwargs):
        """
        Add formset and restock request to the context for rendering the template.
        """
        context = super().get_context_data(**kwargs)
        context['restock_request'] = self.get_object()
        context['formset'] = self.get_formset()
        return context

    def form_valid(self, formset):
        restock_request = self.get_object()

        with transaction.atomic():
            for form in formset:
                if form.cleaned_data:
                    approved_quantity = form.cleaned_data['approved_quantity']
                    if approved_quantity:
                        restock_item = form.instance
                        restock_item.approved_quantity = approved_quantity
                        restock_item.save()
                    

        restock_request.status = 'approved'
        restock_request.save()
            
        messages.success(self.request, 'Restock request approved successfully!')
        return redirect('restockRequests')

    def form_invalid(self, formset):
        print(formset.errors)
        return self.render_to_response(self.get_context_data(formset=formset))


    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: validate and process formset.
        """
        
        formset = self.get_formset(request.POST)

        if formset.is_valid():
            return self.form_valid(formset)
        else:
            # Provide detailed debugging information if needed
            for item_form in formset:
                if item_form.errors:
                    print(f"Formset errors: {item_form.errors}")
            return self.form_invalid(formset)
        
class DeliverRestockRequestView(FormView):
    template_name = 'deliver_restock_request.html'
    form_class = RestockRequestForm

    def get_object(self):
        return get_object_or_404(RestockRequest, pk=self.kwargs['pk'])

    def get_formset(self, data=None):
        restock_request = self.get_object()
        print(restock_request.store)
        RestockRequestItemFormset = inlineformset_factory(
            RestockRequest,
            RestockRequestItem,
            form=DeliveryRestockRequestForm,  # Use DeliveryRestockRequestForm here
            fields=('delivered_quantity',),
            extra=0,
            can_delete=False,
        
        )
        return RestockRequestItemFormset(data=data, instance=restock_request)
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['restock_request'] = self.get_object()
        context['formset'] = self.get_formset()
        return context

    def form_valid(self, formset):
        restock_request = self.get_object()

        with transaction.atomic():
            for form in formset:
                if form.is_valid():
                    delivered_quantity = form.cleaned_data['delivered_quantity']
                    restock_item = form.instance
                    product = restock_item.product.product.product

                    # Ensure there's enough stock in the main store
                    if restock_item.product.quantity >= delivered_quantity:
                        restock_item.delivered_quantity = delivered_quantity
                        restock_item.save()

                        # Update store inventory
                        store_inventory, created = StoreInventory.objects.get_or_create(
                            product=product,
                            store=restock_request.store,
                            defaults={'quantity': 0}
                        )
                        store_inventory.quantity += delivered_quantity
                        store_inventory.save()

                        # Update main store inventory
                        restock_item.product.quantity -= delivered_quantity
                        restock_item.product.save()

                        # Create inventory adjustment record (optional)
                        # InventoryAdjustment.objects.create(
                        #     store_inventory=store_inventory,
                        #     adjusted_quantity=delivered_quantity,
                        #     adjustment_reason="Restock Fulfillment",
                        #     adjusted_by=restock_request.user,
                        #     transfer_to_store=restock_request.store,
                        #     transfer_date=timezone.now()
                        # )

                    else:
                        messages.error(self.request, f"Insufficient stock for {restock_item.product.product_name}.")

        restock_request.status = 'delivered'
        restock_request.save()


        messages.success(self.request, 'Restock request marked as delivered and inventory updated!')
        return redirect('restockRequests')

        return self.form_invalid(formset)
    
    def form_invalid(self, formset):
        
        print(formset.errors)
        return self.render_to_response(self.get_context_data(formset=formset))
    
    def post(self, request, *args, **kwargs):
        formset = self.get_formset(request.POST)


        if formset.is_valid():
            return self.form_valid(formset)
        else:
            return self.form_invalid(formset)

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
            # Update previous quantity before saving the new quantity
            store_inventory.previous_quantity = store_inventory.quantity
            store_inventory.quantity += item.quantity
            store_inventory.save()
        
        # Create an audit trail record
        InventoryAdjustment.objects.create(
            store_inventory=store_inventory,
            adjusted_quantity=item.quantity,  # Assuming a positive quantity indicates an increase
            adjustment_reason="Restock Fulfillment",
            adjusted_by=request.user,  # Assuming the logged-in user is responsible
            transfer_to_store=restock_request.store,  # Set transfer destination store
            transfer_date=timezone.now()  # Set transfer date to current time
        )

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
    managers = Group.objects.get(name='Saloon Managers')
    if user.groups.filter(name='Saloon Managers').exists():
        managed_stores = user.managed_stores.all()
    else:
        return HttpResponseForbidden("You do not have permission to view any store inventories.")
    store_inventories = StoreInventory.objects.filter(store__in=managed_stores)
    
    context = {
        'store_inventories':store_inventories,
        'managed_stores': managed_stores,
    }
    return render(request, 'store_manager.html', context)


def inventory_adjustments(request, inventory_id):
    inventory = get_object_or_404(StoreInventory, id=inventory_id)
    adjustments = inventory.adjustments.all()
    context = {'inventory': inventory, 'adjustments': adjustments}
    return render(request, 'inventory_adjustments.html', context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles=['Finance','Storemanager','Production Manager'])
def create_production_order(request):
    if not request.user.groups.filter(name='Storemanager').exists():
        messages.error(request, "You don't have permission to create production orders.")
        return redirect('store_inventory_list')  # Redirect to homepage on permission error

    if request.method == 'POST':
        formset = ProductionOrderFormSet(request.POST, queryset=ProductionOrder.objects.none())
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.requested_by = request.user
                        instance.save()
                    
                    # Handle deleted forms
                    for obj in formset.deleted_objects:
                        obj.delete()
                    
                messages.success(request, "Production orders created successfully!")
                return redirect('productionList')
            except Exception as e:
                messages.error(request, f"Error creating production orders: {str(e)}")
    else:
        formset = ProductionOrderFormSet(queryset=ProductionOrder.objects.none())

    context = {
        'formset': formset
    }
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
    production_orders = ProductionOrder.objects.filter(status__in=['Created','Approved', 'In Progress', 'Completed','Rejected']).order_by('-created_at')  # Order by creation date descending
    completed_orders = ProductionOrder.objects.filter(status='Completed')
    rejected_orders = ProductionOrder.objects.filter(status='Rejected')
    approved_orders = ProductionOrder.objects.filter(status='Approved')
    context = {
        'production_orders': production_orders,
        'completed_orders': completed_orders,
        'rejected_orders': rejected_orders,
        'approved_orders': approved_orders,
        }
    return render(request, 'production_production_orders.html', context)

# product location report
def product_location_report(request):
    # Get all products and stores
    products = Production.objects.all().order_by('product_name')
    stores = Store.objects.all().order_by('name')
    main_store = "Livara Main Store"  # Special handling for main store
    manufactured = "URI"     # Special handling for manufacturing

    # Initialize data structure for the report
    report_data = []
    
    for product in products:
        print(f"\nProcessing product: {product.product_name}")
        
        # Get manufacturing quantity
        manufacturing_qty = ManufacturedProductInventory.objects.filter(
            product=product
        ).aggregate(total=Sum('quantity'))['total'] or 0
        print(f"Manufacturing quantity: {manufacturing_qty}")

        # Get main store quantity
        # First get the manufactured inventory records for this product
        manufactured_inventory = ManufacturedProductInventory.objects.filter(product=product)
        # Then get main store records that reference these manufactured inventory records
        main_store_qty = LivaraMainStore.objects.filter(
            product__in=manufactured_inventory
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Debug print main store query
        main_store_items = LivaraMainStore.objects.filter(product__in=manufactured_inventory)
        print(f"Main store items found: {main_store_items.count()}")
        for item in main_store_items:
            print(f"Main store item: {item.product.product.product_name} - Qty: {item.quantity}")
        
        print(f"Main store total quantity: {main_store_qty}")

        # Get store quantities
        store_quantities = {}
        for store in stores:
            store_qty = StoreInventory.objects.filter(
                product=product, 
                store=store
            ).aggregate(total=Sum('quantity'))['total'] or 0
            store_quantities[store.id] = store_qty
            print(f"Store {store.name} quantity: {store_qty}")

        row_data = {
            'product': product,
            'manufacturing': manufacturing_qty,
            'main_store': main_store_qty,
            'stores': store_quantities
        }
        report_data.append(row_data)

    context = {
        'stores': stores,
        'report_data': report_data,
        'main_store': main_store,
        'manufactured': manufactured,
    }
    
    return render(request, 'product_location_report.html', context)

# approve production order
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

# reject production order
@require_POST
def reject_production_order(request, order_id):
    try:
        order = ProductionOrder.objects.get(id=order_id)
        reason = request.POST.get('rejection_reason')
        
        if not reason:
            return JsonResponse({'success': False, 'message': 'Rejection reason is required'})
        
        order.status = 'Rejected'
        order.rejection_reason = reason
        order.rejected_by = request.user
        order.rejected_at = timezone.now()
        order.save()
        
        return JsonResponse({'success': True})
    except ProductionOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

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
    for sale_order in sale_orders:
        sale_order.remaining_days = sale_order.get_remaining_days()  # Directly use the method
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

##################### Create a new Store Sale Martinz side #################
def create_store_test(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        formset = TestItemFormset(request.POST, queryset=SaleItem.objects.none())

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.instance.total_items = formset.total_form_count()
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
                        
                    return redirect('listStoreSales')
                else:
                # Add a general error message
                    messages.error(request, "Insufficient quantity in one or more items. Please adjust the quantities or request for production.")
        else:
            messages.error(request, "There was an error with your submission. Please check the form and try again.")
            
    else:
        form = TestForm()
        formset = TestItemFormset(queryset=SaleItem.objects.none())
        
    price_groups = PriceGroup.objects.filter(is_active=True)  # Fetch only active price groups
    context = {'form': form, 'formset': formset, 'price_groups': price_groups}
    return render(request, 'testing.html', context)

#nolonger used as we use pricing group now
def get_wholesale_price(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        if product_id:
            try:
                product = LivaraMainStore.objects.get(pk=product_id)
                production = Production.objects.filter(product=product).first()  # Get associated Production
                return JsonResponse({'wholesale_price': production.wholesale_price})
            except LivaraMainStore.DoesNotExist:
                pass
    return JsonResponse({'wholesale_price': 0})

# store manager mark order as delivered
def update_order_status(request, store_sale_id):
    if request.method == 'POST':
        order = StoreSale.objects.get(pk=store_sale_id)
        if order.status == 'delivered':  # Check if already delivered
            messages.warning(request, 'Order is already marked as delivered.')
        else:
            order.status = 'paid'
            order.save()
            
            # Reduce the quantity in the LivaraMainStore inventory (when marked delivered)
            for sale_item in order.saleitem_set.all():
                product = sale_item.product
                # product.quantity -= sale_item.quantity
                product.save()
            
            # Calculate VAT and Withholding Tax
            if not hasattr(order, 'receipt'):
                total_vat = Decimal('0.00')
                for sale_item in order.saleitem_set.all():
                    if order.vat:
                        vat_amount = sale_item.total_price * order.VAT_RATE
                        total_vat += vat_amount
                
                total_amount = order.total_amount
                withholding_tax_amount = Decimal('0.00')
                if order.withhold_tax:
                    withholding_tax_amount = total_amount * order.WITHHOLDING_TAX_RATE
                
            # Generate a unique receipt number with "MSLE to mean main-store-sale"
            receipt_number = f"MSLE{str(uuid4()).replace('-', '').upper()[:6]}"
            
            # Create and save the receipt
            StoreSaleReceipt.objects.create(
                store_sale=order,
                receipt_number=receipt_number,
                total_amount=total_amount,
                total_vat=total_vat,
                withholding_tax=withholding_tax_amount,
                total_due=total_amount
                
            )
            
            messages.success(request, 'Order status updated and receipt generated successfully!')
        return redirect('listStoreSales')
    else:
        return redirect('listStoreSales')  # Redirect if not a POST request
    
def store_sale_list_receipts(request):
    receipts = StoreSaleReceipt.objects.all().order_by('-created_at')  # Order by most recent
    context = {'receipts': receipts}
    return render(request, 'store_sale_list_receipts.html', context)

def store_sale_receipt_details(request, store_sale_receipt_id):
    receipt = StoreSaleReceipt.objects.get(id=store_sale_receipt_id)
    referer = request.META.get('HTTP_REFERER')
    context = {'receipt': receipt,'referer':referer}
    return render(request,'store_sale_receipt_details.html', context)
    
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
    total_order_amount = sum(
        item.quantity * item.product.product.product.wholesale_price 
        for item in sale_items
            if item.product and item.product.product.product.wholesale_price is not None
        )

    referer = request.META.get('HTTP_REFERER')
    context = {
        'sale_order': sale_order,
        'referer': referer,
        'total_order_amount': total_order_amount,
    }
    return render(request,'store_sale_details.html', context)

## general accessory store####
@login_required
def accessory_store (request):
    # Get all accessories from the AccessoryInventory
    accessory_inventory = AccessoryInventory.objects.all()
    

    # Pass the accessories to the template
    return render(request, 'accessories_main_store.html', {'accessory_inventory': accessory_inventory})

@login_required
def create_new_accessory(request):
    if request.method == 'POST':
        form = NewAccessoryForm(request.POST)

        if form.is_valid():
            accessory = form.save(commit=False)
            accessory.save()  # Save the accessory without assigning the purchase price
            return redirect('accessory_store')  # Redirect to accessory store view
        else:
            print(form.errors)  # Check for validation errors
    else:
        form = NewAccessoryForm()
    return render (request,'create_new_accessory.html',{'form':form})

@login_required
def create_accessory_requisition(request):
    if request.method == 'POST':
        requisition_form = MainStoreAccessoryRequisitionForm(request.POST)
        formset = MainStoreAccessoryRequisitionItemFormSet(request.POST)

        if requisition_form.is_valid() and formset.is_valid():
            requisition = requisition_form.save(commit=False)
            requisition.requested_by = request.user  # Assuming user is authenticated
            requisition.save()

            for form in formset:
                item = form.save(commit=False)
                item.requisition = requisition
                item.save()  # Save the requisition item without assigning the purchase price

            return redirect('main_store_accessory_requisitions_list')  # Redirect to process requisition view

    else:
        requisition_form = MainStoreAccessoryRequisitionForm()
        formset = MainStoreAccessoryRequisitionItemFormSet(queryset=MainStoreAccessoryRequisitionItem.objects.none())

    context = {'requisition_form': requisition_form, 'formset': formset}
    return render(request, 'create_accessory_requisition.html', context)



class AccessoryRequisitonView(DetailView):
    model = MainStoreAccessoryRequisition
    template_name = 'accessory_requisition_details.html'
    context_object_name = 'acc_requisition'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

def process_acccessory_requisition(request, requisition_id):
    requisition = get_object_or_404(MainStoreAccessoryRequisition, id=requisition_id)

    if request.method == 'POST':
        if 'mark_delivered' in request.POST:
            requisition.status = 'delivered'
            requisition.save()

            for item in requisition.items.all():
                inventory_item, created = AccessoryInventory.objects.get_or_create(
                    accessory=item.accessory
                )
                # Use the adjust_stock method to log the adjustment
                inventory_item.adjust_stock(
                    quantity=item.quantity_requested, 
                    description=f"Delivered from requisition #{requisition.id}"
                )


            return redirect('accessory_store')  # Redirect to requisition list
        
        elif 'reject_requisition' in request.POST:
            # Process the requisition as rejected
            requisition.status = 'rejected'
            # ... add specific rejection logic, e.g., sending notifications
            
        requisition.save()
        return redirect('main_store_accessory_requisitions_list')  # Redirect to the requisition list

    # ... other processing logic ...

    return render(request, 'process_accessory_requisition.html', {'requisition': requisition})

@login_required
def main_store_accessory_requisitions_list(request):
    # Get all accessory requisitions from the AccessoryRequisition
    acc_requisitions = MainStoreAccessoryRequisition.objects.all().order_by('-request_date')
    return render (request, 'accessory_requisitions_list.html',{'acc_requisitions':acc_requisitions})

@login_required
def all_stores_inventory_view(request):
    # Retrieve all store accessory inventories
    store_inventories = StoreAccessoryInventory.objects.select_related('store', 'accessory').all()
    # Aggregate store and accessory data
    stores = Store.objects.annotate(
        total_accessories=Count('accessory_inventory'),
        low_stock_count=Sum(
            Case(
                When(accessory_inventory__quantity__lt=5, then=1),
                default=0,
                output_field=models.IntegerField()
            )
        )
    ).prefetch_related('accessory_inventory__accessory')

    return render(request, 'store_inventory.html', {
        'store_inventories': store_inventories, 'stores':stores
    })

def accessory_inventory_report(request):
    # Get date filter inputs from the request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # If no date is provided, default to today
    if not start_date:
        start_date = timezone.now().date()
    else:
        start_date = timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
    
    if not end_date:
        end_date = start_date  # Single day report if no end date provided
    else:
        end_date = timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        
    # Filter adjustments based on approved and delivered requisitions
    approved_requisitions = MainStoreAccessoryRequisition.objects.filter(status='delivered')
    delivered_internal_requests = InternalAccessoryRequest.objects.filter(status='delivered')
    
    # Adjustments based on the selected date range
    accessory_data = AccessoryInventory.objects.annotate(
        current_stock=F('quantity'),
        additions=Sum('accessoryinventoryadjustment__adjustment', filter=Q(
            accessoryinventoryadjustment__adjustment__gt=0,
            accessoryinventoryadjustment__date__lte=end_date,
            accessoryinventoryadjustment__accessory_inventory__accessory__in=MainStoreAccessoryRequisitionItem.objects.filter(
                requisition__status='delivered',
                
            ).values_list('accessory', flat=True)
        )),
        
        deductions=Sum('accessoryinventoryadjustment__adjustment',filter=Q(
            accessoryinventoryadjustment__adjustment__lt=0,
            accessoryinventoryadjustment__date__lte=end_date,
            accessoryinventoryadjustment__accessory_inventory__accessory__in=delivered_internal_requests.values_list('items__accessory_id', flat=True),
                
            )),
        
        
        closing_stock=F('quantity'),
        previous_stock=F('quantity') - Sum('accessoryinventoryadjustment__adjustment', filter=Q(
        accessoryinventoryadjustment__accessory_inventory__accessory__in=approved_requisitions.values_list('items__accessory_id', flat=True),
        accessoryinventoryadjustment__date__lte=end_date,
    ))
    
    ).select_related('accessory')
    
    # Fetch requisition details for each accessory
    for accessory in accessory_data:
        accessory.requisitions = MainStoreAccessoryRequisitionItem.objects.filter(
            requisition__status='delivered',
            accessory=accessory.accessory
        )
        
    for accessory in accessory_data:
        accessory.internal_requests = InternalAccessoryRequest.objects.filter(
            status='delivered',
            items__accessory=accessory.accessory
        )
        # Get deductions from internal requests for each accessory
        accessory.internal_deductions = InternalAccessoryRequestItem.objects.filter(
            request__status='delivered',
            accessory=accessory.accessory
        )
    
    
    
    context = {
        'accessory_data': accessory_data,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'accessory_inventory_report.html', context)

@login_required
def accessory_stock_adjustment_view(request):
    selected_date_str = request.GET.get('date')  # Get selected date from query parameters
    selected_store_id = request.GET.get('store')  # Get selected store from query parameters
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date() if selected_date_str else None

    # Fetch all stores for the dropdown
    stores = Store.objects.all()

    # If no date or store is selected, show an empty page
    if not selected_date or not selected_store_id:
        return render(request, 'accessory_inventory_report.html', {
            'stores': stores,
            'adjustments': [],
            'selected_date': selected_date,
            'selected_store': None,
        })

    # Get the selected store
    selected_store = Store.objects.get(id=selected_store_id)

    # Fetch opening stock for each accessory
    opening_stock = StoreAccessoryInventory.objects.filter(store=selected_store).annotate(
        opening_quantity=Sum(
            'adjustments__adjusted_quantity',
            filter=Q(adjustments__adjustment_date__lt=selected_date),
            default=0
        )
    )

    # Fetch adjustments on the selected date
    adjustments = StoreInventoryAdjustment.objects.filter(
        store_inventory__store=selected_store,
        adjustment_date=selected_date
    ).select_related('store_inventory__accessory', 'adjusted_by')

    # Calculate closing stock for each accessory
    closing_stock = {}
    for item in opening_stock:
        opening = item.opening_quantity or 0
        adjustments_on_date = adjustments.filter(store_inventory__accessory=item.accessory).aggregate(
            total_adjustments=Sum('adjusted_quantity')
        )['total_adjustments'] or 0
        closing_stock[item.accessory.name] = opening + adjustments_on_date

    return render(request, 'store_accessory_inventory_report.html', {
        'stores': stores,
        'adjustments': adjustments,
        'opening_stock': opening_stock,
        'closing_stock': closing_stock,
        'selected_date': selected_date,
        'selected_store': selected_store,
    })

############################################# BRANCH VIEWS #############################################################################################################################################
def error_page(request):
    context = {
		"appSidebarHide": 1,
		"appHeaderHide": 1,
		"appContentClass": 'p-0'
	}
    return render(request, 'error.html', context)


#POS of service sale
def saloon_sale(request):
    current_store = Store.objects.get(manager=request.user)
    search_query = request.GET.get('search', '')
    # Customer Details
    customers = Customer.objects.all()
    # Get store-specific services and products with search filter
    store_services = StoreService.objects.filter(
        store=current_store,
        
    ).select_related('service')
    
    if search_query:
        store_services = store_services.filter(
            Q(service__name__icontains=search_query) |
            Q(service__price__icontains=search_query)
        )

    store_products = StoreInventory.objects.filter(
        store=current_store,
        quantity__gt=0  # Only show products with stock
    ).select_related('product')
    
    if search_query:
        store_products = store_products.filter(
            Q(product__product_name__icontains=search_query)
        )
    
    store_accessories = StoreAccessoryInventory.objects.filter(
        store=current_store,
    ).select_related('accessory')
    
    if search_query:
        store_accessories = store_accessories.filter(
            Q(accessory__name__icontains=search_query)
        )
    
    # Get available staff for services
    available_staff = Staff.objects.filter(
        store=current_store,
    )
    context ={
        'available_staff': available_staff,
        'store_services':store_services,
        'store_products':store_products,
        'store_accessories':store_accessories,
        'customers': customers,
        'appSidebarHide':1,
        'current_store': current_store,
        'appHeaderHide':1,
        'appContentFullHeight':1,
        'appContentClass':"p-1 ps-xl-4 pe-xl-4 pt-xl-3 pb-xl-3",
        'search_query': search_query,
    }

    return render(request, 'create_saloon_order.html', context)


# Get price group for product
def get_product_price_groups(request, product_id):
    print(f"Fetching price groups for product {product_id}")  # Debug log
    try:
        
        product = Production.objects.get(id=product_id)
        
        # Get all price groups
        retail_price = ProductPrice.objects.filter(
            product=product,
            price_group__name__iexact='retail price'  # Assuming your retail price group is named "Retail"
        ).select_related('price_group').first()
        
        
        if retail_price:
            price_groups_data = [{
                'id': retail_price.price_group.id,
                'name': retail_price.price_group.name,
                'description': retail_price.price_group.description,
                'is_active': retail_price.price_group.is_active,
                'price': str(retail_price.price)
            }]
            
            return JsonResponse({
                'success': True,
                'product_name': product.product_name,
                'price_groups': price_groups_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Retail price not found for this product'
            }, status=404)
        
    except Production.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        print(f"Error in get_product_price_groups: {str(e)}")  # Debug log
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
        
# Search for Staff       
def search_staff(request):
    search_term = request.GET.get('term', '')
    if len(search_term) < 2:
        return JsonResponse({'results': []})
        
    staff = Staff.objects.filter(
        Q(first_name__icontains=search_term) |
        Q(last_name__icontains=search_term)
    )[:10]  # Limit to 10 results
    
    results = [{'id': s.id, 'text': f"{s.first_name} {s.last_name}"} for s in staff]
    return JsonResponse({'results': results})
        
@require_http_methods(["POST"])
def new_create_service_sale(request):
    
    try:
        data = json.loads(request.body)
        store_id = data['store_id']
        
        # Debug: Print all services for this store
        store_services = StoreService.objects.filter(store_id=store_id)
        available_service_ids = list(store_services.values_list('service__id', flat=True))
        print(f"\nAvailable service IDs in store {store_id}: {available_service_ids}")
        print(f"\nAvailable services in store {store_id}:")
        for service in store_services:
            print(f"Service ID: {service.service.id}, Name: {service.service.name}")
        
        with transaction.atomic():
            # Create the main sale record
            sale = ServiceSale.objects.create(
                store_id=store_id,
                customer_id=data['customer_id'],
                total_amount=Decimal(str(data['total_amount'])),
                paid_status=data['paid_status'],
                payment_mode=data['payment_mode']
            )
            
            # Handle service items first
            if 'service_items' in data and data['service_items']:
                print("\nProcessing service items:", data['service_items'])
                for item in data['service_items']:
                    service_id = item['service_id']
                    print(f"\nProcessing service item:")
                    print(f"- Service ID: {service_id}")
                    print(f"- Available services: {available_service_ids}")
                    
                    # Try to get the service using a more detailed query
                    store_service = StoreService.objects.filter(
                        store_id=store_id,
                        service__id=service_id
                    ).select_related('service').first()
                    
                    if not store_service:
                        # Debug: Show all available services in this store
                        available_services = list(StoreService.objects.filter(
                            store_id=store_id
                        ).values('id', 'service__id', 'service__name'))
                        
                        print(f"\nAvailable services in store {store_id}:")
                        for svc in available_services:
                            print(f"StoreService ID: {svc['id']}, "
                                f"Service ID: {svc['service__id']}, "
                                f"Name: {svc['service__name']}")
                        
                        raise ValueError(
                            f"Service {service_id} not found in store {store_id}. "
                            f"Available services: {[s['service__id'] for s in available_services]}"
                        )
                    
                    print(f"Found store service: {store_service.service.name}")
                    
                    # Create the service sale item
                    service_item = ServiceSaleItem.objects.create(
                        sale=sale,
                        service=store_service,
                        quantity=int(item['quantity']),
                        total_price=Decimal(str(item['total_price']))
                    )
                    
                    # Add staff if provided
                    if item.get('staff_ids'):
                        staff_ids = [int(sid) for sid in item['staff_ids']]
                        service_item.staff.add(*staff_ids)
                        print(f"Added staff IDs: {staff_ids} to service item")
            
            # Create product sale items
            for item in data['product_items']:
                try:
                    # Get the store inventory instance
                    store_inventory = StoreInventory.objects.get(
                        store_id=store_id,
                        product_id=item['product_id']
                    )
                    
                    # Check if enough stock is available
                    if store_inventory.quantity < item['quantity']:
                        raise ValueError(f"Insufficient stock for product {store_inventory.product.product_name}")
                    
                    product_sale_item = ProductSaleItem.objects.create(
                        sale=sale,
                        product=store_inventory,  # Use the store_inventory instance
                        quantity=item['quantity'],
                        price_group_id=item.get('price_group_id'),
                        total_price=Decimal(str(item['total_price']))
                    )
                    # Assign staff if provided
                    if item.get('staff_id'):
                        # product_sale_item = ProductSaleItem.objects.get(id=item['product_sale_item_id'])
                        product_sale_item.staff_id = item['staff_id']
                        product_sale_item.save()
                        
                        print(f"DEBUG: Assigned staff {item['staff_id']} to product {product_sale_item.id}")
                except StoreInventory.DoesNotExist:
                    raise ValueError(f"Product with ID {item['product_id']} not found in store {store_id}")
            
            
            
            # Create accessory sale items
            if 'accessory_items' in data and data['accessory_items']:
                for item in data['accessory_items']:
                    try:
                        print(f"Processing accessory item: {item}")  # Debug log
                        
                        store_accessory = StoreAccessoryInventory.objects.get(
                            store_id=store_id,
                            accessory_id=item['accessory_id']
                        )
                        
                        if store_accessory.quantity < item['quantity']:
                            raise ValueError(f"Insufficient stock for accessory {store_accessory.accessory.name}")
                        
                        # Ensure proper decimal conversion
                        try:
                            price = Decimal(str(item['price']))
                            total_price = Decimal(str(item['total_price']))
                        except (decimal.InvalidOperation, decimal.ConversionSyntax) as e:
                            print(f"Price conversion error: {e}")  # Debug log
                            print(f"Price value: {item['price']}")  # Debug log
                            print(f"Total price value: {item['total_price']}")  # Debug log
                            raise ValueError(f"Invalid price format for accessory {store_accessory.accessory.name}")
                        
                        AccessorySaleItem.objects.create(
                            sale=sale,
                            accessory=store_accessory,
                            quantity=int(item['quantity']),
                            price=price,
                            total_price=total_price
                        )
                        print(f"Created accessory sale item for: {store_accessory.accessory.name}")  # Debug log
                        
                    except StoreAccessoryInventory.DoesNotExist:
                        raise ValueError(f"Accessory with ID {item['accessory_id']} not found in store {store_id}")
                    except Exception as e:
                        print(f"Error processing accessory: {str(e)}")  # Debug log
                        raise
            
            # Calculate the total
            sale.calculate_total()
            
            return JsonResponse({
                'success': True,
                'sale_id': sale.id,
                'sale_number': sale.service_sale_number,
                'redirect_url': reverse('service_sale_details', args=[sale.id])
            })
            
    except Exception as e:
        print(f"Error creating sale: {str(e)}")  # Debug log
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def sale_details(request, sale_id):
    sale = get_object_or_404(ServiceSale, id=sale_id)
    return render(request, 'saloon_order_details.html', {'sale': sale})
        
@login_required
def create_service_sale(request):
    user_groups = request.user.groups.all()
    if not Group.objects.filter(name='Branch Manager').exists() or not user_groups.filter(name='Branch Manager').exists():
        messages.error(request, 'You do not have permission to create a sale.')
        return redirect('error')

    ServiceFormset = inlineformset_factory(ServiceSale, ServiceSaleItem, form=ServiceSaleItemForm, extra=1, can_delete=True)
    AccessoryFormset = inlineformset_factory(ServiceSale, AccessorySaleItem, form=AccessorySaleItemForm, extra=1, can_delete=True)
    ProductFormset = inlineformset_factory(ServiceSale, ProductSaleItem, form=ProductSaleItemForm, extra=1, can_delete=True)

    if request.method == 'POST':
        sale_form = ServiceSaleForm(request.POST, user=request.user)
        store = sale_form.cleaned_data.get('store') if sale_form.is_valid() else None  # Access after validation
        service_formset = ServiceFormset(request.POST, instance=None, form_kwargs={'store': store})
        accessory_formset = AccessoryFormset(request.POST, instance=None, form_kwargs={'store': store})
        product_formset = ProductFormset(request.POST, instance=None, form_kwargs={'store': store})
        
        if sale_form.is_valid() and service_formset.is_valid() and accessory_formset.is_valid() and product_formset.is_valid():
    
    
            print("Accessory Formset Initial Forms:", request.POST.get('accessory_sale_items-INITIAL_FORMS'))
            print("Product Formset Total Forms:", request.POST.get('product_sale_items-TOTAL_FORMS'))
            print("Product Formset Initial Forms:", request.POST.get('product_sale_items-INITIAL_FORMS'))
            sale = sale_form.save()
            service_formset.instance = sale
            service_formset.save()
            accessory_formset.instance = sale
            accessory_formset.save()
            product_formset.instance = sale
            product_formset.save()
            sale.calculate_total()


            messages.success(request, 'Service Sale has been created successfully')
            return redirect('store_sale_list')
        else:
            # Display detailed formset errors for user correction
            for formset in [service_formset, accessory_formset, product_formset]:
                for form in formset:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{form.prefix}: {field} - {error}")
    
    else:
        sale_form = ServiceSaleForm(user=request.user)
        store = sale_form.fields['store'].queryset.first()  # Default to the first store if exists
        service_formset = ServiceFormset(instance=None, form_kwargs={'store': store})
        accessory_formset = AccessoryFormset(instance=None, form_kwargs={'store': store})
        product_formset = ProductFormset(instance=None, form_kwargs={'store': store})

    return render(request, 'create_service_sale.html', {
        'sale_form': sale_form,
        'service_formset': service_formset,
        'accessory_formset': accessory_formset,
        'product_formset': product_formset,
    })
    
def update_service_sale(request, pk):
    sale = ServiceSale.objects.get(pk=pk)
    ServiceFormset = inlineformset_factory(ServiceSale, ServiceSaleItem, form=ServiceSaleItemForm, extra=1, can_delete=True)
    AccessoryFormset = inlineformset_factory(ServiceSale, AccessorySaleItem, form=AccessorySaleItemForm, extra=1, can_delete=True)
    ProductFormset = inlineformset_factory(ServiceSale, ProductSaleItem, form=ProductSaleItemForm, extra=1, can_delete=True)

    if request.method == 'POST':
        sale_form = ServiceSaleForm(request.POST, instance=sale)
        service_formset = ServiceFormset(request.POST, instance=sale)
        accessory_formset = AccessoryFormset(request.POST, instance=sale)
        product_formset = ProductFormset(request.POST, instance=sale)

        if sale_form.is_valid() and service_formset.is_valid() and accessory_formset.is_valid() and product_formset.is_valid():
            sale = sale_form.save()
            service_formset.save()
            accessory_formset.save()
            product_formset.save()
            messages.success(request, 'Sale updated successfully.')
            return redirect('sale_list')  # Redirect to your sale list view
        else:
            messages.error(request, 'Error updating sale.')
    else:
        sale_form = ServiceSaleForm(instance=sale)
        service_formset = ServiceFormset(instance=sale)
        accessory_formset = AccessoryFormset(instance=sale)
        product_formset = ProductFormset(instance=sale)

    return render(request, 'update_service_sale.html', {
        'sale_form': sale_form,
        'service_formset': service_formset,
        'accessory_formset': accessory_formset,
        'product_formset': product_formset,
        'sale': sale,  # Pass the sale object to the template
    })
    
def store_sale_service_invoice_list(request):
    invoices = ServiceSaleInvoice.objects.all()
    return render(request,'store_service_invoice_list.html', {'invoices': invoices})
    
@login_required
def store_service_sales_view(request):
    # Assuming the logged-in user is the manager of the store
    store = get_object_or_404(Store, manager=request.user)

    # Fetch all service sales for this store
    service_sales = ServiceSale.objects.filter(store=store)

    return render(request, 'store_sale_list.html', {
        'service_sales': service_sales,
        'store': store,
    })
    
def service_sale_details(request, sale_id):
    sale = get_object_or_404(ServiceSale, id=sale_id)
    service_items = sale.service_sale_items.all()
    accessory_items = sale.accessory_sale_items.all()
    product_items = sale.product_sale_items.all()
    context ={
        'sale':sale,
        'service_items': service_items,
        'accessory_items': accessory_items,
        'product_items': product_items,
    }
    return render (request, 'service_sale_details.html', context)

##Pay for the service given at a sa;pm branch
def record_payment_view(request, sale_id):
    sale = get_object_or_404(ServiceSale, id=sale_id)

    if request.method == 'POST':
        form = PaymentForm(request.POST, sale_balance=sale.balance)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            remarks = form.cleaned_data['remarks']

            try:
                with transaction.atomic():
                    # Record payments
                    if payment_method == 'mixed':
                        # Handle mixed payment methods
                        for method in ['cash', 'mobile_money', 'airtel_money', 'visa']:
                            amount_field = f'{method}_amount'
                            if form.cleaned_data.get(amount_field):
                                Payment.objects.create(
                                    sale=sale,
                                    payment_method=method,
                                    amount=form.cleaned_data[amount_field],
                                    remarks=f"{method.title()}: {remarks}"
                                )
                    else:
                        # Single payment method
                        Payment.objects.create(
                            sale=sale,
                            payment_method=payment_method,
                            amount=form.cleaned_data['amount'],
                            remarks=remarks
                        )

                    # Recalculate totals and handle paid status
                    previous_status = sale.paid_status
                    sale.calculate_total()  # This will also create commissions if newly paid
                    
                    if previous_status != 'paid' and sale.paid_status == 'paid':
                        sale.create_service_commissions()
                        sale.create_product_commissions()
                        messages.success(request, "Payment recorded and commissions calculated successfully.")
                    else:
                        messages.success(request, "Payment recorded successfully.")

            except Exception as e:
                print(f"ERROR: {str(e)}")
                messages.error(request, f"Error recording payment: {str(e)}")
                
            return redirect('store_sale_list')
    else:
        form = PaymentForm(sale_balance=sale.balance)

    return render(request, 'record_payment.html', {'form': form, 'sale': sale})

def all_payment_receipts_view(request):
    # Retrieve all payment receipts, ordered by payment date (most recent first)
    payments = Payment.objects.select_related('sale', 'sale__customer', 'sale__store').order_by('-payment_date')

    return render(request, 'salon_payment_receipts.html', {'payments': payments})

def payment_list_view(request):
    # Query all payments grouped by payment method
    payment_method = request.GET.get('payment_method')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    # Base queryset for paid sales
    sales = ServiceSale.objects.filter(paid_status='paid').order_by('-sale_date')
    
    # Apply filters
    if payment_method:
        sales = sales.filter(payments__payment_method=payment_method).distinct()
    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)

    # Calculate summary statistics
    summary_stats = {
        'total_receipts': sales.count(),
        'total_amount': sales.aggregate(total=Sum('total_amount'))['total'] or 0,
        'payment_methods_summary': Payment.objects.filter(
            sale__in=sales
        ).values('payment_method').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ),
        'daily_sales': sales.annotate(
            date=TruncDate('sale_date')
        ).values('date').annotate(
            daily_total=Sum('total_amount'),
            receipt_count=Count('id')
        ).order_by('-date')[:7]  # Last 7 days
    }

    context = {
        'sales': sales,
        'summary_stats': summary_stats,
        'payment_method_choices': Payment.PAYMENT_METHOD_CHOICES,
        'selected_payment_method': payment_method,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'payment_list.html', context)

@login_required
def service_sale_receipt(request, sale_id):
    sale = get_object_or_404(ServiceSale, id=sale_id)
    
    # Calculate subtotal (excluding accessories)
    service_total = sum(item.total_price for item in sale.service_sale_items.all())
    product_total = sum(item.total_price for item in sale.product_sale_items.all())
    subtotal = service_total + product_total
    
    context = {
        'sale': sale,
        'subtotal': subtotal,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'service_sale_receipt.html', context)
    
def store_sale_list(request):
    # Assuming the logged-in user is the manager of the store
    store = get_object_or_404(Store, manager=request.user)
    # Fetch all service sales for this store
    sales = ServiceSale.objects.filter(store=store)

    # Pass the store sales to the template
    return render(request,'store_sale_list.html', {'sales': sales,'store':store})

def finance_store_sale_list(request):
    
    # Fetch all service sales for all stores
    # sales = ServiceSale.objects.all().order_by('-sale_date')
    sales = ServiceSale.objects.select_related('store', 'customer') \
        .prefetch_related(
            'service_sale_items__service',    # Prefetch related services for each sale
            'service_sale_items__staff',     # Prefetch related staff
            'accessory_sale_items__accessory',  # Prefetch related accessories
            'product_sale_items__product'    # Prefetch related products
        ).order_by('-sale_date')

    # Pass the store sales to the template
    return render(request,'finance_store_sale_list.html', {'sales': sales})

#Staff Commissions for service and product sales
@login_required
def monthly_commission_list(request):
    """View to list all monthly commission compilations"""
    # Get filter parameters
    year = request.GET.get('year')
    month = request.GET.get('month')
    staff_id = request.GET.get('staff_id')
    
    # Get service commissions
    service_commissions = StaffCommission.objects.select_related(
        'staff',
        'service_sale_item__service__service',
        'service_sale_item__sale'
    ).annotate(
        commission_type=Value('service', CharField())
    ).order_by('-created_at')
    
    # Get product commissions
    product_commissions = StaffProductCommission.objects.select_related(
        'staff',
        'product_sale_item__product__product',
        'product_sale_item__sale'
    ).annotate(
        commission_type=Value('product', CharField())
    ).order_by('-created_at')
    
    # Apply filters if provided
    if year and month:
        service_commissions = service_commissions.filter(
            created_at__year=year,
            created_at__month=month
        )
        product_commissions = product_commissions.filter(
            created_at__year=year,
            created_at__month=month
        )
    
    if staff_id:
        service_commissions = service_commissions.filter(staff_id=staff_id)
        product_commissions = product_commissions.filter(staff_id=staff_id)
    
    # Combine both querysets
    all_commissions = list(chain(service_commissions, product_commissions))
    all_commissions.sort(key=lambda x: x.created_at, reverse=True)
    
    # Get unique years and months for the filter dropdowns
    service_dates = StaffCommission.objects.dates('created_at', 'month', order='DESC')
    product_dates = StaffProductCommission.objects.dates('created_at', 'month', order='DESC')
    all_dates = set(service_dates) | set(product_dates)
    years = sorted(set(date.year for date in all_dates), reverse=True)
    
    # Get all staff for the filter dropdown
    staff_members = Staff.objects.all().order_by('first_name')
    
    # Calculate totals for both commission types
    service_totals = service_commissions.aggregate(
        total_amount=Sum('commission_amount'),
        total_unpaid=Sum('commission_amount', filter=models.Q(paid=False)),
        total_paid=Sum('commission_amount', filter=models.Q(paid=True))
    )
    # Calculate totals for product commissions
    product_totals = product_commissions.aggregate(
        total_amount=Sum('commission_amount')
    )
    
    # Initialize product paid/unpaid totals
    product_totals['total_paid'] = product_commissions.filter(paid=True).aggregate(
        total=Sum('commission_amount'))['total'] or 0
    product_totals['total_unpaid'] = product_commissions.filter(paid=False).aggregate(
        total=Sum('commission_amount'))['total'] or 0
    
    # Combine totals
    totals = {
        'total_amount': (service_totals['total_amount'] or 0) + (product_totals['total_amount'] or 0),
        'total_unpaid': (service_totals['total_unpaid'] or 0) + (product_totals['total_unpaid'] or 0),
        'total_paid': (service_totals['total_paid'] or 0) + (product_totals['total_paid'] or 0),
    }
    
    context = {
        'commissions': all_commissions,
        'years': years,
        'months': range(1, 13),  # 1 to 12
        'staff_members': staff_members,
        'selected_year': year,
        'selected_month': month,
        'selected_staff': staff_id,
        'totals': totals,
        'current_year': timezone.now().year,
        'current_month': timezone.now().month,
    }
    return render(request, 'monthly_commission_list.html', context)

def product_commission_list(request):
    """View to list all product commission compilations"""
    # Get filter parameters
    year = request.GET.get('year')
    month = request.GET.get('month')
    staff_id = request.GET.get('staff_id')
    
    # Get product commissions with related data
    commissions = StaffProductCommission.objects.select_related(
        'staff',
        'product_sale_item__product__product',
        'product_sale_item__sale'
    ).order_by('-created_at')
    
    # Apply filters if provided
    if year and month:
        commissions = commissions.filter(
            created_at__year=year,
            created_at__month=month
        )
    if staff_id:
        commissions = commissions.filter(staff_id=staff_id)
    
    # Get unique years and months for the filter dropdowns
    available_dates = StaffProductCommission.objects.dates('created_at', 'month', order='DESC')
    years = sorted(set(date.year for date in available_dates), reverse=True)
    
    # Get all staff for the filter dropdown
    staff_members = Staff.objects.all().order_by('first_name')
    
    # Calculate totals
    totals = commissions.aggregate(
        total_amount=Sum('commission_amount'),
        total_unpaid=Sum('commission_amount', filter=models.Q(paid=False)),
        total_paid=Sum('commission_amount', filter=models.Q(paid=True))
    )
    
    context = {
        'commissions': commissions,
        'years': years,
        'months': range(1, 13),
        'staff_members': staff_members,
        'selected_year': year,
        'selected_month': month,
        'selected_staff': staff_id,
        'totals': totals,
        'current_year': timezone.now().year,
        'current_month': timezone.now().month,
    }
    return render(request, 'product_commission_list.html', context)

@login_required
def staff_monthly_commission_detail(request, staff_id, year, month):
    """View detailed commissions for a staff member in a specific month"""
    monthly_commission = MonthlyStaffCommission.objects.get(
        staff_id=staff_id,
        month__year=year,
        month__month=month
    )
    
    individual_commissions = StaffCommission.objects.filter(
        monthly_commission=monthly_commission
    ).select_related('service_sale_item__service__service')

    if request.method == 'POST' and 'mark_paid' in request.POST:
        reference = request.POST.get('payment_reference')
        monthly_commission.mark_as_paid(reference)
        messages.success(request, "Marked commission as paid")
        return redirect('monthly_commission_list')

    context = {
        'monthly_commission': monthly_commission,
        'individual_commissions': individual_commissions,
    }
    return render(request, 'staff_monthly_commission_detail.html', context)
    
@login_required
def store_services_view(request):
    # Get the store managed by the logged-in user
    store = get_object_or_404(Store, manager=request.user)

    # Fetch services offered by the store
    store_services = StoreService.objects.filter(store=store)

    # Pass the store and services to the template
    return render(request, 'each_store_services.html', {'store': store, 'store_services': store_services})

@login_required
def particular_store_inventory(request):
    # Assuming the user is authenticated and has a related Store object
    store = get_object_or_404(Store, manager=request.user)  # Adjust based on your User model

    if store:
        inventory_items = StoreAccessoryInventory.objects.filter(store=store)
        return render(request, 'particular_store_inventory.html', {'inventory_items': inventory_items})
    else:
        # Handle the case where the user is not associated with a store
        return render(request, 'no_store_access.html')
    
    
@login_required
def create_internal_requests(request):
    # If the request is POST, process the form and formset
    if request.method == 'POST':
        form = InternalAccessoryRequestForm(request.POST, user=request.user)
        item_formset = InternalAccessoryRequestItemFormSet(request.POST)
        
        if form.is_valid() and item_formset.is_valid():
            # Save the main InternalAccessoryRequest object
            request = form.save(commit=False)
            request.save()
            
            # Save the items in the formset, attaching them to the main request
            items = item_formset.save(commit=False)
            for item in items:
                item.request = request
                item.save()
                item.save()

            return redirect('store_internal_requests')  # Redirect to a success page

    # For GET requests, create empty forms
    else:
        form = InternalAccessoryRequestForm(user=request.user)
        item_formset = InternalAccessoryRequestItemFormSet(queryset=InternalAccessoryRequestItem.objects.none())

    return render(request, 'create_internal_requests.html', {'form': form, 'item_formset': item_formset})

@login_required
def store_internal_requests(request):
    store = get_object_or_404(Store, manager=request.user)
    internal_requests = InternalAccessoryRequest.objects.filter(store=store)
    return render(request,'store_internal_requests.html', {'internal_requests': internal_requests})


@login_required
def all_internal_requests(request):
    all_requests = InternalAccessoryRequest.objects.all()
    return render(request, 'all_internal_requests.html', {'internal_requests': all_requests})

def internal_request_detail(request, request_id):
    internal_request = get_object_or_404(InternalAccessoryRequest, id=request_id)
    return render(request, 'internal_request_detail.html', {'internal_request': internal_request})

@login_required
def process_internal_request(request, request_id):
    internal_request = get_object_or_404(InternalAccessoryRequest, id=request_id)
    if request.method == 'POST':
        form = ApproveRejectRequestForm(request.POST, instance=internal_request)
        if form.is_valid():
            processed_request = form.save(commit=False)
            processed_request.save()
            messages.success(request, f"Request has been {processed_request.status}.")
            return redirect('all_internal_requests')
    else:
        form = ApproveRejectRequestForm(instance=internal_request)
    return render(request, 'process_internal_request.html', {'internal_request': internal_request, 'form':form})

def mark_as_delivered(request, request_id):
    # Get the request instance with status 'approved'
    accessory_request = get_object_or_404(InternalAccessoryRequest, id=request_id, status='approved')

    if request.method == 'POST':
        form = MarkAsDeliveredForm(request.POST, instance=accessory_request)
        if form.is_valid():
            # Validate sufficient inventory before processing
            if not validate_sufficient_inventory(accessory_request, accessory_request.store):
                messages.error(request, "Insufficient inventory to fulfill the delivery request.")
                return redirect('mark_as_delivered', request_id=request_id)
            with transaction.atomic():
                try:
                    # Deduct from main inventory
                    deduct_from_main_inventory(accessory_request)
                    # Add to store inventory
                    # Add to store inventory
                    for item in accessory_request.items.all():
                        store_inventory, created = StoreAccessoryInventory.objects.get_or_create(
                            store=accessory_request.store,
                            accessory=item.accessory,
                            defaults={'quantity': 0}
                        )
                        store_inventory.quantity += item.quantity_requested
                        store_inventory.save()
                        
                        #log adjustment for accessoreis
                        StoreInventoryAdjustment.objects.create(
                            accessory_inventory = store_inventory,
                            adjustment = 'requisition',
                            quantity = item.quantity_requested,
                            reason = f"Delivered from main inventory via request {accessory_request.id}"
                        )

                    # Mark the request as delivered
                    accessory_request.status = 'delivered'
                    accessory_request.save(update_fields=['status'])

                    messages.success(request, "Request has been marked as delivered and inventory updated.")
                    return redirect('store_internal_requests')

                except Exception as e:
                    print(f"Error occurred: {e}")
                    messages.error(request, str(e))
                    return redirect('mark_as_delivered', request_id=request_id)
            
    else:
        form = MarkAsDeliveredForm(instance=accessory_request)

    return render(request, 'mark_as_delivered.html', {
        'form': form,
        'accessory_request': accessory_request
    })
def validate_sufficient_inventory(request, store):
    for item in request.items.all():
        main_inventory = AccessoryInventory.objects.get(accessory=item.accessory)
        if main_inventory.quantity < item.quantity_requested:
            return False
    return True

def deduct_from_main_inventory(request):
    for item in request.items.all():
        main_inventory = AccessoryInventory.objects.get(accessory=item.accessory)
        
        # Check if there's enough stock
        if main_inventory.quantity < item.quantity_requested:
            raise ValidationError(f"Insufficient stock for {item.accessory.name}")

        # Deduct the quantity from main inventory
        main_inventory.quantity -= item.quantity_requested
        main_inventory.save()

        # Create an adjustment record
        AccessoryInventoryAdjustment.objects.create(
            accessory_inventory=main_inventory,
            adjustment=-item.quantity_requested,  # Negative for deduction
            description="Delivered to store"
        )

def add_to_store_inventory(request, store):
    for item in request.items.all():
            store_inventory, created = StoreAccessoryInventory.objects.get_or_create(
                store=request.store,
                accessory=item.accessory,
                defaults={'quantity': 0}
            )
    
            # Access the object's quantity attribute directly:
            if not created:
                store_inventory.quantity += item.quantity_requested
                store_inventory.save()
            else:
                # Handle case of newly created record (optional)
                pass


@login_required
def branch_staff_view(request):
    # Get the branch managed by the logged-in user (assuming a manager is logged in)
    store = get_object_or_404(Store, manager=request.user)

    # Fetch all staff members assigned to this branch
    staff_members = Staff.objects.filter(store=store)

    # Pass the branch and staff to the template
    return render(request, 'branch_staff.html', {'store': store, 'staff_members': staff_members})

def manager_store_accessory_report(request):
    return render(request, 'manager_store_accessory_report.html')


################REQUISITIONS################################################################################################
def create_requisition(request):
    _RequisitionItemFormSet = modelformset_factory(RequisitionItem, form=RequisitionItemForm, extra=1)

    # Initialize item_formset to None outside the if/else to ensure it's always defined
    item_formset = None 
    
    if request.method == 'POST':
        requisition_form = RequisitionForm(request.POST, request.FILES)
        
        # --- Start of critical change ---
        # Initialize supplier to None or a default before conditional blocks
        current_supplier = None 
        
        # Try to get the supplier from the submitted data *before* full validation,
        # so we can pass it to the item_formset even if the main form has other errors.
        # Use the correct POST key for your supplier field based on its prefix.
        # If RequisitionForm uses prefix='requisition' and field is 'supplier', it's 'requisition-supplier'.
        # If RequisitionForm has no prefix, and field is 'supplier', it's just 'supplier'.
        # Let's assume you're using 'requisition-supplier' based on typical prefixing.
        posted_supplier_id = request.POST.get('supplier') # ADJUST THIS IF YOUR FIELD NAME IS DIFFERENT

        if posted_supplier_id:
            try:
                current_supplier = Supplier.objects.get(pk=posted_supplier_id)
            except Supplier.DoesNotExist:
                # Handle case where posted supplier ID is invalid (e.g., tampered with)
                # The main form's validation will also catch this if it's a ModelChoiceField
                pass 
        # --- End of critical change ---

        # Initialize the formset with the potentially available supplier
        # This formset instance will be used for rendering if the main form is invalid.
        item_formset = _RequisitionItemFormSet(
            request.POST,
            request.FILES,
            queryset=RequisitionItem.objects.none(),
            form_kwargs={'supplier': current_supplier} # Use the safely defined 'current_supplier'
        )
        
        if requisition_form.is_valid() and item_formset.is_valid():
            # If both are valid, proceed to save
            requisition = requisition_form.save(commit=False)
            # requisition.supplier is already set by requisition_form.save() if it's a direct field
            requisition.save()
            
            # Save each form in the formset
            for form in item_formset:
                if form.cleaned_data and form.cleaned_data.get('quantity') and form.cleaned_data.get('raw_material'):
                    requisition_item = form.save(commit=False)
                    requisition_item.requisition = requisition
                    
                    raw_material = form.cleaned_data['raw_material']
                    current_price = RawMaterialPrice.get_current_price(
                        raw_material=raw_material,
                        supplier=current_supplier # Use current_supplier here too
                    )
                    
                    if current_price is not None:
                        requisition_item.price_per_unit = current_price
                    
                    requisition_item.save()
            
            return redirect('requisition_details', requisition_id=requisition.id)
        else:
            # If either form or formset is invalid, they will contain errors.
            # They are already initialized with request.POST data, so they'll render with errors.
            print("Requisition Form Errors:", requisition_form.errors)
            print("Item Formset Errors:", item_formset.errors)
            # Remove the problematic line that was causing the error
            # print("Item Formset Non-Field Errors:", item_formset.non_field_errors())


    else: # GET request
        requisition_form = RequisitionForm()
        # For a GET request, no supplier is selected yet, so formset is initialized with None
        item_formset = _RequisitionItemFormSet(queryset=RequisitionItem.objects.none(), form_kwargs={'supplier': None})

    return render(request, 'create_requisition.html', {
        'requisition_form': requisition_form,
        'item_formset': item_formset,
    })
    
def get_raw_materials_by_supplier(request):
    supplier_id = request.GET.get('supplier_id')
    raw_materials = RawMaterial.objects.filter(suppliers__id=supplier_id)
    data = list(raw_materials.values('id', 'name'))
    return JsonResponse(data, safe=False)

def all_requisitions(request):
    from django.db.models import Q, Count
    from datetime import datetime, timedelta
    
    # Get filter parameters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    supplier = request.GET.get('supplier', '')
    date_range = request.GET.get('date_range', '')
    min_cost = request.GET.get('min_cost', '')
    max_cost = request.GET.get('max_cost', '')
    
    # Start with all requisitions
    requisitions = Requisition.objects.select_related('supplier').prefetch_related('requisitionitem_set').order_by('-created_at', '-id')
    
    # Apply filters
    if search:
        requisitions = requisitions.filter(
            Q(requisition_no__icontains=search) |
            Q(supplier__name__icontains=search) |
            Q(supplier__company_name__icontains=search)
        )
    
    if status:
        requisitions = requisitions.filter(status=status)
    
    if supplier:
        requisitions = requisitions.filter(supplier_id=supplier)
    
    if date_range:
        try:
            start_date, end_date = date_range.split(' - ')
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            requisitions = requisitions.filter(created_at__date__range=[start_date, end_date])
        except:
            pass
    
    if min_cost:
        try:
            min_cost = float(min_cost)
            requisitions = requisitions.filter(total_cost__gte=min_cost)
        except:
            pass
    
    if max_cost:
        try:
            max_cost = float(max_cost)
            requisitions = requisitions.filter(total_cost__lte=max_cost)
        except:
            pass
    
    # Order by created date descending
    requisitions = requisitions.order_by('-created_at')
    
    # Dashboard Statistics
    all_requisitions_count = Requisition.objects.count()
    total_requisitions = all_requisitions_count
    approved_requisitions = Requisition.objects.filter(status='approved').count()
    pending_requisitions = Requisition.objects.filter(status__in=['created', 'checking']).count()
    rejected_requisitions = Requisition.objects.filter(status='rejected').count()
    
    # Status counts for chart
    created_count = Requisition.objects.filter(status='created').count()
    checking_count = Requisition.objects.filter(status='checking').count()
    delivered_count = Requisition.objects.filter(status='delivered').count()
    
    # Get all suppliers for filter dropdown
    suppliers = Supplier.objects.all().order_by('name')
    
    # Recent activities (last 10 requisitions with status changes)
    recent_activities = []
    recent_requisitions = Requisition.objects.select_related('supplier').order_by('-updated_at')[:10]
    
    for req in recent_requisitions:
        if req.status == 'created':
            color = 'created'
            title = f"New Requisition Created"
            description = f"Requisition {req.requisition_no} created for {req.supplier.name}"
        elif req.status == 'approved':
            color = 'approved'
            title = f"Requisition Approved"
            description = f"Requisition {req.requisition_no} approved"
        elif req.status == 'rejected':
            color = 'rejected'
            title = f"Requisition Rejected"
            description = f"Requisition {req.requisition_no} rejected"
        elif req.status == 'checking':
            color = 'checking'
            title = f"Requisition in Checking"
            description = f"Requisition {req.requisition_no} moved to checking"
        elif req.status == 'delivered':
            color = 'delivered'
            title = f"Requisition Delivered"
            description = f"Requisition {req.requisition_no} delivered"
        else:
            color = 'created'
            title = f"Requisition Updated"
            description = f"Requisition {req.requisition_no} status updated"
        
        recent_activities.append({
            'title': title,
            'description': description,
            'time': req.updated_at.strftime('%M minutes ago') if req.updated_at > timezone.now() - timedelta(hours=1) else req.updated_at.strftime('%H:%M, %b %d'),
            'color': color
        })
    
    user_is_production_manager = request.user.groups.filter(name='Production Manager').exists()
    
    context = {
        'requisitions': requisitions,
        'user_is_production_manager': user_is_production_manager,
        'total_requisitions': total_requisitions,
        'approved_requisitions': approved_requisitions,
        'pending_requisitions': pending_requisitions,
        'rejected_requisitions': rejected_requisitions,
        'created_count': created_count,
        'checking_count': checking_count,
        'delivered_count': delivered_count,
        'suppliers': suppliers,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'all_requisitions.html', context)

def export_requisitions_csv(request):
    import csv
    from django.http import HttpResponse
    from django.db.models import Q
    from datetime import datetime
    
    # Get filter parameters (same as all_requisitions view)
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    supplier = request.GET.get('supplier', '')
    date_range = request.GET.get('date_range', '')
    min_cost = request.GET.get('min_cost', '')
    max_cost = request.GET.get('max_cost', '')
    
    # Start with all requisitions
    requisitions = Requisition.objects.select_related('supplier').prefetch_related('requisitionitem_set')
    
    # Apply filters (same logic as all_requisitions view)
    if search:
        requisitions = requisitions.filter(
            Q(requisition_no__icontains=search) |
            Q(supplier__name__icontains=search) |
            Q(supplier__company_name__icontains=search)
        )
    
    if status:
        requisitions = requisitions.filter(status=status)
    
    if supplier:
        requisitions = requisitions.filter(supplier_id=supplier)
    
    if date_range:
        try:
            start_date, end_date = date_range.split(' - ')
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            requisitions = requisitions.filter(created_at__date__range=[start_date, end_date])
        except:
            pass
    
    if min_cost:
        try:
            min_cost = float(min_cost)
            requisitions = requisitions.filter(total_cost__gte=min_cost)
        except:
            pass
    
    if max_cost:
        try:
            max_cost = float(max_cost)
            requisitions = requisitions.filter(total_cost__lte=max_cost)
        except:
            pass
    
    # Order by created date descending
    requisitions = requisitions.order_by('-created_at')
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="requisitions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Requisition Number',
        'Supplier Name',
        'Supplier Company',
        'Status',
        'Created Date',
        'Total Cost (UGX)',
        'Items Count'
    ])
    
    for requisition in requisitions:
        writer.writerow([
            requisition.requisition_no,
            requisition.supplier.name,
            requisition.supplier.company_name,
            requisition.get_status_display(),
            requisition.created_at.strftime('%Y-%m-%d %H:%M'),
            requisition.total_cost,
            requisition.requisitionitem_set.count()
        ])
    
    return response

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
        
@allowed_users(allowed_roles=['Finance'])
def approve_requisition(request, requisition_id):
    requisition = Requisition.objects.get(pk=requisition_id)
    requisition.status = 'approved'
    requisition.save()
    messages.success(request, 'Request approved successfully')
    return redirect('lpos_list')

def reject_requisition(request, requisition_id):
    requisition = Requisition.objects.get(pk=requisition_id)
    requisition.status ='rejected'
    requisition.save()
    messages.success(request, 'Request rejected successfully')
    return redirect('all_requisitions')

################LPOS###########################
def lpo_list(request):
    lpos = LPO.objects.all().order_by('-created_at')
    context = {'lpos': lpos}
    return render(request, 'lpo_list.html', context)

@allowed_users(allowed_roles=['Finance'])
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
            # lpo.is_paid = False
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
        pay_by = request.POST.get('pay_by', '')  # Capture the payment method
        voucher_notes = request.POST.get('voucher_notes', '')
        try:
            amount_paid = Decimal(amount_paid)
            if amount_paid <= 0:
                messages.error(request, "Amount must be positive.")
                return redirect('pay_lpo', lpo_id=lpo.id)
            
            # Update LPO with the new payment
            lpo.amount_paid += amount_paid
            lpo.save()
            
            # Check if full payment
            payment_type = 'full' if lpo.outstanding_balance <= 0 else 'partial'
            
            # Create payment voucher (consider using a form if needed)
            voucher = PaymentVoucher(
                lpo=lpo, 
                amount_paid=amount_paid,
                pay_by=pay_by,
                voucher_notes=voucher_notes, 
                payment_type=payment_type
            )
            # Save the voucher (calls the custom save() logic)
            voucher.save()

            # Check if the balance has been cleared
            if lpo.outstanding_balance <= 0:
                messages.success(request, "Payment completed successfully.")
            else:
                messages.success(request, "Payment received. Outstanding balance updated.")

            return redirect('production_payment_vouchers')  # Redirect to the PO details page

        except ValueError:
            messages.error(request, "Invalid amount.")
            return redirect('pay_lpo', lpo_id=lpo.id)
    
    return render(request, 'lpo_pay.html', {'lpo': lpo})

class LpoDetailView(DetailView):
    model = LPO
    template_name = 'lpo_detail.html'
    context_object_name = 'lpo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
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
    """Enhanced goods received notes with beautiful statistics dashboard"""
    from django.db.models import Sum, Count, Q
    from datetime import datetime, timedelta
    
    # Get all goods received notes
    goods_received_notes = GoodsReceivedNote.objects.select_related(
        'requisition', 'requisition__supplier', 'lpo'
    ).prefetch_related(
        'requisition__requisitionitem_set__raw_material'
    ).all().order_by('-created_at')
    
    # Calculate comprehensive statistics
    total_notes = goods_received_notes.count()
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_notes = goods_received_notes.filter(created_at__gte=thirty_days_ago)
    recent_count = recent_notes.count()
    
    # Status breakdown
    successful_deliveries = goods_received_notes.filter(reason='Successful').count()
    expired_items = goods_received_notes.filter(reason='expired').count()
    quality_issues = goods_received_notes.filter(reason='quality').count()
    spillage_issues = goods_received_notes.filter(reason='spillage').count()
    
    # Calculate total delivered quantities and values
    total_delivered_quantity = 0
    total_delivered_value = 0
    suppliers_count = 0
    raw_materials_count = 0
    
    # Track unique suppliers and raw materials
    suppliers_set = set()
    raw_materials_set = set()
    
    for note in goods_received_notes:
        suppliers_set.add(note.requisition.supplier.id)
        
        for item in note.requisition.requisitionitem_set.all():
            if item.delivered_quantity:
                total_delivered_quantity += item.delivered_quantity
                total_delivered_value += item.delivered_quantity * (item.price_per_unit or 0)
                raw_materials_set.add(item.raw_material.id)
    
    suppliers_count = len(suppliers_set)
    raw_materials_count = len(raw_materials_set)
    
    # Monthly trends (last 6 months)
    monthly_data = []
    for i in range(6):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        
        month_notes = goods_received_notes.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': month_notes
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    # Top suppliers by delivery count
    top_suppliers = goods_received_notes.values(
        'requisition__supplier__name'
    ).annotate(
        delivery_count=Count('id')
    ).order_by('-delivery_count')[:5]
    
    # Recent deliveries for timeline
    recent_deliveries = goods_received_notes[:10]
    
    # Discrepancy statistics
    discrepancy_reports = DiscrepancyDeliveryReport.objects.count()
    pending_replacements = ReplaceNote.objects.filter(status='pending').count()
    total_refunds = DebitNote.objects.count()
    
    context = {
        'goods_received_notes': goods_received_notes,
        'total_notes': total_notes,
        'recent_count': recent_count,
        'successful_deliveries': successful_deliveries,
        'expired_items': expired_items,
        'quality_issues': quality_issues,
        'spillage_issues': spillage_issues,
        'total_delivered_quantity': total_delivered_quantity,
        'total_delivered_value': total_delivered_value,
        'suppliers_count': suppliers_count,
        'raw_materials_count': raw_materials_count,
        'monthly_data': monthly_data,
        'top_suppliers': top_suppliers,
        'recent_deliveries': recent_deliveries,
        'discrepancy_reports': discrepancy_reports,
        'pending_replacements': pending_replacements,
        'total_refunds': total_refunds,
    }
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


def production_payment_vouchers(request):
    # Filter ProDe records where the outstanding balance is greater than 0
    prod_vouchers = PaymentVoucher.objects.all()
    context ={
        'prod_vouchers': prod_vouchers,
    }
    return render(request, 'production_payment_vouchers.html', context)

def production_payment_voucher_detail(request, voucher_number):
    voucher = get_object_or_404(PaymentVoucher, voucher_number=voucher_number)
    context = {
        'voucher': voucher,
        'lpo': voucher.lpo,  # Access related LPO information
    }
    return render(request, 'payment_voucher_detail.html', context)



# now we must add the additional quantities for comformation e.g requested, available 



@login_required
def update_raw_material_price(request, raw_material_id, supplier_id):
    raw_material = get_object_or_404(RawMaterial, id=raw_material_id)
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    # Get the current price value
    current_price_value = RawMaterialPrice.get_current_price(raw_material, supplier)
    
    # Get the current price object if it exists
    current_price_obj = RawMaterialPrice.objects.filter(
        raw_material=raw_material,
        supplier=supplier,
        is_current=True
    ).first()
    
    # Get price history for this material and supplier
    price_history = RawMaterialPrice.objects.filter(
        raw_material=raw_material,
        supplier=supplier
    ).order_by('-effective_date')
    
    if request.method == 'POST':
        form = RawMaterialPriceForm(request.POST)
        if form.is_valid():
            # Set current prices to not current
            RawMaterialPrice.objects.filter(
                raw_material=raw_material,
                supplier=supplier,
                is_current=True
            ).update(is_current=False)
            
            # Create a new price entry
            new_price = form.cleaned_data['price']
            effective_date = form.cleaned_data.get('effective_date', timezone.now())
            
            RawMaterialPrice.objects.create(
                raw_material=raw_material,
                supplier=supplier,
                price=new_price,
                effective_date=effective_date,
                is_current=True,
                created_by=request.user
            )
            
            messages.success(
                request, 
                f"Price for {raw_material.name} from {supplier.name} has been updated to {new_price}."
            )
            next_url = request.GET.get('next', reverse('price_comparison'))
            return redirect(f"{next_url}?material={raw_material_id}")
    else:
        initial = {'effective_date': timezone.now()}
        if current_price_value is not None:
            initial['price'] = current_price_value
        form = RawMaterialPriceForm(initial=initial)
    
    return render(request, 'update_price.html', {
        'form': form,
        'raw_material': raw_material,
        'supplier': supplier,
        'current_price': current_price_obj,  # Use the full object here for template context
        'current_price_value': current_price_value,  # Pass the raw value as well
        'price_history': price_history,
        'next': request.GET.get('next', '')
    })

@login_required
def price_history(request, raw_material_id):
    raw_material = get_object_or_404(RawMaterial, id=raw_material_id)
    prices = RawMaterialPrice.objects.filter(
        raw_material=raw_material
    ).select_related('supplier').order_by('-effective_date')
    
    return render(request, 'price_history.html', {
        'raw_material': raw_material,
        'prices': prices
    })

@login_required
def price_comparison(request, raw_material_id=None):
    raw_materials = RawMaterial.objects.all()
    selected_material = None
    price_data = []
    price_history = [] # This is what your chart needs!
    suppliers_for_chart = []  # Initialize to empty list to prevent UnboundLocalError
    
    # Get material_id from URL parameter or GET parameter
    material_id = raw_material_id or request.GET.get('material')

    # Calculate six months ago from now
    six_months_ago = timezone.now() - timedelta(days=180)  # Approximately 6 months
    
    if material_id:
        try:
            selected_material = RawMaterial.objects.get(id=material_id)
            
            # Get all current prices for this material from all suppliers
            price_data = RawMaterialPrice.objects.filter(
                raw_material=selected_material,
                is_current=True
            ).select_related('supplier').order_by('price')

            price_history = RawMaterialPrice.objects.filter(
                raw_material=selected_material,
                effective_date__gte=six_months_ago # Filter for prices within the last 6 months
            ).select_related('supplier').order_by('effective_date')
            
            # If no prices found with is_current=True, try to get any prices
            if not price_data.exists():
                price_data = RawMaterialPrice.objects.filter(
                    raw_material=selected_material
                ).select_related('supplier').order_by('price')

            # though your current JS infers them from price_history
            suppliers_for_chart = Supplier.objects.filter(
                rawmaterialprice__raw_material=selected_material
            ).distinct().order_by('name')
                
        except RawMaterial.DoesNotExist:
            # If material doesn't exist, just continue with empty price_data
            pass
    
    return render(request, 'price_comparison.html', {
        'raw_materials': raw_materials,
        'selected_material': selected_material,
        'price_data': price_data,
        'price_history': price_history,
        'suppliers_for_chart': suppliers_for_chart,
        'CURRENCY_SYMBOL': settings.CURRENCY_SYMBOL,
    })

@login_required
def price_trends(request, raw_material_id, days=90):
    raw_material = get_object_or_404(RawMaterial, id=raw_material_id)
    date_from = timezone.now() - timedelta(days=days)
    
    # Get all suppliers who have ever supplied this material
    suppliers = Supplier.objects.filter(
        rawmaterialprice__raw_material=raw_material
    ).distinct()
    
    # Prepare data for chart
    chart_data = {
        'labels': [],
        'datasets': []
    }
    
    # Get price history for each supplier
    for supplier in suppliers:
        prices = RawMaterialPrice.objects.filter(
            raw_material=raw_material,
            supplier=supplier,
            effective_date__gte=date_from
        ).order_by('effective_date')
        
        if prices.exists():
            dataset = {
                'label': supplier.name,
                'data': [{'x': price.effective_date.strftime('%Y-%m-%d'), 
                         'y': float(price.price)} 
                        for price in prices],
                'borderColor': f'#{hash(supplier.name) % 0xffffff:06x}',
                'tension': 0.1
            }
            chart_data['datasets'].append(dataset)
    
    return render(request, 'price_trends.html', {
        'raw_material': raw_material,
        'chart_data': json.dumps(chart_data),
        'days': days,
        'suppliers': suppliers
    })

@login_required
def manage_price_alerts(request):
    if request.method == 'POST':
        form = PriceAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            messages.success(request, "Price alert created successfully.")
            return redirect('manage_price_alerts')
    else:
        form = PriceAlertForm()
    
    alerts = PriceAlert.objects.filter(created_by=request.user).select_related('raw_material')
    return render(request, 'manage_alerts.html', {
        'form': form,
        'alerts': alerts
    })

@login_required
def toggle_alert(request, alert_id):
    alert = get_object_or_404(PriceAlert, id=alert_id, created_by=request.user)
    alert.is_active = not alert.is_active
    alert.save()
    return redirect('manage_price_alerts')

@login_required
def delete_alert(request, alert_id):
    alert = get_object_or_404(PriceAlert, id=alert_id, created_by=request.user)
    alert.delete()
    messages.success(request, "Alert deleted successfully.")
    return redirect('manage_price_alerts')


@login_required
def add_raw_material_price(request):
    if request.method == 'POST':
        form = RawMaterialPriceForm(request.POST)
        if form.is_valid():
            raw_material = form.cleaned_data['raw_material']
            supplier = form.cleaned_data['supplier']
            
            # Check if supplier is valid for this raw material
            if not supplier or not raw_material.suppliers.filter(
                pk=supplier.pk
            ).exists():
                form.add_error('supplier', 'Please select a valid supplier for this raw material')
            else:
                # Set any existing prices for this material and supplier as not current
                RawMaterialPrice.objects.filter(
                    raw_material=raw_material,
                    supplier=supplier,
                    is_current=True
                ).update(is_current=False)
                
                # Create the new price
                price = form.save(commit=False)
                price.is_current = True
                price.save()
                
                messages.success(request, f"Price for {raw_material.name} from {supplier.name} has been added.")
                return redirect('price_history', raw_material_id=raw_material.id)
    else:
        form = RawMaterialPriceForm()
    
    return render(request, 'add_raw_material_price.html', {
        'form': form,
        'title': 'Add New Raw Material Price'
    })


@login_required
def all_supplier_prices(request):
    """
    Display all supplier prices for raw materials with filtering and search capabilities
    """
    from django.db.models import Q, Min, Max
    
    # Get filter parameters
    search = request.GET.get('search', '')
    supplier = request.GET.get('supplier', '')
    raw_material = request.GET.get('raw_material', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    price_status = request.GET.get('price_status', '')  # current, historical, all
    
    # Start with all current prices
    prices = RawMaterialPrice.objects.select_related('raw_material', 'supplier').order_by('raw_material__name', 'supplier__name')
    
    # Apply price status filter
    if price_status == 'current':
        prices = prices.filter(is_current=True)
    elif price_status == 'historical':
        prices = prices.filter(is_current=False)
    # If 'all' or empty, show all prices
    
    # Apply search filter
    if search:
        prices = prices.filter(
            Q(raw_material__name__icontains=search) |
            Q(supplier__name__icontains=search) |
            Q(supplier__company_name__icontains=search)
        )
    
    # Apply supplier filter
    if supplier:
        prices = prices.filter(supplier_id=supplier)
    
    # Apply raw material filter
    if raw_material:
        prices = prices.filter(raw_material_id=raw_material)
    
    # Apply price range filters
    if min_price:
        try:
            min_price = float(min_price)
            prices = prices.filter(price__gte=min_price)
        except ValueError:
            pass
    
    if max_price:
        try:
            max_price = float(max_price)
            prices = prices.filter(price__lte=max_price)
        except ValueError:
            pass
    
    # Get statistics
    total_prices = prices.count()
    current_prices = prices.filter(is_current=True).count()
    historical_prices = prices.filter(is_current=False).count()
    
    # Get unique suppliers and raw materials for filter dropdowns
    suppliers = Supplier.objects.filter(rawmaterialprice__in=prices).distinct().order_by('name')
    raw_materials = RawMaterial.objects.filter(rawmaterialprice__in=prices).distinct().order_by('name')
    
    # Get price statistics
    if prices.exists():
        price_stats = prices.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price')
        )
    else:
        price_stats = {'min_price': 0, 'max_price': 0, 'avg_price': 0}
    
    # Group prices by raw material for better organization
    grouped_prices = {}
    for price in prices:
        material_name = price.raw_material.name
        if material_name not in grouped_prices:
            grouped_prices[material_name] = []
        grouped_prices[material_name].append(price)
    
    context = {
        'grouped_prices': grouped_prices,
        'prices': prices,
        'suppliers': suppliers,
        'raw_materials': raw_materials,
        'total_prices': total_prices,
        'current_prices': current_prices,
        'historical_prices': historical_prices,
        'price_stats': price_stats,
        'search': search,
        'selected_supplier': supplier,
        'selected_raw_material': raw_material,
        'selected_min_price': min_price,
        'selected_max_price': max_price,
        'selected_price_status': price_status,
    }
    
    return render(request, 'all_supplier_prices.html', context)

@require_GET
def get_suppliers_for_raw_material(request, raw_material_id):
    try:
        # Get the raw material
        raw_material = RawMaterial.objects.get(pk=raw_material_id)
        
        # Get all suppliers who can supply this raw material
        # Using the many-to-many relationship
        suppliers = raw_material.suppliers.all()
        
        # Get the most recent price for each supplier (if it exists)
        latest_prices = RawMaterialPrice.objects.filter(
            raw_material=raw_material,
            supplier=OuterRef('pk')
        ).order_by('-effective_date')
        
        # Annotate suppliers with their latest price
        suppliers = suppliers.annotate(
            latest_price=Subquery(latest_prices.values('price')[:1])
        ).values('id', 'name', 'latest_price')
        
        return JsonResponse(list(suppliers), safe=False)
        
    except RawMaterial.DoesNotExist:
        return JsonResponse({'error': 'Raw material not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


class RawMaterialDetailView(DetailView):
    model = RawMaterial
    template_name = 'raw_material_detail.html'
    context_object_name = 'raw_material'
    
    def get_queryset(self):
        return RawMaterial.objects.prefetch_related(
            'suppliers',
            'rawmaterialprice_set__supplier',
            'requisitionitem_set__requisition'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw_material = self.object
        
        # Get current price information
        current_prices = raw_material.rawmaterialprice_set.filter(
            is_current=True
        ).select_related('supplier')
        
        # Get price history (last 6 months)
        six_months_ago = timezone.now() - timedelta(days=180)
        price_history = raw_material.rawmaterialprice_set.filter(
            effective_date__gte=six_months_ago
        ).order_by('-effective_date').select_related('supplier')[:30]  # Limit to 30 most recent
        
        # Get recent requisition items for this raw material
        recent_requisitions = raw_material.requisitionitem_set.select_related(
            'requisition', 'requisition__supplier'
        ).order_by('-requisition__created_at')[:10]  # Get 10 most recent
        
        # Get incident write-offs for this raw material
        incident_write_offs = raw_material.write_offs.all().order_by('-date')[:10]  # Get 10 most recent
        
        # Get inventory adjustments for this raw material
        inventory_adjustments = raw_material.rawmaterialinventory_set.all().order_by('-last_updated')[:20]  # Get 20 most recent
        
        context.update({
            'current_prices': current_prices,
            'price_history': price_history,
            'recent_requisitions': recent_requisitions,
            'incident_write_offs': incident_write_offs,
            'inventory_adjustments': inventory_adjustments,
            'suppliers': raw_material.suppliers.all(),
            'CURRENCY_SYMBOL': 'UGX ',  # Add currency symbol for the template
        })
        return context

from django.http import JsonResponse

def get_raw_material_price_list(request):
    raw_material_id = request.GET.get('raw_material_id')
    supplier_id = request.GET.get('supplier_id')
    
    try:
        raw_material = RawMaterial.objects.get(id=raw_material_id)
        supplier = Supplier.objects.get(id=supplier_id)
        
        current_price = RawMaterialPrice.get_current_price(
            raw_material=raw_material,
            supplier=supplier
        )
        
        return JsonResponse({
            'success': True,
            'price': str(current_price) if current_price else '0.00',
            'has_price': current_price is not None
        })
    except (RawMaterial.DoesNotExist, Supplier.DoesNotExist, ValueError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid raw material or supplier'
        }, status=400)

@login_required(login_url='/login/')
def reject_incident_write_off(request, pk):
    try:
        write_off = get_object_or_404(IncidentWriteOff, pk=pk)
        
        if write_off.status == 'pending':
            with transaction.atomic():
                # Update the write-off status
                write_off.status = 'rejected'
                write_off.save()
                
                messages.success(request, f"Write-off for {write_off.raw_material.name} has been rejected.")
        else:
            messages.warning(request, f"This write-off is already {write_off.status}.")
            
    except Exception as e:
        messages.error(request, f"Error rejecting write-off: {str(e)}")
    
    return redirect('incident_write_off_list')

# Store Transfer Views
@login_required
def store_transfer_list(request):
    """List all store transfers with filtering and search"""
    transfers = StoreTransfer.objects.select_related(
        'created_by', 'approved_by'
    ).prefetch_related('items__product__product').all().order_by('-date')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        transfers = transfers.filter(status=status_filter)
    
    # Search by transfer number
    search = request.GET.get('search')
    if search:
        transfers = transfers.filter(
            Q(liv_main_transfer_number__icontains=search) |
            Q(created_by__username__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Calculate statistics
    total_transfers = transfers.count()
    pending_transfers = transfers.filter(status='Pending').count()
    approved_transfers = transfers.filter(status='Approved').count()
    completed_transfers = transfers.filter(status='Completed').count()
    
    # Pagination
    paginator = Paginator(transfers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transfers': page_obj,
        'total_transfers': total_transfers,
        'pending_transfers': pending_transfers,
        'approved_transfers': approved_transfers,
        'completed_transfers': completed_transfers,
        'status_choices': StoreTransfer.STATUS_CHOICES,
    }
    return render(request, 'store_transfer_list.html', context)

@login_required
def store_transfer_create(request):
    """Create a new store transfer"""
    if request.method == 'POST':
        form = StoreTransferForm(request.POST, request.FILES)
        formset = StoreTransferItemFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Save the transfer
                transfer = form.save(commit=False)
                transfer.created_by = request.user
                transfer.save()
                
                # Save the formset
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.transfer = transfer
                    instance.save()
                
                # Delete marked items
                formset.save_existing_objects()
                formset.save_new_objects()
                
                messages.success(request, f'Store transfer {transfer.liv_main_transfer_number} created successfully!')
                return redirect('store_transfer_detail', pk=transfer.pk)
    else:
        form = StoreTransferForm()
        formset = StoreTransferItemFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Store Transfer'
    }
    return render(request, 'store_transfer_form.html', context)

@login_required
def store_transfer_detail(request, pk):
    """View store transfer details"""
    transfer = get_object_or_404(StoreTransfer.objects.select_related(
        'created_by', 'approved_by'
    ).prefetch_related('items__product__product'), pk=pk)
    
    context = {
        'transfer': transfer,
    }
    return render(request, 'store_transfer_detail.html', context)

@login_required
def store_transfer_approve(request, pk):
    """Approve a store transfer"""
    transfer = get_object_or_404(StoreTransfer, pk=pk)
    
    if not transfer.can_be_approved:
        messages.error(request, 'This transfer cannot be approved.')
        return redirect('store_transfer_detail', pk=transfer.pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                transfer.approve(request.user)
                messages.success(request, f'Transfer {transfer.liv_main_transfer_number} approved successfully!')
        except Exception as e:
            messages.error(request, f'Error approving transfer: {str(e)}')
        
        return redirect('store_transfer_detail', pk=transfer.pk)
    
    context = {
        'transfer': transfer,
    }
    return render(request, 'store_transfer_approve.html', context)

@login_required
def store_transfer_complete(request, pk):
    """Mark a store transfer as completed"""
    transfer = get_object_or_404(StoreTransfer, pk=pk)
    
    if not transfer.can_be_completed:
        messages.error(request, 'This transfer cannot be completed.')
        return redirect('store_transfer_detail', pk=transfer.pk)
    
    if request.method == 'POST':
        try:
            transfer.complete()
            messages.success(request, f'Transfer {transfer.liv_main_transfer_number} marked as completed!')
        except Exception as e:
            messages.error(request, f'Error completing transfer: {str(e)}')
        
        return redirect('store_transfer_detail', pk=transfer.pk)
    
    context = {
        'transfer': transfer,
    }
    return render(request, 'store_transfer_complete.html', context)

@login_required
def store_transfer_cancel(request, pk):
    """Cancel a store transfer"""
    transfer = get_object_or_404(StoreTransfer, pk=pk)
    
    if request.method == 'POST':
        try:
            transfer.cancel()
            messages.success(request, f'Transfer {transfer.liv_main_transfer_number} cancelled successfully!')
        except Exception as e:
            messages.error(request, f'Error cancelling transfer: {str(e)}')
        
        return redirect('store_transfer_list')
    
    context = {
        'transfer': transfer,
    }
    return render(request, 'store_transfer_cancel.html', context)

@login_required
def livara_main_store_list(request):
    """List Livara main store inventory"""
    inventory = LivaraMainStore.objects.select_related(
        'product__product'
    ).prefetch_related('adjustments').all().order_by('product__product__product_name')
    
    # Calculate statistics
    total_products = inventory.count()
    total_quantity = sum(item.quantity for item in inventory)
    low_stock_items = inventory.filter(quantity__lt=10)
    
    # Search functionality
    search = request.GET.get('search')
    if search:
        inventory = inventory.filter(
            Q(product__product__product_name__icontains=search) |
            Q(batch_number__icontains=search)
        )
    
    context = {
        'inventory': inventory,
        'total_products': total_products,
        'total_quantity': total_quantity,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'livara_main_store_list.html', context)

@login_required
def livara_main_store_detail(request, pk):
    """View Livara main store item details"""
    item = get_object_or_404(LivaraMainStore.objects.select_related(
        'product__product'
    ).prefetch_related('adjustments'), pk=pk)
    
    # Get recent adjustments
    recent_adjustments = item.adjustments.all()[:10]
    
    context = {
        'item': item,
        'recent_adjustments': recent_adjustments,
    }
    return render(request, 'livara_main_store_detail.html', context)

@login_required
def raw_materials_dashboard(request):
    """Comprehensive raw materials dashboard for production managers"""
    
    # Get all raw materials with their current stock levels
    raw_materials = RawMaterial.objects.all().prefetch_related('suppliers')
    
    # Calculate key metrics
    total_raw_materials = raw_materials.count()
    low_stock_materials = [rm for rm in raw_materials if rm.current_stock <= rm.reorder_point]
    out_of_stock_materials = [rm for rm in raw_materials if rm.current_stock <= 0]
    healthy_stock_materials = [rm for rm in raw_materials if rm.current_stock > rm.reorder_point]
    
    # Calculate total inventory value (approximate)
    total_inventory_value = 0
    for rm in raw_materials:
        # Get average price from suppliers
        avg_price = RawMaterialPrice.objects.filter(
            raw_material=rm, 
            is_current=True
        ).aggregate(Avg('price'))['price__avg'] or 0
        total_inventory_value += float(rm.current_stock) * float(avg_price)
    
    # Recent purchase orders
    recent_purchase_orders = RequisitionItem.objects.select_related(
        'requisition', 'requisition__supplier', 'raw_material'
    ).order_by('-requisition__created_at')[:5]
    
    # Recent inventory adjustments
    recent_adjustments = RawMaterialInventory.objects.select_related(
        'raw_material'
    ).order_by('-last_updated')[:10]
    
    # Price alerts (materials with significant price changes)
    price_alerts = PriceAlert.objects.filter(
        is_active=True
    ).select_related('raw_material')[:5]
    
    # Supplier performance metrics
    suppliers = Supplier.objects.filter(is_active=True)
    supplier_performance = []
    for supplier in suppliers:
        po_count = Requisition.objects.filter(supplier=supplier).count()
        fulfilled_pos = Requisition.objects.filter(
            supplier=supplier, 
            status='delivered'
        ).count()
        fulfillment_rate = (fulfilled_pos / po_count * 100) if po_count > 0 else 0
        
        supplier_performance.append({
            'supplier': supplier,
            'po_count': po_count,
            'fulfillment_rate': fulfillment_rate,
            'reliability_score': supplier.reliability_score
        })
    
    # Sort suppliers by reliability
    supplier_performance.sort(key=lambda x: x['reliability_score'], reverse=True)
    
    # Monthly stock trends (last 6 months)
    
    
    monthly_trends = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        
        # Get total stock for this month
        total_stock = sum([rm.current_stock for rm in raw_materials])
        
        monthly_trends.append({
            'month': month_start.strftime('%b %Y'),
            'total_stock': total_stock
        })
    
    monthly_trends.reverse()
    
    # Critical materials (those with very low stock)
    critical_materials = [rm for rm in low_stock_materials if rm.current_stock < (rm.reorder_point * Decimal('0.5'))]
    
    # Materials by unit measurement
    materials_by_unit = {}
    for rm in raw_materials:
        unit = rm.unit_measurement
        if unit not in materials_by_unit:
            materials_by_unit[unit] = []
        materials_by_unit[unit].append(rm)
    
    context = {
        'total_raw_materials': total_raw_materials,
        'low_stock_materials': low_stock_materials,
        'out_of_stock_materials': out_of_stock_materials,
        'healthy_stock_materials': healthy_stock_materials,
        'critical_materials': critical_materials,
        'total_inventory_value': total_inventory_value,
        'recent_purchase_orders': recent_purchase_orders,
        'recent_adjustments': recent_adjustments,
        'price_alerts': price_alerts,
        'supplier_performance': supplier_performance[:5],  # Top 5 suppliers
        'monthly_trends': monthly_trends,
        'materials_by_unit': materials_by_unit,
        'low_stock_count': len(low_stock_materials),
        'out_of_stock_count': len(out_of_stock_materials),
        'critical_count': len(critical_materials),
    }
    
    return render(request, 'rawmaterials_dashboard.html', context)

@login_required
def manage_raw_material_suppliers(request):
    """Manage the relationship between raw materials and suppliers"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_supplier_to_material':
            raw_material_id = request.POST.get('raw_material_id')
            supplier_id = request.POST.get('supplier_id')
            
            try:
                raw_material = RawMaterial.objects.get(id=raw_material_id)
                supplier = Supplier.objects.get(id=supplier_id)
                
                # Add supplier to raw material
                raw_material.suppliers.add(supplier)
                messages.success(request, f'Supplier "{supplier.name}" added to "{raw_material.name}" successfully!')
                
            except (RawMaterial.DoesNotExist, Supplier.DoesNotExist):
                messages.error(request, 'Invalid raw material or supplier selected.')
                
        elif action == 'remove_supplier_from_material':
            raw_material_id = request.POST.get('raw_material_id')
            supplier_id = request.POST.get('supplier_id')
            
            try:
                raw_material = RawMaterial.objects.get(id=raw_material_id)
                supplier = Supplier.objects.get(id=supplier_id)
                
                # Remove supplier from raw material
                raw_material.suppliers.remove(supplier)
                messages.success(request, f'Supplier "{supplier.name}" removed from "{raw_material.name}" successfully!')
                
            except (RawMaterial.DoesNotExist, Supplier.DoesNotExist):
                messages.error(request, 'Invalid raw material or supplier selected.')
                
        elif action == 'add_material_to_supplier':
            supplier_id = request.POST.get('supplier_id')
            raw_material_id = request.POST.get('raw_material_id')
            
            try:
                supplier = Supplier.objects.get(id=supplier_id)
                raw_material = RawMaterial.objects.get(id=raw_material_id)
                
                # Add raw material to supplier
                supplier.supplied_raw_materials.add(raw_material)
                messages.success(request, f'Raw material "{raw_material.name}" added to supplier "{supplier.name}" successfully!')
                
            except (Supplier.DoesNotExist, RawMaterial.DoesNotExist):
                messages.error(request, 'Invalid supplier or raw material selected.')
                
        elif action == 'remove_material_from_supplier':
            supplier_id = request.POST.get('supplier_id')
            raw_material_id = request.POST.get('raw_material_id')
            
            try:
                supplier = Supplier.objects.get(id=supplier_id)
                raw_material = RawMaterial.objects.get(id=raw_material_id)
                
                # Remove raw material from supplier
                supplier.supplied_raw_materials.remove(raw_material)
                messages.success(request, f'Raw material "{raw_material.name}" removed from supplier "{supplier.name}" successfully!')
                
            except (Supplier.DoesNotExist, RawMaterial.DoesNotExist):
                messages.error(request, 'Invalid supplier or raw material selected.')
    
    # Get all raw materials and suppliers
    raw_materials = RawMaterial.objects.all().prefetch_related('suppliers').order_by('name')
    suppliers = Supplier.objects.filter(is_active=True).prefetch_related('supplied_raw_materials').order_by('name')
    
    # Get materials without suppliers
    materials_without_suppliers = [rm for rm in raw_materials if rm.suppliers.count() == 0]
    
    # Get suppliers without materials
    suppliers_without_materials = [s for s in suppliers if s.supplied_raw_materials.count() == 0]
    
    context = {
        'raw_materials': raw_materials,
        'suppliers': suppliers,
        'materials_without_suppliers': materials_without_suppliers,
        'suppliers_without_materials': suppliers_without_materials,
        'total_materials': raw_materials.count(),
        'total_suppliers': suppliers.count(),
        'materials_with_suppliers': raw_materials.count() - len(materials_without_suppliers),
        'suppliers_with_materials': suppliers.count() - len(suppliers_without_materials),
    }
    
    return render(request, 'production/manage_raw_material_suppliers.html', context)

@require_GET
def get_production_order_quantity(request, production_order_id):
    """API endpoint to get the approved quantity for a production order"""
    try:
        production_order = ProductionOrder.objects.get(id=production_order_id, status='In Progress')
        return JsonResponse({
            'success': True,
            'approved_quantity': production_order.approved_quantity
        })
    except ProductionOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Production order not found or not in progress'
        })

def manufactured_products_report(request):
    period = request.GET.get('period', 'month')  # 'month', 'week', 'day'
    
    if period == 'month':
        truncate_func = TruncMonth
        date_range = timezone.now() - timezone.timedelta(days=365)
    elif period == 'week':
        truncate_func = TruncWeek
        date_range = timezone.now() - timezone.timedelta(weeks=52)  # Last year in weeks
    elif period == 'day':
        truncate_func = TruncDay
        date_range = timezone.now() - timezone.timedelta(days=30)
    elif period == 'year':
        truncate_func = TruncYear
        date_range = timezone.now() - timezone.timedelta(days=365 * 5)
    else:
        truncate_func = TruncMonth
    
    # Query the ManufactureProduct model and group by period and product
    manufactured_products = (
        ManufactureProduct.objects.filter(manufactured_at__gte=date_range)
        .annotate(period=truncate_func('manufactured_at'))
        .values('period', 'product__product_name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('period', 'product__product_name')
    )
    
    context = {
        'manufactured_products': manufactured_products,
        'period': period
    }
    
    return render(request, 'manufactured_products_report.html', context)