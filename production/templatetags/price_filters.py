from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def avg_price(price_data):
    if not price_data:
        return Decimal('0.00')
    total = sum(item.price for item in price_data)
    return total / len(price_data)

@register.filter
def min_price(price_data):
    if not price_data:
        return Decimal('0.00')
    return min(item.price for item in price_data)

@register.filter
def max_price(price_data):
    if not price_data:
        return Decimal('0.00')
    return max(item.price for item in price_data)

@register.filter
def price_range(price_data):
    if not price_data:
        return Decimal('0.00')
    prices = [item.price for item in price_data]
    return max(prices) - min(prices)
