from django.core.management.base import BaseCommand
from production.models import RawMaterial
from decimal import Decimal

class Command(BaseCommand):
    help = 'Fix raw material quantities by recalculating from inventory adjustments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--raw-material-id',
            type=int,
            help='Fix quantity for a specific raw material ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        raw_material_id = options.get('raw_material_id')
        dry_run = options.get('dry_run')
        
        if raw_material_id:
            raw_materials = RawMaterial.objects.filter(id=raw_material_id)
        else:
            raw_materials = RawMaterial.objects.all()
        
        self.stdout.write(f"Processing {raw_materials.count()} raw material(s)...")
        
        for raw_material in raw_materials:
            old_quantity = raw_material.quantity
            new_quantity = raw_material.current_stock
            
            if old_quantity != new_quantity:
                self.stdout.write(
                    f"Raw Material: {raw_material.name} (ID: {raw_material.id})"
                )
                self.stdout.write(f"  Old quantity: {old_quantity}")
                self.stdout.write(f"  New quantity: {new_quantity}")
                self.stdout.write(f"  Difference: {new_quantity - old_quantity}")
                
                if not dry_run:
                    raw_material.update_quantity()
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Updated quantity to {raw_material.quantity}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("  (DRY RUN - No changes made)")
                    )
                self.stdout.write("")
            else:
                self.stdout.write(
                    f"✓ {raw_material.name} (ID: {raw_material.id}) - Quantity is correct: {old_quantity}"
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN COMPLETED - No changes were made")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Raw material quantities have been updated!")
            ) 