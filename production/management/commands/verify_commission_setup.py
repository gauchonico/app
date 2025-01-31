from django.core.management.base import BaseCommand
from production.models import StoreService, ServiceSaleItem, ServiceSale, StaffCommission

class Command(BaseCommand):
    help = 'Verifies commission setup and data'

    def handle(self, *args, **options):
        # Check StoreServices
        self.stdout.write("Checking StoreServices...")
        for service in StoreService.objects.all():
            self.stdout.write(f"\nService: {service}")
            self.stdout.write(f"Commission Rate: {service.commission_rate}")

        # Check Paid Sales
        self.stdout.write("\nChecking Paid Sales...")
        paid_sales = ServiceSale.objects.filter(paid_status='paid')
        for sale in paid_sales:
            self.stdout.write(f"\nSale: {sale.service_sale_number}")
            for item in sale.service_sale_items.all():
                self.stdout.write(f"- Service Item: {item.service.service.name}")
                self.stdout.write(f"  Price: {item.total_price}")
                self.stdout.write(f"  Staff Count: {item.staff.count()}")
                self.stdout.write(f"  Staff: {[staff.first_name for staff in item.staff.all()]}")
                self.stdout.write(f"  Commission Rate: {item.service.commission_rate}")
                
                # Check existing commissions
                commissions = StaffCommission.objects.filter(service_sale_item=item)
                self.stdout.write(f"  Existing Commissions: {commissions.count()}")
                for commission in commissions:
                    self.stdout.write(f"    - {commission.staff.first_name}: {commission.commission_amount}") 