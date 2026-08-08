from django.contrib import admin
from .models import IdempotencyKey


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'endpoint', 'method',
                    'status', 'response_status', 'created_at')
    list_filter = ('status', 'method', 'created_at')
    search_fields = ('key', 'endpoint', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)