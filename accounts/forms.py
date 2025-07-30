from django import forms
from django.forms import ModelForm, inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError
from decimal import Decimal

from production.models import Production
from .models import (
    ChartOfAccounts, Department, Budget, JournalEntry, JournalEntryLine,
    FinancialPeriod, TrialBalance, ProfitLossStatement, BalanceSheet
)

class ChartOfAccountsForm(ModelForm):
    """Form for creating/editing chart of accounts"""
    class Meta:
        model = ChartOfAccounts
        fields = [
            'account_code', 'account_name', 'account_type', 'account_category',
            'description', 'parent_account', 'is_active'
        ]
        widgets = {
            'account_code': forms.TextInput(attrs={'class': 'form-control'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'account_category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parent_account': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_account_code(self):
        account_code = self.cleaned_data['account_code']
        if not account_code.isdigit():
            raise ValidationError("Account code must contain only numbers")
        return account_code

class DepartmentForm(ModelForm):
    """Form for creating/editing departments"""
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'manager', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'manager': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class BudgetForm(ModelForm):
    """Form for creating/editing budgets"""
    class Meta:
        model = Budget
        fields = [
            'department', 'account', 'amount', 'period', 'start_date',
            'end_date', 'description', 'is_active'
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'period': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise ValidationError("End date must be after start date")
        
        return cleaned_data

class JournalEntryForm(ModelForm):
    """Form for creating/editing journal entries"""
    class Meta:
        model = JournalEntry
        fields = [
            'date', 'reference', 'description', 'entry_type', 'department'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'entry_type': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

class JournalEntryLineForm(ModelForm):
    """Form for individual journal entry lines"""
    class Meta:
        model = JournalEntryLine
        fields = ['account', 'entry_type', 'amount', 'description']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-control'}),
            'entry_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BalancedJournalEntryLineFormSet(BaseInlineFormSet):
    """FormSet that ensures journal entries are balanced"""
    
    def clean(self):
        super().clean()
        
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                amount = form.cleaned_data.get('amount', Decimal('0.00'))
                entry_type = form.cleaned_data.get('entry_type')
                
                if entry_type == 'debit':
                    total_debits += amount
                elif entry_type == 'credit':
                    total_credits += amount
        
        if total_debits != total_credits:
            raise ValidationError(
                f"Journal entry must be balanced. Total debits: {total_debits}, "
                f"Total credits: {total_credits}"
            )

# Create inline formset for journal entry lines
JournalEntryLineFormSet = inlineformset_factory(
    JournalEntry,
    JournalEntryLine,
    form=JournalEntryLineForm,
    formset=BalancedJournalEntryLineFormSet,
    extra=2,
    can_delete=True,
    min_num=2,
    validate_min=True,
)

class FinancialPeriodForm(ModelForm):
    """Form for creating/editing financial periods"""
    class Meta:
        model = FinancialPeriod
        fields = ['name', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class TrialBalanceForm(ModelForm):
    """Form for trial balance entries"""
    class Meta:
        model = TrialBalance
        fields = ['period', 'account', 'debit_balance', 'credit_balance']
        widgets = {
            'period': forms.Select(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'debit_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'credit_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class ProfitLossStatementForm(ModelForm):
    """Form for profit and loss statement"""
    class Meta:
        model = ProfitLossStatement
        fields = [
            'period', 'revenue', 'cost_of_goods_sold', 'operating_expenses',
            'other_income', 'other_expenses'
        ]
        widgets = {
            'period': forms.Select(attrs={'class': 'form-control'}),
            'revenue': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost_of_goods_sold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'operating_expenses': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_expenses': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class BalanceSheetForm(ModelForm):
    """Form for balance sheet"""
    class Meta:
        model = BalanceSheet
        fields = [
            'as_of_date', 'current_assets', 'fixed_assets',
            'current_liabilities', 'long_term_liabilities',
            'owner_equity', 'retained_earnings'
        ]
        widgets = {
            'as_of_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'current_assets': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fixed_assets': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'current_liabilities': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'long_term_liabilities': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'owner_equity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'retained_earnings': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

# Report forms
class DateRangeForm(forms.Form):
    """Form for date range selection in reports"""
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date")
        
        return cleaned_data

class BudgetReportForm(forms.Form):
    """Form for budget report filters"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    period = forms.ChoiceField(
        choices=[('', 'All Periods')] + Budget.BUDGET_PERIODS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

class ChartOfAccountsImportForm(forms.Form):
    """Form for importing chart of accounts from CSV"""
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV file with columns: account_code, account_name, account_type, account_category, description",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        label="Overwrite existing accounts",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class BulkJournalEntryForm(forms.Form):
    """Form for bulk journal entry creation"""
    entry_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    reference = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    entry_type = forms.ChoiceField(
        choices=JournalEntry.ENTRY_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    ) 
class ManufacturingReportForm(forms.Form):
    """Form for manufacturing report filters"""
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    product = forms.ModelChoiceField(
        queryset=Production.objects.all().order_by('product_name'),
        required=False,
        empty_label="All Products",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date")
        
        return cleaned_data 
from django import forms
