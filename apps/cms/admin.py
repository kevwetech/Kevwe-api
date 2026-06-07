from django.contrib import admin
from .models import (
    SiteSettings,
    HomePage,
    AboutPage,
    Service,
    ContactInfo,
    ContactMessage,
    FAQ,
    Testimonial,
    TeamMember,
    Feature,
    Gallery,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'site_email', 'maintenance_mode')


@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    list_display = ('hero_title', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'is_featured',
        'is_active', 'order'
    )
    list_filter = ('is_featured', 'is_active')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('order',)


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('title', 'email', 'phone', 'is_active')
    list_filter = ('is_active',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'email', 'subject',
        'status', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('name', 'email', 'subject')
    ordering = ('-created_at',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = (
        'question', 'category',
        'is_featured', 'is_active', 'views'
    )
    list_filter = ('category', 'is_featured', 'is_active')
    search_fields = ('question',)
    ordering = ('order',)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'company', 'rating',
        'status', 'is_featured'
    )
    list_filter = ('status', 'is_featured', 'rating')
    search_fields = ('name', 'company')
    ordering = ('order',)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'title', 'is_active', 'order'
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'title')
    ordering = ('order',)


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order')
    list_filter = ('is_active',)
    ordering = ('order',)


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'gallery_type',
        'is_active', 'order'
    )
    list_filter = ('gallery_type', 'is_active')
    ordering = ('order',)