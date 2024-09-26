from datetime import date
from django import forms
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import LPO, RawMaterialInventory, Requisition, RequisitionItem, SaleItem, StoreAlerts, StoreSale

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

@receiver(post_save, sender=Requisition)
def send_requisition_email(sender, instance, created, **kwargs):
    if created:
        subject = f"New: Manufacturing / Production Requisition: {instance.requisition_no}"
        
        # Retrieve requisition items
        items = instance.requisitionitem_set.all()
        # Check if items are retrieved correctly
        print("Retrieved items:", items)  # For debugging
        items_details = "\n".join([
            f"- {item.raw_material.name}: Quantity: {item.quantity}, Price per unit: {item.price_per_unit}"
            for item in items
        ])
        
        message = f"A new requisition has been created with the following details:\n\n" \
                f"Requisition Number: {instance.requisition_no}\n" \
                f"Supplier: {instance.supplier}\n" \
                f"Status: {instance.status}\n" \
                f"Date: {instance.created_at}\n\n" \
                f"Items:\n{items_details}{items}\n\n" \
                f"Please review the requisition and kindly advise."
        
        recipient_list = ['nicholas.lukyamuzi@mylivara.com']  # Add recipients here
        send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
        
@receiver(post_save, sender=Requisition)
def send_requisition_status_email(sender, instance, **kwargs):
    # Check if the requisition status is 'checking'
    if instance.status == 'checking':
        subject = f"Requisition {instance.requisition_no} Is Ready For Delivery"
        message = f"The requisition with ID {instance.requisition_no} has been updated to the 'checking' status."
        recipient_list = ['nicholas.lukyamuzi@mylivara.com']  # Replace with actual recipient(s)

        try:
            send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
            print(f"Status update email sent for Requisition {instance.requisition_no}.")  # Debugging line
        except Exception as e:
            print(f"Failed to send status update email for Requisition {instance.requisition_no}: {e}")
        
@receiver(post_save, sender=LPO)
def send_lpo_verification_email(sender, instance, **kwargs):
    print(f"Signal triggered for LPO {instance.lpo_number} with status {instance.status}.")  # Debugging line
    if instance.status == 'verified':  # Check if the status is 'verified'
        print(f"Preparing to send email for LPO {instance.pk}.")  # Debugging line
        subject = f"LPO {instance.lpo_number} Verified"
        message = f"The LPO with ID {instance.lpo_number} has been verified and is ready for delivery."
        recipient_list = ['nicholas.lukyamuzi@mylivara.com']  # Replace with actual recipient(s)

        try:
            send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
            print(f"Verification email sent for LPO {instance.pk}.")  # Debugging line
        except Exception as e:
            print(f"Failed to send verification email for LPO {instance.pk}: {e}")
