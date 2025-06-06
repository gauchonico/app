from datetime import datetime, timedelta, date
from decimal import Decimal
import random
from time import timezone
import traceback
from venv import logger
from django.db import models
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth import get_user_model
from django.forms import DecimalField

# from POSMagicApp.models import Customer 
from django.db.models import Sum, F
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError




# Create your models here.
User = get_user_model()

class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    company_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=20, blank=True)  # Consider phone number format

    def __str__(self):
        return self.name
    
class UnitOfMeasurement(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class RawMaterial(models.Model):
    name = models.CharField(max_length=255)
    suppliers = models.ManyToManyField(Supplier, related_name='supplied_raw_materials')
    quantity = models.DecimalField(max_digits=15, decimal_places=5, default=0.00000)
    reorder_point = models.PositiveIntegerField(default=0)
    unit_measurement = models.CharField(max_length=10, blank=True, default='units')
    

    def __str__(self):
        return f"{self.name} in {self.unit_measurement}"
    
    def add_stock(self, quantity):
        with transaction.atomic():
            RawMaterialInventory.objects.create(raw_material=self, adjustment=quantity)
            self.update_quantity()

    def remove_stock(self, quantity):
        with transaction.atomic():
            if self.current_stock < quantity:
                raise ValueError("Not enough stock")
            RawMaterialInventory.objects.create(raw_material=self, adjustment=-quantity)
            self.update_quantity()
    
    @property
    def current_stock(self):
        return self.rawmaterialinventory_set.all().aggregate(models.Sum('adjustment'))['adjustment__sum'] or Decimal(0)
    
    def update_quantity(self):
        self.quantity = self.current_stock
        self.save()

    def set_quantity(self, new_quantity):
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative.")

        new_quantity = Decimal(str(new_quantity))
        current_stock = Decimal(str(self.current_stock))

        adjustment = new_quantity - current_stock
        
        print("Raw Material:", self)
        print("Adjustment:", adjustment)

        with transaction.atomic():
            print("Adjustment:", adjustment)
            try:
                RawMaterialInventory.objects.create(raw_material=self, adjustment=adjustment)
                self.update_quantity()
            except Exception as e:
                logger.error("Error saving RawMaterialInventory: %s", str(e))
                logger.error("Adjustment:", adjustment)
                logger.error("Traceback:", traceback.format_exc())
                raise e  # Re-raise the exception for further handling
            
class IncidentWriteOff(models.Model):
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='write_offs')
    quantity = models.DecimalField(max_digits=5, decimal_places=3, default=0)
    reason = models.TextField()
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending', choices=[('pending', 'Pending'), ('approved', 'Approved')])
    written_off_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = "Incident Write-Off"
        verbose_name_plural = "Incident Write-Offs"

    def __str__(self):
        return f"Write-off of {self.quantity} {self.raw_material} on {self.date} - {self.reason[:20]}"
    

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    fullfilled_qty = models.PositiveIntegerField(default=0, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=0)  # Consider currency
    total_cost = models.DecimalField(max_digits=10, decimal_places=0, blank=True)  # Auto-calculate
    created_at = models.DateTimeField(auto_now_add=True)
    order_number = models.CharField(max_length=10, unique=True)
    status = models.CharField(max_length=255, choices=[  # Add choices for different statuses
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("fulfilled", "Fulfilled"),
        ("rejected", "Rejected"),
        # Add more choices as needed (e.g., "rejected", "canceled")
    ], default="pending")

    def __str__(self):
        return f"Purchase Order for {self.quantity} units of {self.raw_material.name} from {self.supplier.name} (created: {self.created_at.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_price
        super().save(*args, **kwargs)  # Call the original save() method

        if self.status == 'fulfilled':
            self.raw_material.add_stock(self.fullfilled_qty)  # Add stock to the raw material

    @property
    def outstanding(self):
        return self.quantity - self.fullfilled_qty

    
class RawMaterialInventory(models.Model):
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.DO_NOTHING)
    adjustment = models.DecimalField(max_digits=15, decimal_places=5, default=0.00000)
    last_updated = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Call update_stock method after creating or updating the RawMaterialInventory object
        super().save(*args, **kwargs)

class StoreAlerts (models.Model):
    message = models.TextField(blank=True, max_length=100)
    alert_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)
    handled_at = models.DateTimeField(blank=True, null=True)

### next week #####################################

# class ProductionManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().values_list('product_name', flat=True)

class Production(models.Model):
    product_name = models.CharField(max_length=255)
    total_volume = models.DecimalField(max_digits=4, decimal_places=0)  # Adjust precision as needed
    unit_of_measure = models.ForeignKey(UnitOfMeasurement, null=True, blank=True, on_delete=models.SET_NULL)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carrefour_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # New field for price
    # objects = ProductionManager()

    def __str__(self):
        return self.product_name

class ProductionIngredient(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE,related_name="productioningredients")
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    # Instead of percentage, store quantity per unit product volume
    quantity_per_unit_product_volume = models.DecimalField(max_digits=10, decimal_places=5)


    def __str__(self) -> str:
        return f"{self.raw_material} for {self.product} needed for {self.quantity_per_unit_product_volume}"

#Products Pricing Groups
class PriceGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)  # e.g., "Black Friday", "Wholesale"
    description = models.CharField(max_length=255, unique=True, default="No Description")
    is_active = models.BooleanField(default=False)  # Only one group can be active at a time
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # def save(self, *args, **kwargs):
    #     # Ensure only one price group is active at a time
    #     if self.is_active:
    #         PriceGroup.objects.filter(is_active=True).update(is_active=False)
    #     super().save(*args, **kwargs)
        
class ProductPrice(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE, related_name="prices")
    price_group = models.ForeignKey(PriceGroup, on_delete=models.CASCADE, related_name="product_prices")
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price for this product in the group

    class Meta:
        unique_together = ('product', 'price_group')  # Prevent duplicate entries for the same product in the same group

    def __str__(self):
        return f"{self.product.product_name} - {self.price_group.name}: {self.price}"

    
class ProductionBatch(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  # Number of bottles produced
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

class ProductionOrder(models.Model):
    prod_order_no = models.CharField(max_length=50, unique=True, blank=True)
    product = models.ForeignKey(
        'Production', on_delete=models.CASCADE, related_name='production_orders'
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=[
        ('Created', 'Created'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ], default='Created')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    target_completion_date = models.DateField(blank=True, null=True)
    approved_quantity = models.PositiveIntegerField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)  # Added field for rejection reason
    rejected_at = models.DateTimeField(null=True, blank=True)  # Added field for rejection timestamp
    rejected_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='rejected_production_orders'
    )

    def __str__(self):
        return f"Production Order: {self.product.product_name} - {self.quantity} units"
    
    def save(self, *args, **kwargs):
        if not self.prod_order_no:
            self.prod_order_no = self.generate_prod_order_no()
        
        super().save(*args, **kwargs)
    
    def generate_prod_order_no(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        #generate random number
        random_number = random.randint(0000,9999)
        
        # Construct the requisition number
        prod_order_no = f"prod-request-{month}{year}-{random_number}"
        
        # Ensure the generated number is unique
        while ProductionOrder.objects.filter(prod_order_no=prod_order_no).exists():
            random_number = random.randint(1000, 9999)
            prod_order_no = f"prod-req-{month}{year}-{random_number}"
        
        return prod_order_no
    
    def create_approval_notification(self):
        notification = Notification.objects.create(
            recipient=self.store_manager,
            verb='Your production order has been approved!',
            description=f"Order #{self.pk} for '{self.product.product_name}' has been approved and is ready for production.",
        )
        return notification
    
    

    class Meta:
        ordering = ['-created_at'] 
class ManufactureProduct(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  # Number of units manufactured
    manufactured_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    batch_number = models.CharField(max_length=8, unique=True, blank=True)
    # labor_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    expiry_date = models.DateField(null=True,blank=True)
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, null=True, blank=True, related_name='manufactured_products')

    def __str__(self):
        return f"{self.quantity} units of {self.product.product_name} manufactured on {self.manufactured_at.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        # Generate batch number if not set
        if not self.batch_number:
            self.batch_number = self.generate_batch_number()

        # Save the ManufactureProduct instance
        super().save(*args, **kwargs)

        # Record raw material usage based on production ingredients
        self.record_raw_material_usage()

    
    def generate_batch_number(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        exp_year= self.expiry_date.strftime('%y')
        product_prefix = self.product.product_name[:3].upper() #make first letters capital
        #generate random number
        random_number = random.randint(0000,9999)
        
        # Construct the requisition number
        batch_number = f"{product_prefix}-{month}{year}-{exp_year}-{random_number}"
        
        # Ensure the generated number is unique
        while ManufactureProduct.objects.filter(batch_number=batch_number).exists():
            random_number = random.randint(1000, 9999)
            batch_number = f"{product_prefix}-{month}{year}-{exp_year}-{random_number}"
        
        return batch_number
    
        
    
    def record_raw_material_usage(self):
        """Calculate the required raw materials based on product ingredients and record them."""
        for ingredient in self.product.productioningredients.all():
            # Calculate total quantity needed for this batch of products
            total_quantity_needed = ingredient.quantity_per_unit_product_volume * Decimal(self.quantity)

            # Record the raw material usage for this manufactured product
            ManufacturedProductIngredient.objects.create(
                manufactured_product=self,
                raw_material=ingredient.raw_material,
                quantity_used=total_quantity_needed
            )
class ManufacturedProductIngredient(models.Model):
    manufactured_product = models.ForeignKey(ManufactureProduct, on_delete=models.CASCADE, related_name='used_ingredients')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity_used} of {self.raw_material.name} for {self.manufactured_product}"
    
class ManufacturedProductInventory(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    batch_number = models.CharField(max_length=50,blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    expiry_date = models.DateField(blank=True, null=True)
    

    def __str__(self):
        return f"{self.product.product_name} Btch No: {self.batch_number} Qty: ({self.quantity})"

class WriteOff(models.Model):
    manufactured_product_inventory = models.ForeignKey(
        'ManufacturedProductInventory', on_delete=models.CASCADE, related_name='write_offs'
    )
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    date = models.DateField(auto_now_add=True)
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"WriteOff: {self.manufactured_product_inventory.product.product_name} - {self.quantity} units"

################### stores models   
class Store(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_stores', blank=True, null=True)

    def __str__(self):
        return self.name

class ServiceName(models.Model):
    name = models.CharField(max_length=255)  # Service name (e.g., Hairdressing)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price for the service (e.g., 20000)
    
    def __str__(self):
        return self.name


class StoreService(models.Model):
    store = models.ForeignKey('Store', on_delete=models.CASCADE, related_name='store_services')
    service = models.ForeignKey(ServiceName, on_delete=models.CASCADE, related_name='store_services')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 0.10 for 10% commission

    class Meta:
        unique_together = ('store', 'service')  # Ensure that each service is unique per store
        
    def verify_commission_rate(self):
        """Verify that commission rate is properly set"""
        if self.commission_rate <= 0 or self.commission_rate >= 1:
            print(f"WARNING: Unusual commission rate for {self}: {self.commission_rate}")
        return self.commission_rate

    def __str__(self):
        return f"{self.store.name} offers {self.service.name} with {self.commission_rate*100}% commission"
    
    
class ServiceSaleInvoice(models.Model):
    sale = models.OneToOneField('ServiceSale', on_delete=models.CASCADE, related_name='invoice')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    PAID_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
    ]
    paid_status = models.CharField(max_length=20, choices=PAID_STATUS_CHOICES, default='unpaid')

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobilemoney', 'Mobile Money'),
        ('both', 'Both'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)

    remarks = models.TextField(blank=True, null=True)  # Optional remarks
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice for {self.sale} - {self.total_amount}"

    def mark_paid(self):
        """ Mark the invoice as fully paid """
        self.paid_status = 'paid'
        self.save()

class StockTransfer(models.Model):
    from_inventory = models.ForeignKey(ManufacturedProductInventory, on_delete=models.CASCADE, related_name='from_transfers')
    to_store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    transfer_date = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)  # Optional: User who processed the transfer

    def __str__(self):
        return f"Transferred {self.quantity} units of {self.from_inventory.product.product_name} to {self.to_store} on {self.transfer_date.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        
#Staff Commissions
class MonthlyStaffCommission(models.Model):
    """Monthly compilation of staff commissions"""
    staff = models.ForeignKey('POSMagicApp.Staff', on_delete=models.CASCADE, related_name='monthly_commissions')
    month = models.DateField()  # Store first day of the month
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid = models.BooleanField(default=False)
    paid_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        unique_together = ['staff', 'month']
        ordering = ['-month']

    def __str__(self):
        return f"{self.staff.name} - {self.month.strftime('%B %Y')} - {self.total_amount}"
    
    @property
    def month_name(self):
        return self.month.strftime('%B %Y')
    
    def mark_as_paid(self, reference=None):
        with transaction.atomic():
            self.paid = True
            self.paid_date = timezone.now()
            self.payment_reference = reference
            self.save()
            
            # Mark all individual commissions as paid
            StaffCommission.objects.filter(
                staff=self.staff,
                created_at__year=self.month.year,
                created_at__month=self.month.month,
                paid=False
            ).update(paid=True, paid_date=timezone.now())

class StaffCommission(models.Model):
    staff = models.ForeignKey('POSMagicApp.Staff', on_delete=models.CASCADE, related_name='commissions')
    service_sale_item = models.ForeignKey('ServiceSaleItem', on_delete=models.CASCADE, related_name='staff_commissions')
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    paid_date = models.DateTimeField(null=True, blank=True)
    monthly_commission = models.ForeignKey(MonthlyStaffCommission, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def compile_monthly_commissions(cls, year=None, month=None):
        """Compile monthly commissions for all staff"""
        if year is None or month is None:
            # Use previous month by default
            today = timezone.now()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

        # Get first day of the month
        month_start = timezone.datetime(year, month, 1)
        
        # Get all staff with commissions for the month
        staff_commissions = cls.objects.filter(
            created_at__year=year,
            created_at__month=month,
            paid=False
        ).values('staff').annotate(
            total_commission=Sum('commission_amount')
        )

        # Create monthly commission records
        for staff_comm in staff_commissions:
            monthly_commission, created = MonthlyStaffCommission.objects.get_or_create(
                staff_id=staff_comm['staff'],
                month=month_start,
                defaults={'total_amount': staff_comm['total_commission']}
            )
            if not created:
                monthly_commission.total_amount = staff_comm['total_commission']
                monthly_commission.save()

            # Link individual commissions to monthly compilation
            cls.objects.filter(
                staff_id=staff_comm['staff'],
                created_at__year=year,
                created_at__month=month,
                paid=False
            ).update(monthly_commission=monthly_commission)


##### Main Livara Store Transfer      
class LivaraMainStore(models.Model):
    product = models.ForeignKey(ManufacturedProductInventory, on_delete=models.CASCADE,related_name='livara_main_store')
    quantity = models.PositiveIntegerField()
    batch_number = models.CharField(max_length=50, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    expiry_date = models.DateField(null=True, blank=True)
    previous_quantity = models.PositiveIntegerField(default=0)
    adjustment_date = models.DateTimeField(null=True, blank=True)
    adjustment_reason = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__ (self):
        return f"{self.product.product.product_name} (Batch: {self.batch_number})"

#Adjustment mobel to track mainstore changes
class LivaraInventoryAdjustment(models.Model):
    store_inventory = models.ForeignKey(LivaraMainStore, on_delete=models.CASCADE, related_name='adjustments')
    adjusted_quantity = models.IntegerField()
    adjustment_date = models.DateTimeField(auto_now_add=True)
    adjustment_reason = models.CharField(max_length=255)
    adjusted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Optional: Track who made the adjustment
    

    def __str__(self):
        return f"Adjustment of {self.adjusted_quantity} units for {self.store_inventory.product} on {self.adjustment_date}"
    
class StoreTransfer(models.Model):
    liv_main_transfer_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    delivery_document = models.FileField(upload_to='uploads/products/', null=True, blank=True)
    notes = models.CharField(max_length=40, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'),('Approved','Approved'), ('Completed', 'Completed')], default='Pending')
    
    def __str__(self):
        return f"Transfer {self.liv_main_transfer_number} by {self.created_by}"
    
    def save(self, *args, **kwargs):
        if not self.liv_main_transfer_number:
            self.liv_main_transfer_number = self.generate_liv_main_transfer_number()
        super().save(*args, **kwargs)

    def generate_liv_main_transfer_number(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        
        # Generate random number
        random_number = random.randint(1000, 9999)
        
        # Construct the LPO number
        liv_main_transfer_number = f"LIV-MAIN-TRNS-{month}{year}-{random_number}"
        
        # Ensure the generated number is unique
        while StoreTransfer.objects.filter(liv_main_transfer_number=liv_main_transfer_number).exists():
            random_number = random.randint(1000, 9999)
            liv_main_transfer_number = f"pod-po{month}{year}-{random_number}"
        
        return liv_main_transfer_number

class StoreTransferItem(models.Model):
    transfer = models.ForeignKey(StoreTransfer, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(ManufacturedProductInventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    delivered_quantity = models.PositiveIntegerField(null=True, blank=True)  # New field for delivered quantity


#Livara Mainstore Write off
class StoreWriteOff(models.Model):
    REASON_CHOICES = [
        ('expired', 'Expired Product'),
        ('damaged', 'Damaged/Broken'),
        ('spillage', 'Spillage'),
        ('quality', 'Quality Issues'),
        ('other', 'Other')
    ]

    main_store_product = models.ForeignKey(LivaraMainStore, on_delete=models.CASCADE, related_name='write_offs')
    quantity = models.PositiveIntegerField()
    batch_number = models.CharField(max_length=50)  # Will be populated from LivaraMainStore
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    notes = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_writeoffs'
    )
    approved_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Write-off of {self.quantity} units from batch {self.batch_number} - {self.reason}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            # Ensure batch number matches the main store product
            self.batch_number = self.main_store_product.batch_number
            
            # Validate quantity
            if self.quantity > self.main_store_product.quantity:
                raise ValidationError("Write-off quantity cannot exceed available stock")

        if self.approved and not self.approved_date:
            self.approved_date = timezone.now()
            
            # Create an inventory adjustment record
            LivaraInventoryAdjustment.objects.create(
                store_inventory=self.main_store_product,
                adjusted_quantity=-self.quantity,  # Negative for write-offs
                adjustment_reason=f"Write-off: {self.get_reason_display()} - {self.notes}",
                adjusted_by=self.approved_by
            )
            
            # Update main store quantity
            self.main_store_product.previous_quantity = self.main_store_product.quantity
            self.main_store_product.quantity -= self.quantity
            self.main_store_product.adjustment_date = timezone.now()
            self.main_store_product.adjustment_reason = f"Write-off: {self.get_reason_display()}"
            self.main_store_product.save()

        super().save(*args, **kwargs)

    @property
    def adjustment_record(self):
        """Get the related inventory adjustment record if it exists"""
        return LivaraInventoryAdjustment.objects.filter(
            store_inventory=self.main_store_product,
            adjustment_date__gte=self.approved_date,
            adjustment_reason__startswith="Write-off:"
        ).first() if self.approved_date else None

    
# 1. Main Accessory Model
class Accessory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name


# 2. Main Store Accessory Inventory (Livara Main Store)
class AccessoryInventory(models.Model):
    accessory = models.ForeignKey(Accessory, on_delete=models.CASCADE, related_name='main_inventory')
    quantity = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.accessory.name} "
    
    @property
    def current_stock(self):
        return self.quantity
    
    @current_stock.setter
    def current_stock(self, value):
        self.quantity = value
        self.save()  # Make sure to save the model if you're using a setter

    def adjust_stock(self, quantity, description=""):
        """Method to create an adjustment for the inventory."""
        with transaction.atomic():
            AccessoryInventoryAdjustment.objects.create(
                accessory_inventory=self, adjustment=quantity, description=description, date=timezone.now()
            )
            self.quantity += quantity  # Update the quantity directly in the inventory
            self.save()

# Accessory Inventory Adjustments
class AccessoryInventoryAdjustment(models.Model):
    accessory_inventory = models.ForeignKey(AccessoryInventory, on_delete=models.CASCADE,null=True, blank=True)
    adjustment = models.DecimalField(max_digits=15, decimal_places=5, default=0.0)
    description = models.CharField(max_length=255, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'Increase' if self.adjustment > 0 else 'Decrease'} of {self.adjustment} units at {self.date}"
    
# Main Store Accessory Requisition Model
class MainStoreAccessoryRequisition(models.Model):
    accessory_req_number = models.CharField(max_length=50, unique=True, blank=True)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delivered', 'Delivered')
    ], default='pending')
    comments = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Requisition by {self.requested_by.username} on {self.request_date}"
    
    def save(self, *args, **kwargs):
        if not self.accessory_req_number:
            self.accessory_req_number = self.generate_accessory_req_number()
        
        super().save(*args, **kwargs)
    
    def generate_accessory_req_number(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        
        # Generate random number
        random_number = random.randint(1000, 9999)
        
        # Construct the LPO number
        accessory_req_number = f"acc-main-{month}{year}-{random_number}"
        
        # Ensure the generated number is unique
        while MainStoreAccessoryRequisition.objects.filter(accessory_req_number=accessory_req_number).exists():
            random_number = random.randint(1000, 9999)
            accessory_req_number = f"pod-po{month}{year}-{random_number}"
        
        return accessory_req_number


# Individual Accessory Requisition Items
class MainStoreAccessoryRequisitionItem(models.Model):
    requisition = models.ForeignKey(MainStoreAccessoryRequisition, related_name='items', on_delete=models.CASCADE)
    accessory = models.ForeignKey('Accessory', on_delete=models.CASCADE)
    quantity_requested = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity_requested} units of {self.accessory.name}"
    

    


##############################################

class RestockRequest(models.Model):
    liv_store_transfer_number = models.CharField(max_length=50, unique=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name="requested_restocks")  # Optional: User who requested
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, choices=[
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("delivered", "Delivered"),
        ("rejected", "Rejected"),
    ], default="pending")
    comments = models.TextField(blank=True)  # Optional: Comments or reasons for rejection


    def __str__(self):
        return f"Restock Request for {self.liv_store_transfer_number}-{self.store.name} (requested by: {self.requested_by.username if self.requested_by else 'N/A'})"
    
    def save(self, *args, **kwargs):
        if not self.liv_store_transfer_number:
            self.liv_store_transfer_number = self.generate_liv_store_transfer_number()
        super().save(*args, **kwargs)

    def generate_liv_store_transfer_number(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        
        # Generate random number
        random_number = random.randint(1000, 9999)
        
        # Construct the LPO number
        liv_store_transfer_number = f"LIV-STORE-TRNS-{month}{year}-{random_number}"
        
        # Ensure the generated number is unique
        while RestockRequest.objects.filter(liv_store_transfer_number=liv_store_transfer_number).exists():
            random_number = random.randint(1000, 9999)
            liv_store_transfer_number = f"pod-po{month}{year}-{random_number}"
        
        return liv_store_transfer_number
    
class RestockRequestItem(models.Model):
    restock_request = models.ForeignKey(RestockRequest, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(LivaraMainStore, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    approved_quantity = models.PositiveIntegerField(null=True, blank=True)  # Approved quantity
    delivered_quantity = models.PositiveIntegerField(null=True, blank=True)  # New field for delivered quantity
    

    def __str__(self):
        return f"{self.quantity} units of {self.product.product.product.product_name} for restock request {self.restock_request}"
    
        
class TransferApproval(models.Model):
    transfer = models.ForeignKey(RestockRequest, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE)
    approved_date = models.DateTimeField(auto_now_add=True)
    approved_quantity = models.PositiveIntegerField()  # Approved quantity
    
class StoreInventory(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)  # Link to manufactured product
    store = models.ForeignKey(Store, on_delete=models.CASCADE)  # Link to store
    quantity = models.PositiveIntegerField()
    last_updated = models.DateTimeField(auto_now=True)  # Track last update
    previous_quantity = models.PositiveIntegerField(default=0)
    low_stock_flag = models.BooleanField(default=False)
    

    def save(self, *args, **kwargs):
        self.low_stock_flag = self.quantity < 100  # Adjust the threshold as needed
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.product.product_name} ({self.quantity}) in {self.store.name} - Last Updated: {self.last_updated.strftime('%Y-%m-%d')}"

    class Meta:
        unique_together = (('product', 'store'),)
        
    

# store inventory adjustment model   
class InventoryAdjustment(models.Model): ### for manufacture products ###
    store_inventory = models.ForeignKey(StoreInventory, on_delete=models.CASCADE, related_name='adjustments')
    adjusted_quantity = models.IntegerField()
    adjustment_date = models.DateTimeField(auto_now_add=True)
    adjustment_reason = models.CharField(max_length=255)
    adjusted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    transfer_to_store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    transfer_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Adjustment of {self.adjusted_quantity} units for {self.store_inventory.product} on {self.adjustment_date}"


##Accessories for all salons 
class StoreAccessoryInventory(models.Model):#### For Accessories in each Store ##
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='accessory_inventory')
    accessory = models.ForeignKey(Accessory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('store', 'accessory')
        verbose_name_plural = "Store Accessory Inventories"

    def __str__(self):
        return f"{self.accessory.name} - {self.quantity} units in {self.store.name}"

    def is_low_stock(self):
        return self.quantity < 20  # Adjust as needed
    
# 4. Requisition Model (Request for restock in each store)
class InternalAccessoryRequest(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    request_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),('delivered','Delivered')],default="pending")

    comments = models.TextField(blank=True)

    def __str__(self):
        return f"Request from {self.store.name} on {self.request_date}"


# 5. Requisition Item Model (Items in a Requisition)
class InternalAccessoryRequestItem(models.Model):
    request = models.ForeignKey(InternalAccessoryRequest, on_delete=models.CASCADE, related_name='items',null=True,blank=True)
    accessory = models.ForeignKey(Accessory, on_delete=models.CASCADE)
    quantity_requested = models.PositiveIntegerField()
    # Other fields like price, notes, etc., if needed

    def __str__(self):
        return f"{self.quantity_requested} x {self.accessory.name}"
    
class ServiceSale(models.Model):
    PAID_STATUS_CHOICES = [
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid'),
    ]
    service_sale_number = models.CharField(max_length=20, unique=True,editable=False, null=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='service_sales')
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE, related_name='service_sales')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_date = models.DateTimeField(auto_now_add=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_status = models.CharField(max_length=20, choices=PAID_STATUS_CHOICES, default='not_paid')
    payment_mode = models.CharField(max_length=255, choices=[
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('visa', 'Visa'),
        ('mixed', 'Mixed'),
    ],default='cash')
    payment_remarks = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return f"Sale #{self.id} - {self.customer}"
    
    def save(self, *args, **kwargs):
        # Automatically generate a unique number if not already set
        if not self.service_sale_number:
            self.service_sale_number = self.generate_service_sale_number()
        super().save(*args, **kwargs)

    def generate_service_sale_number(self):
        """Generate a unique number based on store, date, and random digits."""
        store_prefix = self.store.name[:2].upper()  # First two letters of the store name
        date_part = timezone.now().strftime('%m%y') if self.sale_date else ''
        random_part = f"{random.randint(1000, 9999)}"  # Random 4-digit number
        return f"{store_prefix}-{date_part}-{random_part}"

    def calculate_total(self):
        total = sum(item.total_price for item in self.service_sale_items.all())
        total += sum(item.total_price for item in self.accessory_sale_items.all())
        total += sum(item.total_price for item in self.product_sale_items.all())
        
        self.total_amount = total
        
        # Sum payments from the Payment model
        self.paid_amount = self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        
        self.balance = total - self.paid_amount
        self.paid_status = 'paid' if self.balance <= 0 else 'not_paid'
        self.save()
        
    def create_service_commissions(self):
        """Create commission records for all service items in this sale"""
        print(f"\nDEBUG: Creating commissions for sale {self.service_sale_number}")
        
        with transaction.atomic():
            for service_item in self.service_sale_items.all():
                print(f"\nDEBUG: Processing service item: {service_item.service.service.name}")
                staff_count = service_item.staff.count()
                
                if staff_count == 0:
                    print("DEBUG: No staff assigned to this service")
                    continue
                
                # Calculate commission
                commission_rate = service_item.service.commission_rate
                total_commission = service_item.total_price * Decimal(str(commission_rate))
                per_staff_commission = total_commission / Decimal(staff_count)
                
                print(f"DEBUG: Commission calculation:")
                print(f"- Total price: {service_item.total_price}")
                print(f"- Commission rate: {commission_rate}")
                print(f"- Total commission: {total_commission}")
                print(f"- Staff count: {staff_count}")
                print(f"- Per staff commission: {per_staff_commission}")
                
                # Create commission records
                for staff_member in service_item.staff.all():
                    commission = StaffCommission.objects.create(
                        staff=staff_member,
                        service_sale_item=service_item,
                        commission_amount=per_staff_commission
                    )
                    print(f"DEBUG: Created commission for {staff_member.first_name}: {commission.commission_amount}")
    def create_product_commissions(self):
        """Create commission records for products with assigned staff"""
        print(f"\nDEBUG: Creating product commissions for sale {self.service_sale_number}")
        
        with transaction.atomic():
            product_items = self.product_sale_items.all()
            print(f"DEBUG: Found {product_items.count()} product items")
            
            for product_item in product_items:
                print(f"\nDEBUG: Processing product: {product_item.product.product.product_name}")
                print(f"DEBUG: Staff assigned: {product_item.staff}")
                print(f"DEBUG: Product total price: {product_item.total_price}")
                
                if product_item.staff:
                    commission_amount = product_item.total_price * Decimal('0.05')  # 5% commission
                    print(f"DEBUG: Calculated commission amount: {commission_amount}")
                    
                    # Delete any existing commission
                    existing_commission = StaffProductCommission.objects.filter(product_sale_item=product_item)
                    if existing_commission.exists():
                        print(f"DEBUG: Deleting existing commission")
                        existing_commission.delete()
                    
                    try:
                        # Create new commission
                        commission = StaffProductCommission.objects.create(
                            staff=product_item.staff,
                            product_sale_item=product_item,
                            commission_amount=commission_amount
                        )
                        print(f"DEBUG: Successfully created commission for {product_item.staff.first_name}: {commission_amount}")
                    except Exception as e:
                        print(f"ERROR creating commission: {str(e)}")
                else:
                    print(f"DEBUG: No staff assigned to this product item")
        
    def mark_as_paid(self):
        if self.paid_status != 'paid' and self.balance <= 0:
            with transaction.atomic():
                self.paid_status = 'paid'
                self.save()
                
                # Create service commissions
                self.create_service_commissions()
                
                # Create product commissions
                self.create_product_commissions()
                
                try:
                    # Adjust inventory for accessories
                    self._deduct_accessory_inventory()
                    
                    # Adjust inventory for products
                    self._deduct_product_inventory()
                    
                except ValueError as e:
                    raise ValueError(f"Inventory adjustment failed: {str(e)}")

    def _deduct_accessory_inventory(self):
        """Deduct inventory for accessories and log adjustments."""
        for accessory_item in self.accessory_sale_items.all():
            store_accessory_inventory = accessory_item.accessory
            if store_accessory_inventory.quantity < accessory_item.quantity:
                raise ValueError(f"Insufficient stock for {store_accessory_inventory.accessory.name}")

            # Deduct inventory
            original_quantity = store_accessory_inventory.quantity
            store_accessory_inventory.quantity -= accessory_item.quantity
            store_accessory_inventory.save()

            # Log adjustment
            StoreInventoryAdjustment.objects.create(
                accessory_inventory=store_accessory_inventory,
                adjustment='sale',
                quantity=-accessory_item.quantity,
                reason=f"Sold in a ServiceSale #{self.id}"
            )
            # Debug: Log inventory changes
            print(f"Accessory {store_accessory_inventory.accessory.name}: Deducted {accessory_item.quantity}. Original: {original_quantity}, Remaining: {store_accessory_inventory.quantity}")
    def _deduct_product_inventory(self):
        """Deduct inventory for products and log adjustments."""
        for product_item in self.product_sale_items.all():
            store_inventory = product_item.product
            if store_inventory.quantity < product_item.quantity:
                raise ValueError(f"Insufficient stock for {store_inventory.product.product_name}")

            # Deduct inventory and update previous quantity
            store_inventory.previous_quantity = store_inventory.quantity
            store_inventory.quantity -= product_item.quantity
            store_inventory.save()

            # Log adjustment
            InventoryAdjustment.objects.create(
                store_inventory=store_inventory,
                adjusted_quantity=-product_item.quantity,
                adjustment_reason=f"Sold in ServiceSale #{self.id}",
                adjusted_by=None,  # Set this to the appropriate user if available
            )

    def record_payment(self, payment_method, amount, remarks=None):
        """Record a new payment and update sale status."""
        Payment.objects.create(
            sale=self,
            payment_method=payment_method,
            amount=amount,
            remarks=remarks
        )
        self.calculate_total()
        
    
        
    def create_invoice(self):
        """Create an invoice for this sale."""
        invoice = ServiceSaleInvoice.objects.create(sale=self, total_amount=self.total_amount)
        return invoice
    
class ServiceSaleItem(models.Model):
    sale = models.ForeignKey(ServiceSale, on_delete=models.CASCADE, related_name='service_sale_items')
    service = models.ForeignKey(StoreService, on_delete=models.CASCADE)
    staff = models.ManyToManyField('POSMagicApp.Staff', related_name='service_sales')
    quantity = models.PositiveIntegerField(default=1)  # For multiple services of the same type
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def calculate_and_create_commissions(self):
        """Calculate and create commission records for staff members"""
        with transaction.atomic():
            # First, delete any existing commissions for this sale item
            StaffCommission.objects.filter(service_sale_item=self).delete()
            
            # Get the number of staff members
            staff_members = self.staff.all()
            staff_count = staff_members.count()
            if staff_count == 0:
                print("DEBUG: No staff members assigned!")
                return

            # Calculate total commission amount
            commission_rate = self.service.commission_rate
            total_commission = self.total_price * Decimal(str(commission_rate))
            
            print(f"DEBUG: Total Commission: {total_commission}")

            # Calculate per-staff commission (divide equally)
            per_staff_commission = total_commission / Decimal(staff_count)
            print(f"DEBUG: Per Staff Commission: {per_staff_commission}")

            # Create commission records for each staff member
            for staff_member in staff_members:
                commission = StaffCommission.objects.create(
                    staff=staff_member,
                    service_sale_item=self,
                    commission_amount=per_staff_commission
                )
                print(f"DEBUG: Created commission for {staff_member.name}: {commission.commission_amount}")

    def save(self, *args, **kwargs):
        print(f"\nDEBUG: Saving ServiceSaleItem")
        # Calculate total price
        self.total_price = self.quantity * self.service.service.price
        print(f"DEBUG: Total Price calculated: {self.total_price}")
        
        # First save the service sale item
        super().save(*args, **kwargs)
        
        # Check if sale is paid
        if self.sale.paid_status == 'paid':
            print("DEBUG: Sale is paid, calculating commissions")
            self.calculate_and_create_commissions()
        else:
            print(f"DEBUG: Sale not paid yet. Status: {self.sale.paid_status}")
            
    def __str__(self):
        return f"{self.quantity} x {self.service.service.name} for Sale #{self.sale.id}"
    
class AccessorySaleItem(models.Model):
    sale = models.ForeignKey(ServiceSale, on_delete=models.CASCADE, related_name='accessory_sale_items')
    accessory = models.ForeignKey(StoreAccessoryInventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.price
        super().save(*args, **kwargs)
        
        # Recalculate the total for the related sale
        self.sale.calculate_total()
    def __str__(self):
        return f"{self.quantity} x {self.accessory.accessory.name} for Sale #{self.sale.id}"
        
class ProductSaleItem(models.Model):
    sale = models.ForeignKey(ServiceSale, on_delete=models.CASCADE, related_name='product_sale_items')
    product = models.ForeignKey(StoreInventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_group = models.ForeignKey(PriceGroup, on_delete=models.SET_NULL, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    staff = models.ForeignKey('POSMagicApp.Staff', 
                                on_delete=models.SET_NULL,
                                null=True,
                                related_name='product_sales',
                                help_text="Staff member who recommended this product")
    PRODUCT_COMMISSION_RATE = Decimal('0.05')  # 10% commission rate
    
    def calculate_price(self):
        # First check if there's a specific price for this product in the selected price group
        if self.price_group:
            try:
                product_price = ProductPrice.objects.get(
                    product=self.product.product,
                    price_group=self.price_group
                )
                return product_price.price
            except ProductPrice.DoesNotExist:
                pass
        
        # If no specific price group or price not found, return default price
        return self.product.product.price
    
    def calculate_and_create_commission(self):
        """Calculate and create commission record for staff member if assigned"""
        if self.staff and self.sale.paid_status == 'paid':
            # Delete any existing commission for this product sale item
            StaffProductCommission.objects.filter(product_sale_item=self).delete()
            commission_amount = self.total_price * self.PRODUCT_COMMISSION_RATE
            
            # Create or update commission record
            StaffProductCommission.objects.create(
                staff=self.staff,
                product_sale_item=self,
                commission_amount=commission_amount
            )
            print(f"DEBUG: Created product commission for {self.staff.first_name}: {commission_amount}")
    
    def save(self, *args, **kwargs):
        # Calculate total price based on price group
        unit_price = self.calculate_price()
        self.total_price = self.quantity * unit_price
        super().save(*args, **kwargs)
        
        # Calculate commission if staff is assigned and sale is paid
        if self.sale.paid_status == 'paid':
            self.calculate_and_create_commission()
        
        # Recalculate the total for the related sale
        self.sale.calculate_total()
    
    def __str__(self):
        return f"{self.quantity} x {self.product.product.product_name} for Sale #{self.sale.id}"
    
class StoreInventoryAdjustment(models.Model):
    ADJUSTMENT_TYPE_CHOICES = [
        ('requisition', 'Internal Requisition'),
        ('sale', 'Service Sale'),
        ('other', 'Other'),
    ]
    accessory_inventory = models.ForeignKey(StoreAccessoryInventory, on_delete=models.CASCADE, related_name='adjustments')
    adjustment = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    quantity = models.IntegerField()  # Positive for increase, negative for decrease
    reason = models.TextField(blank=True, null=True)  # Optional, for extra details
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.adjustment}: {self.quantity} on {self.accessory_inventory.store.name}"
    
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('visa', 'Visa'),
    ]

    sale = models.ForeignKey('ServiceSale', on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.amount} via {self.payment_method} for Sale #{self.sale.id}"



class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    verb = models.CharField(max_length=255)
    description = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.verb} - {self.description[:20]}"
    
#### store sales
    
class StoreSale(models.Model):
    VAT_RATE = Decimal('0.18')  # Default VAT rate (18%)
    WITHHOLDING_TAX_RATE = Decimal(0.06)  # Default withholding tax rate (6%)
    PAYMENT_DURATION = timedelta(days=45)  # Default payment duration (45 days)

    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE)
    sale_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=255, choices=[
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    ], default="pending")
    due_date = models.DateField(blank=True, null=True)  # Calculated due date
    # Additional sale statuses
    STATUS_CHOICES = (
        ("ordered", "Ordered"),
        ("delivered", "Delivered"),
        ("paid","Paid"),
    )
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="ordered")
    withhold_tax = models.BooleanField(default=False)  # Option to withhold tax
    vat = models.BooleanField(default=False)  # Option to apply VAT
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Total sale amount

    def __str__(self):
        return f"Store Sale for {self.customer.first_name} on {self.sale_date.strftime('%Y-%m-%d')}"
    
    
    def calculate_total(self):
        try:
            # Get all sale items associated with this StoreSale
            sale_items = self.saleitem_set.all()  # Fetch all sale items for this sale
            
            # Calculate subtotal using the chosen price for each sale item
            subtotal = sum(item.quantity * item.chosen_price for item in sale_items if item.chosen_price is not None)
            print(f"Subtotal: {subtotal}")  # Debugging output

            # Convert subtotal to Decimal if needed
            subtotal = Decimal(subtotal)

            total = subtotal
            if self.vat:
                vat_amount = subtotal * self.VAT_RATE
                print(f"VAT Amount: {vat_amount}")  # Debugging output
                total += vat_amount
            if self.withhold_tax:
                withholding_tax_amount = total * self.WITHHOLDING_TAX_RATE
                print(f"Withholding Tax Amount: {withholding_tax_amount}")  # Debugging output
                total += withholding_tax_amount

            print(f"Final Total: {total}")  # Debugging output
            return total
        except (TypeError, ValueError) as e:
            print(f"Error in calculate_total: {e}")  # Debugging output
            return Decimal('0.00')

    def save(self, *args, **kwargs):
        if not self.pk:
            #save sale to generate id before calculating total
            super().save(*args, **kwargs)
        # Calculate total before saving
        self.total_amount = self.calculate_total()
        if not self.due_date and self.sale_date:  # Check if sale_date is not None
            self.due_date = self.sale_date + self.PAYMENT_DURATION
        super().save(*args, **kwargs)  # Call parent save method
        
    def get_remaining_days(self):
        today = date.today()
        due_date = self.due_date if self.due_date else self.sale_date + self.PAYMENT_DURATION
        return (due_date - today).days  # Allow negative values for overdue days
        
class SaleItem(models.Model):
    sale = models.ForeignKey(StoreSale, on_delete=models.CASCADE)  # Link to StoreSale
    product = models.ForeignKey(LivaraMainStore, on_delete=models.CASCADE)  # Link to product
    price_group = models.ForeignKey(PriceGroup, null=True, blank=True, on_delete=models.SET_NULL)  # Selected price group
    quantity = models.DecimalField(max_digits=10, decimal_places=0)
    chosen_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # New field for chosen price
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)  # Calculated total price

    def __str__(self):
        return f"{self.quantity} units of {self.product} for Sale #{self.sale.id}"
    
    def save(self, *args, **kwargs):
        # Fetch the price from the selected price group
        if self.price_group:
            product_price = ProductPrice.objects.filter(product=self.product.product.product, price_group=self.price_group).first()
            if product_price:
                self.chosen_price = product_price.price
        else:
            # Default to the wholesale price if no group is selected
            self.chosen_price = self.product.product.product.wholesale_price

        # Calculate the total price
        self.total_price = (self.quantity * self.chosen_price) if self.chosen_price else 0
        super().save(*args, **kwargs)  # Call parent save method
        

class StoreSaleReceipt(models.Model):
    store_sale = models.OneToOneField(StoreSale, on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=10, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_vat = models.DecimalField(max_digits=10, decimal_places=2)
    withholding_tax = models.DecimalField(max_digits=10, decimal_places=2)
    total_due = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.receipt_number} for StoreSale {self.store_sale.id}"
        
        
################### Requsition models
class Requisition(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('checking', 'Checking'),
        ('delivered', 'Delivered'),
    ]
    
    requisition_no = models.CharField(max_length=50, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    price_list_document = models.FileField(upload_to='uploads/products/', null=True, blank=True)
    items = models.ManyToManyField(RawMaterial, through='RequisitionItem')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places =0,null=True, blank=True)
    
    def __str__(self):
        return f'Requisition {self.requisition_no}'

    def save(self, *args, **kwargs):
        if not self.requisition_no:
            self.requisition_no = self.generate_requisition_no()
            
        # First save the requisition instance to get the primary key
        if not self.pk:
            super().save(*args, **kwargs)  # Save the instance first to get the primary key
        
        # Calculate total cost after saving the requisition and once it has a primary key
        self.total_cost = self.calculate_total_cost()
            
        # Handle status change for LPO creation
        if self.pk:  # Check if it's an existing record
            previous_status = Requisition.objects.get(pk=self.pk).status
            if previous_status == 'created' and self.status == 'approved':
                # Create LPO if status changes from 'created' to 'approved'
                LPO.objects.create(requisition=self)

        super().save(*args, **kwargs)
            
    def generate_requisition_no(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        #generate random number
        random_number = random.randint(0000,9999)
        
        # Construct the requisition number
        requisition_no = f"prod-req-{month}{year}-{random_number}"
        
        # Ensure the generated number is unique
        while Requisition.objects.filter(requisition_no=requisition_no).exists():
            random_number = random.randint(1000, 9999)
            requisition_no = f"prod-req-{month}{year}-{random_number}"
        
        return requisition_no
    
    def calculate_total_cost(self):
        # Sum the total cost of all requisition items
        return sum(item.total_cost for item in self.requisitionitem_set.all())
            
class RequisitionItem(models.Model):
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    delivered_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.raw_material.name} - {self.quantity}'
    
    @property
    def total_cost(self):
        # Calculate the total cost for this specific item
        return self.price_per_unit * self.delivered_quantity
    
class LPO(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    PAYMENT_DURATION_CHOICES = [
        (0, 'Immediate Payment'),
        (10, '10 days'),
        (20, '20 days'),
        (30, '30 days'),
        (45, '45 days')
    ]

    PAYMENT_OPTIONS_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('cash', 'Cash'),
    ]
    lpo_number = models.CharField(max_length=50, unique=True, blank=True)
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invoice_document = models.FileField(upload_to='uploads/products/')
    quotation_document = models.FileField(upload_to='uploads/products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_duration = models.IntegerField(choices=PAYMENT_DURATION_CHOICES, default=10)
    payment_option = models.CharField(max_length=20, choices=PAYMENT_OPTIONS_CHOICES, default='cash')
    
    
    # Payment tracking fields
    is_paid = models.BooleanField(default=False, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=0, default=0.00,null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'LPO {self.lpo_number} for {self.requisition.requisition_no}'
    
    def save(self, *args, **kwargs):
        if not self.lpo_number:
            self.lpo_number = self.generate_lpo_number()
            
        # Update payment status based on amount paid
        if self.amount_paid >= self.requisition.total_cost:
            self.is_paid = True
            self.payment_date = timezone.now()  # Record payment date
        else:
            self.is_paid = False
        
        super().save(*args, **kwargs)
    
    def generate_lpo_number(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        
        # Generate random number
        random_number = random.randint(1000, 9999)
        
        # Construct the LPO number
        lpo_number = f"prod-po-{month}{year}-{random_number}"
        
        # Ensure the generated number is unique
        while LPO.objects.filter(lpo_number=lpo_number).exists():
            random_number = random.randint(1000, 9999)
            lpo_number = f"pod-po{month}{year}-{random_number}"
        
        return lpo_number

    def verify(self):
        if self.status == 'pending':
            print("Verifying LPO...")
            self.status = 'verified'
            self.is_paid = False
            self.save()
            
            # Update the corresponding requisition status to 'checking'
            if self.requisition.status == 'approved':
                print(f"Updating requisition {self.requisition.requisition_no} to checking...")
                self.requisition.status = 'checking'
                self.requisition.save()

    def reject(self):
        if self.status == 'pending':
            self.status = 'rejected'
            self.save()
    
    @property
    def outstanding_balance(self):
        """Calculate the outstanding balance by subtracting amount paid from total cost."""
        return max(0, self.requisition.total_cost - self.amount_paid)
            
class GoodsReceivedNote(models.Model):
    REASON_CHOICES = [
        ('Successful', 'Successful'),
        ('expired', 'Expired'),
        ('quality', 'Poor Quality'),
        ('spillage', 'Spillage'),
    ]
    gcr_number = models.CharField(max_length=50, unique=True, blank=True)
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE)
    lpo = models.ForeignKey(LPO, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reason = models.CharField(max_length=255, blank=True, null=True, choices=REASON_CHOICES)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Goods Received Note for {self.requisition.requisition_no}'
    
    def save(self, *args, **kwargs):
        if not self.gcr_number:
            self.gcr_number = self.generate_gcr_number()
        
        super().save(*args, **kwargs)
    
    def generate_gcr_number(self):
        current_date = timezone.now()
        month = current_date.strftime('%m')  # Month as two digits (08)
        year = current_date.strftime('%y')   # Year as last two digits (24)
        
        # Generate random number
        random_number = random.randint(1000, 9999)
        
        # Construct the GRC number
        gcr_number = f"prod-gcr-{month}{year}-{random_number}"
        
        # Ensure the generated number is unique
        while GoodsReceivedNote.objects.filter(gcr_number=gcr_number).exists():
            random_number = random.randint(1000, 9999)
            gcr_number = f"prod-gcr-{month}{year}-{random_number}"
        
        return gcr_number
    
    
class DiscrepancyDeliveryReport(models.Model):
    ACTION_CHOICES = [
        ('refund', 'Refund from Supplier'),
        ('replace', 'Replace Missing Items'),
    ]

    goods_received_note = models.ForeignKey(GoodsReceivedNote, on_delete=models.CASCADE)
    action_taken = models.CharField(max_length=10, choices=ACTION_CHOICES)
    description = models.TextField(blank=True, null=True)
    date_reported = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_action_taken_display()} - {self.goods_received_note.id}"
    
class ReplaceNote(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('refunded','Refunded')
    ]

    replace_note_number = models.CharField(max_length=20, unique=True, editable=False)
    discrepancy_report = models.ForeignKey('DiscrepancyDeliveryReport', on_delete=models.CASCADE, related_name='replace_notes')
    date_created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        if not self.replace_note_number:
            max_number = ReplaceNote.objects.aggregate(models.Max('id'))['id__max']
            self.replace_note_number = f"RN-{(max_number or 0) + 1:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Replace Note {self.replace_note_number} - {self.discrepancy_report.goods_received_note.id}"

class ReplaceNoteItem(models.Model):
    replace_note = models.ForeignKey(ReplaceNote, related_name='items', on_delete=models.CASCADE)
    raw_material = models.ForeignKey('RawMaterial', on_delete=models.CASCADE)
    ordered_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    delivered_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_to_replace = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.raw_material.name} - {self.quantity_to_replace}"

class DebitNote(models.Model):
    debit_note_number = models.CharField(max_length=20, unique=True, editable=False)
    discrepancy_report = models.ForeignKey('DiscrepancyDeliveryReport', on_delete=models.CASCADE, related_name='debit_notes')
    total_deducted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    date_created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.debit_note_number:
            max_number = DebitNote.objects.aggregate(models.Max('id'))['id__max']
            self.debit_note_number = f"DN-{(max_number or 0) + 1:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Debit Note {self.debit_note_number} - {self.discrepancy_report.goods_received_note.id}"
    

class PaymentVoucher(models.Model):
    voucher_number = models.CharField(max_length=50, unique=True, blank=True)
    lpo = models.ForeignKey(LPO, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    pay_by = models.CharField(max_length=20, choices=[('cash', 'Cash'),('bank', 'Bank Transfer'),('mobile', 'Mobile Money')],blank=True, null=True)
    voucher_notes = models.TextField(blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=[('full', 'Full Payment'), ('partial', 'Partial Payment')], default='partial')
    
    def __str__(self):
        return f"Voucher #{self.voucher_number} for LPO {self.lpo.lpo_number}"

    def save(self, *args, **kwargs):
        if not self.voucher_number:
            super().save(*args, **kwargs)
            
            self.voucher_number = self.generate_voucher_number()
            
            # Save again with the generated voucher number
            super().save(update_fields=['voucher_number'])
            
        if self.payment_type == 'full' and self.amount_paid < self.lpo.requisition.total_cost:
            raise ValueError("Cannot mark as 'Full Payment' if the amount is less than LPO total.")
        super().save(*args, **kwargs)

    def generate_voucher_number(self):
        current_date = timezone.now()
        return f"PROD-PV-{current_date.strftime('%Y%m%d')}-{self.id}"
    

# Signal to update LPO on PaymentVoucher save
@receiver(post_save, sender=PaymentVoucher)
def update_lpo_payment(sender, instance, **kwargs):
    lpo = instance.lpo
    total_paid = PaymentVoucher.objects.filter(lpo=lpo).aggregate(total=models.Sum('amount_paid'))['total'] or 0
    lpo.amount_paid = total_paid
    lpo.is_paid = total_paid >= lpo.requisition.total_cost
    lpo.payment_date = timezone.now() if lpo.is_paid else None
    lpo.save()

class StaffProductCommission(models.Model):
    staff = models.ForeignKey('POSMagicApp.Staff', on_delete=models.CASCADE, related_name='product_commissions')
    product_sale_item = models.OneToOneField(ProductSaleItem, on_delete=models.CASCADE, related_name='commission')
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Commission for {self.staff.first_name} - {self.product_sale_item}"