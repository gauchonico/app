from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView
from django.utils import timezone
from django.contrib import messages
from django.db import transaction

from salon.forms import *
from salon.models import *
# Create your views here.

def salon(request):
    no_of_salons = SalonBranch.objects.count()
    no_of_services = Service.objects.count()
    no_of_products = SalonProduct.objects.count()
    
    context = {
        'no_of_salons': no_of_salons,
        'no_of_services': no_of_services,
        'no_of_products': no_of_products,
    }
    return render(request, 'salon.html', context)


class SalonProductCreateView(CreateView):
    model = SalonProduct
    form_class = SalonProductForm
    template_name = 'add_salon_product.html'
    success_url = reverse_lazy('salonproduct_list')
    
class SalonProductUpdateView(UpdateView):
    model = SalonProduct
    form_class = SalonProductForm
    template_name = 'salonproduct_form.html'
    success_url = reverse_lazy('salonproduct_list')

class SalonProductDeleteView(DeleteView):
    model = SalonProduct
    template_name = 'salonproduct_confirm_delete.html'
    success_url = reverse_lazy('salonproduct_list')

class ServiceCreateView(CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_form.html'
    success_url = reverse_lazy('salon:service_list')

class ServiceUpdateView(UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_form.html'
    success_url = reverse_lazy('salon:service_list')

class ServiceDeleteView(DeleteView):
    model = Service
    template_name = 'service_confirm_delete.html'
    success_url = reverse_lazy('salon:service_list')
    
class SalonProductListView(ListView):
    model = SalonProduct
    template_name = 'salonproduct_list.html'

class ServiceListView(ListView):
    model = Service
    template_name = 'service_list.html'


def create_general_requisition(request):
    if request.method == 'POST':
        requisition_form = GeneralRequisitionForm(request.POST)
        formset = GeneralRequisitionItemFormSet(request.POST)
        
        if requisition_form.is_valid() and formset.is_valid():
            requisition = requisition_form.save(commit=False)
            requisition.requested_by = request.user
            requisition.save()
            
            for form in formset:
                if form.cleaned_data.get('product'):
                    item = form.save(commit=False)
                    item.requisition = requisition
                    item.save()
                    
            return redirect('general_requisition_list')
    else:
        requisition_form = GeneralRequisitionForm()
        formset = GeneralRequisitionItemFormSet()
    
    return render(request, 'create_general_requisition.html', {
        'requisition_form': requisition_form,
        'formset': formset,
    })
    
def general_requisition_list(request):
    requisitions = GeneralRequisition.objects.all()
    context = {
        'requisitions': requisitions,
    }
    return render(request, 'general_requisitions_list.html', context)
    
def requisition_details(request, pk):
    requisition = get_object_or_404(GeneralRequisition, pk=pk)
    items = GeneralRequisitionItem.objects.filter(requisition=requisition)
    context = {
        'requisition': requisition,
        'items': items,
    }
    
    return render(request, 'general_requisition_details.html', context)

def mark_requisition_as_delivered(request, pk):
    requisition = get_object_or_404(GeneralRequisition, pk=pk)
    # # Check if the user has permission to perform this action
    # if not request.user.has_perm('app_name.can_mark_as_delivered'):  # Adjust permission as needed
    #     return HttpResponseForbidden("You don't have permission to perform this action.")
    
    if request.method == 'POST':
        # Mark the requisition as delivered
        requisition.status = 'delivered'
        requisition.delivery_date = timezone.now()
        requisition.save()
        
        # Update branch inventory
        for item in requisition.items.all():
            branch_inventory, created = BranchInventory.objects.get_or_create(
                branch=requisition.branch, 
                product=item.product,
                defaults={'quantity': 0}
            )
            branch_inventory.quantity += item.quantity
            branch_inventory.save()

        return redirect('requisition_details', pk=requisition.pk)  # Redirect to the requisition detail page

    return render(request, 'mark_as_delivered.html', {'requisition': requisition})

#all Salon inventories
def salon_inventory_list(request):
    salons = SalonBranch.objects.prefetch_related('inventory').all()
    return render(request, 'salon_inventory_list.html', {'salons': salons})

def create_salon_restock_requests(request):
    # Get the salon branch associated with the logged-in user
    try:
        user_salon_branch = SalonBranch.objects.get(manager=request.user)
    except SalonBranch.DoesNotExist:
        user_salon_branch = None  # Handle the case where no branch is found
        
    if request.method == 'POST':
        form = SalonRestockRequestForm(request.POST)
        item_formset = SalonRestockRequestItemFormset(request.POST)

        if form.is_valid() and item_formset.is_valid():
            restock_request = form.save(commit=False)
            restock_request.requested_by = request.user
            # Set the salon branch based on the user's association
            if user_salon_branch:  # Ensure that the branch exists
                restock_request.salon = user_salon_branch
            restock_request.save()

            # Save items
            item_formset.instance = restock_request
            item_formset.save()

            return redirect('view_salon_restock_requests')
    else:
        form = SalonRestockRequestForm()
        item_formset = SalonRestockRequestItemFormset()

    return render(request, 'create_salon_restock_request.html', {
        'form': form,
        'item_formset': item_formset,
    })

def deliver_salon_restock_request(request, restock_request_id):
    try:
        restock_request = SalonRestockRequest.objects.get(pk=restock_request_id, status='pending')
    except SalonRestockRequest.DoesNotExist:
        raise Http404("Restock request not found or already processed.")
    user_salon_branch = SalonBranch.objects.get(manager=request.user)
    
    if request.method == 'POST':
        # Check if Livara has sufficient stock for all products
        for item in restock_request.items.all():
            livara_inventory = LivaraMainStore.objects.get(product=item.product.product)
            if livara_inventory.quantity < item.quantity:
                raise Exception(f"Insufficient stock in Livara for {item.product.product_name}")

        # Update branch inventory and deduct from Livara inventory
        with transaction.atomic():
            for item in restock_request.items.all():
                livara_inventory = LivaraMainStore.objects.get(product=item.product.product)
                branch_inventory, created = BranchInventory.objects.get_or_create(salon=user_salon_branch, product=item.product)
                branch_inventory.quantity += item.quantity
                livara_inventory.quantity -= item.quantity
                branch_inventory.save()
                livara_inventory.save()

        restock_request.status = 'delivered'
        restock_request.save()
        return redirect('view_salon_restock_requests')  # Redirect to success page
    else:
        # Display a confirmation page before marking as delivered
        context = {'restock_request': restock_request}
        return render(request, 'mark_delivered_confirmation.html', context)
    
def view_salon_restock_requests(request):
    restock_requests = SalonRestockRequest.objects.all().prefetch_related('items__product')
    user_is_salon_manager = request.user.groups.filter(name='Saloon Managers').exists()
    context ={
        'user_is_salon_manager': user_is_salon_manager,
        'restock_requests': restock_requests,
    }
    return render(request, 'salon_restock_requests.html', context)

def restock_request_details(request, salon_restock_req_no):
    restock_request = get_object_or_404(SalonRestockRequest, salon_restock_req_no=salon_restock_req_no)
    user_is_salon_manager = request.user.groups.filter(name='Saloon Managers').exists()
    items = restock_request.items.all()  # Get all items related to this restock request
    
    context = {
        'restock_request': restock_request,
        'items': items,
        'user_is_salon_manager': user_is_salon_manager,
    }
    return render(request, 'restock_request_detail.html', context)

def branch_inventory(request):
    # Replace this with your custom logic to determine the user's salon branch
    user_salon_branch = SalonBranch.objects.get(  # Adjust the filter based on your criteria
        manager=request.user
    )

    branch_inventory = BranchInventory.objects.filter(branch=user_salon_branch)

    return render(request, 'branch_inventory.html', {'branch_inventory': branch_inventory})