from django.contrib import admin
from .models import Country, State, City, Zone, Address


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'phone_code',
        'currency_code', 'is_active'
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'country', 'is_active'
    )
    list_filter = ('is_active', 'country')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'state', 'is_active'
    )
    list_filter = ('is_active', 'state__country')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'city', 'radius_km',
        'price_multiplier', 'is_active'
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'city__name')
    ordering = ('name',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'address_type', 'street_address',
        'city', 'state', 'is_default'
    )
    list_filter = ('address_type', 'is_default', 'is_verified')
    search_fields = ('user__email', 'street_address')
    ordering = ('-created_at',)