from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'user', 'gateway', 'status',
        'payment_for', 'amount', 'created_at'
    )
    list_filter = ('gateway', 'status', 'payment_for')
    search_fields = ('reference', 'user__email')
    ordering = ('-created_at',)