from django.core.exceptions import ValidationError
from django.db import models
import uuid
from django.contrib.auth import get_user_model

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

    def save(self, *args, **kwargs):
        # Detect if email changed
        try:
            old_instance = RentalCompany.objects.get(pk=self.pk)
            email_changed = old_instance.email != self.email
        except RentalCompany.DoesNotExist:
            email_changed = True  # New instance

        super().save(*args, **kwargs)

        # Sync superuser email if it changed
        if email_changed:
            User = get_user_model()
            superuser = User.objects.filter(is_superuser=True).first()
            if superuser and superuser.email != self.email:
                superuser.email = self.email
                superuser.save()