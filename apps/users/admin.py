from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile, SavedAddress



@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'email',
        'full_name',
        'role',
        'is_verified',
        'is_active',
        'created_at'
    )
    list_filter = ('role', 'is_verified', 'is_active')
    search_fields = ('email', 'full_name')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone', 'avatar')}),
        ('Role & Status', {'fields': ('role', 'is_verified', 'is_active', 'is_staff')}),
        ('Permissions', {'fields': ('is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'gender', 'date_of_birth', 'referral_code']

@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'name', 'city', 'is_default', 'is_active']
    list_filter  = ['label', 'is_default']
