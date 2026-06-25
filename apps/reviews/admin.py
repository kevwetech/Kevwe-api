from django.contrib import admin
from .models import Review, ReviewHelpfulness, ReviewReport


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'objects_type', 'objects_id',
        'rating', 'status', 'is_verified',
        'is_featured', 'created_at'
    )
    list_filter = (
        'objects_type', 'status',
        'is_verified', 'is_featured'
    )
    search_fields = ('user__email', 'comment', 'title')
    ordering = ('-created_at',)


@admin.register(ReviewHelpfulness)
class ReviewHelpfulnessAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'is_helpful', 'created_at')
    list_filter = ('is_helpful',)
    ordering = ('-created_at',)


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = (
        'review', 'reported_by',
        'reason', 'is_resolved', 'created_at'
    )
    list_filter = ('reason', 'is_resolved')
    ordering = ('-created_at',)