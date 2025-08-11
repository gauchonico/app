from django.core.management.base import BaseCommand
from django.db import transaction
from production.models import PaymentVoucher
from accounts.models import ChartOfAccounts


class Command(BaseCommand):
    help = 'Migrate existing payment vouchers to use Chart of Accounts'

    def handle(self, *args, **options):
        self.stdout.write('Starting payment voucher migration...')
        
        # Get default accounts with more specific filtering
        try:
            # Get Cash account (prefer exact match first, then contains)
            try:
                cash_account = ChartOfAccounts.objects.get(account_name__iexact='cash')
            except ChartOfAccounts.DoesNotExist:
                cash_account = ChartOfAccounts.objects.filter(
                    account_name__icontains='cash',
                    account_type='asset'
                ).first()
            
            # Get Bank account 
            try:
                bank_account = ChartOfAccounts.objects.get(account_name__icontains='bank')
            except ChartOfAccounts.MultipleObjectsReturned:
                bank_account = ChartOfAccounts.objects.filter(
                    account_name__icontains='bank',
                    account_type='asset'
                ).first()
            
            # Get Accounts Payable (be more specific)
            try:
                payable_account = ChartOfAccounts.objects.get(account_name__iexact='accounts payable')
            except ChartOfAccounts.DoesNotExist:
                try:
                    payable_account = ChartOfAccounts.objects.get(account_name__icontains='accounts payable')
                except ChartOfAccounts.MultipleObjectsReturned:
                    payable_account = ChartOfAccounts.objects.filter(
                        account_name__icontains='payable',
                        account_type='liability'
                    ).first()
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error finding accounts: {e}. Please ensure you have Cash, Bank, and Accounts Payable accounts set up.'
                )
            )
            return
        
        # Check if we found all required accounts
        if not cash_account:
            self.stdout.write(self.style.ERROR('Cash account not found!'))
            return
        if not bank_account:
            self.stdout.write(self.style.ERROR('Bank account not found!'))
            return
        if not payable_account:
            self.stdout.write(self.style.ERROR('Accounts Payable account not found!'))
            return
        
        self.stdout.write('\nFound accounts:')
        self.stdout.write(f'Cash: {cash_account.account_code} - {cash_account.account_name}')
        self.stdout.write(f'Bank: {bank_account.account_code} - {bank_account.account_name}')
        self.stdout.write(f'Payable: {payable_account.account_code} - {payable_account.account_name}')
        
        # Update existing vouchers
        with transaction.atomic():
            vouchers_updated = 0
            vouchers_failed = 0
            
            for voucher in PaymentVoucher.objects.filter(payment_account__isnull=True):
                try:
                    # Set payment account based on legacy pay_by field
                    if voucher.pay_by == 'cash':
                        voucher.payment_account = cash_account
                    elif voucher.pay_by == 'bank':
                        voucher.payment_account = bank_account
                    elif voucher.pay_by == 'mobile':
                        voucher.payment_account = bank_account  # Default mobile to bank
                    else:
                        voucher.payment_account = payable_account  # Default fallback
                    
                    # Fix payment type validation issue
                    if voucher.payment_type == 'full' and voucher.lpo.requisition.total_cost:
                        # Check if this is actually a full payment
                        if voucher.amount_paid < voucher.lpo.requisition.total_cost:
                            # This should be marked as partial payment
                            voucher.payment_type = 'partial'
                            self.stdout.write(f'Corrected payment type for voucher {voucher.voucher_number}: full -> partial')
                    
                    voucher.save()
                    vouchers_updated += 1
                    
                    self.stdout.write(f'Updated voucher {voucher.voucher_number}: {voucher.pay_by} -> {voucher.payment_account.account_name}')
                    
                except Exception as e:
                    vouchers_failed += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Failed to update voucher {voucher.voucher_number}: {str(e)}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nMigration completed:'
                f'\n- Successfully migrated: {vouchers_updated} payment vouchers'
                f'\n- Failed: {vouchers_failed} payment vouchers'
            )
        ) 