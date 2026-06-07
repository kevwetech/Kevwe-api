from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'user','rating','created_at'
    )
    list_filter = ('rating',)
    search_fields = ('user__email', 'product__name')
    ordering = ('-created_at',)