from django.core.management.base import BaseCommand
from production.models import RawMaterial

class Command(BaseCommand):
    help = 'Reset raw material inventory quantities to 0'

    def handle(self, *args, **options):
        RawMaterial.objects.all().update(quantity=0)
        self.stdout.write(self.style.SUCCESS('Command executed successfully.'))