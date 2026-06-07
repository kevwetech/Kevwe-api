from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import TimeStampedModel


class Review(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    # Generic foreign key to support any model
    # (products, rooms, services etc)
    product_id = models.IntegerField()
    product_type = models.CharField(
        max_length=50,
        default='product'
    )

    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        # One review per user per product
        unique_together = ('user', 'product_id', 'product_type')

    def __str__(self):
        return f"{self.user.email} - {self.rating}★"