import os
from django.db import models
import uuid

from django.dispatch import receiver
from django.db.models.signals import post_delete

from middleware_platform import settings


def driver_license_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{instance.id}.{ext}"
    return os.path.join('drivers_license', filename)

class Guest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=False, null=False)
    phone = models.CharField(max_length=20, blank=False, null=False)
    fiscal_code = models.CharField(max_length=50, blank=True, null=True)

    driver_license = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        # Ensure UUID is generated before calling super().save() so upload_to gets correct value
        if not self.id:
            self.id = uuid.uuid4()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
@receiver(post_delete, sender=Guest)
def delete_driver_license_file(sender, instance, **kwargs):
    if instance.driver_license:
        file_path = os.path.join(settings.MEDIA_ROOT, instance.driver_license)
        if os.path.isfile(file_path):
            os.remove(file_path)
