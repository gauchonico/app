"""
Forms for the customer loyalty system
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import LoyaltySettings, Customer, CustomerLoyaltyTransaction


class LoyaltySettingsForm(forms.ModelForm):
    """Form for configuring loyalty system settings"""
    
    class Meta:
        model = LoyaltySettings
        fields = [
            'calculation_method', 'points_per_order', 'points_per_currency_unit',
            'birthday_bonus_multiplier', 'weekend_bonus_multiplier', 'loyalty_tier_bonus',
            'points_redemption_enabled', 'points_to_currency_ratio', 'minimum_points_redemption',
            'points_expiry_months', 'is_active'
        ]
        widgets = {
            'calculation_method': forms.Select(attrs={'class': 'form-control'}),
            'points_per_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'points_per_currency_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'birthday_bonus_multiplier': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '1.0'}),
            'weekend_bonus_multiplier': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '1.0'}),
            'loyalty_tier_bonus': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'points_redemption_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'points_to_currency_ratio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '1'}),
            'minimum_points_redemption': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'points_expiry_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['calculation_method'].help_text = "How points are calculated for each order"
        self.fields['points_per_order'].help_text = "Fixed points awarded per order (for Fixed method)"
        self.fields['points_per_currency_unit'].help_text = "Points per currency unit spent (e.g., 0.01 = 1 point per 100 UGX)"
        self.fields['birthday_bonus_multiplier'].help_text = "Multiplier for birthday month (2.0 = double points)"
        self.fields['weekend_bonus_multiplier'].help_text = "Multiplier for weekend orders"
        self.fields['points_to_currency_ratio'].help_text = "Points needed for 1 currency unit (100 = 100 points = 1 UGX)"
        self.fields['minimum_points_redemption'].help_text = "Minimum points required to redeem"
        self.fields['points_expiry_months'].help_text = "Months until points expire (0 = never expire)"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate bonus multipliers
        birthday_multiplier = cleaned_data.get('birthday_bonus_multiplier')
        weekend_multiplier = cleaned_data.get('weekend_bonus_multiplier')
        
        if birthday_multiplier and birthday_multiplier < 1.0:
            raise ValidationError({'birthday_bonus_multiplier': 'Bonus multiplier must be at least 1.0'})
        
        if weekend_multiplier and weekend_multiplier < 1.0:
            raise ValidationError({'weekend_bonus_multiplier': 'Bonus multiplier must be at least 1.0'})
        
        # Validate redemption settings
        points_to_currency = cleaned_data.get('points_to_currency_ratio')
        min_redemption = cleaned_data.get('minimum_points_redemption')
        
        if points_to_currency and min_redemption:
            if min_redemption < points_to_currency:
                raise ValidationError({
                    'minimum_points_redemption': 'Minimum redemption should be at least equal to points-to-currency ratio'
                })
        
        return cleaned_data


class PointsRedemptionForm(forms.Form):
    """Form for customers to redeem loyalty points"""
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select customer"
    )
    points_to_redeem = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        help_text="Number of points to redeem"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text="Optional notes for this redemption"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter customers with loyalty points
        self.fields['customer'].queryset = Customer.objects.filter(
            loyalty_points__gt=0
        ).order_by('first_name', 'last_name')
    
    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        points_to_redeem = cleaned_data.get('points_to_redeem')
        
        if customer and points_to_redeem:
            # Check if customer has enough points
            if points_to_redeem > customer.loyalty_points:
                raise ValidationError({
                    'points_to_redeem': f'Customer only has {customer.loyalty_points} points available'
                })
            
            # Check minimum redemption requirement
            loyalty_settings = LoyaltySettings.get_current_settings()
            if loyalty_settings and points_to_redeem < loyalty_settings.minimum_points_redemption:
                raise ValidationError({
                    'points_to_redeem': f'Minimum redemption is {loyalty_settings.minimum_points_redemption} points'
                })
            
            # Check if redemption is enabled
            if loyalty_settings and not loyalty_settings.points_redemption_enabled:
                raise ValidationError('Points redemption is currently disabled')
        
        return cleaned_data
    
    def get_redemption_value(self):
        """Calculate the currency value of points being redeemed"""
        customer = self.cleaned_data.get('customer')
        points_to_redeem = self.cleaned_data.get('points_to_redeem')
        
        if customer and points_to_redeem:
            loyalty_settings = LoyaltySettings.get_current_settings()
            if loyalty_settings:
                return points_to_redeem / loyalty_settings.points_to_currency_ratio
        return 0


class ManualPointsAdjustmentForm(forms.Form):
    """Form for manually adjusting customer loyalty points (admin only)"""
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select customer"
    )
    points_adjustment = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Points to add (positive) or subtract (negative)"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text="Reason for this adjustment"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.order_by('first_name', 'last_name')
    
    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        points_adjustment = cleaned_data.get('points_adjustment')
        
        if customer and points_adjustment:
            # If subtracting points, ensure customer has enough
            if points_adjustment < 0 and abs(points_adjustment) > customer.loyalty_points:
                raise ValidationError({
                    'points_adjustment': f'Cannot subtract {abs(points_adjustment)} points. Customer only has {customer.loyalty_points} points.'
                })
        
        return cleaned_data


class LoyaltyReportFilterForm(forms.Form):
    """Form for filtering loyalty reports"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="Start date"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="End date"
    )
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Filter by specific customer (optional)"
    )
    transaction_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(CustomerLoyaltyTransaction.TRANSACTION_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Filter by transaction type"
    )
    loyalty_tier = forms.ChoiceField(
        choices=[
            ('', 'All Tiers'),
            ('BRONZE', 'Bronze'),
            ('SILVER', 'Silver'),
            ('GOLD', 'Gold'),
            ('VIP', 'VIP'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Filter by customer tier"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.order_by('first_name', 'last_name')
