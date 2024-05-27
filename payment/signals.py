from django.db.models.signals import post_save, pre_delete
from .models import StaffCommission, Transaction

def update_staff_commission(sender, instance, created, **kwargs):
    if created:  # Handle new transactions (same logic as before)
        commission_amount = instance.total_amount * instance.commission_percentage / 100
        StaffCommission.objects.create(
            staff=instance.staff,
            transaction=instance,
            commission_amount=commission_amount
        )
    else:  # Update existing staff commission if transaction changes
        try:
            original_commission = StaffCommission.objects.get(transaction=instance)
            # Calculate difference in commission amount due to transaction changes
            commission_difference = (instance.total_amount * instance.commission_percentage / 100) - original_commission.commission_amount
            original_commission.commission_amount += commission_difference
            original_commission.save()
        except StaffCommission.DoesNotExist:
            # No staff commission existed for this transaction, likely created after the initial save
            pass  # Consider logging or handling this scenario as needed

def delete_staff_commission(sender, instance, **kwargs):
    # Delete associated staff commission when a transaction is deleted
    StaffCommission.objects.filter(transaction=instance).delete()

post_save.connect(update_staff_commission, sender=Transaction)
pre_delete.connect(delete_staff_commission, sender=Transaction)