from django.contrib import admin
from .models import Plan, PlanFeature, Subscription, SubscriptionHistory

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'price', 'billing_cycle',
        'trial_days', 'is_active', 'is_featured'
    )
    list_filter = ('billing_cycle', 'is_active', 'is_featured')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)

@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ('plan', 'feature', 'is_included')
    list_filter = ('plan', 'is_included')
    search_fields = ('feature',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'status',
        'start_date', 'end_date', 'auto_renew'
    )
    list_filter = ('status', 'plan', 'auto_renew')
    search_fields = ('user__email',)
    ordering = ('-created_at',)

@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'action',
        'amount', 'created_at'
    )
    list_filter = ('action', 'plan')
    search_fields = ('user__email',)
    ordering = ('-created_at',)