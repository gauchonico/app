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
    QUALITY_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('cash_on_delivery', 'Cash on Delivery'),
        ('net_7', 'Net 7 Days'),
        ('net_15', 'Net 15 Days'),
        ('net_30', 'Net 30 Days'),
        ('net_45', 'Net 45 Days'),
        ('net_60', 'Net 60 Days'),
        ('advance_payment', 'Advance Payment'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    company_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    
    # Enhanced supplier attributes
    quality_rating = models.CharField(max_length=20, choices=QUALITY_CHOICES, default='good')
    payment_terms = models.CharField(max_length=30, choices=PAYMENT_TERMS_CHOICES, default='net_30')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Maximum credit allowed")
    is_active = models.BooleanField(default=True)
    reliability_score = models.DecimalField(max_digits=3, decimal_places=1, default=5.0, help_text="Score out of 10")
    notes = models.TextField(blank=True, help_text="Additional notes about supplier")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.quality_rating})"
    
    class Meta:
        ordering = ['name']
    
class UnitOfMeasurement(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    default_store = models.ForeignKey(
        'production.Store', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    def __str__(self):
        return f"{self.user.username}'s profile"

class RawMaterial(models.Model):
    name = models.CharField(max_length=255)
    suppliers = models.ManyToManyField(Supplier, related_name='supplied_raw_materials')
    quantity = models.DecimalField(max_digits=15, decimal_places=5, default=0.00000)
    reorder_point = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
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
    status = models.CharField(max_length=20, default='pending', choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')])
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
        # Save the inventory adjustment first
        super().save(*args, **kwargs)
        # Then update the raw material quantity
        self.raw_material.update_quantity()

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
    QC_STATUS_CHOICES = [
        ('pending', 'QC Pending'),
        ('in_progress', 'QC In Progress'),
        ('passed', 'QC Passed'),
        ('failed', 'QC Failed'),
        ('on_hold', 'QC On Hold'),
        ('not_required', 'QC Not Required'),
    ]
    
    product = models.ForeignKey(Production, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  # Number of units manufactured
    manufactured_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    batch_number = models.CharField(max_length=8, unique=True, blank=True)
    # labor_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    expiry_date = models.DateField(null=True,blank=True)
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, null=True, blank=True, related_name='manufactured_products')
    
    # Quality Control Integration
    qc_status = models.CharField(max_length=20, choices=QC_STATUS_CHOICES, default='pending')
    qc_required = models.BooleanField(default=True, help_text="Whether this batch requires quality control testing")
    qc_sample_quantity = models.PositiveIntegerField(default=0, help_text="Number of sample bottles to allocate for QC")
    can_release_to_inventory = models.BooleanField(default=False, help_text="Whether this batch can be released to inventory")
    
    # Production Cost Tracking
    total_production_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Total production cost for this batch")

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

    def create_quality_control_test(self, sample_quantity=None, assigned_tester=None, priority='medium'):
        """Create a quality control test for this manufactured product batch"""
        if not self.qc_required:
            return None
            
        # Use provided sample quantity or default to qc_sample_quantity
        test_sample_qty = sample_quantity or self.qc_sample_quantity or 1
        
        # Create the quality control test
        qc_test = QualityControlTest.objects.create(
            manufactured_product=self,
            sample_quantity=test_sample_qty,
            assigned_tester=assigned_tester,
            priority=priority,
            test_name=f"Quality Test for {self.product.product_name} - Batch {self.batch_number}"
        )
        
        # Create sample allocation
        SampleAllocation.objects.create(
            manufactured_product=self,
            quantity_allocated=test_sample_qty,
            allocated_by=assigned_tester if assigned_tester else None,
            sample_expiry_date=self.expiry_date
        )
        
        # Update QC status
        self.qc_status = 'in_progress'
        self.save(update_fields=['qc_status'])
        
        return qc_test

    def get_current_quality_test(self):
        """Get the most recent quality control test for this batch"""
        return self.quality_tests.filter(status__in=['pending', 'in_progress']).first()

    def get_latest_qc_result(self):
        """Get the latest quality control result"""
        latest_test = self.quality_tests.order_by('-created_at').first()
        return latest_test.overall_result if latest_test else 'pending'

    def can_be_released(self):
        """Check if this batch can be released to inventory based on QC status"""
        if not self.qc_required:
            return True
        return self.qc_status == 'passed' and self.can_release_to_inventory

    def get_total_samples_allocated(self):
        """Get total number of samples allocated for testing"""
        return self.sample_allocations.aggregate(
            total=models.Sum('quantity_allocated')
        )['total'] or 0

    def get_available_quantity_for_inventory(self):
        """Get quantity available for inventory (excluding samples)"""
        total_samples = self.get_total_samples_allocated()
        return max(0, self.quantity - total_samples)
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


################### Quality Control Models ###################

class QualityControlTest(models.Model):
    """
    Main model for quality control testing of manufactured products
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Testing'),
        ('in_progress', 'Testing In Progress'),
        ('completed', 'Testing Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    
    RESULT_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('conditional_pass', 'Conditional Pass'),
        ('pending', 'Pending'),
    ]

    # Link to the manufactured product batch
    manufactured_product = models.ForeignKey(
        ManufactureProduct, 
        on_delete=models.CASCADE, 
        related_name='quality_tests'
    )
    
    # Test identification
    test_number = models.CharField(max_length=50, unique=True, blank=True)
    test_name = models.CharField(max_length=255, default="Standard Quality Test")
    
    # Sample information
    sample_quantity = models.PositiveIntegerField(help_text="Number of sample bottles allocated for testing")
    sample_taken_at = models.DateTimeField(auto_now_add=True)
    
    # Test scheduling and execution
    scheduled_test_date = models.DateTimeField(null=True, blank=True)
    actual_test_date = models.DateTimeField(null=True, blank=True)
    testing_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Personnel
    assigned_tester = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_quality_tests'
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_quality_tests'
    )
    
    # Test status and priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Results
    overall_result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='pending')
    pass_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Notes and observations
    testing_notes = models.TextField(blank=True, help_text="General testing observations and notes")
    failure_reasons = models.TextField(blank=True, help_text="Detailed reasons if test fails")
    recommendations = models.TextField(blank=True, help_text="QC recommendations and actions")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Quality Control Test"
        verbose_name_plural = "Quality Control Tests"

    def __str__(self):
        return f"QC Test {self.test_number} - {self.manufactured_product.product.product_name}"

    def save(self, *args, **kwargs):
        if not self.test_number:
            self.test_number = self.generate_test_number()
        
        # Auto-set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            
        super().save(*args, **kwargs)

    def generate_test_number(self):
        """Generate unique test number like QC240101-001"""
        current_date = timezone.now()
        date_str = current_date.strftime('%y%m%d')
        
        # Count tests for today
        today_tests = QualityControlTest.objects.filter(
            created_at__date=current_date.date()
        ).count()
        
        return f"QC{date_str}-{today_tests + 1:03d}"

    @property
    def is_overdue(self):
        """Check if test is overdue based on scheduled date"""
        if self.scheduled_test_date and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.scheduled_test_date
        return False

    @property
    def days_since_sampling(self):
        """Calculate days since sample was taken"""
        return (timezone.now() - self.sample_taken_at).days


class QualityTestParameter(models.Model):
    """
    Individual test parameters for quality control (pH, density, color, etc.)
    """
    PARAMETER_TYPES = [
        ('physical', 'Physical'),
        ('chemical', 'Chemical'),
        ('microbiological', 'Microbiological'),
        ('sensory', 'Sensory'),
        ('performance', 'Performance'),
    ]
    
    MEASUREMENT_UNITS = [
        ('ph', 'pH'),
        ('percentage', '%'),
        ('mg_per_ml', 'mg/ml'),
        ('ppm', 'PPM'),
        ('visual', 'Visual'),
        ('pass_fail', 'Pass/Fail'),
        ('numeric', 'Numeric'),
        ('text', 'Text'),
    ]
    
    quality_test = models.ForeignKey(
        QualityControlTest, 
        on_delete=models.CASCADE, 
        related_name='test_parameters'
    )
    
    # Parameter definition
    parameter_name = models.CharField(max_length=100)
    parameter_type = models.CharField(max_length=20, choices=PARAMETER_TYPES)
    measurement_unit = models.CharField(max_length=20, choices=MEASUREMENT_UNITS)
    
    # Expected/target values
    target_value = models.CharField(max_length=100, blank=True, help_text="Target or expected value")
    min_acceptable = models.CharField(max_length=100, blank=True)
    max_acceptable = models.CharField(max_length=100, blank=True)
    
    # Actual results
    measured_value = models.CharField(max_length=100, blank=True)
    result_status = models.CharField(
        max_length=20, 
        choices=[('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')], 
        default='na'
    )
    
    # Additional information
    test_method = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    tested_at = models.DateTimeField(null=True, blank=True)
    tested_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        ordering = ['parameter_name']

    def __str__(self):
        return f"{self.parameter_name}: {self.measured_value} ({self.result_status})"


class QualityControlAction(models.Model):
    """
    Actions taken based on quality control results
    """
    ACTION_TYPES = [
        ('release', 'Release to Inventory'),
        ('hold', 'Hold for Further Testing'),
        ('rework', 'Rework Required'),
        ('discard', 'Discard Batch'),
        ('conditional_release', 'Conditional Release'),
        ('quarantine', 'Quarantine'),
    ]
    
    quality_test = models.ForeignKey(
        QualityControlTest, 
        on_delete=models.CASCADE, 
        related_name='qc_actions'
    )
    
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    action_reason = models.TextField()
    quantity_affected = models.PositiveIntegerField(help_text="Units affected by this action")
    
    # Personnel and timing
    authorized_by = models.ForeignKey(User, on_delete=models.CASCADE)
    action_date = models.DateTimeField(auto_now_add=True)
    
    # Follow-up information
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Status tracking
    is_completed = models.BooleanField(default=False)
    completion_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-action_date']

    def __str__(self):
        return f"{self.action_type} - {self.quality_test.test_number}"


class SampleAllocation(models.Model):
    """
    Track sample bottles allocated for testing from manufactured batches
    """
    manufactured_product = models.ForeignKey(
        ManufactureProduct, 
        on_delete=models.CASCADE, 
        related_name='sample_allocations'
    )
    
    sample_id = models.CharField(max_length=50, unique=True, blank=True)
    quantity_allocated = models.PositiveIntegerField()
    allocation_date = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Sample storage and handling
    storage_location = models.CharField(max_length=255, blank=True)
    storage_temperature = models.CharField(max_length=50, blank=True)
    special_handling_notes = models.TextField(blank=True)
    
    # Status
    is_used = models.BooleanField(default=False)
    used_date = models.DateTimeField(null=True, blank=True)
    
    # Expiry tracking
    sample_expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-allocation_date']

    def __str__(self):
        return f"Sample {self.sample_id} - {self.quantity_allocated} units"

    def save(self, *args, **kwargs):
        if not self.sample_id:
            self.sample_id = self.generate_sample_id()
        super().save(*args, **kwargs)

    def generate_sample_id(self):
        """Generate unique sample ID like SMP240101-001"""
        current_date = timezone.now()
        date_str = current_date.strftime('%y%m%d')
        
        # Count samples for today
        today_samples = SampleAllocation.objects.filter(
            allocation_date__date=current_date.date()
        ).count()
        
        return f"SMP{date_str}-{today_samples + 1:03d}"

################### stores models   
class Store(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_stores', blank=True, null=True)

    def __str__(self):
        return self.name
class ServiceCategory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
class ServiceName(models.Model):
    name = models.CharField(max_length=255)  # Service name (e.g., Hairdressing)
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='service_categories', null=True, blank=True)
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
    
# tracking stock movement from production    
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
                adjustment_reason=f"Write-off #{self.id} - {self.get_reason_display()}: {self.notes}",
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
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
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
    quantity_requested = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity_requested} units of {self.accessory.name}"
    

    


############################################## small livara stores request for restock

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
        
        # Construct the small store number
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
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
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
    quantity_requested = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    # Other fields like price, notes, etc., if needed

    def __str__(self):
        return f"{self.quantity_requested} x {self.accessory.name}"

#Cash Drawer Sessions
class CashDrawerSession(models.Model):
    SESSION_STATUS = (
        ('open', 'Open'),
        ('closed', 'Closed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cash_drawer_sessions')
    store = models.ForeignKey('production.Store', on_delete=models.PROTECT)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    opening_time = models.DateTimeField(auto_now_add=True)
    closing_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=SESSION_STATUS, default='open')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-opening_time']
        verbose_name = 'Cash Drawer Session'
        verbose_name_plural = 'Cash Drawer Sessions'

    def get_expected_balance(self):
        """Calculate the expected balance based on opening balance and transactions"""
        total_transactions = self.transactions.aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'))
        )['total'] or Decimal('0')
        return (self.opening_balance or Decimal('0')) + total_transactions

    @property
    def difference(self):
        if self.closing_balance is not None:
            return self.closing_balance - (self.opening_balance + self.cash_total)
        return None
    
    @property
    def cash_total(self):
        return self.transactions.filter(payment_method='cash').aggregate(
            total=models.Sum('amount')
        )['total__sum'] or 0
    
    def __str__(self):
        return f"Session {self.id} - {self.store.name} - {self.opening_time.strftime('%Y-%m-%d %H:%M')}"

class CashDrawerTransaction(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile_money', 'MTN Momo'),
        ('airtel_money', 'Airtel Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other'),
    )
    
    TRANSACTION_TYPES = (
        ('sale', 'Sale'),
        ('expense', 'Expense'),
        ('float', 'Float Addition'),
        ('withdrawal', 'Withdrawal'),
        ('other', 'Other'),
    )
    
    session = models.ForeignKey(CashDrawerSession, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Optional: Link to related models
    service_sale = models.ForeignKey('production.ServiceSale', on_delete=models.SET_NULL, null=True, blank=True)
    # expense = models.ForeignKey('accounting.Expense', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['session', 'transaction_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} ({self.payment_method})"

#Refreshments model
class Refreshment(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='refreshments',null=True,blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost price per unit")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Selling price per unit")
    quantity = models.PositiveIntegerField(default=0, help_text="Current stock quantity")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('store', 'name')  # Prevent duplicate names within the same store

    def __str__(self):
        return f"{self.name} (Qty: {self.quantity}) in {self.store.name}"

    def update_stock(self, quantity, action, user, notes=None, reference=None):
        """Update stock and create history record"""
        previous_quantity = self.quantity
        
        # Update the quantity
        self.quantity += quantity
        self.save()
        
        # Create history record
        RefreshmentStockHistory.objects.create(
            refreshment=self,
            action=action,
            quantity=quantity,
            previous_quantity=previous_quantity,
            new_quantity=self.quantity,
            notes=notes,
            created_by=user,
            reference=reference
        )
        
        return self.quantity

    def save(self, *args, **kwargs):
        # Ensure sale price is not less than cost
        if self.sale_price < self.cost:
            self.sale_price = self.cost
        super().save(*args, **kwargs)

        # Calculate total price
        self.total_price = self.quantity * self.sale_price
        super().save(*args, **kwargs)

class RefreshmentStockHistory(models.Model):
    REFRESHMENT_ACTION_CHOICES = [
        ('addition', 'Stock Addition'),
        ('deduction', 'Stock Deduction'),
        ('update', 'Stock Update'),
        ('sale', 'Sale'),
        ('adjustment', 'Manual Adjustment'),
    ]

    refreshment = models.ForeignKey(Refreshment, on_delete=models.CASCADE, related_name='stock_history')
    action = models.CharField(max_length=20, choices=REFRESHMENT_ACTION_CHOICES)
    quantity = models.IntegerField(help_text="Positive for addition, negative for deduction")
    previous_quantity = models.IntegerField(help_text="Quantity before this action")
    new_quantity = models.IntegerField(help_text="Quantity after this action")
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True, null=True, 
                               help_text="Reference ID (e.g., order number, adjustment ID)")

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Refreshment Stock History'

    def __str__(self):
        return f"{self.get_action_display()} - {self.refreshment.name} ({self.quantity:+})"


class ServiceSale(models.Model):
    PAID_STATUS_CHOICES = [
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid'),
    ]
    
    INVOICE_STATUS_CHOICES = [
        ('not_invoiced', 'Not Invoiced'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ]
    
    service_sale_number = models.CharField(max_length=20, unique=True,editable=False, null=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='service_sales')
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE, related_name='service_sales', help_text="Account holder/Payer")
    service_recipient = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE, related_name='services_received', null=True, blank=True, help_text="Who actually received the service (can be different from customer)")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_date = models.DateTimeField(auto_now_add=True)
    credit_notes = models.ManyToManyField('StoreCreditNote', blank=True, related_name='service_sales')
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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_service_sales')
    
    
    # Invoice and workflow tracking
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='not_invoiced')
    invoiced_at = models.DateTimeField(null=True, blank=True, help_text="When the sale was invoiced")
    cancelled_at = models.DateTimeField(null=True, blank=True, help_text="When the sale was cancelled")
    
    # Performance tracking fields
    sale_creation_time = models.DurationField(null=True, blank=True, help_text="Time taken to create the sale")
    payment_processing_time = models.DurationField(null=True, blank=True, help_text="Time taken to process payment")
    total_workflow_time = models.DurationField(null=True, blank=True, help_text="Total time from sale creation to payment completion")
    
    # Queue and Service timing fields
    queue_start_time = models.DateTimeField(null=True, blank=True, help_text="When customer entered the queue")
    service_start_time = models.DateTimeField(null=True, blank=True, help_text="When service actually started")
    service_end_time = models.DateTimeField(null=True, blank=True, help_text="When service was completed")
    queue_waiting_time = models.DurationField(null=True, blank=True, help_text="Time spent waiting in queue")
    service_duration = models.DurationField(null=True, blank=True, help_text="Total time spent on service")
    slot_number = models.PositiveIntegerField(null=True, blank=True, help_text="Queue slot number for this customer")

    @property
    def actual_recipient(self):
        """Get who actually received the service"""
        return self.service_recipient if self.service_recipient else self.customer
    
    @property
    def is_guardian_transaction(self):
        """Check if this is a guardian paying for a dependent's service"""
        return self.service_recipient and self.service_recipient != self.customer
    
    @property
    def transaction_description(self):
        """Get a clear description of the transaction"""
        if self.is_guardian_transaction:
            return f"Service for {self.service_recipient.name} (Paid by {self.customer.name})"
        return f"Service for {self.customer.name}"
    
    def can_authorize_service(self):
        """Check if the customer can authorize this service"""
        if not self.service_recipient:
            return self.customer.can_make_purchases
        
        return self.customer.can_authorize_for(self.service_recipient)
    
    def __str__(self):
        if self.is_guardian_transaction:
            return f"Sale #{self.id} - {self.service_recipient.name} (via {self.customer.name})"
        return f"Sale #{self.id} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        # Check if this is an existing instance being updated
        if self.pk:
            old_instance = ServiceSale.objects.get(pk=self.pk)
            paid_status_changed = (old_instance.paid_status != self.paid_status)
        else:
            paid_status_changed = False

        # Automatically generate a unique number if not already set
        if not self.service_sale_number:
            self.service_sale_number = self.generate_service_sale_number()

        # Save the instance first
        super().save(*args, **kwargs)

        # If paid_status changed to 'paid', the post_save signal will handle the cash drawer transaction
        if paid_status_changed and self.paid_status == 'paid':
            # The signal will handle the rest
            pass

    def generate_service_sale_number(self):
        """Generate a unique number based on store, date, and random digits."""
        store_prefix = self.store.name[:2].upper()  # First two letters of the store name
        date_part = timezone.now().strftime('%m%y') if self.sale_date else ''
        random_part = f"{random.randint(1000, 9999)}"  # Random 4-digit number
        return f"{store_prefix}-{date_part}-{random_part}"

    def calculate_total(self):
        total = sum(item.total_price for item in self.service_sale_items.all())
        # Accessory items are not included in totals
        total += sum(item.total_price for item in self.product_sale_items.all())
        total += sum(item.total_price for item in self.refreshment_sale_items.all()) 
        
        self.total_amount = total
        
        # Sum payments from the Payment model
        self.paid_amount = self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        
        self.balance = total - self.paid_amount
        self.paid_status = 'paid' if self.balance <= 0 else 'not_paid'
        self.save()

    def _deduct_refreshment_stock(self):
        """Deduct refreshment stock for all refreshment items in the sale."""
        for refreshment_item in self.refreshment_sale_items.all():
            try:
                refreshment_item._update_refreshment_stock()
            except ValueError as e:
                raise ValueError(f"Failed to update refreshment stock: {str(e)}")
        
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
        
    def mark_as_paid(self, reference=None):
        """Finalize a sale that is fully paid: set status, create commissions, and deduct inventories.
        Safe to call multiple times; inventory deductions are idempotent using adjustment existence checks.
        """
        if self.balance <= 0:
            with transaction.atomic():
                # Ensure status is paid
                if self.paid_status != 'paid':
                    self.paid_status = 'paid'
                    self.save(update_fields=['paid_status'])

                # Create commissions
                self.create_service_commissions()
                self.create_product_commissions()

                try:
                    # Prevent double-deduction by checking for prior adjustments referencing this sale
                    accessory_already_deducted = StoreInventoryAdjustment.objects.filter(
                        accessory_inventory__store=self.store,
                        adjustment='sale',
                        reason__icontains=f"ServiceSale #{self.id}"
                    ).exists()

                    product_already_deducted = InventoryAdjustment.objects.filter(
                        store_inventory__store=self.store,
                        adjustment_reason__icontains=f"ServiceSale #{self.id}"
                    ).exists()

                    refreshment_already_deducted = RefreshmentStockHistory.objects.filter(
                        refreshment__store=self.store,
                        reference=f"ServiceSale-{self.id}"
                    ).exists()

                    if not accessory_already_deducted:
                        self._deduct_accessory_inventory()

                    if not product_already_deducted:
                        self._deduct_product_inventory()

                    if not refreshment_already_deducted:
                        self._deduct_refreshment_stock()

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
        """Create an invoice for this sale and update invoice status."""
        from django.utils import timezone
        
        if self.invoice_status == 'cancelled':
            raise ValueError("Cannot create invoice for cancelled sale")
            
        if self.invoice_status == 'invoiced':
            # Return existing invoice
            return getattr(self, 'invoice', None)
            
        # Create new invoice
        invoice = ServiceSaleInvoice.objects.create(sale=self, total_amount=self.total_amount)
        
        # Update invoice status and timestamp
        self.invoice_status = 'invoiced'
        self.invoiced_at = timezone.now()
        self.save()
        
        return invoice
    
    def cancel_sale(self, reason=None):
        """Cancel the sale and prevent further processing."""
        from django.utils import timezone
        
        if self.paid_status == 'paid':
            raise ValueError("Cannot cancel a paid sale")
            
        self.invoice_status = 'cancelled'
        self.cancelled_at = timezone.now()
        if reason:
            self.payment_remarks = f"Cancelled: {reason}"
        self.save()
    
    def can_process_payment(self):
        """Check if payment can be processed for this sale."""
        return self.invoice_status == 'invoiced' and self.paid_status != 'paid'
    
    def get_workflow_status(self):
        """Get human-readable workflow status."""
        if self.invoice_status == 'cancelled':
            return 'Cancelled'
        elif self.invoice_status == 'not_invoiced':
            return 'Pending Invoice'
        elif self.invoice_status == 'invoiced' and self.paid_status == 'not_paid':
            return 'Awaiting Payment'
        elif self.paid_status == 'paid':
            return 'Completed'
        else:
            return 'Unknown'
    
    def get_timing_summary(self):
        """Get a summary of timing metrics."""
        return {
            'sale_creation_time': self.sale_creation_time,
            'payment_processing_time': self.payment_processing_time,
            'total_workflow_time': self.total_workflow_time,
            'queue_waiting_time': self.queue_waiting_time,
            'service_duration': self.service_duration,
            'sale_date': self.sale_date,
            'queue_start_time': self.queue_start_time,
            'service_start_time': self.service_start_time,
            'service_end_time': self.service_end_time,
            'invoiced_at': self.invoiced_at,
            'cancelled_at': self.cancelled_at,
        }
    
    def start_queue_timer(self):
        """Start the queue timer when customer enters the queue and assign slot number"""
        from django.utils import timezone
        if not self.queue_start_time:
            self.queue_start_time = timezone.now()
            
            # Assign slot number if not already assigned
            if not self.slot_number:
                # Get the next slot number for this store today
                today = timezone.now().date()
                last_slot = ServiceSale.objects.filter(
                    store=self.store,
                    queue_start_time__date=today,
                    slot_number__isnull=False
                ).aggregate(max_slot=models.Max('slot_number'))['max_slot'] or 0
                
                self.slot_number = last_slot + 1
            
            self.save(update_fields=['queue_start_time', 'slot_number'])
            return True
        return False
    
    def start_service_timer(self):
        """Start the service timer when work begins on the customer"""
        from django.utils import timezone
        now = timezone.now()
        
        # Calculate queue waiting time if not already calculated
        if self.queue_start_time and not self.queue_waiting_time:
            self.queue_waiting_time = now - self.queue_start_time
        
        # Set service start time
        if not self.service_start_time:
            self.service_start_time = now
            self.save(update_fields=['service_start_time', 'queue_waiting_time'])
            return True
        return False
    
    def end_service_timer(self):
        """End the service timer when service is completed (usually on payment)"""
        from django.utils import timezone
        now = timezone.now()
        
        # Set service end time and calculate duration
        if self.service_start_time and not self.service_end_time:
            self.service_end_time = now
            self.service_duration = now - self.service_start_time
            self.save(update_fields=['service_end_time', 'service_duration'])
            return True
        return False
    
    def get_service_status(self):
        """Get the current service status based on timing"""
        if not self.queue_start_time:
            return 'created'
        elif not self.service_start_time:
            return 'in_queue'
        elif not self.service_end_time:
            return 'in_progress'
        else:
            return 'completed'
    
    def get_current_waiting_time(self):
        """Get current waiting time if customer is still in queue"""
        if self.queue_start_time and not self.service_start_time:
            from django.utils import timezone
            return timezone.now() - self.queue_start_time
        return self.queue_waiting_time
    
    def get_current_service_time(self):
        """Get current service time if service is in progress"""
        if self.service_start_time and not self.service_end_time:
            from django.utils import timezone
            return timezone.now() - self.service_start_time
        return self.service_duration
    
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
        # Calculate total price - handle None price
        service_price = self.service.service.price or 0
        self.total_price = self.quantity * service_price
        print(f"DEBUG: Total Price calculated: {self.total_price}")
        
        # First save the service sale item
        super().save(*args, **kwargs)

        # Recalculate the total for the related sale
        self.sale.calculate_total()
        
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
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
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
        # Handle None price
        return self.product.product.price or 0
    
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
        # Ensure unit_price is not None
        if unit_price is None:
            unit_price = 0
            
        if not self.total_price or kwargs.get('force_recalculate', False):
            self.total_price = self.quantity * unit_price

        super().save(*args, **kwargs)
        
        # Calculate commission if staff is assigned and sale is paid
        if self.sale.paid_status == 'paid':
            self.calculate_and_create_commission()
        
        # Recalculate the total for the related sale
        self.sale.calculate_total()
    
    def __str__(self):
        return f"{self.quantity} x {self.product.product.product_name} for Sale #{self.sale.id}"


#RefreshmentItem
class RefreshmentSaleItem(models.Model):
    """
    Model for tracking refreshments sold as part of a service sale.
    """
    sale = models.ForeignKey(ServiceSale, on_delete=models.CASCADE, related_name='refreshment_sale_items')
    refreshment = models.ForeignKey('Refreshment', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Recalculate the total for the related sale
        self.sale.calculate_total()
        
        # If sale is paid, update refreshment stock
        if self.sale.paid_status == 'paid':
            self._update_refreshment_stock()
    
    def _update_refreshment_stock(self):
        """Update refreshment stock and create stock history record"""
        with transaction.atomic():
            # Get the refreshment with select_for_update to prevent race conditions
            refreshment = Refreshment.objects.select_for_update().get(pk=self.refreshment.pk)
            
            # Check if stock is sufficient
            if refreshment.quantity < self.quantity:
                raise ValueError(f"Insufficient stock for {refreshment.name}. Available: {refreshment.quantity}, Requested: {self.quantity}")
            
            # Update stock
            previous_quantity = refreshment.quantity
            refreshment.quantity -= self.quantity
            refreshment.save()
            
            # Create stock history record
            RefreshmentStockHistory.objects.create(
                refreshment=refreshment,
                action='sale',
                quantity=-self.quantity,  # Negative for deduction
                previous_quantity=previous_quantity,
                new_quantity=refreshment.quantity,
                notes=f"Sold in ServiceSale #{self.sale.id}",
                created_by=self.sale.store.manager,  # Assuming store has a manager field
                reference=f"ServiceSale-{self.sale.id}"
            )
    
    def __str__(self):
        return f"{self.quantity} x {self.refreshment.name} for Sale #{self.sale.id}"

    
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


#Payment tracking for service sales   
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('visa', 'Visa'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    sale = models.ForeignKey('ServiceSale', on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.amount} via {self.payment_method} for Sale #{self.sale.id}"


class ProductSalePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('visa', 'Visa'),
        ('bank_transfer', 'Bank Transfer'),
        ('mixed', 'Mixed'),
    ]

    sale = models.ForeignKey('StoreProductSale', on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who created the payment")

    def __str__(self):
        return f"{self.amount} via {self.payment_method} for Product Sale #{self.sale.id}"


class ProductSaleReceipt(models.Model):
    """
    Receipt model for product sales - similar to StoreSaleReceipt but for product-only sales
    """
    receipt_number = models.CharField(max_length=20, unique=True, blank=True, help_text="Unique receipt number")
    sale = models.OneToOneField('StoreProductSale', on_delete=models.CASCADE, related_name='receipt')
    
    # Customer information
    customer_name = models.CharField(max_length=200, help_text="Customer name for receipt")
    customer_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Customer phone number")
    customer_email = models.EmailField(blank=True, null=True, help_text="Customer email address")
    
    # Receipt details
    receipt_date = models.DateTimeField(auto_now_add=True, help_text="Date and time receipt was generated")
    total_due = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount due for the sale")
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount paid so far")
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, help_text="Remaining balance to be paid")
    
    # Receipt status
    is_paid = models.BooleanField(default=False, help_text="Whether the receipt is fully paid")
    is_cancelled = models.BooleanField(default=False, help_text="Whether the receipt is cancelled")
    
    # Store and staff information
    store = models.ForeignKey('Store', on_delete=models.CASCADE, help_text="Store where the sale was made")
    staff_name = models.CharField(max_length=200, help_text="Staff member who handled the sale")
    
    # Additional information
    notes = models.TextField(blank=True, help_text="Additional notes for the receipt")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who created the receipt")
    
    class Meta:
        ordering = ['-receipt_date']
        verbose_name = "Product Sale Receipt"
        verbose_name_plural = "Product Sale Receipts"
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.customer_name} - UGX {self.total_due:,.0f}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()
        
        # Auto-populate fields from sale if not provided
        if self.sale:
            if not self.customer_name:
                self.customer_name = f"{self.sale.customer.first_name} {self.sale.customer.last_name}"
            if not self.customer_phone and self.sale.customer.phone:
                self.customer_phone = self.sale.customer.phone
            if not self.customer_email and self.sale.customer.email:
                self.customer_email = self.sale.customer.email
            if not self.store:
                self.store = self.sale.store
            if not self.staff_name:
                self.staff_name = f"{self.sale.store.manager.first_name} {self.sale.store.manager.last_name}"
            
            # Calculate totals from sale
            self.total_due = self.sale.total_amount
            self.total_paid = self.sale.paid_amount or 0
            self.balance_due = self.sale.balance or self.total_due
            self.is_paid = self.sale.paid_status == 'paid'
        
        super().save(*args, **kwargs)
    
    def generate_receipt_number(self):
        """Generate a unique receipt number"""
        from datetime import datetime
        import uuid
        
        current_date = datetime.now().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4()).replace('-', '').upper()[:6]
        return f"PR{current_date}{unique_id}"
    
    def update_payment_status(self):
        """Update payment status based on current payments"""
        if self.sale:
            self.total_paid = self.sale.paid_amount or 0
            self.balance_due = self.sale.balance or self.total_due
            self.is_paid = self.sale.paid_status == 'paid'
            self.save(update_fields=['total_paid', 'balance_due', 'is_paid'])



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
    """Store Sale Order - Initial order capture"""
    VAT_RATE = Decimal('0.18')  # Default VAT rate (18%)
    WITHHOLDING_TAX_RATE = Decimal(0.06)  # Default withholding tax rate (6%)
    
    # Order Information
    order_number = models.CharField(max_length=20, unique=True, help_text="Unique order number", null=True, blank=True)
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    
    # Order Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial fields
    subtotal = models.DecimalField(max_length=10, max_digits=10, decimal_places=2, default=0, help_text="Subtotal before tax")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Tax amount")
    withholding_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Withholding tax amount")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total order amount")
    
    # Tax and billing
    tax_code = models.ForeignKey('TaxCode', on_delete=models.SET_NULL, null=True, blank=True)
    withhold_tax = models.BooleanField(default=False)
    billing_address = models.TextField(blank=True, null=True)
    
    # Additional fields
    description = models.TextField(blank=True, null=True, help_text="Order description or notes")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_date']
        verbose_name = "Store Sale Order"
        verbose_name_plural = "Store Sale Orders"

    def __str__(self):
        return f"Order {self.order_number} - {self.customer.first_name}"

    def save(self, *args, **kwargs):
        # Auto-generate order number if not provided
        if not self.order_number:
            from datetime import datetime
            import uuid
            current_date = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4()).replace('-', '').upper()[:6]
            self.order_number = f"ORD{current_date}{unique_id}"
        
        # Auto-populate billing address from customer if not provided
        if not self.billing_address and self.customer:
            self.billing_address = f"{self.customer.address}\nPhone: {self.customer.phone}\nEmail: {self.customer.email}"
        
        # Calculate financial amounts
        self.calculate_financial_amounts()
        
        super().save(*args, **kwargs)

    def calculate_financial_amounts(self):
        """Calculate and set all financial amounts for the order"""
        try:
            sale_items = self.saleitem_set.all()
            subtotal = sum(item.quantity * item.chosen_price for item in sale_items if item.chosen_price is not None)
            self.subtotal = Decimal(subtotal)
            
            # Calculate tax amount
            if self.tax_code:
                self.tax_amount = self.tax_code.calculate_tax_amount(self.subtotal)
            else:
                self.tax_amount = Decimal('0.00')
            
            # Calculate withholding tax
            if self.withhold_tax:
                self.withholding_tax = (self.subtotal + self.tax_amount) * self.WITHHOLDING_TAX_RATE
            else:
                self.withholding_tax = Decimal('0.00')
            
            # Calculate total amount
            self.total_amount = self.subtotal + self.tax_amount + self.withholding_tax
            
        except (TypeError, ValueError) as e:
            print(f"Error in calculate_financial_amounts: {e}")
            self.subtotal = Decimal('0.00')
            self.tax_amount = Decimal('0.00')
            self.withholding_tax = Decimal('0.00')
            self.total_amount = Decimal('0.00')

    @property
    def can_create_invoice(self):
        """Check if order can be invoiced"""
        return self.status in ['confirmed'] and self.total_amount > 0

    @property
    def has_invoice(self):
        """Check if order has been invoiced"""
        return hasattr(self, 'sales_invoice')

    def create_invoice(self):
        """Create a sales invoice for this order"""
        if not self.can_create_invoice:
            raise ValueError("Order cannot be invoiced")
        
        if self.has_invoice:
            raise ValueError("Order already has an invoice")
        
        # Create the invoice with 'sent' status
        invoice = SalesInvoice.objects.create(
            store_sale=self,
            invoice_number=f"INV-{self.order_number}",
            customer=self.customer,
            invoice_date=timezone.now(),
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            withholding_tax=self.withholding_tax,
            total_amount=self.total_amount,
            tax_code=self.tax_code,
            billing_address=self.billing_address,
            status='sent',  # Set status to 'sent' immediately
            created_by=self.created_by
        )
        
        # Update order status
        self.status = 'invoiced'
        self.save()
        
        return invoice

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
                # No price configured in the selected group - this should be handled by form validation
                raise ValueError(f"No price configured for {self.product.product.product.product_name} in price group '{self.price_group.name}'. Please contact Finance to set up pricing.")
        else:
            # No price group selected - this should be handled by form validation
            raise ValueError(f"Price group is required for {self.product.product.product.product_name}. Please select a pricing group.")

        # Calculate the total price
        self.total_price = (self.quantity * self.chosen_price) if self.chosen_price else 0
        super().save(*args, **kwargs)  # Call parent save method
        
class StoreSalePayment(models.Model):
    """Track customer payments for store sales with Chart of Accounts integration"""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('cheque', 'Cheque'),
        ('credit_card', 'Credit Card'),
        ('other', 'Other'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Payment details
    receipt = models.ForeignKey('StoreSaleReceipt', on_delete=models.CASCADE, related_name='payments')
    payment_reference = models.CharField(max_length=50, unique=True, help_text="Unique payment reference number")
    payment_date = models.DateTimeField(auto_now_add=True, help_text="Date and time of payment")
    
    # Financial details
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount paid by customer")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, help_text="Method of payment")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Chart of Accounts integration
    revenue_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.PROTECT, 
                                       related_name='store_sale_payments', 
                                       help_text="Revenue account to credit (e.g., Sales Revenue)")
    bank_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.PROTECT, 
                                    related_name='store_sale_bank_payments', 
                                    help_text="Bank account to debit (e.g., Bank Account)")
    
    # Customer and receipt details
    customer_name = models.CharField(max_length=200, help_text="Customer name for reference")
    receipt_number = models.CharField(max_length=20, help_text="Receipt number being paid")
    
    # Additional details
    transaction_id = models.CharField(max_length=100, blank=True, null=True, 
                                    help_text="External transaction ID (bank transfer, mobile money, etc.)")
    notes = models.TextField(blank=True, help_text="Additional payment notes")
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   help_text="User who received the payment")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = "Store Sale Payment"
        verbose_name_plural = "Store Sale Payments"
    
    def __str__(self):
        return f"Payment {self.payment_reference} - {self.customer_name} - UGX {self.amount_paid:,.0f}"
    
    def save(self, *args, **kwargs):
        # Auto-generate payment reference if not provided
        if not self.payment_reference:
            from datetime import datetime
            import uuid
            current_date = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4()).replace('-', '').upper()[:6]
            self.payment_reference = f"PAY{current_date}{unique_id}"
        
        # Auto-populate customer and receipt details
        if not self.customer_name and self.receipt:
            self.customer_name = self.receipt.customer_name
        if not self.receipt_number and self.receipt:
            self.receipt_number = self.receipt.receipt_number
        
        super().save(*args, **kwargs)
        
        # Update receipt payment status after payment is completed
        if self.payment_status == 'completed':
            self.update_receipt_payment_status()
    
    def update_receipt_payment_status(self):
        """Update the receipt payment status based on total payments"""
        if not self.receipt:
            return
        
        total_paid = sum(payment.amount_paid for payment in self.receipt.payments.filter(payment_status='completed'))
        receipt_total = self.receipt.total_due
        
        if total_paid >= receipt_total:
            self.receipt.payment_status = 'paid'
        elif total_paid > 0:
            self.receipt.payment_status = 'partial'
        else:
            self.receipt.payment_status = 'pending'
        
        self.receipt.save()
    
    @property
    def payment_method_display(self):
        """Get human-readable payment method"""
        return dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method, self.payment_method)
    
    @property
    def is_completed(self):
        """Check if payment is completed"""
        return self.payment_status == 'completed'
    
    @property
    def can_be_reversed(self):
        """Check if payment can be reversed"""
        return self.payment_status == 'completed' and self.payment_date.date() >= (timezone.now().date() - timedelta(days=30))

class SalesInvoice(models.Model):
    """Sales Invoice - Formal billing document created from Store Sale Order"""
    PAYMENT_DURATION = timedelta(days=45)  # Default payment duration (45 days)
    
    # Invoice Information
    store_sale = models.OneToOneField(StoreSale, on_delete=models.CASCADE, related_name='sales_invoice')
    invoice_number = models.CharField(max_length=20, unique=True, help_text="Unique invoice number")
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE)
    invoice_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(help_text="Payment due date")
    
    # Invoice Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('overdue', 'Overdue'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Subtotal before tax")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Tax amount")
    withholding_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Withholding tax amount")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total invoice amount")
    
    # Tax and billing
    tax_code = models.ForeignKey('TaxCode', on_delete=models.SET_NULL, null=True, blank=True)
    billing_address = models.TextField(blank=True, null=True)
    
    # Payment tracking
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount paid")
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Remaining balance")
    
    # Additional fields
    notes = models.TextField(blank=True, help_text="Invoice notes")
    terms_conditions = models.TextField(blank=True, help_text="Payment terms and conditions")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name = "Sales Invoice"
        verbose_name_plural = "Sales Invoices"

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.first_name}"

    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not provided
        if not self.invoice_number:
            from datetime import datetime
            import uuid
            current_date = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4()).replace('-', '').upper()[:6]
            self.invoice_number = f"INV{current_date}{unique_id}"
        
        # Set due date if not provided
        if not self.due_date:
            from datetime import date
            self.due_date = date.today() + self.PAYMENT_DURATION
        
        # Calculate balance due
        self.balance_due = self.total_amount - self.amount_paid
        
        # Update status based on payment
        if self.balance_due <= 0:
            self.status = 'paid'
        elif self.is_overdue:
            self.status = 'overdue'
        
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        from datetime import date
        return self.balance_due > 0 and date.today() > self.due_date

    @property
    def days_overdue(self):
        """Calculate days overdue"""
        from datetime import date
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    @property
    def payment_status_display(self):
        """Get payment status with overdue indicator"""
        if self.is_overdue:
            return f"Overdue ({self.days_overdue} days)"
        elif self.balance_due <= 0:
            return "Paid"
        elif self.amount_paid > 0:
            return f"Partially Paid (UGX {self.amount_paid:,.0f})"
        else:
            return "Unpaid"

    @property
    def can_create_receipt(self):
        """Check if invoice can have receipts created"""
        return self.status in ['sent', 'overdue'] and self.balance_due > 0

    @property
    def has_receipts(self):
        """Check if invoice has receipts"""
        return self.receipts.exists()

    def create_receipt(self, amount_paid, payment_method, **kwargs):
        """Create a receipt for payment on this invoice"""
        if not self.can_create_receipt:
            raise ValueError("Invoice cannot have receipts created")
        
        if amount_paid > self.balance_due:
            raise ValueError("Payment amount exceeds balance due")
        
        # Create receipt
        receipt = StoreSaleReceipt.objects.create(
            sales_invoice=self,
            receipt_number=f"RCP-{self.invoice_number}-{timezone.now().strftime('%Y%m%d%H%M')}",
            customer_name=f"{self.customer.first_name} {self.customer.last_name}",
            customer_phone=self.customer.phone,
            customer_email=self.customer.email,
            total_due=amount_paid,
            payment_method=payment_method,
            **kwargs
        )
        
        # Update invoice payment
        self.amount_paid += amount_paid
        self.save()
        
        return receipt
        

class StoreSaleReceipt(models.Model):
    """Sales Receipt - Payment tracking document created from Sales Invoice"""
    
    # Receipt Information
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='receipts', null=True, blank=True)
    receipt_number = models.CharField(max_length=20, unique=True, help_text="Unique receipt number for payment reference")
    receipt_date = models.DateTimeField(help_text="Date when receipt was created",default=timezone.now)
    
    # Customer Information
    customer_name = models.CharField(max_length=200, help_text="Customer name for payment reference", null=True, blank=True)
    customer_phone = models.CharField(max_length=20, help_text="Customer contact for payment follow-up", blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True, help_text="Customer email for payment notifications")
    
    # Payment Information
    total_due = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount paid in this receipt")
    payment_method = models.CharField(max_length=20, choices=StoreSalePayment.PAYMENT_METHOD_CHOICES, help_text="Method of payment", null=True, blank=True)
    
    # Chart of Accounts Integration
    receiving_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.PROTECT, 
                                        related_name='receipts_received', 
                                        help_text="Account to receive payment (e.g., Cash, Bank)", null=True, blank=True)
    accounts_receivable_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.PROTECT, 
                                                   related_name='receipts_receivable', 
                                                   help_text="Accounts Receivable account to credit", null=True, blank=True)
    
    # Payment Status
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Payment'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('overdue', 'Overdue'),
    ], default='paid', help_text="Current payment status")
    
    # Additional fields
    notes = models.TextField(blank=True, help_text="Additional notes for payment processing")
    reference_number = models.CharField(max_length=50, blank=True, help_text="External reference number")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-receipt_date']
        verbose_name = "Sales Receipt"
        verbose_name_plural = "Sales Receipts"

    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.customer_name}"

    def save(self, *args, **kwargs):
        # Auto-generate receipt number if not provided
        if not self.receipt_number:
            from datetime import datetime
            import uuid
            current_date = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4()).replace('-', '').upper()[:6]
            self.receipt_number = f"RCP{current_date}{unique_id}"
        
        super().save(*args, **kwargs)

    @property
    def invoice_number(self):
        """Get the related invoice number"""
        return self.sales_invoice.invoice_number

    @property
    def order_number(self):
        """Get the related order number"""
        return self.sales_invoice.store_sale.order_number
        

class RawMaterialPrice(models.Model):
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=5)
    effective_date = models.DateTimeField(default=timezone.now)
    is_current = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.raw_material} - {self.supplier}: {self.price} (as of {self.effective_date.strftime('%Y-%m-%d')})"
    
    def save(self, *args, **kwargs):
        # Set all other prices for this material-supplier combination as not current
        if self.is_current:
            RawMaterialPrice.objects.filter(
                raw_material=self.raw_material,
                supplier=self.supplier,
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_current_price(cls, raw_material, supplier):
        try:
            return cls.objects.get(
                raw_material=raw_material,
                supplier=supplier,
                is_current=True
            ).price
        except cls.DoesNotExist:
            return None

class PriceAlert(models.Model):
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    threshold_price = models.DecimalField(max_digits=12, decimal_places=5)
    is_above = models.BooleanField(default=True, 
        help_text="Alert when price goes above (checked) or below threshold")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

# Add this after the RawMaterialPrice model and before the PriceAlert model

class TaxCode(models.Model):
    """Tax codes for different tax rates and types"""
    code = models.CharField(max_length=10, unique=True, help_text="Tax code (e.g., VAT18, VAT0)")
    name = models.CharField(max_length=100, help_text="Tax name (e.g., VAT 18%, Zero Rated)")
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Tax rate percentage (e.g., 18.00 for 18%)")
    is_active = models.BooleanField(default=True, help_text="Whether this tax code is active")
    description = models.TextField(blank=True, help_text="Additional description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.rate}%)"

    @property
    def rate_decimal(self):
        """Return rate as decimal (e.g., 0.18 for 18%)"""
        return self.rate / 100

    def calculate_tax_amount(self, base_amount):
        """Calculate tax amount for a given base amount"""
        return (base_amount * self.rate_decimal).quantize(Decimal('0.01'))

    def calculate_total_with_tax(self, base_amount):
        """Calculate total amount including tax"""
        return (base_amount * (1 + self.rate_decimal)).quantize(Decimal('0.01'))

    def calculate_base_amount_from_total(self, total_amount):
        """Calculate base amount from tax-inclusive total"""
        return (total_amount / (1 + self.rate_decimal)).quantize(Decimal('0.01'))

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
    total_cost = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    
    # Tax settings
    amounts_are_tax_inclusive = models.BooleanField(default=False, help_text="If checked, amounts include tax")
    default_tax_code = models.ForeignKey(TaxCode, on_delete=models.SET_NULL, null=True, blank=True, 
                                       help_text="Default tax code for items in this requisition")
    
    def __str__(self):
        return f"Requisition {self.requisition_no} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.requisition_no:
            self.generate_requisition_no()
        super().save(*args, **kwargs)

    def generate_requisition_no(self):
        # Get the current date
        current_date = timezone.now().date()
        date_str = current_date.strftime('%Y%m%d')
        
        # Get the count of requisitions for today
        today_requisitions = Requisition.objects.filter(
            created_at__date=current_date
        ).count()
        
        # Generate the requisition number
        self.requisition_no = f"REQ{date_str}{today_requisitions + 1:03d}"

    def calculate_total_cost(self):
        # Sum the total cost of all requisition items plus expense items
        items_total = sum(item.total_cost for item in self.requisitionitem_set.all())
        expenses_total = sum(expense.amount for expense in self.expense_items.all())
        return items_total + expenses_total

    def calculate_total_tax(self):
        """Calculate total tax amount for all items"""
        return sum(item.tax_amount for item in self.requisitionitem_set.all())

    def calculate_subtotal_before_tax(self):
        """Calculate subtotal before tax"""
        return sum(item.subtotal_before_tax for item in self.requisitionitem_set.all())

    def calculate_grand_total_with_tax(self):
        """Calculate grand total including tax"""
        return self.calculate_subtotal_before_tax() + self.calculate_total_tax()

    def debug_total_calculation(self):
        """Debug method to understand total calculation"""
        items = list(self.requisitionitem_set.all())
        expenses = list(self.expense_items.all())
        
        print(f"Requisition {self.requisition_no} calculation:")
        print(f"Items count: {len(items)}")
        for item in items:
            print(f"  - {item.raw_material.name}: {item.quantity} × {item.price_per_unit} = {item.total_cost}")
        
        print(f"Expenses count: {len(expenses)}")
        for expense in expenses:
            print(f"  - {expense.expense_account.account_name}: {expense.amount}")
        
        items_total = sum(item.total_cost for item in items)
        expenses_total = sum(expense.amount for expense in expenses)
        total = items_total + expenses_total
        
        print(f"Items total: {items_total}")
        print(f"Expenses total: {expenses_total}")
        print(f"Grand total: {total}")
        print(f"Stored total_cost: {self.total_cost}")
        
        return {
            'items_total': items_total,
            'expenses_total': expenses_total,
            'calculated_total': total,
            'stored_total': self.total_cost
        }

    @property
    def items_subtotal(self):
        return sum(item.total_cost for item in self.requisitionitem_set.all())
            
    @property
    def expenses_total(self):
        return sum(expense.amount for expense in self.expense_items.all())

    @property
    def items_subtotal(self):
        return sum(item.total_cost for item in self.requisitionitem_set.all())

    @property
    def extra_expenses_total(self):
        return sum(expense.amount for expense in self.expense_items.all())

    def recalculate_and_save_total(self):
        """Recalculate total cost and save it to the database"""
        old_total = self.total_cost
        self.total_cost = self.calculate_total_cost()
        self.save(update_fields=['total_cost'])
        
        print(f"Requisition {self.requisition_no}: Updated total from {old_total} to {self.total_cost}")
        return self.total_cost

# Choices for pricing source
PRICING_SOURCE_CHOICES = [
    ('system', 'System Price'),
    ('manual', 'Manual Price'),
]

# Choices for payment duration
PAYMENT_DURATION_CHOICES = [
    (10, '10 Days'),
    (15, '15 Days'),
    (30, '30 Days'),
    (45, '45 Days'),
    (60, '60 Days'),
]

# Choices for payment options
PAYMENT_OPTIONS_CHOICES = [
    ('cash', 'Cash'),
    ('bank', 'Bank Transfer'),
    ('mobile', 'Mobile Money'),
]

class RequisitionItem(models.Model):
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE, related_name='requisitionitem_set')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    delivered_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pricing_source = models.CharField(max_length=10, choices=PRICING_SOURCE_CHOICES, default='system')
    manual_price_reason = models.TextField(blank=True, null=True)
    system_price_at_creation = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_code = models.ForeignKey(TaxCode, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return f'{self.raw_material.name} - {self.quantity} units for {self.requisition.requisition_no}'

    def save(self, *args, **kwargs):
        # Set default tax code from requisition if not specified
        if not self.tax_code and self.requisition.default_tax_code:
            self.tax_code = self.requisition.default_tax_code
        
        # Set system price at creation for manual pricing
        if self.pricing_source == 'manual' and not self.system_price_at_creation:
            # Get the current system price for this raw material and supplier
            current_price = RawMaterialPrice.get_current_price(
                raw_material=self.raw_material,
                supplier=self.requisition.supplier
            )
            if current_price:
                self.system_price_at_creation = current_price
        
        super().save(*args, **kwargs)
    
    def update_supplier_price_on_delivery(self):
        """Update the supplier's price for this raw material when requisition is delivered"""
        if self.pricing_source == 'manual' and self.price_per_unit:
            # Update the supplier's price for this raw material
            RawMaterialPrice.objects.update_or_create(
                raw_material=self.raw_material,
                supplier=self.requisition.supplier,
                defaults={'price': self.price_per_unit}
            )
    
    @property
    def current_price(self):
        """Get the current system price for this raw material and supplier"""
        return RawMaterialPrice.get_current_price(
            raw_material=self.raw_material,
            supplier=self.requisition.supplier
        )
    
    @property
    def subtotal_before_tax(self):
        """Calculate subtotal before tax"""
        return self.quantity * self.price_per_unit
    
    @property
    def tax_amount(self):
        """Calculate tax amount based on tax code"""
        if not self.tax_code:
            return 0
        
        subtotal = self.subtotal_before_tax
        if self.requisition.amounts_are_tax_inclusive:
            # If tax inclusive, calculate tax from total
            return subtotal - self.tax_code.calculate_base_amount_from_total(subtotal)
        else:
            # If tax exclusive, add tax to subtotal
            return self.tax_code.calculate_tax_amount(subtotal)

    @property
    def total_cost(self):
        """Calculate total cost including tax"""
        subtotal = self.subtotal_before_tax
        if not self.tax_code:
            return subtotal
        
        if self.requisition.amounts_are_tax_inclusive:
            # If tax inclusive, the subtotal already includes tax
            return subtotal
        else:
            # If tax exclusive, add tax to subtotal
            return self.tax_code.calculate_total_with_tax(subtotal)

    @property
    def price_difference(self):
        """Calculate difference between manual and system price"""
        if self.pricing_source == 'manual' and self.system_price_at_creation:
            return self.price_per_unit - self.system_price_at_creation
        return 0
    
    @property
    def price_variance_percentage(self):
        """Calculate price variance as percentage"""
        if self.pricing_source == 'manual' and self.system_price_at_creation and self.system_price_at_creation > 0:
            return (self.price_difference / self.system_price_at_creation) * 100
        return 0
    

class RequisitionExpenseItem(models.Model):
    """Model for storing individual expense line items for requisitions"""
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE, related_name='expense_items')
    expense_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.CASCADE, 
                                       limit_choices_to={'account_type': 'expense'})
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, help_text="Description of the expense")
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now=True,blank=True,null=True)

    def __str__(self):
        return f"{self.expense_account} - {self.amount} for {self.requisition.requisition_no}"

    class Meta:
        ordering = ['created_at']
    
    
class LPO(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    lpo_number = models.CharField(max_length=50, unique=True, blank=True)
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invoice_document = models.FileField(upload_to='uploads/products/', null=True, blank=True)
    quotation_document = models.FileField(upload_to='uploads/products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_duration = models.IntegerField(choices=PAYMENT_DURATION_CHOICES, default=10)
    payment_option = models.CharField(max_length=20, choices=PAYMENT_OPTIONS_CHOICES, default='cash')
    
    # Payment tracking fields
    is_paid = models.BooleanField(default=False, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=0, default=0.00, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'LPO {self.lpo_number} for {self.requisition.requisition_no}'
    
    def save(self, *args, **kwargs):
        if not self.lpo_number:
            self.lpo_number = self.generate_lpo_number()
            
        # Ensure amount_paid and total_cost are not None before comparison
        req_total_cost = self.requisition.total_cost if self.requisition.total_cost is not None else 0
        current_amount_paid = self.amount_paid if self.amount_paid is not None else 0

        if current_amount_paid >= req_total_cost and req_total_cost > 0:
            self.is_paid = True
            if not self.payment_date: # Only set if not already set
                self.payment_date = timezone.now()
        else:
            self.is_paid = False
            # Do not clear payment_date if it was previously set and LPO is partially paid
        
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
            lpo_number = f"prod-po-{month}{year}-{random_number}"
        
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
        total_cost = self.requisition.total_cost or 0
        amount_paid = self.amount_paid or 0
        return max(0, total_cost - amount_paid)
    
    def debug_outstanding_balance(self):
        """Debug method to understand outstanding balance calculation"""
        req_total = self.requisition.total_cost
        req_debug = self.requisition.debug_total_calculation()
        
        print(f"\nLPO {self.lpo_number} outstanding balance calculation:")
        print(f"Requisition total_cost (stored): {req_total}")
        print(f"Amount paid: {self.amount_paid}")
        print(f"Outstanding balance: {self.outstanding_balance}")
        print(f"Requisition calculation details:")
        for key, value in req_debug.items():
            print(f"  {key}: {value}")
        
        return {
            'requisition_total': req_total,
            'amount_paid': self.amount_paid,
            'outstanding_balance': self.outstanding_balance,
            'requisition_debug': req_debug
        }

# Choices for pricing source
            
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
    
    # Chart of Accounts integration for proper accounting
    payment_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.CASCADE, 
                                      help_text="Account used for payment (e.g., Cash, Bank, Accounts Payable)",blank=True, null=True)
    
    # Legacy field for backward compatibility (will be deprecated)
    pay_by = models.CharField(max_length=20, choices=[('cash', 'Cash'),('bank', 'Bank Transfer'),('mobile', 'Mobile Money')],blank=True, null=True)
    
    voucher_notes = models.TextField(blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=[('full', 'Full Payment'), ('partial', 'Partial Payment')], default='partial')
    
    def __str__(self):
        return f"Voucher #{self.voucher_number} for LPO {self.lpo.lpo_number}"

    def save(self, *args, **kwargs):
        if not self.voucher_number:
            self.voucher_number = self.generate_voucher_number()
            
        # Set legacy pay_by field based on payment_account for backward compatibility
        if self.payment_account:
            account_name_lower = self.payment_account.account_name.lower()
            if 'cash' in account_name_lower:
                self.pay_by = 'cash'
            elif 'bank' in account_name_lower:
                self.pay_by = 'bank'
            elif 'mobile' in account_name_lower or 'money' in account_name_lower:
                self.pay_by = 'mobile'
            else:
                self.pay_by = 'bank'  # Default fallback
            
        if self.payment_type == 'full' and self.amount_paid < self.lpo.requisition.total_cost:
            raise ValueError("Cannot mark as 'Full Payment' if the amount is less than LPO total.")
        super().save(*args, **kwargs)

    def generate_voucher_number(self):
        current_date = timezone.now()
        # Use a combination of date, time, and random number to ensure uniqueness
        date_part = current_date.strftime('%Y%m%d')
        time_part = current_date.strftime('%H%M%S')
        random_part = random.randint(1000, 9999)
        
        voucher_number = f"PROD-PV-{date_part}-{time_part}-{random_part}"
        
        # Ensure the generated number is unique
        while PaymentVoucher.objects.filter(voucher_number=voucher_number).exists():
            random_part = random.randint(1000, 9999)
            voucher_number = f"PROD-PV-{date_part}-{time_part}-{random_part}"
        
        return voucher_number

    @property
    def payment_method_display(self):
        """Return a user-friendly display of the payment method"""
        if self.payment_account:
            return f"{self.payment_account.account_code} - {self.payment_account.account_name}"
        return self.get_pay_by_display() if self.pay_by else "Unknown"

# Signal to update LPO on PaymentVoucher save
@receiver(post_save, sender=PaymentVoucher)
def update_lpo_payment(sender, instance, **kwargs):
    # Update the LPO payment status when a payment voucher is created
    lpo = instance.lpo
    lpo.amount_paid = lpo.paymentvoucher_set.aggregate(total=models.Sum('amount_paid'))['total'] or 0
    lpo.is_paid = lpo.amount_paid >= lpo.requisition.total_cost  # Fixed: access through requisition
    if lpo.is_paid:
        lpo.payment_date = timezone.now()
    lpo.save()

@receiver(post_save, sender=RawMaterialInventory)
def update_raw_material_quantity_on_inventory_change(sender, instance, **kwargs):
    """Automatically update raw material quantity when inventory adjustment is made"""
    try:
        instance.raw_material.update_quantity()
    except Exception as e:
        # Log the error but don't prevent the save
        print(f"Error updating raw material quantity: {e}")

class StaffProductCommission(models.Model):
    staff = models.ForeignKey('POSMagicApp.Staff', on_delete=models.CASCADE, related_name='product_commissions')
    product_sale_item = models.OneToOneField(ProductSaleItem, on_delete=models.CASCADE, related_name='commission')
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Commission for {self.staff.first_name} - {self.product_sale_item}"

class SavedCommissionReport(models.Model):
    """Saved commission reports for future reference"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    staff = models.ForeignKey('POSMagicApp.Staff', on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    report_data = models.JSONField()  # Store the detailed report data
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    @property
    def period_name(self):
        if self.start_date.month == self.end_date.month and self.start_date.year == self.end_date.year:
            return self.start_date.strftime('%B %Y')
        return f"{self.start_date} to {self.end_date}"

# Signal to update supplier prices when requisition is delivered
@receiver(post_save, sender=Requisition)
def update_supplier_prices_on_delivery(sender, instance, **kwargs):
    """Update supplier prices when requisition status changes to 'delivered'"""
    if instance.status == 'delivered':
        # Update supplier prices for all items with manual pricing
        updated_count = 0
        for item in instance.requisitionitem_set.all():
            if item.update_supplier_price_on_delivery():
                updated_count += 1
        
        if updated_count > 0:
            print(f"Updated {updated_count} supplier prices for requisition {instance.requisition_no}")


# Choices for pricing source

# Register models with auditlog for audit tracking
from auditlog.registry import auditlog

# Register key models for audit tracking
# auditlog.register(Supplier)
# auditlog.register(RawMaterial) 
# Temporarily disable auditlog registrations due to changes_text constraint issues
# This can be re-enabled once auditlog version compatibility is resolved

# auditlog.register(Requisition)
# auditlog.register(RequisitionItem)
# auditlog.register(RequisitionExpenseItem)
# auditlog.register(LPO)
# auditlog.register(PaymentVoucher)
# auditlog.register(RawMaterialPrice)
# auditlog.register(TaxCode)
# auditlog.register(GoodsReceivedNote)
# auditlog.register(Production)
# auditlog.register(ManufactureProduct)
# auditlog.register(StoreSalePayment)

class CreditNote(models.Model):
    """Credit Note - Document for returns, refunds, and invoice adjustments"""
    
    CREDIT_NOTE_TYPES = [
        ('return', 'Customer Return'),
        ('refund', 'Refund'),
        ('adjustment', 'Invoice Adjustment'),
        ('discount', 'Discount/Allowance'),
        ('error', 'Invoice Error'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Credit Note Information
    credit_note_number = models.CharField(max_length=20, unique=True, help_text="Unique credit note number")
    credit_note_date = models.DateTimeField(auto_now_add=True, help_text="Date when credit note was created")
    credit_note_type = models.CharField(max_length=20, choices=CREDIT_NOTE_TYPES, help_text="Type of credit note")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Related Documents
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='credit_notes', 
                                    help_text="Related sales invoice")
    
    # Customer Information
    customer_name = models.CharField(max_length=200, help_text="Customer name")
    customer_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Customer contact")
    customer_email = models.EmailField(blank=True, null=True, help_text="Customer email")
    
    # Financial Information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, help_text="Subtotal before tax")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Tax amount")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total credit amount")
    
    # Chart of Accounts Integration
    accounts_receivable_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.PROTECT, 
                                                   related_name='credit_notes_receivable', 
                                                   help_text="Accounts Receivable account to debit")
    sales_return_account = models.ForeignKey('accounts.ChartOfAccounts', on_delete=models.PROTECT, 
                                           related_name='credit_notes_sales_return', 
                                           help_text="Sales Returns account to credit")
    
    # Additional Information
    reason = models.TextField(help_text="Reason for credit note")
    reference_number = models.CharField(max_length=50, blank=True, help_text="External reference number")
    notes = models.TextField(blank=True, help_text="Additional notes")
    
    # Audit Information
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User who created the credit note")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-credit_note_date']
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"
    
    def __str__(self):
        return f"Credit Note {self.credit_note_number} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate credit note number if not provided
        if not self.credit_note_number:
            from datetime import datetime
            import uuid
            current_date = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4()).replace('-', '').upper()[:6]
            self.credit_note_number = f"CN{current_date}{unique_id}"
        
        # Calculate total if not set
        if not self.total_amount:
            self.total_amount = self.subtotal + self.tax_amount
        
        super().save(*args, **kwargs)
    
    @property
    def invoice_number(self):
        """Get the related invoice number"""
        return self.sales_invoice.invoice_number
    
    @property
    def order_number(self):
        """Get the related order number"""
        return self.sales_invoice.store_sale.order_number
    
    @property
    def can_be_applied(self):
        """Check if credit note can be applied to invoice"""
        return self.status == 'issued' and self.sales_invoice.balance_due > 0
    
    def apply_to_invoice(self):
        """Apply credit note to reduce invoice balance"""
        if not self.can_be_applied:
            raise ValueError("Credit note cannot be applied")
        
        # Calculate how much can be applied
        amount_to_apply = min(self.total_amount, self.sales_invoice.balance_due)
        
        # Update invoice balance
        self.sales_invoice.amount_paid += amount_to_apply
        self.sales_invoice.save()
        
        # Update credit note status
        self.status = 'applied'
        self.save()
        
        # Create journal entry for the credit note application
        from accounts.models import JournalEntry, JournalEntryLine
        
        journal_entry = JournalEntry.objects.create(
            date=self.credit_note_date.date(),
            reference=f"CN-{self.credit_note_number}",
            description=f"Credit note applied to Invoice {self.invoice_number}",
            entry_type='credit_note',
            created_by=self.created_by,
            is_posted=True,
            posted_at=timezone.now()
        )
        
        # Create journal entry lines
        # Debit: Accounts Receivable (reduce receivable)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.accounts_receivable_account,
            entry_type='debit',
            amount=amount_to_apply,
            description=f"Credit note applied for {self.customer_name}"
        )
        
        # Credit: Sales Returns
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.sales_return_account,
            entry_type='credit',
            amount=amount_to_apply,
            description=f"Credit note for Invoice {self.invoice_number}"
        )
        
        return amount_to_apply


class StoreCreditNote(models.Model):
    CREDIT_NOTE_TYPES = (
        ('product_return', 'Product Return'),
        ('service_cancellation', 'Service Cancellation'),
        ('price_adjustment', 'Price Adjustment'),
        ('other', 'Other')
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('exchanged', 'Exchanged'),
        ('refunded', 'Refunded'),
        ('void', 'Void')
    )
    
    credit_note_number = models.CharField(max_length=50, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_credit_notes')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='updated_credit_notes')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    note_type = models.CharField(max_length=50, choices=CREDIT_NOTE_TYPES)
    reason = models.TextField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_refunded = models.BooleanField(default=False)
    refund_date = models.DateTimeField(null=True, blank=True)
    refund_method = models.CharField(max_length=50, blank=True, null=True)
    refund_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Link to the original sale
    product_sale = models.ForeignKey('StoreProductSale', on_delete=models.SET_NULL, null=True, blank=True)
    service_sale = models.ForeignKey('ServiceSale', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Store the customer for easy filtering
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.PROTECT)
    
    def save(self, *args, **kwargs):
        if not self.credit_note_number:
            # Generate credit note number: CN-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_cn = CreditNote.objects.filter(
                credit_note_number__startswith=f'SCN-{today}'
            ).order_by('-credit_note_number').first()
            
            if last_cn:
                last_num = int(last_cn.credit_note_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.credit_note_number = f'CN-{today}-{new_num:04d}'
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.credit_note_number
class CreditNoteItem(models.Model):
    ITEM_TYPES = (
        ('service', 'Service'),
        ('product', 'Product'),
        ('accessory', 'Accessory'),
        ('refreshment', 'Refreshment'),
    )
    
    credit_note = models.ForeignKey('StoreCreditNote', on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, null=True, blank=True)
    
    # These fields will be used based on item_type
    service = models.ForeignKey('StoreService', on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey('StoreInventory', on_delete=models.SET_NULL, null=True, blank=True)
    accessory = models.ForeignKey('StoreAccessoryInventory', on_delete=models.SET_NULL, null=True, blank=True)
    refreshment = models.ForeignKey('Refreshment', on_delete=models.SET_NULL, null=True, blank=True)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        item_name = self.get_item_name()
        return f"{self.quantity} x {item_name} (Credit Note: {self.credit_note.credit_note_number})"
    
    def get_item_name(self):
        if self.item_type == 'service' and self.service:
            return self.service.service.name
        elif self.item_type == 'product' and self.product:
            return self.product.product.product_name
        elif self.item_type == 'accessory' and self.accessory:
            return self.accessory.accessory.name
        elif self.item_type == 'refreshment' and self.refreshment:
            return self.refreshment.name
        return 'Unknown Item'


class StoreProductSale(models.Model):
    """
    Model for walk-in customers who only buy products (no services)
    Separate from ServiceSale for product-only transactions
    """
    PAID_STATUS_CHOICES = [
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid'),
    ]
    
    PAYMENT_MODE_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('visa', 'Visa'),
        ('mixed', 'Mixed'),
    ]
    
    product_sale_number = models.CharField(max_length=20, unique=True, editable=False, null=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='product_sales')
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE, related_name='product_sales', help_text="Customer who purchased the products")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_notes = models.ManyToManyField('StoreCreditNote', blank=True, related_name='product_sales')
    sale_date = models.DateTimeField(auto_now_add=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_status = models.CharField(max_length=20, choices=PAID_STATUS_CHOICES, default='not_paid')
    payment_mode = models.CharField(max_length=255, choices=PAYMENT_MODE_CHOICES, default='cash')
    payment_remarks = models.CharField(max_length=150, null=True, blank=True)
    cash_drawer_session = models.ForeignKey(
        'CashDrawerSession', 
        on_delete=models.PROTECT, 
        related_name='product_sales',
        null=True,
        blank=True,
        help_text="The cash drawer session this sale is associated with"
    )
    
    # Performance tracking
    sale_creation_time = models.DurationField(null=True, blank=True, help_text="Time taken to create the sale")
    payment_processing_time = models.DurationField(null=True, blank=True, help_text="Time taken to process payment")
    total_workflow_time = models.DurationField(null=True, blank=True, help_text="Total time from sale creation to payment completion")
    
    class Meta:
        ordering = ['-sale_date']
        verbose_name = 'Product Sale'
        verbose_name_plural = 'Product Sales'
    
    def __str__(self):
        return f"Product Sale #{self.product_sale_number or self.id} - {self.customer.first_name} {self.customer.last_name}"
    
    def save(self, *args, **kwargs):
        if not self.product_sale_number:
            self.product_sale_number = self.generate_sale_number()
        super().save(*args, **kwargs)
    
    def generate_sale_number(self):
        """Generate unique product sale number"""
        from datetime import datetime
        today = datetime.now().date()
        prefix = f"PS{today.strftime('%Y%m%d')}"
        
        # Get the last sale number for today
        last_sale = StoreProductSale.objects.filter(
            product_sale_number__startswith=prefix
        ).order_by('-product_sale_number').first()
        
        if last_sale:
            try:
                last_number = int(last_sale.product_sale_number[-4:])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:04d}"
    
    @property
    def can_process_payment(self):
        """Check if payment can be processed"""
        return self.paid_status == 'not_paid' and self.balance > 0
    
    def mark_as_paid(self, user):
        """Mark the sale as paid, deduct inventory, create receipt, and record transaction"""
        if self.balance <= 0:
            with transaction.atomic():
                # Check if inventory adjustments for this sale already exist
                product_deductions_exist = InventoryAdjustment.objects.filter(
                    adjustment_reason__icontains=f"ProductSale #{self.id}"
                ).exists()
                
                # Get or create an open cash drawer session for the user
                from .models import CashDrawerSession, CashDrawerTransaction
                
                # Find an open session for the user and store
                session = CashDrawerSession.objects.filter(
                    user=user,
                    store=self.store,
                    status='open'
                ).order_by('-opening_time').first()
                
                if not session:
                    raise ValueError("No open cash drawer session found. Please open a cash drawer session before making a sale.")
                
                self.cash_drawer_session = session
                self.paid_status = 'paid'
                self.save(update_fields=['paid_status', 'cash_drawer_session'])
                
                # Create cash drawer transaction
                CashDrawerTransaction.objects.create(
                    session=session,
                    transaction_type='sale',
                    payment_method=self.payment_mode,
                    amount=self.total_amount,
                    reference=f"Product Sale #{self.product_sale_number or self.id}",
                    notes=f"Product sale to {self.customer}",
                    user=user
                )
                
                # Deduct product inventory if not already done
                if not product_deductions_exist:
                    self._deduct_product_inventory()
                else:
                    print(f"DEBUG: Product deductions for ProductSale #{self.id} already exist. Skipping.")
                
                # Create receipt if it doesn't exist
                if not hasattr(self, 'receipt'):
                    ProductSaleReceipt.objects.create(
                        sale=self,
                        store=self.store,
                        created_by=user
                    )
                
                return True
        return False
    
    def _deduct_product_inventory(self):
        """Deduct products from store inventory"""
        for item in self.product_sale_items.all():
            try:
                store_inventory = StoreInventory.objects.get(
                    store=self.store,
                    product=item.product.product
                )
                
                if store_inventory.quantity >= item.quantity:
                    # Create inventory adjustment record
                    InventoryAdjustment.objects.create(
                        store_inventory=store_inventory,
                        adjusted_quantity=-item.quantity,  # Negative for deduction
                        adjustment_reason=f"ProductSale #{self.id} - {item.product.product.product_name}",
                        adjusted_by=None,  # System adjustment
                    )
                    
                    # Update inventory quantity
                    store_inventory.quantity -= item.quantity
                    store_inventory.save()
                else:
                    raise ValueError(f"Insufficient stock for {item.product.product.product_name}. Available: {store_inventory.quantity}, Required: {item.quantity}")
                    
            except StoreInventory.DoesNotExist:
                raise ValueError(f"Product {item.product.product.product_name} not found in store inventory")
    
    def get_timing_summary(self):
        """Get a summary of timing metrics."""
        return {
            'sale_creation_time': self.sale_creation_time,
            'payment_processing_time': self.payment_processing_time,
            'total_workflow_time': self.total_workflow_time,
            'sale_date': self.sale_date,
        }


class StoreProductSaleItem(models.Model):
    """
    Individual product items in a product sale
    """
    sale = models.ForeignKey(StoreProductSale, on_delete=models.CASCADE, related_name='product_sale_items')
    product = models.ForeignKey(StoreInventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = 'Product Sale Item'
        verbose_name_plural = 'Product Sale Items'
    
    def __str__(self):
        return f"{self.product.product_name} x {self.quantity} - {self.sale}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Update sale total
        self.sale.total_amount = sum(item.total_price for item in self.sale.product_sale_items.all())
        self.sale.balance = self.sale.total_amount - self.sale.paid_amount
        self.sale.save(update_fields=['total_amount', 'balance'])


