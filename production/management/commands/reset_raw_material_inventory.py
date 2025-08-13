from django.core.management.base import BaseCommand
from production.models import RawMaterial, RawMaterialInventory
from django.db import transaction


class Command(BaseCommand):
    help = 'Reset all raw material inventory quantities to 0'

    def add_arguments(self, parser):
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Preview what will be changed without making changes',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the reset operation',
        )

    def handle(self, *args, **options):
        preview = options['preview']
        confirm = options['confirm']
        
        # Get all raw materials
        raw_materials = RawMaterial.objects.all()
        
        # Get inventory adjustments count
        inventory_adjustments = RawMaterialInventory.objects.count()
        
        if not raw_materials.exists():
            self.stdout.write(
                self.style.WARNING('No raw materials found in the system.')
            )
            return
        
        # Show current inventory status
        self.stdout.write(
            self.style.SUCCESS(f'Found {raw_materials.count()} raw materials:')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Found {inventory_adjustments} inventory adjustments:')
        )
        
        total_current_stock = 0
        materials_with_stock = 0
        
        for material in raw_materials:
            current_stock = material.quantity or 0
            total_current_stock += current_stock
            if current_stock > 0:
                materials_with_stock += 1
                self.stdout.write(
                    f'  • {material.name}: {current_stock} {material.unit_measurement}'
                )
        
        # Show some inventory adjustments
        if inventory_adjustments > 0:
            self.stdout.write('')
            self.stdout.write('Sample inventory adjustments:')
            sample_adjustments = RawMaterialInventory.objects.select_related('raw_material')[:5]
            for adjustment in sample_adjustments:
                self.stdout.write(
                    f'  • {adjustment.raw_material.name}: {adjustment.adjustment} (updated: {adjustment.last_updated.strftime("%Y-%m-%d %H:%M")})'
                )
            if inventory_adjustments > 5:
                self.stdout.write(f'  ... and {inventory_adjustments - 5} more adjustments')
        
        self.stdout.write('')
        self.stdout.write(
            f'Total current stock across all materials: {total_current_stock}'
        )
        self.stdout.write(
            f'Materials with stock > 0: {materials_with_stock}'
        )
        self.stdout.write(
            f'Total inventory adjustments: {inventory_adjustments}'
        )
        
        if preview:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('PREVIEW MODE - No changes will be made')
            )
            self.stdout.write('This would reset all raw material quantities to 0.')
            return
        
        if not confirm:
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR('⚠️  WARNING: This will reset ALL raw material inventory to 0!')
            )
            self.stdout.write('This action cannot be undone.')
            self.stdout.write('')
            self.stdout.write('To proceed, run the command with --confirm flag:')
            self.stdout.write('python manage.py reset_raw_material_inventory --confirm')
            return
        
        # Proceed with reset
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('Resetting all raw material inventory to 0...')
        )
        
        try:
            with transaction.atomic():
                # Delete all inventory adjustments to reset to 0
                deleted_adjustments = RawMaterialInventory.objects.all().delete()
                adjustment_count = deleted_adjustments[0] if deleted_adjustments else 0
                
                # Reset all raw material quantities to 0
                updated_count = RawMaterial.objects.update(quantity=0)
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully deleted {adjustment_count} inventory adjustments!')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully reset {updated_count} raw materials to 0 quantity!')
                )
                
                # Verify the reset
                remaining_stock = RawMaterial.objects.filter(quantity__gt=0).count()
                remaining_adjustments = RawMaterialInventory.objects.count()
                
                if remaining_stock == 0 and remaining_adjustments == 0:
                    self.stdout.write(
                        self.style.SUCCESS('✅ Verification: All raw materials now have 0 quantity and no inventory adjustments.')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Warning: {remaining_stock} materials still have stock > 0, {remaining_adjustments} adjustments remain')
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during reset: {str(e)}')
            )
            return
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS('🎉 Raw material inventory has been reset successfully!')
        )
        self.stdout.write('Your new requisitions will now start with a clean inventory slate.')
