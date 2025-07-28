from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from decimal import Decimal
from .models import (
    ChartOfAccounts, Department, Budget, JournalEntry, JournalEntryLine,
    FinancialPeriod, TrialBalance, ProfitLossStatement, BalanceSheet,
    ProductionExpense, SalesRevenue
)

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ['account_code', 'account_name', 'account_type', 'account_category', 'balance', 'is_active']
    list_filter = ['account_type', 'account_category', 'is_active', 'created_at']
    search_fields = ['account_code', 'account_name', 'description']
    ordering = ['account_code']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('account_code', 'account_name', 'account_type', 'account_category')
        }),
        ('Details', {
            'fields': ('description', 'parent_account', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'manager', 'total_budget', 'total_spent', 'remaining_budget', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    readonly_fields = ['created_at']
    
    def total_budget(self, obj):
        return f"UGX {obj.total_budget:,.2f}"
    total_budget.short_description = 'Total Budget'
    
    def total_spent(self, obj):
        return f"UGX {obj.total_spent:,.2f}"
    total_spent.short_description = 'Total Spent'
    
    def remaining_budget(self, obj):
        return f"UGX {obj.remaining_budget:,.2f}"
    remaining_budget.short_description = 'Remaining Budget'

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['department', 'account', 'amount', 'period', 'start_date', 'end_date', 'spent_amount', 'remaining_amount', 'utilization_percentage', 'is_active']
    list_filter = ['department', 'period', 'is_active', 'start_date', 'end_date']
    search_fields = ['department__name', 'account__account_name', 'description']
    ordering = ['-start_date']
    readonly_fields = ['created_at', 'spent_amount', 'remaining_amount', 'utilization_percentage']
    
    def spent_amount(self, obj):
        return f"UGX {obj.spent_amount:,.2f}"
    spent_amount.short_description = 'Spent Amount'
    
    def remaining_amount(self, obj):
        return f"UGX {obj.remaining_amount:,.2f}"
    remaining_amount.short_description = 'Remaining Amount'
    
    def utilization_percentage(self, obj):
        return f"{obj.utilization_percentage:.1f}%"
    utilization_percentage.short_description = 'Utilization %'

class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 2
    fields = ['account', 'entry_type', 'amount', 'description']

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'date', 'description', 'entry_type', 'department', 'total_debits', 'total_credits', 'is_balanced', 'is_posted', 'created_by']
    list_filter = ['entry_type', 'is_posted', 'date', 'department', 'created_at']
    search_fields = ['entry_number', 'description', 'reference']
    ordering = ['-date', '-created_at']
    readonly_fields = ['entry_number', 'created_at', 'posted_at', 'total_debits', 'total_credits', 'is_balanced']
    inlines = [JournalEntryLineInline]
    
    fieldsets = (
        ('Entry Information', {
            'fields': ('entry_number', 'date', 'reference', 'description', 'entry_type', 'department')
        }),
        ('Status', {
            'fields': ('is_posted', 'posted_at', 'created_by')
        }),
        ('Totals', {
            'fields': ('total_debits', 'total_credits', 'is_balanced'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def total_debits(self, obj):
        return f"UGX {obj.total_debits:,.2f}"
    total_debits.short_description = 'Total Debits'
    
    def total_credits(self, obj):
        return f"UGX {obj.total_credits:,.2f}"
    total_credits.short_description = 'Total Credits'
    
    def is_balanced(self, obj):
        if obj.is_balanced:
            return format_html('<span style="color: green;">✓ Balanced</span>')
        else:
            return format_html('<span style="color: red;">✗ Unbalanced</span>')
    is_balanced.short_description = 'Balanced'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new entries
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_closed', 'closed_by', 'created_at']
    list_filter = ['is_closed', 'start_date', 'end_date']
    search_fields = ['name']
    ordering = ['-start_date']
    readonly_fields = ['created_at', 'closed_at']

@admin.register(TrialBalance)
class TrialBalanceAdmin(admin.ModelAdmin):
    list_display = ['period', 'account', 'debit_balance', 'credit_balance', 'net_balance', 'created_at']
    list_filter = ['period', 'account__account_type', 'created_at']
    search_fields = ['account__account_name', 'period__name']
    ordering = ['period__start_date', 'account__account_code']
    readonly_fields = ['created_at']
    
    def debit_balance(self, obj):
        return f"UGX {obj.debit_balance:,.2f}"
    debit_balance.short_description = 'Debit Balance'
    
    def credit_balance(self, obj):
        return f"UGX {obj.credit_balance:,.2f}"
    credit_balance.short_description = 'Credit Balance'
    
    def net_balance(self, obj):
        return f"UGX {obj.net_balance:,.2f}"
    net_balance.short_description = 'Net Balance'

@admin.register(ProfitLossStatement)
class ProfitLossStatementAdmin(admin.ModelAdmin):
    list_display = ['period', 'revenue', 'cost_of_goods_sold', 'gross_profit', 'operating_expenses', 'operating_income', 'net_income', 'created_at']
    list_filter = ['period', 'created_at']
    search_fields = ['period__name']
    ordering = ['-period__start_date']
    readonly_fields = ['created_at']
    
    def revenue(self, obj):
        return f"UGX {obj.revenue:,.2f}"
    revenue.short_description = 'Revenue'
    
    def cost_of_goods_sold(self, obj):
        return f"UGX {obj.cost_of_goods_sold:,.2f}"
    cost_of_goods_sold.short_description = 'Cost of Goods Sold'
    
    def gross_profit(self, obj):
        return f"UGX {obj.gross_profit:,.2f}"
    gross_profit.short_description = 'Gross Profit'
    
    def operating_expenses(self, obj):
        return f"UGX {obj.operating_expenses:,.2f}"
    operating_expenses.short_description = 'Operating Expenses'
    
    def operating_income(self, obj):
        return f"UGX {obj.operating_income:,.2f}"
    operating_income.short_description = 'Operating Income'
    
    def net_income(self, obj):
        return f"UGX {obj.net_income:,.2f}"
    net_income.short_description = 'Net Income'

@admin.register(BalanceSheet)
class BalanceSheetAdmin(admin.ModelAdmin):
    list_display = ['as_of_date', 'current_assets', 'fixed_assets', 'total_assets', 'current_liabilities', 'long_term_liabilities', 'total_liabilities', 'total_equity', 'is_balanced', 'created_at']
    list_filter = ['as_of_date', 'created_at']
    search_fields = ['as_of_date']
    ordering = ['-as_of_date']
    readonly_fields = ['created_at', 'is_balanced']
    
    def current_assets(self, obj):
        return f"UGX {obj.current_assets:,.2f}"
    current_assets.short_description = 'Current Assets'
    
    def fixed_assets(self, obj):
        return f"UGX {obj.fixed_assets:,.2f}"
    fixed_assets.short_description = 'Fixed Assets'
    
    def total_assets(self, obj):
        return f"UGX {obj.total_assets:,.2f}"
    total_assets.short_description = 'Total Assets'
    
    def current_liabilities(self, obj):
        return f"UGX {obj.current_liabilities:,.2f}"
    current_liabilities.short_description = 'Current Liabilities'
    
    def long_term_liabilities(self, obj):
        return f"UGX {obj.long_term_liabilities:,.2f}"
    long_term_liabilities.short_description = 'Long Term Liabilities'
    
    def total_liabilities(self, obj):
        return f"UGX {obj.total_liabilities:,.2f}"
    total_liabilities.short_description = 'Total Liabilities'
    
    def total_equity(self, obj):
        return f"UGX {obj.total_equity:,.2f}"
    total_equity.short_description = 'Total Equity'
    
    def is_balanced(self, obj):
        if obj.is_balanced:
            return format_html('<span style="color: green;">✓ Balanced</span>')
        else:
            return format_html('<span style="color: red;">✗ Unbalanced</span>')
    is_balanced.short_description = 'Balanced'

@admin.register(ProductionExpense)
class ProductionExpenseAdmin(admin.ModelAdmin):
    list_display = ['requisition', 'journal_entry', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['requisition__requisition_no', 'journal_entry__entry_number']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

@admin.register(SalesRevenue)
class SalesRevenueAdmin(admin.ModelAdmin):
    list_display = ['get_sale_reference', 'journal_entry', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['service_sale__service_sale_number', 'store_sale__id', 'journal_entry__entry_number']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    def get_sale_reference(self, obj):
        if obj.service_sale:
            return f"Service Sale: {obj.service_sale.service_sale_number}"
        elif obj.store_sale:
            return f"Store Sale: {obj.store_sale.id}"
        return "Unknown Sale"
    get_sale_reference.short_description = 'Sale Reference'

# Custom admin site configuration
admin.site.site_header = "POS Magic Accounting System"
admin.site.site_title = "POS Magic Admin"
admin.site.index_title = "Welcome to POS Magic Accounting Administration"
