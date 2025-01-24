import datetime
from time import timezone
from django.db import models
from django.contrib.auth.models import User

from POSMagic.settings import STATIC_URL
from production.models import Store

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
        ('WHOLESALE','Wholesale'),
        ('RETAIL','Retail')
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    type_of_customer = models.CharField(max_length=100, choices=TYPE_OF_CUSTOMER, default='RETAIL')
    date_of_birth = models.DateField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='uploads/products/', null=True, blank=True, default=STATIC_URL + '/img/user/profile.jpg')
    
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
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

