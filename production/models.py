from datetime import datetime, timedelta
from decimal import Decimal
import random
from time import timezone
from django.db import models
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth import get_user_model
from django.forms import DecimalField

from POSMagicApp.models import Customer 
from django.db.models import Sum, F
from django.utils import timezone




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
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='raw_materials')
    quantity = models.DecimalField(max_digits=15, decimal_places=5, default=0.00000)
    reorder_point = models.PositiveIntegerField(default=0.0)
    unit_measurement = models.CharField(max_length=10, blank=True, null=True)
    

    def __str__(self):
        return f"{self.name} in {self.unit_measurement}"
    
    def latest_price(self):
        """Fetch the most recent price_per_unit from RequisitionItem."""
        latest_requisition_item = RequisitionItem.objects.filter(raw_material=self).order_by('-id').first()
        return latest_requisition_item.price_per_unit if latest_requisition_item else 0

    @property
    def stock_value(self):
        """Calculate the total value of the current stock based on the latest price."""
        latest_price = self.latest_price()
        return self.current_stock * latest_price
    
    def add_stock(self, quantity):
        RawMaterialInventory.objects.create(raw_material=self, adjustment=quantity)

    def remove_stock(self, quantity):
        if self.current_stock < quantity:
            raise ValueError("Not enough stock")
        RawMaterialInventory.objects.create(raw_material=self, adjustment=-quantity)
    
    @property
    def current_stock(self):
        return self.rawmaterialinventory_set.all().aggregate(models.Sum('adjustment'))['adjustment__sum'] or 0
    
    def update_quantity(self):
        self.quantity = self.current_stock
        self.save()

    def set_quantity(self, new_quantity):
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative.")
        adjustment = new_quantity - self.current_stock
        with transaction.atomic():
            RawMaterialInventory.objects.create(raw_material=self, adjustment=adjustment)
            self.update_quantity()
    
    # Method to check if the material is below reorder point
    @property
    def below_reorder_point(self):
        return self.current_stock < self.reorder_point
    

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
    

class Production(models.Model):
    product_name = models.CharField(max_length=255)
    total_volume = models.DecimalField(max_digits=4, decimal_places=0)  # Adjust precision as needed
    unit_of_measure = models.ForeignKey(UnitOfMeasurement, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.product_name

class ProductionIngredient(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE,related_name="productioningredients")
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    # Instead of percentage, store quantity per unit product volume
    quantity_per_unit_product_volume = models.DecimalField(max_digits=10, decimal_places=5)


    def __str__(self) -> str:
        return f"{self.raw_material} for {self.product} needed for {self.quantity_per_unit_product_volume}"

    
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
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ], default='Created')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    target_completion_date = models.DateField(blank=True, null=True)
    approved_quantity = models.PositiveIntegerField(blank=True, null=True)

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
    
class ManufacturedProductInventory(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=4, decimal_places=2)
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


##### Main Store Transfer      
class LivaraMainStore(models.Model):
    product = models.ForeignKey(ManufacturedProductInventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    batch_number = models.CharField(max_length=50, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    expiry_date = models.DateField(null=True, blank=True)
    
    def __str__ (self):
        return f"{self.quantity} units of {self.product.product.product_name} in Main Store"
    
class StoreTransfer(models.Model):
    notes = models.CharField(max_length=40, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Completed', 'Completed')], default='Pending')
    
    def __str__(self):
        return f"Transfer {self.id} by {self.created_by}"

class StoreTransferItem(models.Model):
    transfer = models.ForeignKey(StoreTransfer, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(ManufacturedProductInventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    


##############################################

class RestockRequest(models.Model):
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
        return f"Restock Request for {self.store.name} (requested by: {self.requested_by.username if self.requested_by else 'N/A'})"
    
class RestockRequestItem(models.Model):
    restock_request = models.ForeignKey(RestockRequest, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(LivaraMainStore, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} units of {self.product.product.product.product_name} for restock request {self.restock_request}"
    
class StoreInventory(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)  # Link to manufactured product
    store = models.ForeignKey(Store, on_delete=models.CASCADE)  # Link to store
    quantity = models.PositiveIntegerField()
    last_updated = models.DateTimeField(auto_now=True)  # Track last update

    def __str__(self):
        return f"{self.product.product_name} ({self.quantity}) in {self.store.name} - Last Updated: {self.last_updated.strftime('%Y-%m-%d')}"

    class Meta:
        unique_together = (('product', 'store'),)

# what to add 
# bottle top and bottle without affecting the total volume
# add utilities and labour cost information to be added while manufacturing. utility cost information
# total vo,ume of the product.
# when creating a product  measurements litres make sure its capital or something
# 



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
    VAT_RATE = 0.18  # Default VAT rate (18%)
    WITHHOLDING_TAX_RATE = 0.06  # Default withholding tax rate (6%)
    PAYMENT_DURATION = timedelta(days=45)  # Default payment duration (45 days)

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
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
            quantity_values = self.saleitem_set.values_list('quantity')
            unit_price_values = self.saleitem_set.values_list('unit_price')
            
            # Print the retrieved values for debugging
            print(f"Quantity values: {quantity_values}")
            print(f"Unit price values: {unit_price_values}")
            
            # Check if any values are non-numeric
            if any(not isinstance(value, (int, float, Decimal)) for value in quantity_values + unit_price_values):
                raise ValueError("Non-numeric values encountered in quantity or unit_price")

            # Proceed with the calculation assuming numeric values
            subtotal = self.saleitem_set.aggregate(subtotal=Sum(F('quantity') * F('unit_price')))['subtotal'] or 0
            total = subtotal  # Set total to subtotal by default

            # Apply VAT if selected
            if self.vat:
                total += subtotal * self.VAT_RATE

            # Apply withholding tax if selected
            if self.withhold_tax:
                total -= total * self.WITHHOLDING_TAX_RATE

            return total
        except (TypeError, ValueError):
            # Handle potential data type or conversion errors
            return 0  # Or return a more appropriate value (e.g., None)

    def save(self, *args, **kwargs):
        # Calculate total before saving
        self.total_amount = self.calculate_total()
        if self.sale_date:  # Check if sale_date is not None
            self.due_date = self.sale_date + self.PAYMENT_DURATION
        super().save(*args, **kwargs)  # Call parent save method
        
class SaleItem(models.Model):
    sale = models.ForeignKey(StoreSale, on_delete=models.CASCADE)  # Link to StoreSale
    product = models.ForeignKey(LivaraMainStore, on_delete=models.CASCADE)  # Link to product
    quantity = models.DecimalField(max_digits=10, decimal_places=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)  # Calculated total price

    def __str__(self):
        return f"{self.quantity} units of {self.product} for Sale #{self.sale.id}"
    
    def save(self, *args, **kwargs):
        self.total_price = (self.quantity * self.unit_price)
        super().save(*args, **kwargs)  # Call parent save method
        
        
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
        return self.price_per_unit * self.quantity
    
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