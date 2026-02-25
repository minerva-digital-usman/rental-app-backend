"""
Quick test script to verify Aruba SMTP is working.
Run from the project root:  python test_smtp.py
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "middleware_platform.settings")
django.setup()

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

# ── Recipient ────────────────────────────────────────────────
TO_EMAIL = "usmancf88@gmail.com"

# ── Build the message ────────────────────────────────────────
subject = "Aruba SMTP Test"
html_content = """
<html>
    <body>
        <h2>SMTP Test Successful!</h2>
        <p>If you're reading this, the Aruba SMTP configuration is working correctly on the deployed server.</p>
        <p>Sent via Django <code>EmailMultiAlternatives</code>.</p>
    </body>
</html>
"""

sender_name = getattr(settings, "DEFAULT_FROM_NAME", "")
sender_email = settings.DEFAULT_FROM_EMAIL
from_email = f"{sender_name} <{sender_email}>" if sender_name else sender_email

text_content = strip_tags(html_content)

print(f"Sending test email to {TO_EMAIL} ...")
print(f"From: {from_email}")
print(f"EMAIL_BACKEND : {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST    : {getattr(settings, 'EMAIL_HOST', '(not set)')}")
print(f"EMAIL_PORT    : {getattr(settings, 'EMAIL_PORT', '(not set)')}")
print(f"EMAIL_USE_TLS : {getattr(settings, 'EMAIL_USE_TLS', '(not set)')}")
print(f"EMAIL_USE_SSL : {getattr(settings, 'EMAIL_USE_SSL', '(not set)')}")
print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', '(not set)')}")
print()

try:
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[TO_EMAIL],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
    print("Email sent successfully!")
except Exception as e:
    print(f"SMTP send FAILED: {e}")
    print()
    print("Make sure your settings.py has the Aruba SMTP config, for example:")
    print()
    print("  EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'")
    print("  EMAIL_HOST           = 'smtps.aruba.it'")
    print("  EMAIL_PORT           = 465")
    print("  EMAIL_USE_SSL        = True")
    print("  EMAIL_HOST_USER      = 'your-email@your-domain.it'")
    print("  EMAIL_HOST_PASSWORD  = 'your-password'")
    sys.exit(1)
