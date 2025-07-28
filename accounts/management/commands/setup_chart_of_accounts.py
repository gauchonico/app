from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import ChartOfAccounts, Department
from decimal import Decimal

class Command(BaseCommand):
    help = 'Set up initial chart of accounts and departments for POS Magic'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial chart of accounts...')
        
        # Create standard chart of accounts
        accounts_data = [
            # Assets (1000-1999)
            {'code': '1000', 'name': 'Cash', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1100', 'name': 'Accounts Receivable', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1200', 'name': 'Inventory', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1300', 'name': 'Prepaid Expenses', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1500', 'name': 'Equipment', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1600', 'name': 'Buildings', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1700', 'name': 'Accumulated Depreciation', 'type': 'asset', 'category': 'fixed_asset'},
            
            # Liabilities (2000-2999)
            {'code': '2000', 'name': 'Accounts Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2100', 'name': 'Accrued Expenses', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2200', 'name': 'Notes Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2500', 'name': 'Long-term Loans', 'type': 'liability', 'category': 'long_term_liability'},
            
            # Equity (3000-3999)
            {'code': '3000', 'name': 'Owner Capital', 'type': 'equity', 'category': 'owner_equity'},
            {'code': '3100', 'name': 'Owner Drawings', 'type': 'equity', 'category': 'owner_equity'},
            {'code': '3200', 'name': 'Retained Earnings', 'type': 'equity', 'category': 'retained_earnings'},
            
            # Revenue (4000-4999)
            {'code': '4000', 'name': 'Service Revenue', 'type': 'revenue', 'category': 'operating_revenue'},
            {'code': '4100', 'name': 'Product Sales', 'type': 'revenue', 'category': 'operating_revenue'},
            {'code': '4200', 'name': 'Other Revenue', 'type': 'revenue', 'category': 'other_revenue'},
            
            # Expenses (5000-5999)
            {'code': '5000', 'name': 'Cost of Goods Sold', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5100', 'name': 'Raw Materials', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5200', 'name': 'Direct Labor', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5300', 'name': 'Manufacturing Overhead', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            
            # Operating Expenses (6000-6999)
            {'code': '6000', 'name': 'Salaries and Wages', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6100', 'name': 'Rent Expense', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6200', 'name': 'Utilities', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6300', 'name': 'Office Supplies', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6400', 'name': 'Advertising', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6500', 'name': 'Insurance', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6600', 'name': 'Maintenance and Repairs', 'type': 'expense', 'category': 'operating_expense'},
            
            # Administrative Expenses (7000-7999)
            {'code': '7000', 'name': 'Professional Fees', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7100', 'name': 'Legal Fees', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7200', 'name': 'Accounting Fees', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7300', 'name': 'Bank Charges', 'type': 'expense', 'category': 'administrative_expense'},
            
            # Financial Expenses (8000-8999)
            {'code': '8000', 'name': 'Interest Expense', 'type': 'expense', 'category': 'financial_expense'},
            {'code': '8100', 'name': 'Bank Fees', 'type': 'expense', 'category': 'financial_expense'},
        ]
        
        created_count = 0
        for account_data in accounts_data:
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
        
        self.stdout.write(f'Created {created_count} new accounts')
        
        # Create default departments
        departments_data = [
            {'code': 'PROD', 'name': 'Production', 'description': 'Manufacturing and production activities'},
            {'code': 'SALES', 'name': 'Sales', 'description': 'Sales and marketing activities'},
            {'code': 'ADMIN', 'name': 'Administration', 'description': 'Administrative and management activities'},
            {'code': 'FIN', 'name': 'Finance', 'description': 'Financial and accounting activities'},
            {'code': 'HR', 'name': 'Human Resources', 'description': 'Human resources and personnel management'},
        ]
        
        dept_created_count = 0
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults={
                    'name': dept_data['name'],
                    'description': dept_data['description'],
                    'is_active': True,
                }
            )
            if created:
                dept_created_count += 1
                self.stdout.write(f'Created department: {dept.code} - {dept.name}')
        
        self.stdout.write(f'Created {dept_created_count} new departments')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up initial chart of accounts and departments!')
        ) 