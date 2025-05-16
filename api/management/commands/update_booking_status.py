from django.core.management.base import BaseCommand
from django.utils import timezone
from api.booking.models import Booking
import pytz

class Command(BaseCommand):
    help = "Update bookings to completed if their end time has passed"

    def handle(self, *args, **options):
        # 1. Get current time in Rome
        rome_tz = pytz.timezone('Europe/Rome')
        now_rome = timezone.now().astimezone(rome_tz)  # e.g., 2025-05-16 11:39:40+02:00
        print("Current time in Rome:", now_rome)

        # 2. Get all active bookings
        active_bookings = Booking.objects.filter(status=Booking.STATUS_ACTIVE)
        
        updated_ids = []

        for booking in active_bookings:
            # 3. Treat DB UTC time as Rome time (since DB is 2 hours ahead)
            #    (e.g., DB stores 13:30:00+00:00 but actually means 13:30:00+02:00)
            end_time_rome = booking.end_time.replace(tzinfo=None)  # Remove UTC
            end_time_rome = rome_tz.localize(end_time_rome)  # Force as Rome time
            print("Booking end time in Rome:", end_time_rome)

            # 4. Compare Rome times
            if end_time_rome <= now_rome:
                updated_ids.append(booking.id)

        # 5. Bulk update completed bookings
        if updated_ids:
            Booking.objects.filter(id__in=updated_ids).update(status=Booking.STATUS_COMPLETED)
            self.stdout.write(self.style.SUCCESS(f"Updated {len(updated_ids)} bookings to completed"))
        else:
            self.stdout.write("No bookings needed updates")