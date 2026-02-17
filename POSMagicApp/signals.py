"""
Signal handlers for the loyalty points system
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import LoyaltySettings, Customer, CustomerLoyaltyTransaction
from accounts.models import ChartOfAccounts


@receiver(post_save, sender='production.ServiceSale')
def award_loyalty_points_service_sale(sender, instance, created, **kwargs):
    """Award loyalty points when a ServiceSale is created or updated"""
    if not created or not instance.customer:
        return
    
    # Only award points for completed/paid sales
    if hasattr(instance, 'status') and instance.status not in ['COMPLETED', 'PAID']:
        return
    
    # Get loyalty settings
    loyalty_settings = LoyaltySettings.get_current_settings()
    if not loyalty_settings or not loyalty_settings.is_active:
        return
    
    # Calculate points based on total amount
    total_amount = getattr(instance, 'total_amount', 0) or getattr(instance, 'amount', 0)
    if not total_amount:
        return
    
    points = loyalty_settings.calculate_order_points(
        order_amount=total_amount,
        customer=instance.customer,
        order_date=instance.created_at if hasattr(instance, 'created_at') else timezone.now()
    )
    
    if points > 0:
        # Award points to customer
        instance.customer.add_loyalty_points(
            points=points,
            transaction_type='EARNED',
            order_reference=f"ServiceSale-{instance.id}",
            description=f"Points earned from service sale #{getattr(instance, 'service_sale_number', instance.id)}",
            created_by=getattr(instance, 'created_by', None)
        )


@receiver(post_save, sender='production.StoreSale')
def award_loyalty_points_store_sale(sender, instance, created, **kwargs):
    """Award loyalty points when a StoreSale is created or updated"""
    if not created or not instance.customer:
        return
    
    # Only award points for completed/paid sales
    if hasattr(instance, 'status') and instance.status not in ['COMPLETED', 'PAID']:
        return
    
    # Get loyalty settings
    loyalty_settings = LoyaltySettings.get_current_settings()
    if not loyalty_settings or not loyalty_settings.is_active:
        return
    
    # Calculate points based on total amount
    total_amount = getattr(instance, 'total_amount', 0) or getattr(instance, 'amount', 0)
    if not total_amount:
        return
    
    points = loyalty_settings.calculate_order_points(
        order_amount=total_amount,
        customer=instance.customer,
        order_date=instance.created_at if hasattr(instance, 'created_at') else timezone.now()
    )
    
    if points > 0:
        # Award points to customer
        instance.customer.add_loyalty_points(
            points=points,
            transaction_type='EARNED',
            order_reference=f"StoreSale-{instance.id}",
            description=f"Points earned from store sale #{instance.id}",
            created_by=getattr(instance, 'created_by', None)
        )



# Birthday bonus points signal
@receiver(post_save, sender=Customer)
def check_birthday_bonus(sender, instance, created, **kwargs):
    """Check if today is customer's birthday and award bonus points"""
    if not instance.date_of_birth:
        return
    
    today = timezone.now().date()
    if (instance.date_of_birth.month == today.month and 
        instance.date_of_birth.day == today.day):
        
        # Check if birthday bonus already awarded this year
        current_year = today.year
        existing_bonus = CustomerLoyaltyTransaction.objects.filter(
            customer=instance,
            transaction_type='BONUS',
            description__icontains='birthday',
            created_at__year=current_year
        ).exists()
        
        if not existing_bonus:
            loyalty_settings = LoyaltySettings.get_current_settings()
            if loyalty_settings and loyalty_settings.is_active:
                # Award birthday bonus points
                birthday_points = int(loyalty_settings.points_per_order * loyalty_settings.birthday_bonus_multiplier)
                instance.add_loyalty_points(
                    points=birthday_points,
                    transaction_type='BONUS',
                    description=f"Happy Birthday! Bonus points for {current_year}",
                )

# POSMagicApp/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Staff

@receiver(post_save, sender=Staff)
def create_staff_commission_account(sender, instance, created, **kwargs):
    _ensure_staff_commission_account(instance)


def _ensure_staff_commission_account(staff):
    """
    Get or create a per-staff Commission Payable sub-account.
    Account code format: 2110-{staff.pk:04d}  e.g. 2110-0003
    Parent is always account_code='2110' (Commission Payable)
    Returns the account or None if parent is missing.
    """

    try:
        parent = ChartOfAccounts.objects.get(account_code='2110')
    except ChartOfAccounts.DoesNotExist:
        import logging
        logging.getLogger(__name__).error(
            "Parent account 2110 (Commission Payable) not found. "
            f"Cannot create sub-account for staff {staff.pk}."
        )
        return None

    account_code = f"2110-{staff.pk:04d}"
    full_name = f"{staff.first_name} {staff.last_name}"

    account, created = ChartOfAccounts.objects.get_or_create(
        account_code=account_code,
        defaults={
            'account_name': f"Commissions Payable - {full_name}",
            'account_type': 'liability',
            'account_category': 'current_liability',
            'parent_account': parent,
            'description': (
                f"Commission payable account for {full_name} "
                f"({staff.specialization})"
            ),
            'is_active': True,
        }
    )

    if created:
        import logging
        logging.getLogger(__name__).info(
            f"Created commission account {account_code} for {full_name}"
        )

    return account