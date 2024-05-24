from django.db import models
from django.contrib.auth.models import User
from POSMagicApp.models import Customer, Product, Branch, Staff

# Create your models here.

# class SalonMaterial(models.Model):
#     name = models.CharField(max_length=255)
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     unit_of_measurement = models.CharField(max_length=10, blank=True)

#     def __str__(self):
#         return self.name

# class SalonMaterialInventory(models.Model):
#     material = models.ForeignKey(SalonMaterial, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
#     last_updated = models.DateField(auto_now=True, null=True)  # Track last update date

#     def __str__(self):
#         return f"{self.material.name} - {self.quantity}"

#     def restock(self, quantity_added):
#         """
#         Increase the quantity of this material in stock.

#         Args:
#             quantity_added (int): The positive quantity to add to the inventory.
#         """
#         if quantity_added <= 0:
#             raise ValueError("Restock quantity must be a positive integer.")
#         self.quantity += quantity_added
#         self.save()


class CommissionRate(models.Model):
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    # You can add additional fields like start_date, end_date for time-based rates (optional)

    def __str__(self):
        return f"{self.percentage}"

class order_details(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    is_delivery = models.BooleanField(default=False)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, blank=True)
    notes = models.CharField(max_length=100)
    commission_rate = models.ForeignKey(CommissionRate, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Order Details"
    def __str__(self):
        return f'Order Details - {str(self.id)}'
    
# class OrderDetailSalonMaterial(models.Model):
#     order_detail = models.ForeignKey(order_details, on_delete=models.CASCADE)
#     salon_material = models.ForeignKey(SalonMaterial, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
    
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
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, null=True, blank=True)
    commission_amount= models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)



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
        

