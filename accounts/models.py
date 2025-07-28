from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import date, datetime
import uuid

class ChartOfAccounts(models.Model):
    """Chart of Accounts - Standard accounting structure"""
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    ACCOUNT_CATEGORIES = [
        # Assets
        ('current_asset', 'Current Asset'),
        ('fixed_asset', 'Fixed Asset'),
        ('intangible_asset', 'Intangible Asset'),
        
        # Liabilities
        ('current_liability', 'Current Liability'),
        ('long_term_liability', 'Long Term Liability'),
        
        # Equity
        ('owner_equity', 'Owner Equity'),
        ('retained_earnings', 'Retained Earnings'),
        
        # Revenue
        ('operating_revenue', 'Operating Revenue'),
        ('other_revenue', 'Other Revenue'),
        
        # Expenses
        ('cost_of_goods_sold', 'Cost of Goods Sold'),
        ('operating_expense', 'Operating Expense'),
        ('administrative_expense', 'Administrative Expense'),
        ('financial_expense', 'Financial Expense'),
    ]
    
    account_code = models.CharField(max_length=10, unique=True, help_text="Account number (e.g., 1000, 2000)")
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    account_category = models.CharField(max_length=30, choices=ACCOUNT_CATEGORIES)
    description = models.TextField(blank=True)
    parent_account = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_accounts')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['account_code']
        verbose_name_plural = "Chart of Accounts"
    
    def __str__(self):
        return f"{self.account_code} - {self.account_name}"
    
    @property
    def balance(self):
        """Calculate current balance for this account"""
        return self.journal_entries.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def is_debit_balance(self):
        """Check if account normally has debit balance"""
        return self.account_type in ['asset', 'expense']
    
    @property
    def is_credit_balance(self):
        """Check if account normally has credit balance"""
        return self.account_type in ['liability', 'equity', 'revenue']

class Department(models.Model):
    """Departments for budget allocation"""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def total_budget(self):
        """Get total budget for this department"""
        return self.budgets.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def total_spent(self):
        """Get total spent for this department"""
        return self.journal_entries.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def remaining_budget(self):
        """Calculate remaining budget"""
        return self.total_budget - self.total_spent

class Budget(models.Model):
    """Budget allocation for departments"""
    BUDGET_PERIODS = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='budgets')
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    period = models.CharField(max_length=20, choices=BUDGET_PERIODS, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['department', 'account', 'period', 'start_date']
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.department.name} - {self.account.account_name} - {self.amount}"
    
    @property
    def spent_amount(self):
        """Calculate amount spent against this budget"""
        return self.journal_entries.filter(
            date__gte=self.start_date,
            date__lte=self.end_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def remaining_amount(self):
        """Calculate remaining budget"""
        return self.amount - self.spent_amount
    
    @property
    def utilization_percentage(self):
        """Calculate budget utilization percentage"""
        if self.amount == 0:
            return 0
        return (self.spent_amount / self.amount) * 100

class JournalEntry(models.Model):
    """Journal entries for double-entry bookkeeping"""
    ENTRY_TYPES = [
        ('manual', 'Manual Entry'),
        ('system', 'System Generated'),
        ('production', 'Production Related'),
        ('sales', 'Sales Related'),
        ('purchase', 'Purchase Related'),
    ]
    
    entry_number = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField(default=date.today)
    reference = models.CharField(max_length=255, blank=True, help_text="Reference number or description")
    description = models.TextField()
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES, default='manual')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = "Journal Entries"
    
    def __str__(self):
        return f"JE-{self.entry_number} - {self.date} - {self.description[:50]}"
    
    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        super().save(*args, **kwargs)
    
    def generate_entry_number(self):
        """Generate unique journal entry number"""
        year = timezone.now().year
        count = JournalEntry.objects.filter(
            entry_number__startswith=f"JE-{year}"
        ).count() + 1
        return f"JE-{year}-{count:04d}"
    
    @property
    def total_debits(self):
        """Calculate total debits"""
        return self.entries.filter(entry_type='debit').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def total_credits(self):
        """Calculate total credits"""
        return self.entries.filter(entry_type='credit').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def is_balanced(self):
        """Check if debits equal credits"""
        return self.total_debits == self.total_credits
    
    def post_entry(self):
        """Post the journal entry"""
        if not self.is_balanced:
            raise ValueError("Journal entry must be balanced before posting")
        
        self.is_posted = True
        self.posted_at = timezone.now()
        self.save()

class JournalEntryLine(models.Model):
    """Individual lines in a journal entry"""
    ENTRY_TYPES = [
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ]
    
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='entries')
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.CASCADE, related_name='journal_entries')
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['entry_type', 'account__account_code']
    
    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.account_name} - {self.entry_type} {self.amount}"

class FinancialPeriod(models.Model):
    """Financial periods for reporting"""
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    def close_period(self, user):
        """Close the financial period"""
        self.is_closed = True
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save()

class TrialBalance(models.Model):
    """Trial balance for a specific period"""
    period = models.ForeignKey(FinancialPeriod, on_delete=models.CASCADE, related_name='trial_balances')
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.CASCADE)
    debit_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    credit_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['period', 'account']
        ordering = ['account__account_code']
    
    def __str__(self):
        return f"TB - {self.period.name} - {self.account.account_name}"
    
    @property
    def net_balance(self):
        """Calculate net balance (debit - credit)"""
        return self.debit_balance - self.credit_balance

class ProfitLossStatement(models.Model):
    """Profit and Loss statement for a period"""
    period = models.ForeignKey(FinancialPeriod, on_delete=models.CASCADE, related_name='profit_loss_statements')
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    cost_of_goods_sold = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    operating_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    operating_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    other_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    other_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['period']
        ordering = ['-period__start_date']
    
    def __str__(self):
        return f"P&L - {self.period.name} - Net Income: {self.net_income}"
    
    def calculate_totals(self):
        """Calculate P&L totals"""
        self.gross_profit = self.revenue - self.cost_of_goods_sold
        self.operating_income = self.gross_profit - self.operating_expenses
        self.net_income = self.operating_income + self.other_income - self.other_expenses
        self.save()

class BalanceSheet(models.Model):
    """Balance sheet for a specific date"""
    as_of_date = models.DateField()
    # Assets
    current_assets = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    fixed_assets = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Liabilities
    current_liabilities = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    long_term_liabilities = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_liabilities = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Equity
    owner_equity = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    retained_earnings = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_equity = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['as_of_date']
        ordering = ['-as_of_date']
    
    def __str__(self):
        return f"Balance Sheet - {self.as_of_date}"
    
    def calculate_totals(self):
        """Calculate balance sheet totals"""
        self.total_assets = self.current_assets + self.fixed_assets
        self.total_liabilities = self.current_liabilities + self.long_term_liabilities
        self.total_equity = self.owner_equity + self.retained_earnings
        self.save()
    
    @property
    def is_balanced(self):
        """Check if assets = liabilities + equity"""
        return self.total_assets == (self.total_liabilities + self.total_equity)

# Integration models to link with production system
class ProductionExpense(models.Model):
    """Link production requisitions to accounting"""
    requisition = models.ForeignKey('production.Requisition', on_delete=models.CASCADE, related_name='accounting_entries')
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='production_expenses')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['requisition', 'journal_entry']
    
    def __str__(self):
        return f"Production Expense - {self.requisition.requisition_no} - {self.amount}"

class SalesRevenue(models.Model):
    """Link sales to accounting"""
    service_sale = models.ForeignKey('production.ServiceSale', on_delete=models.CASCADE, related_name='accounting_entries', null=True, blank=True)
    store_sale = models.ForeignKey('production.StoreSale', on_delete=models.CASCADE, related_name='accounting_entries', null=True, blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='sales_revenues')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['journal_entry']
    
    def __str__(self):
        sale_ref = self.service_sale.service_sale_number if self.service_sale else self.store_sale.id
        return f"Sales Revenue - {sale_ref} - {self.amount}"

class StoreTransfer(models.Model):
    """Link store transfers to accounting"""
    transfer = models.ForeignKey('production.StoreTransfer', on_delete=models.CASCADE, related_name='accounting_entries', null=True, blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='store_transfers')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transfer_type = models.CharField(max_length=20, choices=[
        ('production_to_store', 'Production to Store'),
        ('store_to_store', 'Store to Store'),
        ('store_to_salon', 'Store to Salon'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['transfer', 'journal_entry']
    
    def __str__(self):
        return f"Store Transfer - {self.transfer_type} - {self.amount}"

class ManufacturingRecord(models.Model):
    """Link manufacturing records to accounting"""
    manufacture_product = models.ForeignKey('production.ManufacturedProductInventory', on_delete=models.CASCADE, related_name='accounting_entries', null=True, blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='manufacturing_records')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['manufacture_product', 'journal_entry']
    
    def __str__(self):
        return f"Manufacturing - {self.manufacture_product.batch_number if self.manufacture_product else 'N/A'} - {self.amount}"

class PaymentRecord(models.Model):
    """Link payment vouchers to accounting"""
    payment_voucher = models.ForeignKey('production.PaymentVoucher', on_delete=models.CASCADE, related_name='accounting_entries', null=True, blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='payment_records')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['payment_voucher', 'journal_entry']
    
    def __str__(self):
        return f"Payment - {self.payment_voucher.voucher_number if self.payment_voucher else 'N/A'} - {self.amount}"

class StoreBudget(models.Model):
    """Store-specific budget tracking"""
    store = models.ForeignKey('production.Store', on_delete=models.CASCADE, related_name='budgets')
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.CASCADE, related_name='store_budgets')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    period = models.CharField(max_length=20, choices=Budget.BUDGET_PERIODS, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['store', 'account', 'period', 'start_date']
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.store.name} - {self.account.account_name} - {self.amount}"
    
    @property
    def spent_amount(self):
        """Calculate amount spent against this store budget"""
        return self.journal_entries.filter(
            date__gte=self.start_date,
            date__lte=self.end_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def remaining_amount(self):
        """Calculate remaining budget"""
        return self.amount - self.spent_amount
    
    @property
    def utilization_percentage(self):
        """Calculate budget utilization percentage"""
        if self.amount == 0:
            return 0
        return (self.spent_amount / self.amount) * 100

class StoreFinancialSummary(models.Model):
    """Store financial summary for reporting"""
    store = models.ForeignKey('production.Store', on_delete=models.CASCADE, related_name='financial_summaries')
    date = models.DateField()
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    operating_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['store', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.store.name} - {self.date} - Net Profit: {self.net_profit}"
    
    def calculate_totals(self):
        """Calculate financial totals"""
        self.gross_profit = self.total_sales - self.total_cost
        self.net_profit = self.gross_profit - self.operating_expenses
        self.save()
