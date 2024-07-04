from datetime import date
from django import forms
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import RawMaterialInventory, SaleItem, StoreAlerts, StoreSale

@receiver(post_save, sender=RawMaterialInventory)
def send_alert_for_rawmaterial(sender, instance, created, **kwargs):
    
    print(instance.__dict__)
    # @update checks current stock inventory
    if instance.raw_material.current_stock < instance.raw_material.reorder_point:
        StoreAlerts.objects.create(
            message=f"The reorder point for {instance.raw_material.name} is {instance.raw_material.reorder_point}",
            alert_type="purchase_order"
        )


# @receiver(pre_save, sender=SaleItem)
# def check_quantity(sender, instance, **kwargs):
#     product = instance.product
#     if product.quantity < instance.quantity:
#         raise forms.ValidationError(f"Insufficient stock for {product.product.product_name}. Available stock: {product.quantity}")
#     if product.expiry_date and product.expiry_date < date.today():
#         raise forms.ValidationError(f"Product {product.product.product_name} has expired on {product.expiry_date}.")