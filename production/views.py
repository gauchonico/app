from decimal import Decimal
from django.contrib import messages
from django.forms.formsets import BaseFormSet
from django.forms import ValidationError, inlineformset_factory, modelformset_factory
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .utils import approve_restock_request, cost_per_unit
from .forms import AddSupplierForm, EditSupplierForm, AddRawmaterialForm, CreatePurchaseOrderForm, ManufactureProductForm, ProductionForm, ProductionIngredientForm, ProductionIngredientFormSet, RestockRequestEditForm, RestockRequestForm, StoreAlertForm, StoreForm
from .models import ManufactureProduct, ManufacturedProductInventory, ProductionIngredient, Production, RawMaterial, RestockRequest, Store, StoreAlerts, StoreInventory, Supplier, PurchaseOrder

# Create your views here.

def productionPage(request):
    return render(request, "production_index.html")

@login_required(login_url='/login/')
def supplierList(request):
    suppliers = Supplier.objects.all()
    context ={
        'suppliers': suppliers,
    }
    return render(request, "suppliers_list.html", context)

def addSupplier(request):
    if request.method == 'POST':
        form = AddSupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New Supplier Successfully added")
            return redirect('supplierList')
    else:
        form = AddSupplierForm()
        context = {'form': form}
    return render(request, "add-supplier.html", context)

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

def deleteSupplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    supplier.delete()
    messages.success(request, "Supplier has been deleted successfully")
    return redirect('supplierList')

@login_required(login_url='/login/')
def rawmaterialsList(request):
    rawmaterials = RawMaterial.objects.all()
    context = {
        'rawmaterials': rawmaterials,
    }
    return render(request, "raw-materials-list.html", context)

def addRawmaterial(request):
    if request.method == 'POST':
        form = AddRawmaterialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New Raw Material Successfully added")
            return redirect('rawmaterialsList')
    else:
        form = AddRawmaterialForm()
        context = {'form': form}
    return render(request, "add-rawmaterial.html", context)

def storeManagement(request):
    return render(request, "store-management.html")

@login_required(login_url='/login/')
def storeRequests(request):
    porders = PurchaseOrder.objects.all()
    store_alerts = StoreAlerts.objects.filter(handled=False)
    context = {
        'porders': porders,
        'store_alerts': store_alerts,
    }
    return render(request, "store-requests.html", context)
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



### Purchase Orders #########################################################################
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

def purhcaseOrderDetails (request, purchase_order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
    context = {
        'purchase_order':purchase_order,
    }
    return render (request, "purchase-order-details.html", context)

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

@login_required(login_url='/login/')
def productsList(request):
    products = Production.objects.all()
    context = {
       'products': products,

    }
    return render(request, "products-list.html", context)

def productDetails(request, product_id):
    product = Production.objects.get( pk=product_id)
    ingridients = ProductionIngredient.objects.filter(product=product_id)
    context = {
        'product': product,
        'ingredients': ingridients,
    }
    return render(request, "product-details.html", context)

# class ProductionIngredientFormSet(BaseFormSet):
#     def get_queryset(self):
#         # Always return a queryset with empty forms
#         return super().get_queryset().none()

def create_product(request):
    ingredient_formset =  inlineformset_factory(Production, ProductionIngredient, form=ProductionIngredientForm, extra=5)
    if request.method == 'POST':
        product_form = ProductionForm(request.POST)
        formset = ingredient_formset(request.POST)

        if product_form.is_valid() and formset.is_valid():
            excluded_materials = ["Bottle Tops", "Bottle 250 ml", "Bottle 150 ml","Label for Product"] 
            
            total_ingredient_volume = sum(
                form.cleaned_data.get('quantity_per_unit_product_volume', 0) for form in formset if form.is_valid() and form.cleaned_data['raw_material'].name not in excluded_materials
                )
            product = product_form.save(commit=False)
            if total_ingredient_volume != product.total_volume:
                messages.error(request, "Sum of ingredient quantities must equal product volume<br>Check your Formula Again")
                return redirect('createProduct')
            else:
                product.save()
                formset.instance = product
                formset.save()
                messages.success(request, "You have successfully created A product")
                return redirect('productsList')  # Redirect to product list view after creation
        else:
            # Handle form validation errors (optional: display them in the template)
            pass
    else:
        product_form = ProductionForm()
        formset = ingredient_formset()
    return render(request, 'create-product.html', {'product_form': product_form, 'formset': formset})

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


# def addIngredients(request):
#     # form submissions for new produc

#     production_form = ProductionForm(request.POST)
#     ingredient_formset = ProductionIngredientFormSet(request.POST)

#     if production_form.is_valid() and ingredient_formset.is_valid():
#         # Save the product
#         product = production_form.save()

#         # Save the ingredients associated with the product
#         ingredients = ingredient_formset.save(commit=False)
#         for ingredient in ingredients:
#             ingredient.product = product
#             ingredient.save()

#         return redirect('productsList')
#     else:
#         print(production_form.errors)
#         print(ingredient_formset.errors)
#         # Render the form for creating a new product and its ingredients
#         production_form = ProductionForm()
#         ingredient_formset = ProductionIngredientFormSet()

#     return render(request, 'add-ingredients.html', {'production_form': production_form, 'ingredient_formset': ingredient_formset})

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

def manufacture_product(request, product_id):
    product = Production.objects.get(pk=product_id)
    
    # Handle case where product is not found
    if not product:
        return redirect('productsList')  # Redirect to product list on error

    if request.method == 'POST':
        form = ManufactureProductForm(request.POST)  # Create form instance with POST data
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            batch_number = form.cleaned_data['batch_number']
            labor_cost_per_unit = form.cleaned_data['labor_cost_per_unit']  # Access labor cost
            expiry_date = form.cleaned_data['expiry_date']
            

            # Check for sufficient raw material stock (optional)
            sufficient_stock = True
            for ingredient in product.productioningredients.all():
                quantity_needed = ingredient.quantity_per_unit_product_volume * quantity
                if ingredient.raw_material.current_stock < quantity_needed:
                    sufficient_stock = False
                    messages.error(request, f"Insufficient stock for {ingredient.raw_material.name}. Required: {quantity_needed}, Available: {ingredient.raw_material.current_stock}")
                    break  # Exit loop if any ingredient has insufficient stock

            if sufficient_stock:

                deduct_raw_materials(product, quantity)
                manufacture_product = ManufactureProduct.objects.create(
                    product=product,
                    quantity=quantity,
                    notes=notes,  # Add notes to model creation
                    batch_number=batch_number,
                    labor_cost_per_unit=labor_cost_per_unit,
                    expiry_date = expiry_date,
                )
                #update manufactured product inventory
                manufactured_product_inventory, created = ManufacturedProductInventory.objects.get_or_create(
                    product=product,
                    batch_number=batch_number,
                    defaults={'quantity': quantity,'expiry_date':expiry_date}  # Update or create with quantity
                )
                if not created:
                    manufactured_product_inventory.quantity += quantity
                    manufactured_product_inventory.save()  # Update existing inventory
                
                cost_per = cost_per_unit(product)
                total_cost = (cost_per * quantity) + (labor_cost_per_unit * quantity)
                
                context ={
                    'cost_per': cost_per,
                    'total_cost': total_cost,
                }

                messages.success(request, f"Successfully manufactured {quantity} units of {product.product_name}")
                return redirect('manufacturedProductList')  # Redirect to product list after success
        else:
            # Handle form validation errors
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ManufactureProductForm()  # Create an empty form instance for GET requests

    return render(request, 'manufacture-product.html', {'product': product, 'form': form})


def deduct_raw_materials(product, quantity):
    for ingredient in product.productioningredients.all():
        quantity_needed = ingredient.quantity_per_unit_product_volume * quantity
        ingredient.raw_material.remove_stock(quantity_needed)

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

def manufacturedproduct_detail(request, product_id):
    manufactured_product = get_object_or_404(ManufactureProduct, pk=product_id)
    product = manufactured_product.product
    quantity = manufactured_product.quantity
    ingredient_costs = cost_per_unit(product)
    
    # Calculate total cost considering quantity
    total_ingredient_cost = 0
    for ingredient_cost in cost_per_unit(product):
        total_ingredient_cost += ingredient_cost['cost_per_unit']
    
    total_labour_cost = manufactured_product.labor_cost_per_unit * quantity
    cost_per_product = total_ingredient_cost + total_labour_cost
    total_production_cost = cost_per_product * quantity

    
    # Prepare data for ingredients used
    ingredients_used_data = []
    for ingredient_cost in ingredient_costs:
        ingredient_used_data = {
            'name': ingredient_cost['name'],
            'quantity': ingredient_cost['quantity'],
            'cost_per_unit': ingredient_cost['cost_per_unit'],
        }
        ingredients_used_data.append(ingredient_used_data)
    context = {
        'manufactured_product': manufactured_product,
        'quantity': quantity,
        'product': product,
        'ingredients_used': ingredients_used_data,
        # 'cost_per_product': cost_per_product,
        'cost_per_product': cost_per_product, #cost per bottle
        'total_labour_cost': total_labour_cost,
        'ingredient_costs': ingredient_costs,
        'total_production_cost':total_production_cost,
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

def product_inventory_details(request, inventory_id):

    inventory_item = get_object_or_404(ManufacturedProductInventory, pk=inventory_id)  # Assuming Production model represents product
    product = inventory_item.product



    context = {
        'inventory_item':inventory_item,
        'product':product,
    }
    return render (request, 'product-inventory-details.html', context)

def all_stores(request):
    stores = Store.objects.all()
    context = {
        'stores': stores,
    }
    return render (request, 'all-stores.html', context)

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

def delete_store(request, store_id):
    store = get_object_or_404(Store, pk=store_id)
    if request.method == 'POST':
        store.delete()
        return redirect('allStores')  # Redirect to 'allStores' view after deletion
    context = {'store': store}
    return render(request, 'delete-store.html', context)

def restock_requests (request):
    restock_requests = RestockRequest.objects.all().order_by('-request_date')
    context = {
       'restock_requests': restock_requests,
    }
    
    return render(request, 'restock-requests.html', context)

def create_restock_request(request):
    if request.method == 'POST':
        form = RestockRequestForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new restock request
            return redirect('restockRequests')  # Redirect to list view on success
    else:
        form = RestockRequestForm()  # Create an empty form

    context = {'form': form}
    
    return render(request, 'create-restock-requests.html', context)

def edit_restock_request(request, request_id):
    restock_request = get_object_or_404(RestockRequest, pk=request_id)

    if request.method == 'POST':
        form = RestockRequestEditForm(request.POST, instance=restock_request)
        if form.is_valid():
            form.save()
            return redirect('restockRequests')
        else:
            form = RestockRequestEditForm()

    context ={
        'restock_request':restock_request,
    }
    return render(request, 'edit-restock-requests.html',context)

def approve_restock_requests(request, request_id):
  restock_request = get_object_or_404(RestockRequest, pk=request_id)

  if restock_request.status == "pending":  # Check if request is pending
    with transaction.atomic():
      approve_restock_request(request_id)  # Call your approval function
  
  # Redirect to the restock request list view after approval (or display a message)
  return redirect('restockRequests')

def reject_restock_request(request, request_id):
  restock_request = get_object_or_404(RestockRequest, pk=request_id)

  if restock_request.status == "pending":
    restock_request.status = "rejected"
    restock_request.save()

  # Redirect to the restock request list view after rejection (or display a message)
  return redirect('restockRequests')


def store_inventory_list(request):
    stores = Store.objects.all()  # Get all stores
    # Get all store inventory objects (optional: filter or order)
    store_inventory = StoreInventory.objects.all().select_related('store', 'product')  # Optimize query

    context = {'store_inventory': store_inventory, 'stores':stores }
    return render(request, 'general-stores.html', context)
