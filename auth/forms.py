# backend/auth/forms.py
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

class StrictAdminPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data['email'].lower()  # Normalize email
        User = get_user_model()
        
        # Check if email exists AND belongs to a staff member
        if not User.objects.filter(
            email__iexact=email, 
            is_staff=True
        ).exists():
            raise ValidationError(
                "No admin account found with this email address.",
                code="invalid_staff_email"
            )
        return email

    # Critical: Override to prevent email sending for invalid cases
    def save(self, **kwargs):
        email = self.cleaned_data["email"]
        if not self.get_users(email):  # Final safety check
            raise ValidationError("Email validation failed")
        return super().save(**kwargs)