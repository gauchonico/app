from django import template
from django.utils.html import format_html
from decimal import Decimal, InvalidOperation
import logging
from datetime import date

logger = logging.getLogger(__name__)

register = template.Library()

@register.filter
def multiply(value, arg):
    return value * arg

@register.filter(name='currency')
def currency(value, currency_symbol='UGX'):
    try:
        logger.debug(f'Value to format: {value}')
        value = Decimal(value)
        return format_html('{}{:,.2f}', currency_symbol, value)
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.error(f'Error formatting value: {value}, Exception: {e}')
        return value
    
@register.filter
def is_pdf(file_url):
    return file_url.lower().endswith('.pdf')

@register.filter
def is_image(file_url):
    return file_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))

@register.filter
def days_difference(date1, date2):
    return (date2 - date1).days

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    return dictionary.get(key)