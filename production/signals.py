from datetime import date
from threading import Thread
from django import forms
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver, Signal
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction
from .models import LPO, Accessory, AccessoryInventoryAdjustment, GoodsReceivedNote, IncidentWriteOff, InternalAccessoryRequest, MainStoreAccessoryRequisition, RawMaterialInventory,RawMaterialPrice, PriceAlert, Requisition, RequisitionItem, SaleItem, Store, StoreAccessoryInventory, StoreAlerts, StoreSale

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

# Define a custom signal
requisition_completed = Signal()

@receiver(post_save, sender=RequisitionItem)
def trigger_requisition_email(sender, instance, **kwargs):
    requisition = instance.requisition
    # Check if items exist after every RequisitionItem save
    if requisition.requisitionitem_set.exists():
        # Emit custom signal after all items are added
        requisition_completed.send(sender=Requisition, instance=requisition)

@receiver(requisition_completed)
def send_requisition_email(sender, instance, **kwargs):
    transaction.on_commit(lambda: send_email(instance))

def send_email(instance):
    requisition_items = instance.requisitionitem_set.all()
    context = {
        'requisition_number': instance.requisition_no,
        'supplier': instance.supplier,
        'status': instance.status,
        'created_at': instance.created_at,
        'items': requisition_items,
        'total_cost': instance.total_cost,
    }
    print(requisition_items)
    
    html_message = render_to_string('requisition_email.html', context)
    subject = f"New: Manufacturing / Production Requisition: {instance.requisition_no}"
    from_email = 'lukyamuzinicholas10@gmail.com'
    recipient_list = ['lukyamuzinicholas10@gmail.com']
    
    send_mail(subject, '', from_email, recipient_list, html_message=html_message, fail_silently=False)
        
@receiver(post_save, sender=Requisition)
def send_requisition_status_email(sender, instance, **kwargs):
    # Check if the requisition status is 'checking'
    if instance.status == 'checking':
        def send_email_task():
            subject = f"Requisition {instance.requisition_no} Is Ready For Delivery"
            message = f"The requisition with ID {instance.requisition_no} has been updated to the 'checking' status."
            recipient_list = ['vivian.nambozo@mylivara.com','victoria.zemei@mylivara.com']  # Replace with actual recipient(s)

            try:
                send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
                print(f"Status update email sent for Requisition {instance.requisition_no}.")  # Debugging line
            except Exception as e:
                print(f"Failed to send status update email for Requisition {instance.requisitionno}: {e}")

        # Create a new thread to send the email
        email_thread = Thread(target=send_email_task)
        email_thread.start()

        print(f"Requisition {instance.requisition_no} saved successfully. Email sending in progress...")
        
@receiver(post_save, sender=LPO)
def send_lpo_verification_email(sender, instance, **kwargs):
    # print(f"Signal triggered for LPO {instance.lpo_number} with status {instance.status}.")  # Debugging line
    if instance.status == 'verified':  # Check if the status is 'verified'
        # print(f"Preparing to send email for LPO {instance.pk}.")  # Debugging line
        def send_email_veification():
            subject = f"LPO {instance.lpo_number} Verified"
            message = f"The LPO with ID {instance.lpo_number} has been verified and is ready for delivery."
            recipient_list = ['florence.mwesigye@mylivara.com','vivian.nambozo@mylivara.com','victoria.zemei@mylivara.com']  # Replace with actual recipient(s)

            try:
                send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
                print(f"Verification email sent for LPO {instance.pk}.")  # Debugging line
            except Exception as e:
                print(f"Failed to send verification email for LPO {instance.pk}: {e}")
                
            # Create a new thread to send the email
        email_thread = Thread(target=send_email_veification)
        email_thread.start()
            
@receiver(post_save,
    sender=GoodsReceivedNote )
def send_grn_creation_email(sender, instance, created, **kwargs):
    if created:
        print(f"Signal triggered for new GRN {instance.gcr_number}.")  # Debugging line

        subject = f"New GRN Created: {instance.gcr_number}"
        message = f"A new Goods Received Note (GRN) with ID {instance.pk} and number {instance.gcr_number} has been created."
        recipient_list = ['florence.mwesigye@mylivara.com','vivian.nambozo@mylivara.com']  # Replace with actual recipient(s)

        try:
            send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
            print(f"Creation email sent for GRN {instance.pk}.")  # Debugging line
        except Exception as e:
            print(f"Failed to send creation email for GRN {instance.pk}: {e}")
            
@receiver(post_save, sender=IncidentWriteOff)
def send_write_off_notification(sender, instance, created, **kwargs):
    if created:
        subject = "New Incident Write-Off Created"
        message = f"Please review this newly created Incident Write-Off raw_material: {instance.raw_material} quantity: {instance.quantity}, reason: {instance.reason} status: {instance.status}"
        
        recipient_list = ['florence.mwesigye@mylivara.com','vivian.nambozo@mylivara.com','victoria.zemei@mylivara.com']  # Replace with actual email addresses
        try:
            send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
        except Exception as e:
            print(f"Failed to send creation email for GRN {instance.pk}: {e}")
            
@receiver(post_save, sender=MainStoreAccessoryRequisition)
def send_email_for_accessories_requisition(sender, instance, created, **kwargs):
    if created:
        subject = "New Requisition For Salon Accessories from"
        message = f"Please review this newly created Requisition for salon accessories: {instance.accessory_req_number} status: {instance.status}"
        recipient_list = ['florence.mwesigye@mylivara.com','vivian.nambozo@mylivara.com','lukyamuzin91@gmail.com']  # Replace with actual email addresses
        try:
            send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
        except Exception as e:
                    print(f"Failed to send creation email for accessories requisition {instance.pk}: {e}")
                    
            
@receiver(post_save, sender=InternalAccessoryRequest)
def send_email_for_internal_accessory_request(sender, instance, created, **kwargs):
    if created:
        subject = "New Internal Accessory Request"
        message = f"Please review this newly created Internal Accessory Request: {instance.store} status: {instance.comments}"
        recipient_list = ['florence.mwesigye@mylivara.com','vivian.nambozo@mylivara.com','lukyamuzin91@gmail.com']  # Replace with actual email addresses
        try:
            send_mail(subject, message, 'lukyamuzinicholas10@gmail.com', recipient_list)
        except Exception as e:
            print(f"Failed to send creation email for internal accessory request {instance.pk}: {e}")


@receiver(post_save, sender=RawMaterialPrice)
def check_price_alerts(sender, instance, created, **kwargs):
    if created and instance.is_current:
        alerts = PriceAlert.objects.filter(
            raw_material=instance.raw_material,
            is_active=True
        )
        
        for alert in alerts:
            condition_met = (
                (alert.is_above and instance.price > alert.threshold_price) or
                (not alert.is_above and instance.price < alert.threshold_price)
            )
            
            if condition_met:
                # Send notification (implement your notification logic)
                send_price_alert_notification(alert, instance)