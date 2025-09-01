from django.core.management.base import BaseCommand
from production.models import ManufactureProduct
from production.utils import cost_per_unit
from decimal import Decimal


class Command(BaseCommand):
    help = 'Update existing manufacturing records with correct production costs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('=== UPDATING MANUFACTURING PRODUCTION COSTS ==='))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN MODE - No changes will be made'))
        
        # Get all manufacturing records without production costs
        manufacturing_records = ManufactureProduct.objects.filter(
            total_production_cost__isnull=True
        ).select_related('product')
        
        self.stdout.write(f'Found {manufacturing_records.count()} records to update')
        
        updated_count = 0
        error_count = 0
        
        for manufacture_product in manufacturing_records:
            try:
                # Calculate cost using the existing cost_per_unit function
                cost_per = cost_per_unit(manufacture_product.product)
                total_cost_per_unit = sum(cost_data['cost_per_ingredient'] for cost_data in cost_per)
                total_production_cost = total_cost_per_unit * manufacture_product.quantity
                
                self.stdout.write(
                    f'Product: {manufacture_product.product.product_name} '
                    f'(Qty: {manufacture_product.quantity}) '
                    f'Cost: UGX {total_production_cost:,.2f}'
                )
                
                if not dry_run:
                    manufacture_product.total_production_cost = total_production_cost
                    manufacture_product.save(update_fields=['total_production_cost'])
                
                updated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error updating {manufacture_product.product.product_name}: {e}'
                    )
                )
                error_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== SUMMARY ===\n'
                f'Records processed: {updated_count}\n'
                f'Errors: {error_count}\n'
                f'Mode: {"DRY RUN" if dry_run else "UPDATED"}'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    'Run without --dry-run to apply changes'
                )
            )
