

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Shop.models import Cart  # Adjust the import path as necessary

class Command(BaseCommand):
    help = 'Clears old completed carts from the database'

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(hours=24)  # Adjust time as needed
        old_carts = Cart.objects.filter(is_active=False, completed_at__lt=threshold)
        count = old_carts.count()
        old_carts.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully cleared {count} old carts'))