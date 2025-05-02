from django.core.exceptions import ValidationError
from django.db import models
import uuid

class RentalCompany(models.Model):
    """
    Represents a vehicle rental company integrated into the platform.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    portal_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL for the rental company's admin portal or reference"
    )

    def __str__(self):
        return self.name

    def clean(self):
        """
        Ensure only one RentalCompany exists in the database.
        """
        # Check if this is a new instance (not an update)
        if not self.pk and RentalCompany.objects.exists():
            raise ValidationError("Only one RentalCompany is allowed.")
