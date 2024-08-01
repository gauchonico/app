from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix invalid decimal values in ProductionIngredient'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, quantity_per_unit_product_volume FROM production_productioningredient")
            for row in cursor.fetchall():
                ingredient_id, value = row
                try:
                    Decimal(value)
                except InvalidOperation:
                    self.stdout.write(self.style.WARNING(f'Fixing invalid value: {value} in ProductionIngredient id {ingredient_id}'))
                    cursor.execute("UPDATE production_productioningredient SET quantity_per_unit_product_volume = '0.00' WHERE id = %s", [ingredient_id])