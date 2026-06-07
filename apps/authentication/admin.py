from django.contrib import admin
from .models import OTPVerification

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_type', 'is_used', 'created_at')
    list_filter = ('otp_type', 'is_used')
    search_fields = ('user__email',)
    ordering = ('-created_at',)