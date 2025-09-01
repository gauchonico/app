from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from production.models import StaffCommission, StaffProductCommission, MonthlyStaffCommission
from .services import AccountingService

@receiver(post_save, sender=StaffCommission)
def create_service_commission_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when service commission is created"""
    if created:
        try:
            # Get a default user for system entries (could be admin or service user)
            user = User.objects.filter(is_superuser=True).first()
            if user:
                AccountingService.create_service_commission_journal_entry(instance, user)
            else:
                print("No superuser found for commission journal entry creation")
        except Exception as e:
            print(f"Error creating service commission journal entry: {e}")

@receiver(post_save, sender=StaffProductCommission)
def create_product_commission_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when product commission is created"""
    if created:
        try:
            # Get a default user for system entries
            user = User.objects.filter(is_superuser=True).first()
            if user:
                AccountingService.create_product_commission_journal_entry(instance, user)
            else:
                print("No superuser found for commission journal entry creation")
        except Exception as e:
            print(f"Error creating product commission journal entry: {e}")

@receiver(post_save, sender=MonthlyStaffCommission)
def create_commission_payment_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when monthly commission is paid"""
    if not created and instance.paid and instance.paid_date:
        # Only create journal entry when commission is marked as paid
        try:
            user = User.objects.filter(is_superuser=True).first()
            if user:
                # Determine payment method (default to cash, could be enhanced later)
                payment_method = 'cash'
                if 'mobile' in str(instance.payment_reference).lower():
                    payment_method = 'mobile_money'
                elif 'bank' in str(instance.payment_reference).lower():
                    payment_method = 'bank_transfer'
                
                AccountingService.create_commission_payment_journal_entry(
                    instance, user, payment_method
                )
            else:
                print("No superuser found for commission payment journal entry creation")
        except Exception as e:
            print(f"Error creating commission payment journal entry: {e}")
