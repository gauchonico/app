from django.db import models
from django.contrib.auth.models import User
from POSMagicApp.models import Customer, Product, Branch, Staff

# Create your models here.

class order_details(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    is_delivery = models.BooleanField(default=False)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, blank=True)
    notes = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Order Details"
    def __str__(self):
        return f'Order Details - {str(self.id)}'
    
class Transaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)  # Assuming Customer is your existing model
    products = models.ManyToManyField(Product)  # Assuming Product is your existing model
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')  # Payment status
    is_delivery = models.BooleanField(default=False)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction for {self.customer} on {self.date}"  # Customize as per your requirements



#Order Model 
class Ordern(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=20, decimal_places=2)
    date_ordered = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Order - {str(self.id)}'


#Order Items Model
class OrderItem(models.Model):
    order = models.ForeignKey(Ordern, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=20, decimal_places=2)

    def __str__(self):
        return f'Order Item - {str(self.id)}'
        

