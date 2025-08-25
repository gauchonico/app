from django.core.management.base import BaseCommand
from django.db import transaction
from production.models import StoreSale, SalesInvoice, SaleItem, LivaraInventoryAdjustment
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create LivaraInventoryAdjustment records for existing invoiced sales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if some adjustments already exist',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write("Analyzing existing sales invoices...")
        
        # Get all invoiced sales that have invoices
        invoiced_sales = StoreSale.objects.filter(
            status='invoiced',
            sales_invoice__isnull=False
        ).select_related('sales_invoice')
        
        self.stdout.write(f"Found {invoiced_sales.count()} invoiced sales to process")
        
        adjustments_created = 0
        adjustments_skipped = 0
        errors = 0
        
        # Get system user for adjustments (or first superuser)
        try:
            system_user = User.objects.filter(is_superuser=True).first()
            if not system_user:
                system_user = User.objects.first()
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("No users found in the system. Please create a user first.")
            )
            return
        
        for sale in invoiced_sales:
            try:
                with transaction.atomic():
                    invoice = sale.sales_invoice
                    
                    # Check if adjustments already exist for this invoice
                    existing_adjustments = LivaraInventoryAdjustment.objects.filter(
                        adjustment_reason__icontains=f"Invoice #{invoice.invoice_number}"
                    )
                    
                    if existing_adjustments.exists() and not force:
                        self.stdout.write(
                            f"Skipping Invoice #{invoice.invoice_number} - adjustments already exist"
                        )
                        adjustments_skipped += 1
                        continue
                    
                    # Get all sale items for this sale
                    sale_items = SaleItem.objects.filter(sale=sale).select_related('product')
                    
                    if not sale_items.exists():
                        self.stdout.write(
                            f"Warning: No sale items found for Sale #{sale.order_number}"
                        )
                        continue
                    
                    # Create adjustment records for each item
                    for item in sale_items:
                        if item.product:  # Ensure the product exists
                            adjustment_reason = f"Store Sale - Invoice #{invoice.invoice_number} (Historical)"
                            
                            if dry_run:
                                self.stdout.write(
                                    f"Would create adjustment: {item.product.product.product.product_name} "
                                    f"(-{item.quantity}) - {adjustment_reason}"
                                )
                            else:
                                # Delete existing adjustments if force is used
                                if force:
                                    LivaraInventoryAdjustment.objects.filter(
                                        store_inventory=item.product,
                                        adjustment_reason__icontains=f"Invoice #{invoice.invoice_number}"
                                    ).delete()
                                
                                LivaraInventoryAdjustment.objects.create(
                                    store_inventory=item.product,
                                    adjusted_quantity=-item.quantity,  # Negative for sales
                                    adjustment_reason=adjustment_reason,
                                    adjusted_by=system_user
                                )
                                
                            adjustments_created += 1
                        else:
                            self.stdout.write(
                                f"Warning: Sale item has no associated product - Sale #{sale.order_number}"
                            )
                    
                    if not dry_run:
                        self.stdout.write(
                            f"✓ Created adjustments for Invoice #{invoice.invoice_number} "
                            f"(Sale #{sale.order_number})"
                        )
                        
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing Sale #{sale.order_number}: {str(e)}"
                    )
                )
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDRY RUN SUMMARY:\n"
                    f"- Would create {adjustments_created} adjustment records\n"
                    f"- Would skip {adjustments_skipped} existing adjustments\n"
                    f"- {errors} errors encountered\n\n"
                    f"Run without --dry-run to actually create the records"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSUMMARY:\n"
                    f"- Created {adjustments_created} adjustment records\n"
                    f"- Skipped {adjustments_skipped} existing adjustments\n"
                    f"- {errors} errors encountered"
                )
            )
            
        if adjustments_created > 0:
            self.stdout.write(
                "\nYou can now view the adjustments at: /production/livara-inventory-adjustments/"
            )
