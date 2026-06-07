from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class WishlistItem(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist'
    )
    product_id = models.IntegerField()
    product_type = models.CharField(
        max_length=50,
        default='product'
    )
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'product_id', 'product_type')

    def __str__(self):
        return f"{self.user.email} - {self.product_id}"