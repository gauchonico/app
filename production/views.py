from decimal import Decimal
from django.contrib import messages
from django.forms.formsets import BaseFormSet
from django.forms import ValidationError, inlineformset_factory, modelformset_factory
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db import transaction

from POSMagicApp.decorators import allowed_users
from .utils import approve_restock_request, cost_per_unit
from .forms import AddSupplierForm, ApprovePurchaseForm, EditSupplierForm, AddRawmaterialForm, CreatePurchaseOrderForm, ManufactureProductForm, ProductionForm, ProductionIngredientForm, ProductionIngredientFormSet, ProductionOrderForm, RestockApproveForm, RestockRequestEditForm, RestockRequestForm, StoreAlertForm, StoreForm
from .models import ManufactureProduct, ManufacturedProductInventory, Notification, ProductionIngredient, Production, ProductionOrder, RawMaterial, RestockRequest, Store, StoreAlerts, StoreInventory, Supplier, PurchaseOrder

# Create your views here.
@login_required(login_url='/login/')
def productionPage(request):
    return render(request, "production_index.html")


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
        form = AddSupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New Supplier Successfully added")
            return redirect('supplierList')
    else:
        form = AddSupplierForm()
        context = {'form': form}
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

@login_required(login_url='/login/')
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



### Purchase Orders #########################################################################
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

# class ProductionIngredientFormSet(BaseFormSet):
#     def get_queryset(self):
#         # Always return a queryset with empty forms
#         return super().get_queryset().none()


@login_required(login_url='/login/')
def create_product(request):
    ingredient_formset =  inlineformset_factory(Production, ProductionIngredient, form=ProductionIngredientForm, extra=7)
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
                # total_cost = (cost_per * quantity) + (labor_cost_per_unit * quantity)
                total_cost = sum(cost_data['cost_per_unit'] for cost_data in cost_per) + (labor_cost_per_unit * quantity)
                
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

@login_required(login_url='/login/')
def product_inventory_details(request, inventory_id):

    inventory_item = get_object_or_404(ManufacturedProductInventory, pk=inventory_id)  # Assuming Production model represents product
    product = inventory_item.product



    context = {
        'inventory_item':inventory_item,
        'product':product,
    }
    return render (request, 'product-inventory-details.html', context)

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
def restock_requests (request):
    restock_requests = RestockRequest.objects.all().order_by('-request_date')

    user_groups = request.user.groups.all()  # This retrieves all groups the user belongs to
    user_group = user_groups.first()

    context = {
       'restock_requests': restock_requests,
       'user_group': user_group,
    }
    
    return render(request, 'restock-requests.html', context)


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
def edit_restock_request(request, request_id):
    restock_request = get_object_or_404(RestockRequest, pk=request_id)
    form = RestockRequestEditForm(instance=restock_request)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('restockRequests')
        else:
            form = RestockRequestEditForm(instance=restock_request)  # Create an empty form for GET requests
            # Form is already defined, no need to re-initialize here

    context = {
        'form': form,
    }
    return render(request, 'edit-restock-requests.html', context)

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
@allowed_users(allowed_roles=['Finance','Storemanager'])
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
    production_orders = ProductionOrder.objects.filter(status__in=['Approved', 'In Progress', 'Completed']).order_by('-created_at')  # Order by creation date descending
    context = {'production_orders': production_orders}
    return render(request, 'production_production_orders.html', context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles='Finance')
def approve_production_order(request, pk):
    if not request.user.groups.filter(name='Finance').exists():
        messages.error(request, "You don't have permission to create production orders.")
        return redirect('store_inventory_list')  # Redirect to homepage on permission error
    
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
                    return redirect('financeProduction')
            except ValueError:
                messages.error(request, "Invalid approved quantity. Please enter a number.")
    context = {'production_order': production_order}
    return render(request, 'approve_production_order.html', context)

@login_required(login_url='/login/')
@allowed_users(allowed_roles='Finance')
def start_production_progress(request, pk):
    if not request.user.groups.filter(name='Finance').exists():
        messages.error(request, "You don't have permission to create production orders.")
        return redirect('store_inventory_list')  # Redirect to homepage on permission error
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

def finance_approve_restock_requests(request, pk):
    restock_request = RestockRequest.objects.get(pk=pk)  # Order by creation date descending
    form = RestockApproveForm(request.POST, instance=restock_request)
    if request.method == 'POST':  
        if form.is_valid():
            form.save()
            messages.success(request, "Restock Request Details have been updated successfully")
            return redirect ('financeRestockRequests')
        else:
            form = RestockApproveForm(instance=restock_request)

    context = {'form': form}
    return render(request, 'approve_restock_order.html', context)

