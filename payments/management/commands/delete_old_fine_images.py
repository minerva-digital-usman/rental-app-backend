from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils import timezone

from payments.challan.models import TrafficFine

class Command(BaseCommand):
    help = 'Deletes TrafficFine images older than 7 days'

    def handle(self, *args, **kwargs):
        threshold_date = timezone.now() - timedelta(days=7)
        fines = TrafficFine.objects.filter(created_at__lt=threshold_date, image__isnull=False)

        for fine in fines:
            self.stdout.write(f"Deleting image for fine ID: {fine.id}")
            fine.image.delete(save=False)
            fine.image = None
            fine.save()
        
        self.stdout.write(self.style.SUCCESS(f"Deleted {fines.count()} fine images"))