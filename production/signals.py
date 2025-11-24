from datetime import date
from threading import Thread
from django import forms
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver, Signal
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction
from .models import LPO, Accessory, AccessoryInventoryAdjustment, GoodsReceivedNote, IncidentWriteOff, InternalAccessoryRequest, MainStoreAccessoryRequisition, RawMaterialInventory,RawMaterialPrice, PriceAlert, Requisition, RequisitionItem, SaleItem, Store, StoreAccessoryInventory, StoreAlerts, StoreSale, Payment, ServiceSaleInvoice, AccessorySaleItem, ServiceSale,ServiceSaleItem,ProductSaleItem,ServiceSale, CashDrawerTransaction, CashDrawerSession, StoreProductSale
@receiver(post_save, sender=Payment)
def update_invoice_and_sale_on_payment(sender, instance, created, **kwargs):
    """When a payment is saved, recompute sale totals and update invoice/payment status."""
    sale = instance.sale
    # Capture previous status before recalculation
    previous_status = sale.paid_status
    # Recalculate sale totals (updates paid_amount, balance, paid_status)
    sale.calculate_total()

    # Ensure invoice exists
    invoice = getattr(sale, 'invoice', None)
    if not invoice:
        # Create invoice if missing, align amount to sale total
        invoice = ServiceSaleInvoice.objects.create(sale=sale, total_amount=sale.total_amount)

    # Mirror paid status
    if sale.balance <= 0:
        invoice.paid_status = 'paid'
    elif sale.paid_amount > 0:
        invoice.paid_status = 'partially_paid'
    else:
        invoice.paid_status = 'unpaid'

    # Set payment method from the latest payment
    invoice.payment_method = instance.payment_method if hasattr(instance, 'payment_method') else invoice.payment_method
    invoice.total_amount = sale.total_amount
    invoice.save(update_fields=['paid_status', 'payment_method', 'total_amount', 'updated_at'])

    # Optionally keep ServiceSale invoice_status in sync
    if invoice.paid_status == 'paid' and sale.invoice_status != 'invoiced':
        sale.invoice_status = 'invoiced'
        sale.save(update_fields=['invoice_status'])

    # If sale transitioned to fully paid here (via this payment), finalize it
    if previous_status != 'paid' and sale.paid_status == 'paid':
        try:
            sale.mark_as_paid()
        except Exception as e:
            # Avoid breaking signal chain; log or print for now
            print(f"Error finalizing sale on payment: {e}")

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
            recipient_list = ['victoria.zemei@mylivara.com']  # Replace with actual recipient(s)

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


@receiver(post_delete, sender=ServiceSaleItem)
@receiver(post_delete, sender=ProductSaleItem)
@receiver(post_delete, sender=AccessorySaleItem)
def update_sale_total_on_delete(sender, instance, **kwargs):
    """Update the sale total when an item is deleted"""
    try:
        instance.sale.calculate_total()
    except:
        # Handle case where sale was already deleted
        pass


print("Cash drawer transaction signal connected")

@receiver(post_save, sender=StoreProductSale)
def create_product_sale_transaction(sender, instance, created, **kwargs):
    """
    Create a cash drawer transaction when a product sale is marked as paid
    """
    # Skip if this is a new instance or not marked as paid
    if created or instance.paid_status != 'paid':
        return

    # Skip if already has a cash drawer session (handled in mark_as_paid)
    if hasattr(instance, 'cash_drawer_session') and instance.cash_drawer_session:
        return
        
    # Get the current user (try to get from request thread local)
    from django.utils.module_loading import import_string
    from django.conf import settings
    
    user = None
    try:
        from django.utils.deprecation import MiddlewareMixin
        user_middleware = import_string(settings.MIDDLEWARE[0])()
        if hasattr(user_middleware, 'get_user'):
            user = user_middleware.get_user(None)
    except (ImportError, AttributeError, IndexError):
        pass
    
    # If no user found, use the store manager or a system user
    if user is None or not user.is_authenticated:
        user = instance.store.manager if hasattr(instance.store, 'manager') else None
        if user is None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(is_superuser=True).first()
    
    # Find an open session for the user and store
    session = CashDrawerSession.objects.filter(
        user=user,
        store=instance.store,
        status='open'
    ).order_by('-opening_time').first()
    
    if session:
        # Create cash drawer transaction
        CashDrawerTransaction.objects.create(
            session=session,
            transaction_type='sale',
            payment_method=instance.payment_mode,
            amount=instance.total_amount,
            reference=f"Product Sale #{instance.product_sale_number or instance.id}",
            notes=f"Product sale to {instance.customer}",
            user=user
        )
        
        # Link the session to the sale
        instance.cash_drawer_session = session
        instance.save(update_fields=['cash_drawer_session'])
    else:
        print(f"Warning: No open cash drawer session found for product sale #{instance.id}")

print("Product sale transaction signal connected")
@receiver(post_save, sender=ServiceSale)
def create_cashdrawer_transaction(sender, instance, created, **kwargs):
    """
    Create a cash drawer transaction when a service sale is paid in full
    """
    # Only proceed if the sale is being updated (not created) and is now paid
    if not created and instance.paid_status == 'paid':
        with transaction.atomic():
            try:
                if not instance.created_by:
                    raise ValueError("No user associated with this sale")
                
                # Get the active cash drawer session for this user and store
                cash_drawer = CashDrawerSession.objects.get(
                    user=instance.created_by,
                    store=instance.store,
                    status='open'
                )
                
                # Check if a transaction already exists for this sale
                if not CashDrawerTransaction.objects.filter(service_sale=instance).exists():

                    # Map payment methods to cash drawer transaction methods
                    payment_method_mapping = {
                        'cash': 'cash',
                        'mobile_money': 'mtn_momo',
                        'airtel_money': 'airtel_money',
                        'bank_transfer': 'bank_transfer',
                    }
                    
                    # Get the payment method from the sale's payments if available
                    payment_method = None
                    if hasattr(instance, 'payments') and instance.payments.exists():
                        # Get the most recent payment method
                        latest_payment = instance.payments.latest('payment_date')
                        payment_method = payment_method_mapping.get(
                            latest_payment.payment_method.lower(),
                            'other'
                        )
                    else:
                        # Fall back to the sale's payment_mode
                        payment_method = payment_method_mapping.get(
                            (instance.payment_mode or 'cash').lower(),
                            'cash'  # Default to cash if no mapping found
                        )
                    
                    # Create the cash drawer transaction
                    CashDrawerTransaction.objects.create(
                        session=cash_drawer,
                        transaction_type='sale',
                        payment_method=payment_method,
                        amount=instance.total_amount,
                        service_sale=instance,
                        user=instance.created_by,
                        notes=f"Service sale #{instance.id}",
                        reference=f"SS-{instance.id}"
                    )
                    
            
                    # Update the cash drawer's balance
                    cash_drawer.current_balance += instance.total_amount
                    cash_drawer.save(update_fields=['current_balance'])
                    
            except CashDrawerSession.DoesNotExist:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"No active cash drawer session found for user {instance.created_by} and store {instance.store}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating cash drawer transaction: {str(e)}", exc_info=True)