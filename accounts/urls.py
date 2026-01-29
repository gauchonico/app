from django.urls import path
from . import views, commission_views, payable_views, account_ledger_views, service_sales_views

app_name = 'accounts'

urlpatterns = [
    # Main Accounting Views
    path('accounting_dashboard/', views.accounting_dashboard, name='accounting_dashboard'),
    # path('dashboard/', views.accounting_dashboard, name='dashboard'),
    
    # Chart of Accounts
    path('chart-of-accounts/', views.chart_of_accounts_list, name='chart_of_accounts_list'),
    path('chart-of-accounts/create/', views.chart_of_accounts_create, name='chart_of_accounts_create'),
    path('chart-of-accounts/<int:pk>/update/', views.chart_of_accounts_update, name='chart_of_accounts_update'),
    path('chart-of-accounts/<int:pk>/delete/', views.chart_of_accounts_delete, name='chart_of_accounts_delete'),
    
    # Departments
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments-detail/<int:pk>', views.department_detail, name='departmet_detail'),
    path('departments/<int:pk>/update/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    
    # Journal Entries
    path('journal-entries/', views.journal_entry_list, name='journal_entry_list'),
    path('journal-entries/create/', views.journal_entry_create, name='journal_entry_create'),
    path('journal-entries/<int:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('journal-entries/<int:pk>/update/', views.journal_entry_update, name='journal_entry_update'),
    path('journal-entries/<int:pk>/delete/', views.journal_entry_delete, name='journal_entry_delete'),
    
    # Financial Reports
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    
    # Budgets
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/update/', views.budget_update, name='budget_update'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),
    path('budget-report/', views.budget_report, name='budget_report'),
    
    # Manufacturing Integration
    path('manufacturing-report/', views.manufacturing_report, name='manufacturing_report'),
    # path('sync-manufacturing/', views.sync_manufacturing_to_accounting, name='sync_manufacturing'),
    
    # Commission Accounting (NEW)
    path('commission-expense-report/', commission_views.commission_expense_report, name='commission_expense_report'),
    path('sync-commission-accounting/', commission_views.sync_commission_accounting, name='sync_commission_accounting'),
    
    # Accounts Payable (NEW)
    path('accounts-payable-details/', payable_views.accounts_payable_details, name='accounts_payable_details'),
    path('supplier-payable-summary/', payable_views.supplier_payable_summary, name='supplier_payable_summary'),
    
    # Account Ledger Views (NEW)
    path('account-ledger/<int:account_id>/', account_ledger_views.account_ledger_details, name='account_ledger_details'),
    path('account-summary/<int:account_id>/', account_ledger_views.account_summary_report, name='account_summary_report'),
    
    # Unified Service Sales Views (NEW)
    path('service-sales-dashboard/', service_sales_views.unified_service_sales_dashboard, name='unified_service_sales_dashboard'),
    path('service-sales-analytics/', service_sales_views.service_sales_analytics, name='service_sales_analytics'),
    path('service-sale-detail/<int:sale_id>/', service_sales_views.service_sale_detail_admin, name='service_sale_detail_admin'),
    path('export-service-sales/', service_sales_views.export_service_sales_data, name='export_service_sales_data'),
]