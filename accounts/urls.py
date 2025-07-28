from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Dashboard
    path('', views.accounting_dashboard, name='dashboard'),
    
    # Chart of Accounts
    path('chart-of-accounts/', views.chart_of_accounts_list, name='chart_of_accounts_list'),
    path('chart-of-accounts/create/', views.chart_of_accounts_create, name='chart_of_accounts_create'),
    path('chart-of-accounts/<int:pk>/update/', views.chart_of_accounts_update, name='chart_of_accounts_update'),
    path('chart-of-accounts/<int:pk>/delete/', views.chart_of_accounts_delete, name='chart_of_accounts_delete'),
    
    # Departments
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/update/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    
    # Budgets
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/update/', views.budget_update, name='budget_update'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),
    
    # Journal Entries
    path('journal-entries/', views.journal_entry_list, name='journal_entry_list'),
    path('journal-entries/create/', views.journal_entry_create, name='journal_entry_create'),
    path('journal-entries/<int:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('journal-entries/<int:pk>/update/', views.journal_entry_update, name='journal_entry_update'),
    path('journal-entries/<int:pk>/delete/', views.journal_entry_delete, name='journal_entry_delete'),
    path('journal-entries/<int:pk>/post/', views.journal_entry_post, name='journal_entry_post'),
    
    # Reports
    path('reports/trial-balance/', views.trial_balance, name='trial_balance'),
    path('reports/profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('reports/budget/', views.budget_report, name='budget_report'),
    
    # API endpoints
    path('api/account/<int:account_id>/balance/', views.get_account_balance, name='get_account_balance'),
    path('api/department/<int:department_id>/budget/', views.get_department_budget, name='get_department_budget'),
] 