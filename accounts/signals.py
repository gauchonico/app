from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from accounts.services import AccountingService
from production.models import StoreSale, Requisition, StoreTransfer, ManufactureProduct, PaymentVoucher

@receiver(post_save, sender=StoreSale)
def create_sales_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a store sale is created"""
    if created and instance.total_amount:
        # Get the user who created the sale (you might need to adjust this based on your user tracking)
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            AccountingService.create_sales_journal_entry(instance, admin_user)

@receiver(post_save, sender=Requisition)
def create_requisition_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a requisition is approved"""
    if instance.status in ['approved', 'checking', 'delivered'] and instance.total_cost:
        # Check if already synced
        if not hasattr(instance, 'accounting_entries') or not instance.accounting_entries.exists():
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                AccountingService.create_requisition_expense_journal_entry(instance, admin_user)

@receiver(post_save, sender=ManufactureProduct)
def create_manufacturing_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a product is manufactured"""
    if created:
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            AccountingService.create_manufacturing_journal_entry(instance, admin_user)

@receiver(post_save, sender=StoreTransfer)
def create_store_transfer_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a store transfer is completed"""
    if instance.status == 'Completed':
        # Check if already synced
        if not hasattr(instance, 'accounting_entries') or not instance.accounting_entries.exists():
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                AccountingService.create_store_transfer_journal_entry(instance, admin_user)

@receiver(post_save, sender=PaymentVoucher)
def create_payment_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a payment voucher is created"""
    if created:
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            AccountingService.create_payment_journal_entry(instance, admin_user) 