from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView
from django.utils import timezone

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
                    
            return redirect('requisition_details', pk=requisition.pk)
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