from django.core.management.base import BaseCommand
from production.models import TaxCode

class Command(BaseCommand):
    help = 'Create default tax codes for the system'

    def handle(self, *args, **options):
        # Default tax codes
        tax_codes = [
            {
                'code': 'VAT18',
                'name': 'VAT 18%',
                'rate': 18.00,
                'description': 'Standard VAT rate in Uganda'
            },
            {
                'code': 'VAT0',
                'name': 'Zero Rated',
                'rate': 0.00,
                'description': 'Zero-rated supplies'
            },
            {
                'code': 'EXEMPT',
                'name': 'Exempt',
                'rate': 0.00,
                'description': 'Exempt from VAT'
            },
            {
                'code': 'VAT16',
                'name': 'VAT 16%',
                'rate': 16.00,
                'description': 'Reduced VAT rate'
            }
        ]

        created_count = 0
        for tax_data in tax_codes:
            tax_code, created = TaxCode.objects.get_or_create(
                code=tax_data['code'],
                defaults=tax_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created tax code: {tax_code.code} - {tax_code.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Tax code already exists: {tax_code.code} - {tax_code.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new tax codes')
        ) 