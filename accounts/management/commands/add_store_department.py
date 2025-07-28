from django.core.management.base import BaseCommand
from accounts.models import Department, ChartOfAccounts

class Command(BaseCommand):
    help = 'Add store department and related accounts for store operations'

    def handle(self, *args, **options):
        self.stdout.write('Adding store department and related accounts...')
        
        # Create store department
        store_dept, created = Department.objects.get_or_create(
            code='STORE',
            defaults={
                'name': 'Store Operations',
                'description': 'Store management, inventory, and retail operations',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(f'Created department: {store_dept.code} - {store_dept.name}')
        else:
            self.stdout.write(f'Department already exists: {store_dept.code} - {store_dept.name}')
        
        # Add store-specific accounts
        store_accounts = [
            # Store-specific assets
            {'code': '1210', 'name': 'Store Inventory', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1220', 'name': 'Store Equipment', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1230', 'name': 'Store Supplies', 'type': 'asset', 'category': 'current_asset'},
            
            # Store-specific revenue
            {'code': '4110', 'name': 'Store Sales Revenue', 'type': 'revenue', 'category': 'operating_revenue'},
            {'code': '4120', 'name': 'Store Service Revenue', 'type': 'revenue', 'category': 'operating_revenue'},
            {'code': '4130', 'name': 'Store Commission Revenue', 'type': 'revenue', 'category': 'operating_revenue'},
            
            # Store-specific expenses
            {'code': '5010', 'name': 'Store Cost of Goods Sold', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5020', 'name': 'Store Inventory Loss', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5030', 'name': 'Store Shrinkage', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            
            # Store operating expenses
            {'code': '6700', 'name': 'Store Rent', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6710', 'name': 'Store Utilities', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6720', 'name': 'Store Security', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6730', 'name': 'Store Cleaning', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6740', 'name': 'Store Marketing', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6750', 'name': 'Store Staff Training', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6760', 'name': 'Store Equipment Maintenance', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6770', 'name': 'Store Insurance', 'type': 'expense', 'category': 'operating_expense'},
        ]
        
        created_count = 0
        for account_data in store_accounts:
            account, created = ChartOfAccounts.objects.get_or_create(
                account_code=account_data['code'],
                defaults={
                    'account_name': account_data['name'],
                    'account_type': account_data['type'],
                    'account_category': account_data['category'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created account: {account.account_code} - {account.account_name}')
        
        self.stdout.write(f'Created {created_count} new store-related accounts')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully added store department and related accounts!')
        ) 