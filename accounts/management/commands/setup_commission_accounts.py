from django.core.management.base import BaseCommand
from accounts.models import ChartOfAccounts

class Command(BaseCommand):
    help = 'Set up commission-related accounts in chart of accounts'

    def handle(self, *args, **options):
        self.stdout.write('Setting up commission-related accounts...')
        
        # Commission-related accounts
        commission_accounts = [
            # Commission Expenses
            {
                'code': '6010', 
                'name': 'Staff Commission Expense', 
                'type': 'expense', 
                'category': 'operating_expense',
                'description': 'Commission expenses paid to staff for services and product sales'
            },
            {
                'code': '6015', 
                'name': 'Service Commission Expense', 
                'type': 'expense', 
                'category': 'operating_expense',
                'description': 'Commission expenses for service sales'
            },
            {
                'code': '6016', 
                'name': 'Product Commission Expense', 
                'type': 'expense', 
                'category': 'operating_expense',
                'description': 'Commission expenses for product sales'
            },
            
            # Commission Liabilities (Payables)
            {
                'code': '2110', 
                'name': 'Commission Payable', 
                'type': 'liability', 
                'category': 'current_liability',
                'description': 'Outstanding commission amounts owed to staff'
            },
            {
                'code': '2115', 
                'name': 'Monthly Commission Payable', 
                'type': 'liability', 
                'category': 'current_liability',
                'description': 'Monthly compiled commission amounts owed to staff'
            },
            
            # Additional Cash Accounts if needed
            {
                'code': '1010', 
                'name': 'Mobile Money', 
                'type': 'asset', 
                'category': 'current_asset',
                'description': 'Mobile money accounts and balances'
            },
            {
                'code': '1020', 
                'name': 'Bank Account', 
                'type': 'asset', 
                'category': 'current_asset',
                'description': 'Bank account balances'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for account_data in commission_accounts:
            account, created = ChartOfAccounts.objects.get_or_create(
                account_code=account_data['code'],
                defaults={
                    'account_name': account_data['name'],
                    'account_type': account_data['type'],
                    'account_category': account_data['category'],
                    'description': account_data['description'],
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created account: {account.account_code} - {account.account_name}'
                    )
                )
            else:
                # Update existing account if needed
                account.account_name = account_data['name']
                account.description = account_data['description']
                account.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Updated existing account: {account.account_code} - {account.account_name}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Commission accounts setup complete! Created: {created_count}, Updated: {updated_count}'
            )
        )
