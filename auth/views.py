# auth/views.py or any appropriate views file

from django.contrib.auth.views import PasswordResetView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from api.booking.email_service import Email
from django.contrib import messages

class CustomAdminPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            admin_user = User.objects.filter(is_superuser=True, email=email).first()
            if not admin_user:
                form.add_error("email", "Admin user not found or email does not match.")
                return self.form_invalid(form)

            uid = urlsafe_base64_encode(force_bytes(admin_user.pk))
            token = default_token_generator.make_token(admin_user)
            reset_link = self.request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )

            # Send email using Brevo
            subject = "Admin Password Reset Request"
            html_content = f"""
            <html>
                <body>
                    <p>Hello Admin,</p>
                    <p>You requested a password reset. Click the link below to set a new password:</p>
                    <p><a href="{reset_link}">Reset Your Password</a></p>
                    <p>If you did not request this, please ignore this email.</p>
                </body>
            </html>
            """
            email_client = Email()
            email_client._send_email_via_brevo(
                subject=subject,
                html_content=html_content,
                recipient_list=[admin_user.email]
            )

            messages.success(self.request, "Password reset email sent successfully.")
            return redirect(self.success_url)

        except Exception as e:
            form.add_error(None, f"Error: {str(e)}")
            return self.form_invalid(form)
