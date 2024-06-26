from datetime import timedelta
from decimal import Decimal
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
    name = models.CharField(max_length=255)
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
    quantity = models.PositiveIntegerField(default=0)
    reorder_point = models.PositiveIntegerField(default=0)
    
    unit_measurement = models.CharField(max_length=10, blank=True, null=True)
    

    def __str__(self):
        return self.name
    
    def add_stock(self, quantity):
        RawMaterialInventory.objects.create(raw_material=self, adjustment=quantity)

    def remove_stock(self, quantity):
        if self.current_stock < quantity:
            raise ValueError("Not enough stock")
        RawMaterialInventory.objects.create(raw_material=self, adjustment=-quantity)
    
    @property
    def current_stock(self):
        return self.rawmaterialinventory_set.all().aggregate(models.Sum('adjustment'))['adjustment__sum'] or 0
    

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    fullfilled_qty = models.PositiveIntegerField(default=0, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=0)  # Consider currency
    total_cost = models.DecimalField(max_digits=10, decimal_places=0, blank=True)  # Auto-calculate
    created_at = models.DateTimeField(auto_now_add=True)
    order_number = models.CharField(max_length=10)
    status = models.CharField(max_length=255, choices=[  # Add choices for different statuses
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("fulfilled", "Fulfilled"),
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
    adjustment = models.IntegerField(default=0)

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

    def __str__(self):
        return self.product_name

class ProductionIngredient(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE,related_name="productioningredients")
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    # Instead of percentage, store quantity per unit product volume
    quantity_per_unit_product_volume = models.DecimalField(max_digits=4, decimal_places=0) 

    def __str__(self) -> str:
        return f"{self.raw_material} for {self.product} needed for {self.quantity_per_unit_product_volume}"

    
class ProductionBatch(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  # Number of bottles produced
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

class ManufactureProduct(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  # Number of units manufactured
    manufactured_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    batch_number = models.CharField(max_length=8)
    labor_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    expiry_date = models.DateField(null=True,blank=True)

    def __str__(self):
        return f"{self.quantity} units of {self.product.product_name} manufactured on {self.manufactured_at.strftime('%Y-%m-%d')}"
    
class ManufacturedProductInventory(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    batch_number = models.CharField(max_length=50,blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    expiry_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.product_name} batch number{self.batch_number} ({self.quantity})- Last Updated: {self.last_updated}"


 ################### stores models   
class Store(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

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

class RestockRequest(models.Model):
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name="requested_restocks")  # Optional: User who requested
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, choices=[
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("delivered", "Delivered"),
        ("rejected", "Rejected"),
    ], default="pending")
    comments = models.TextField(blank=True)  # Optional: Comments or reasons for rejection
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name="approved_restocks")  # User who approved/rejected

    def __str__(self):
        return f"Restock Request for {self.quantity} units of {self.product.product_name} from {self.store.name} (requested by: {self.requested_by.username if self.requested_by else 'N/A'})"
    
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

class ProductionOrder(models.Model):
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
    
    def create_approval_notification(self):
        notification = Notification.objects.create(
            recipient=self.store_manager,
            verb='Your production order has been approved!',
            description=f"Order #{self.pk} for '{self.product.product_name}' has been approved and is ready for production.",
        )
        return notification

    class Meta:
        ordering = ['-created_at'] 

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
    product = models.ForeignKey(ManufacturedProductInventory, on_delete=models.CASCADE)  # Link to product
    quantity = models.DecimalField(max_digits=10, decimal_places=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)  # Calculated total price

    def __str__(self):
        return f"{self.quantity} units of {self.product} for Sale #{self.sale.id}"
    
    def save(self, *args, **kwargs):
        self.total_price = (self.quantity * self.unit_price)
        super().save(*args, **kwargs)  # Call parent save method
        