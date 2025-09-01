from django.core.management.base import BaseCommand
from accounts.models import ChartOfAccounts

class Command(BaseCommand):
    help = 'Set up comprehensive chart of accounts aligned with LIVARA business model'

    def handle(self, *args, **options):
        self.stdout.write('Setting up LIVARA Chart of Accounts...')
        
        # LIVARA Business Model Chart of Accounts
        accounts = [
            # ========== ASSETS (1000-1999) ==========
            
            # Current Assets (1000-1299)
            {'code': '1000', 'name': 'Cash on Hand', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1010', 'name': 'Mobile Money (MTN/Airtel)', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1020', 'name': 'Bank Account - Operations', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1025', 'name': 'Bank Account - Savings', 'type': 'asset', 'category': 'current_asset'},
            
            # Accounts Receivable (1100-1199)
            {'code': '1100', 'name': 'Accounts Receivable - Store Sales', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1110', 'name': 'Accounts Receivable - Service Sales', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1120', 'name': 'Staff Advances', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1130', 'name': 'Prepaid Supplier Payments', 'type': 'asset', 'category': 'current_asset'},
            
            # Inventory Assets (1200-1299)
            {'code': '1200', 'name': 'Raw Materials Inventory - Main Store', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1210', 'name': 'Work in Process Inventory', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1220', 'name': 'Finished Goods Inventory', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1230', 'name': 'Store Inventory - Products', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1240', 'name': 'Accessories Inventory', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1250', 'name': 'Packaging Materials', 'type': 'asset', 'category': 'current_asset'},
            {'code': '1260', 'name': 'Inventory in Transit', 'type': 'asset', 'category': 'current_asset'},
            
            # Fixed Assets (1500-1699)
            {'code': '1500', 'name': 'Manufacturing Equipment', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1510', 'name': 'Store Equipment & Fixtures', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1520', 'name': 'Computer Equipment', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1530', 'name': 'Furniture & Office Equipment', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1540', 'name': 'Vehicles', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1600', 'name': 'Buildings & Improvements', 'type': 'asset', 'category': 'fixed_asset'},
            
            # Accumulated Depreciation (1700-1799)
            {'code': '1700', 'name': 'Accumulated Depreciation - Equipment', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1710', 'name': 'Accumulated Depreciation - Vehicles', 'type': 'asset', 'category': 'fixed_asset'},
            {'code': '1720', 'name': 'Accumulated Depreciation - Buildings', 'type': 'asset', 'category': 'fixed_asset'},
            
            # ========== LIABILITIES (2000-2999) ==========
            
            # Current Liabilities (2000-2299)
            {'code': '2000', 'name': 'Accounts Payable - Suppliers', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2010', 'name': 'Accrued Expenses', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2020', 'name': 'VAT Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2030', 'name': 'Withholding Tax Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2040', 'name': 'PAYE Tax Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2050', 'name': 'NSSF Payable', 'type': 'liability', 'category': 'current_liability'},
            
            # Staff Liabilities (2100-2199)
            {'code': '2100', 'name': 'Salaries & Wages Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2110', 'name': 'Commission Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2115', 'name': 'Monthly Commission Payable', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2120', 'name': 'Staff Bonuses Payable', 'type': 'liability', 'category': 'current_liability'},
            
            # Customer Liabilities (2200-2299)
            {'code': '2200', 'name': 'Customer Deposits', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2210', 'name': 'Customer Prepayments', 'type': 'liability', 'category': 'current_liability'},
            {'code': '2220', 'name': 'Gift Card Liabilities', 'type': 'liability', 'category': 'current_liability'},
            
            # Long-term Liabilities (2500-2999)
            {'code': '2500', 'name': 'Long-term Loans', 'type': 'liability', 'category': 'long_term_liability'},
            {'code': '2510', 'name': 'Equipment Financing', 'type': 'liability', 'category': 'long_term_liability'},
            
            # ========== EQUITY (3000-3999) ==========
            {'code': '3000', 'name': 'Owner Capital', 'type': 'equity', 'category': 'owner_equity'},
            {'code': '3100', 'name': 'Owner Drawings', 'type': 'equity', 'category': 'owner_equity'},
            {'code': '3200', 'name': 'Retained Earnings', 'type': 'equity', 'category': 'retained_earnings'},
            {'code': '3300', 'name': 'Current Year Earnings', 'type': 'equity', 'category': 'retained_earnings'},
            
            # ========== REVENUE (4000-4999) ==========
            
            # Sales Revenue (4100-4199)
            {'code': '4100', 'name': 'Store Sales Revenue - Products', 'type': 'revenue', 'category': 'operating_revenue'},
            {'code': '4110', 'name': 'Service Sales Revenue', 'type': 'revenue', 'category': 'operating_revenue'},
            {'code': '4120', 'name': 'Accessory Sales Revenue', 'type': 'revenue', 'category': 'operating_revenue'},
            {'code': '4130', 'name': 'Commission Revenue (Received)', 'type': 'revenue', 'category': 'operating_revenue'},
            
            # Other Revenue (4200-4999)
            {'code': '4200', 'name': 'Interest Income', 'type': 'revenue', 'category': 'other_revenue'},
            {'code': '4210', 'name': 'Foreign Exchange Gains', 'type': 'revenue', 'category': 'other_revenue'},
            {'code': '4220', 'name': 'Rental Income', 'type': 'revenue', 'category': 'other_revenue'},
            {'code': '4230', 'name': 'Miscellaneous Income', 'type': 'revenue', 'category': 'other_revenue'},
            
            # ========== COST OF GOODS SOLD (5000-5999) ==========
            
            # Manufacturing Costs (5000-5199)
            {'code': '5000', 'name': 'Raw Materials Used', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5010', 'name': 'Direct Labor - Manufacturing', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5020', 'name': 'Manufacturing Overhead', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5030', 'name': 'Packaging Costs', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5040', 'name': 'Quality Control Costs', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5050', 'name': 'Production Utilities', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            
            # Inventory Adjustments (5100-5199)
            {'code': '5100', 'name': 'Inventory Write-offs', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5110', 'name': 'Inventory Shrinkage', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5120', 'name': 'Damaged Goods', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            {'code': '5130', 'name': 'Expired Products', 'type': 'expense', 'category': 'cost_of_goods_sold'},
            
            # ========== OPERATING EXPENSES (6000-6999) ==========
            
            # Staff Expenses (6000-6199)
            {'code': '6000', 'name': 'Salaries & Wages', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6010', 'name': 'Staff Commission Expense', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6015', 'name': 'Service Commission Expense', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6016', 'name': 'Product Commission Expense', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6020', 'name': 'Staff Bonuses', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6030', 'name': 'NSSF Contributions', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6040', 'name': 'Staff Training', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6050', 'name': 'Staff Welfare', 'type': 'expense', 'category': 'operating_expense'},
            
            # Store Operations (6200-6399)
            {'code': '6200', 'name': 'Store Rent', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6210', 'name': 'Store Utilities', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6220', 'name': 'Store Security', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6230', 'name': 'Store Cleaning', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6240', 'name': 'Store Maintenance', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6250', 'name': 'Store Supplies', 'type': 'expense', 'category': 'operating_expense'},
            
            # Manufacturing Operations (6400-6599)
            {'code': '6400', 'name': 'Factory Rent', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6410', 'name': 'Factory Utilities', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6420', 'name': 'Equipment Maintenance', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6430', 'name': 'Factory Supplies', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6440', 'name': 'Safety Equipment', 'type': 'expense', 'category': 'operating_expense'},
            
            # Marketing & Sales (6600-6799)
            {'code': '6600', 'name': 'Advertising', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6610', 'name': 'Social Media Marketing', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6620', 'name': 'Promotional Materials', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6630', 'name': 'Trade Shows & Events', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6640', 'name': 'Website & E-commerce', 'type': 'expense', 'category': 'operating_expense'},
            
            # Transportation & Logistics (6800-6899)
            {'code': '6800', 'name': 'Delivery Expenses', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6810', 'name': 'Fuel & Vehicle Expenses', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6820', 'name': 'Shipping & Courier', 'type': 'expense', 'category': 'operating_expense'},
            {'code': '6830', 'name': 'Vehicle Maintenance', 'type': 'expense', 'category': 'operating_expense'},
            
            # ========== ADMINISTRATIVE EXPENSES (7000-7999) ==========
            {'code': '7000', 'name': 'Office Rent', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7010', 'name': 'Office Supplies', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7020', 'name': 'Telephone & Internet', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7030', 'name': 'Professional Fees', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7040', 'name': 'Legal Fees', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7050', 'name': 'Accounting Fees', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7060', 'name': 'Insurance', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7070', 'name': 'Licenses & Permits', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7080', 'name': 'Software Subscriptions', 'type': 'expense', 'category': 'administrative_expense'},
            {'code': '7090', 'name': 'Depreciation Expense', 'type': 'expense', 'category': 'administrative_expense'},
            
            # ========== FINANCIAL EXPENSES (8000-8999) ==========
            {'code': '8000', 'name': 'Interest Expense', 'type': 'expense', 'category': 'financial_expense'},
            {'code': '8010', 'name': 'Bank Charges', 'type': 'expense', 'category': 'financial_expense'},
            {'code': '8020', 'name': 'Foreign Exchange Losses', 'type': 'expense', 'category': 'financial_expense'},
            {'code': '8030', 'name': 'Late Payment Penalties', 'type': 'expense', 'category': 'financial_expense'},
        ]
        
        created_count = 0
        updated_count = 0
        
        for account_data in accounts:
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
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created: {account.account_code} - {account.account_name}'
                    )
                )
            else:
                # Update existing account
                account.account_name = account_data['name']
                account.account_type = account_data['type']
                account.account_category = account_data['category']
                account.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Updated: {account.account_code} - {account.account_name}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\\nLIVARA Chart of Accounts setup complete!'
            )
        )
        self.stdout.write(f'Created: {created_count} accounts')
        self.stdout.write(f'Updated: {updated_count} accounts')
        self.stdout.write(f'Total: {created_count + updated_count} accounts configured')
