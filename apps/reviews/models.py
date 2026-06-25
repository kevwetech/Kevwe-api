from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import TimeStampedModel


class Review(TimeStampedModel):
    """
    Unified review system for all reviewable entities
    Supports: product, business, driver, order, delivery, ride
    """
    OBJECT_TYPE_CHOICES = (
        ('product', 'Product'),
        ('business', 'Business'),
        ('driver', 'Driver'),
        ('order', 'Order'),
        ('delivery', 'Delivery'),
        ('ride', 'Ride'),
        ('booking', 'Booking'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    # Generic FK - supports any model
    objects_id = models.IntegerField()
    objects_type = models.CharField(
        max_length=50,
        choices=OBJECT_TYPE_CHOICES,
        default='product'
    )

    # Rating
    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    # Content
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    comment = models.TextField(blank=True, null=True)

    # Sub-ratings (optional breakdown)
    food_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # for restaurants
    delivery_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # delivery speed
    service_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # customer service
    value_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # value for money

    # Media
    images = models.JSONField(
        default=list,
        blank=True
    )  # list of image URLs

    # Linked order (for verified reviews)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews'
    )
    is_verified = models.BooleanField(
        default=False
    )  # verified purchase/order

    # Business response
    reply = models.TextField(blank=True, null=True)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_replies'
    )
    replied_at = models.DateTimeField(null=True, blank=True)

    # Moderation
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='approved'
    )
    is_featured = models.BooleanField(default=False)

    # Helpfulness
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'objects_id', 'objects_type')

    def __str__(self):
        return f"{self.user.email} - {self.objects_type} - {self.rating}★"

    @property
    def average_sub_rating(self):
        """Average of all sub-ratings"""
        ratings = [
            r for r in [
                self.food_rating,
                self.delivery_rating,
                self.service_rating,
                self.value_rating
            ] if r is not None
        ]
        if ratings:
            return round(sum(ratings) / len(ratings), 1)
        return None


class ReviewHelpfulness(TimeStampedModel):
    """
    Track helpful/not helpful votes on reviews
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='helpfulness_votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='helpfulness_votes'
    )
    is_helpful = models.BooleanField()

    class Meta:
        unique_together = ('review', 'user')

    def __str__(self):
        vote = 'helpful' if self.is_helpful else 'not helpful'
        return f"{self.user.email} - {vote}"


class ReviewReport(TimeStampedModel):
    """
    Report inappropriate reviews
    """
    REASON_CHOICES = (
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('fake', 'Fake Review'),
        ('offensive', 'Offensive Language'),
        ('irrelevant', 'Irrelevant'),
        ('other', 'Other'),
    )

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_reports'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES
    )
    description = models.TextField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports'
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ('review', 'reported_by')

    def __str__(self):
        return f"Report on review {self.review.id} - {self.reason}"