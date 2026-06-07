from django.db import models
from django.conf import settings
import random


class OTPVerification(models.Model):
    OTP_TYPE_CHOICES = (
        ('email_verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='otps'
    )
    otp = models.CharField(max_length=6)
    otp_type = models.CharField(
        max_length=20,
        choices=OTP_TYPE_CHOICES
    )
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.otp_type}"

    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))