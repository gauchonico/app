from django.utils import timezone
from django.db import models
from django.apps import apps
from django.db.models import Sum, F
from django.contrib.auth.models import User
import logging

from production.models import Supplier
# Create your models here.

# Get the Staff and Customer models dynamically
logger = logging.getLogger(__name__)

class SalonBranch(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    manager = models.ForeignKey('POSMagicApp.Staff' , on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_branches')

    def __str__(self):
        return self.name
    
class SalonProduct(models.Model):
    COMMISSION_CHOICES = [
        (5, '5%'),
        (10, '10%'),
        (15, '15%'),
    ]

    name = models.CharField(max_length=100)
    supplier = models.ForeignKey(Supplier,on_delete=models.CASCADE, related_name='salon_products')
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.PositiveIntegerField(choices=COMMISSION_CHOICES, default=5)

    def __str__(self):
        return self.name
    
class Service(models.Model):
    COMMISSION_CHOICES = [
        (5, '5%'),
        (10, '10%'),
        (15, '15%'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.PositiveIntegerField(choices=COMMISSION_CHOICES, default=5)

    def __str__(self):
        return self.name
    
class BranchInventory(models.Model):
    branch = models.ForeignKey(SalonBranch, on_delete=models.CASCADE, related_name='inventory')
    product = models.ForeignKey(SalonProduct, on_delete=models.CASCADE, related_name='branch_inventory')
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.product.name} - {self.branch.name} - {self.quantity}'
    
    def save(self, *args, **kwargs):
        if self.pk:  # Check if instance already exists
            old_quantity = BranchInventory.objects.get(pk=self.pk).quantity
            quantity_change = self.quantity - old_quantity
            if quantity_change != 0:
                InventoryUpdateHistory.objects.create(
                    branch=self.branch,
                    product=self.product,
                    quantity_change=quantity_change,
                    updated_by=None  # You can pass the current user if available
                )
        super().save(*args, **kwargs)
    
class InventoryUpdateHistory(models.Model):
    branch = models.ForeignKey(SalonBranch, on_delete=models.CASCADE, related_name='update_histories', blank=True, null=True)
    product = models.ForeignKey(SalonProduct, on_delete=models.CASCADE, related_name='update_histories',blank=True, null=True)
    quantity_change = models.IntegerField()  # Positive for additions, negative for deductions
    updated_at = models.DateTimeField(default=timezone.now)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f'{self.product.name} - {self.quantity_change} at {self.updated_at}'
    
class Sale(models.Model):
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE, related_name='sales')
    branch = models.ForeignKey(SalonBranch, on_delete=models.CASCADE, related_name='sales')
    sale_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    attended_by = models.ForeignKey('POSMagicApp.Staff', on_delete=models.SET_NULL, null=True, related_name='sales')

    def __str__(self):
        return f'Sale to {self.customer} on {self.sale_date}'

    def calculate_total_amount(self):
        services_cost = self.services.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        products_cost = self.products.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        self.total_amount = services_cost + products_cost
        self.save()

class SaleProduct(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey(SalonProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    branch_inventory = models.ForeignKey(BranchInventory, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        # Deduct the product quantity from the branch's inventory
        if self.branch_inventory and self.quantity <= self.branch_inventory.quantity:
            self.branch_inventory.quantity -= self.quantity
            self.branch_inventory.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product.name} - {self.quantity}'

class SaleService(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    staff = models.ForeignKey('POSMagicApp.Staff', on_delete=models.CASCADE)  # Staff member performing the service
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.service.name} by {self.staff} - {self.quantity}'
    
############General requisition############
class GeneralRequisition(models.Model):
    REQUISITION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delivered', 'Delivered'),
    ]
    
    requisition_no = models.CharField(max_length=100, unique=True)
    branch = models.ForeignKey(SalonBranch, on_delete=models.CASCADE, related_name='general_requisitions')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='salon_requisitions')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=REQUISITION_STATUS_CHOICES, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.requisition_no:
            max_number = GeneralRequisition.objects.aggregate(models.Max('id'))['id__max']
            self.requisition_no = f"GBR-{(max_number or 0) + 1:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.requisition_no} - {self.branch.name}'
    
    def mark_as_delivered(self):
        self.status = 'delivered'
        self.delivery_date = timezone.now()
        self.save()
        
        logger.info(f'Requisition {self.requisition_no} marked as delivered.')
        
        # Update branch inventory
        for item in self.items.all():
            branch_inventory, created = BranchInventory.objects.get_or_create(
                branch=self.branch, 
                product=item.product,
                defaults={'quantity': 0}
            )
            quantity_change = item.quantity
            branch_inventory.quantity += quantity_change
            branch_inventory.save()
            
            # Log the update
            InventoryUpdateHistory.objects.create(
                branch=self.branch,
                product=item.product,
                quantity_change=quantity_change,
                updated_by=None  # You can pass the current user if available
            )
            
            logger.info(f'Updated inventory for {item.product.name}: {branch_inventory.quantity} units')
    
class GeneralRequisitionItem(models.Model):
    requisition = models.ForeignKey(GeneralRequisition, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(SalonProduct, on_delete=models.CASCADE, related_name='salon_requisition_items')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product.name} - {self.quantity}'
    
########## Internal Requisition ###########
    
class InternalRequisition(models.Model):
    REQUISITION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delivered', 'Delivered'),
    ]
    
    requisition_no = models.CharField(max_length=100, unique=True)
    branch = models.ForeignKey(SalonBranch, on_delete=models.CASCADE, related_name='internal_requisitions')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=REQUISITION_STATUS_CHOICES, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.requisition_no:
            max_number = InternalRequisition.objects.aggregate(models.Max('id'))['id__max']
            self.requisition_no = f"IBR-{(max_number or 0) + 1:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.requisition_no} - {self.branch.name}'
    
class InternalRequisitionItem(models.Model):
    requisition = models.ForeignKey(InternalRequisition, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(SalonProduct, on_delete=models.CASCADE, related_name='internal_requisition_items')
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.product.name} - {self.quantity}'