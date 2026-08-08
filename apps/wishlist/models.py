from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


# Valid item types a customer can save. Keep in sync with the
# marketplace's interaction types + business itself.
WISHLIST_ITEM_TYPES = (
    ('product',     'Product'),       # catalog.Product
    ('bookable',    'Bookable Item'), # bookings.BookableItem (rooms etc.)
    ('service',     'Service'),       # services.Service
    ('appointment', 'Appointment'),   # appointments.AppointmentService
    ('business',    'Business'),      # marketplace.Business (whole vendor)
    ('route',       'Transport Route'),
)


class WishlistCollection(TimeStampedModel):
    """
    Optional named lists to organize saved items.
    e.g. "Hotels for December", "Restaurants to Try"
    Every user has one is_default collection created lazily.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_collections',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_wishlist_collection',
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.name}"

    @property
    def items_count(self):
        return self.items.count()


class WishlistItem(TimeStampedModel):
    """
    Generic (polymorphic) saved item.
    item_type + item_id points at any marketplace object.
    Django does not enforce the FK — the service layer validates
    the combination exists before creating.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist',
    )
    collection = models.ForeignKey(
        WishlistCollection,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='items',
    )
    item_id = models.PositiveIntegerField()
    item_type = models.CharField(
        max_length=50,
        choices=WISHLIST_ITEM_TYPES,
        default='product',
    )
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'item_id', 'item_type'],
                name='unique_user_wishlist_item',
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.item_type} - {self.item_id}"