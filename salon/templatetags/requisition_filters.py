from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply value and arg"""
    return value * arg

@register.simple_tag
def sum_total(items):
    """Calculate the total sum for all requisition items"""
    total = sum(item.price * item.quantity for item in items)
    return round(total, 2)