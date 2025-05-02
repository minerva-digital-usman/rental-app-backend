from django.db import models
import uuid

class Guest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField( blank=False, null=False)
    phone = models.CharField(max_length=20,  blank=False, null=False)
    fiscal_code = models.CharField(max_length=50, blank=True, null=True)
    
    # Change from CharField to ImageField to store the image and generate its URL
    # driver_license = models.ImageField(upload_to='drivers_license/', blank=False, null=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
