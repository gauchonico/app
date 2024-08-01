from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Check for invalid decimal values in ProductionIngredient'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, quantity_per_unit_product_volume FROM production_productioningredient")
            for row in cursor.fetchall():
                ingredient_id, value = row
                try:
                    Decimal(value)
                except InvalidOperation:
                    self.stdout.write(self.style.ERROR(f'Invalid value: {value} in ProductionIngredient id {ingredient_id}'))