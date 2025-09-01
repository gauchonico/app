import datetime
from time import timezone
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os

# Import CloudinaryField only if we have credentials
try:
    if not settings.DEBUG and os.environ.get('CLOUDINARY_CLOUD_NAME'):
        from cloudinary.models import CloudinaryField
        USE_CLOUDINARY = True
    else:
        USE_CLOUDINARY = False
except:
    USE_CLOUDINARY = False

from POSMagic.settings import STATIC_URL
from production.models import Store, StoreSale
from decimal import Decimal

# Create your models here.
    
class Branch(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    
class Staff(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    # branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    store = models.ForeignKey('production.Store', on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True, blank=True)
    nin_no = models.CharField(max_length=100, null=True, blank=True)
    comission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.1)
    specialization = models.CharField(max_length=100, choices=(('HAIR_CARE', 'Hair Care'), ('STYLING', 'Styling'), ('OTHER', 'Other'),('BARBER', 'Barber'),('NAIL_ARTIST', 'Nail Artist'),('MASSEUSE', 'Masseuse')), default='OTHER')

    def __str__(self):
        return f'{self.first_name}  {self.last_name} - {self.specialization} - {self.store}'
    
class Customer(models.Model):
    TYPE_OF_CUSTOMER = (
        ('WHOLESALE','Wholesaler'),
        ('RETAIL','Retailer'),
        ('CLIENT','Client')
    )
    
    SEX_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    RELATIONSHIP_CHOICES = (
        ('SELF', 'Self'),
        ('PARENT', 'Parent/Guardian'),
        ('CHILD', 'Child/Dependent'),
        ('SPOUSE', 'Spouse'),
        ('SIBLING', 'Sibling'),
        ('OTHER', 'Other Relative'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    type_of_customer = models.CharField(max_length=100, choices=TYPE_OF_CUSTOMER, default='CLIENT')
    date_of_birth = models.DateField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='customer_profiles/', null=True, blank=True, help_text="Customer profile picture")
    
    # Enhanced fields
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, null=True, blank=True, help_text="Gender - required for clients")
    is_minor = models.BooleanField(default=False, help_text="Is this person under 18?")
    guardian = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='dependents', help_text="Parent/Guardian for minors")
    relationship_to_guardian = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='SELF', help_text="Relationship to account holder")
    
    # Business-specific fields
    kyc_verified = models.BooleanField(default=False, help_text="Has completed KYC verification")
    can_make_purchases = models.BooleanField(default=True, help_text="Can this person authorize purchases")
    emergency_contact = models.CharField(max_length=100, blank=True, help_text="Emergency contact number")
    notes = models.TextField(blank=True, help_text="Additional notes about customer")
    
    # Loyalty Points fields
    loyalty_points = models.PositiveIntegerField(default=0, help_text="Current available loyalty points")
    total_points_earned = models.PositiveIntegerField(default=0, help_text="Total points earned over lifetime")
    total_points_redeemed = models.PositiveIntegerField(default=0, help_text="Total points redeemed over lifetime")
    loyalty_tier = models.CharField(max_length=20, default='BRONZE', help_text="Customer loyalty tier")
    joined_loyalty_date = models.DateTimeField(auto_now_add=True, help_text="When customer joined loyalty program", null=True, blank=True)
    
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    @property
    def full_name_with_relation(self):
        """Display name with relationship info for dependents"""
        if self.guardian:
            return f"{self.name} ({self.get_relationship_to_guardian_display()} of {self.guardian.name})"
        return self.name
    
    @property
    def account_holder(self):
        """Get the main account holder (guardian or self)"""
        return self.guardian if self.guardian else self
    
    def get_all_dependents(self):
        """Get all dependents under this customer's account"""
        return self.dependents.all()
    
    def can_authorize_for(self, service_recipient):
        """Check if this customer can authorize services for another person"""
        # Self authorization
        if self == service_recipient:
            return self.can_make_purchases
        
        # Guardian authorization for dependents
        if service_recipient.guardian == self:
            return self.can_make_purchases and self.kyc_verified
        
        return False
    
    def get_display_info(self):
        """Get formatted display information"""
        info = {
            'name': self.name,
            'type': self.get_type_of_customer_display(),
            'age': self.age,
            'sex': self.get_sex_display() if self.sex else None,
            'is_minor': self.is_minor,
            'guardian': self.guardian.name if self.guardian else None,
            'kyc_status': 'Verified' if self.kyc_verified else 'Pending',
            'loyalty_points': self.loyalty_points,
            'loyalty_tier': self.get_loyalty_tier_display(),
        }
        return info
    
    # Loyalty Points Methods
    def get_total_orders(self):
        """Get total number of orders for this customer"""
        # Count from both Transaction and ServiceSale models
        sale_orders = StoreSale.objects.filter(customer=self).count()
        try:
            from production.models import ServiceSale
            service_sale_count = ServiceSale.objects.filter(customer=self).count()
            return  service_sale_count + sale_orders
        except:
            return sale_orders
    
    def get_loyalty_tier_display(self):
        """Get formatted loyalty tier with description"""
        tier_descriptions = {
            'BRONZE': 'Bronze Member',
            'SILVER': 'Silver Member', 
            'GOLD': 'Gold Member',
            'VIP': 'VIP Member'
        }
        return tier_descriptions.get(self.loyalty_tier, self.loyalty_tier)
    
    def update_loyalty_tier(self):
        """Update customer's loyalty tier based on total orders"""
        order_count = self.get_total_orders()
        
        if order_count >= 50:
            self.loyalty_tier = 'VIP'
        elif order_count >= 20:
            self.loyalty_tier = 'GOLD'
        elif order_count >= 10:
            self.loyalty_tier = 'SILVER'
        else:
            self.loyalty_tier = 'BRONZE'
        
        self.save(update_fields=['loyalty_tier'])
        return self.loyalty_tier
    
    def add_loyalty_points(self, points, transaction_type='EARNED', order_reference='', description='', created_by=None):
        """Add loyalty points to customer account"""
        if points <= 0:
            return False
            
        # Update customer points
        self.loyalty_points += points
        self.total_points_earned += points
        self.save(update_fields=['loyalty_points', 'total_points_earned'])
        
        # Create transaction record
        CustomerLoyaltyTransaction.objects.create(
            customer=self,
            transaction_type=transaction_type,
            points=points,
            order_reference=order_reference,
            description=description,
            created_by=created_by
        )
        
        # Update loyalty tier
        self.update_loyalty_tier()
        return True
    
    def redeem_loyalty_points(self, points, description='', created_by=None):
        """Redeem loyalty points from customer account"""
        if points <= 0 or points > self.loyalty_points:
            return False
            
        # Check minimum redemption requirement
        loyalty_settings = LoyaltySettings.get_current_settings()
        if points < loyalty_settings.minimum_points_redemption:
            return False
            
        # Update customer points
        self.loyalty_points -= points
        self.total_points_redeemed += points
        self.save(update_fields=['loyalty_points', 'total_points_redeemed'])
        
        # Create transaction record
        CustomerLoyaltyTransaction.objects.create(
            customer=self,
            transaction_type='REDEEMED',
            points=-points,  # Negative for redemption
            description=description,
            created_by=created_by
        )
        
        return True
    
    def get_loyalty_summary(self):
        """Get comprehensive loyalty information"""
        return {
            'current_points': self.loyalty_points,
            'total_earned': self.total_points_earned,
            'total_redeemed': self.total_points_redeemed,
            'tier': self.get_loyalty_tier_display(),
            'total_orders': self.get_total_orders(),
            'member_since': self.joined_loyalty_date,
            'recent_transactions': self.loyalty_transactions.all()[:5]
        }

    def __str__(self):
        if self.guardian:
            return f'{self.first_name} {self.last_name} (via {self.guardian.name})'
        return f'{self.first_name} {self.last_name}'

class Product(models.Model):
    CATEGORY_CHOICES = (
        ('BABERSHOP', 'Babershop'),
        ('HAIRCARE', 'Haircare'),
        ('KIDS_HAIR', 'Kids Hair'),
        ('DREADLOCKS', 'Dreadlocks'),
        ('NAIL_ART', 'Nail Art'),
        ('PRODUCTS', 'Products'),
        ('SALOOMATERIALS','Service Materials'),
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='PRODUCTS')
    description = models.CharField(max_length=100, default='', blank=True, null=True)
    image = models.ImageField(upload_to='uploads/products/')

    def __str__(self):
        return self.name
    
class Order(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    )
    DELIVERY_STATUS_CHOICES = (
        ('DELIVERED', 'Delivered'),
        ('IN_PROGRESS', 'In Progress'),
        ('PENDING', 'Pending'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True) 
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    date = models.DateField(default=datetime.date.today)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, blank=True, null=True)
    is_delivery = models.BooleanField(default=False)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.first_name}"


# Loyalty System Models
class LoyaltySettings(models.Model):
    """Global settings for the loyalty points system"""
    
    POINT_CALCULATION_METHODS = (
        ('FIXED', 'Fixed Points per Order'),
        ('PERCENTAGE', 'Percentage of Order Value'),
        ('TIERED', 'Tiered Based on Order Value'),
    )
    
    # Basic settings
    points_per_order = models.PositiveIntegerField(default=10, help_text="Fixed points awarded per order")
    points_per_currency_unit = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.01'), 
                                                  help_text="Points per currency unit spent (e.g., 1 point per 100 UGX)")
    calculation_method = models.CharField(max_length=20, choices=POINT_CALCULATION_METHODS, default='FIXED')
    
    # Bonus multipliers
    birthday_bonus_multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('2.0'),
                                                   help_text="Multiplier for birthday month (e.g., 2.0 = double points)")
    weekend_bonus_multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('1.5'),
                                                  help_text="Multiplier for weekend orders")
    loyalty_tier_bonus = models.BooleanField(default=True, help_text="Enable bonus points for loyal customers")
    
    # Redemption settings
    points_redemption_enabled = models.BooleanField(default=True)
    points_to_currency_ratio = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('100.00'),
                                                  help_text="Points needed for 1 currency unit (e.g., 100 points = 1 UGX)")
    minimum_points_redemption = models.PositiveIntegerField(default=500, help_text="Minimum points required to redeem")
    
    # System settings
    points_expiry_months = models.PositiveIntegerField(default=12, help_text="Months until points expire (0 = never)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Loyalty Settings"
        verbose_name_plural = "Loyalty Settings"
    
    def __str__(self):
        return f"Loyalty Settings ({self.calculation_method})"
    
    @classmethod
    def get_current_settings(cls):
        """Get the current active loyalty settings"""
        settings = cls.objects.filter(is_active=True).first()
        if not settings:
            # Create default settings if none exist
            settings = cls.objects.create()
        return settings
    
    def calculate_order_points(self, order_amount, customer=None, order_date=None):
        """Calculate points for an order based on current settings"""
        if not self.is_active:
            return 0
            
        base_points = 0
        
        if self.calculation_method == 'FIXED':
            base_points = self.points_per_order
        elif self.calculation_method == 'PERCENTAGE':
            base_points = int(order_amount * self.points_per_currency_unit)
        elif self.calculation_method == 'TIERED':
            # Tiered system based on order value
            if order_amount >= 100000:  # 100k UGX
                base_points = int(order_amount * self.points_per_currency_unit * 2)
            elif order_amount >= 50000:  # 50k UGX
                base_points = int(order_amount * self.points_per_currency_unit * 1.5)
            else:
                base_points = int(order_amount * self.points_per_currency_unit)
        
        # Apply bonus multipliers
        multiplier = Decimal('1.0')
        
        # Birthday bonus
        if customer and customer.date_of_birth and order_date:
            if customer.date_of_birth.month == order_date.month:
                multiplier *= self.birthday_bonus_multiplier
        
        # Weekend bonus
        if order_date and order_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            multiplier *= self.weekend_bonus_multiplier
        
        # Loyalty tier bonus
        if self.loyalty_tier_bonus and customer:
            order_count = customer.get_total_orders()
            if order_count >= 50:
                multiplier *= Decimal('2.0')  # VIP customers
            elif order_count >= 20:
                multiplier *= Decimal('1.5')  # Gold customers
            elif order_count >= 10:
                multiplier *= Decimal('1.2')  # Silver customers
        
        final_points = int(base_points * multiplier)
        return max(final_points, 0)


class CustomerLoyaltyTransaction(models.Model):
    """Track all loyalty point transactions for customers"""
    
    TRANSACTION_TYPES = (
        ('EARNED', 'Points Earned'),
        ('REDEEMED', 'Points Redeemed'),
        ('EXPIRED', 'Points Expired'),
        ('ADJUSTED', 'Manual Adjustment'),
        ('BONUS', 'Bonus Points'),
    )
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loyalty_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    points = models.IntegerField(help_text="Positive for earned/bonus, negative for redeemed/expired")
    order_reference = models.CharField(max_length=100, blank=True, help_text="Reference to order/transaction that generated points")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When these points expire")
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Loyalty Transaction"
        verbose_name_plural = "Loyalty Transactions"
    
    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.points} points"


 

