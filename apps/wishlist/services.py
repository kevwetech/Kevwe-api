"""
Wishlist service layer.
Validates that item_type + item_id actually points at a real object
before it gets saved — Django can't enforce a polymorphic FK.
"""
from django.apps import apps


# Maps item_type → (app_label, ModelName) for existence checks.
ITEM_TYPE_MODELS = {
    'product':     ('catalog', 'Product'),
    'bookable':    ('bookings', 'BookableItem'),
    'service':     ('services', 'Service'),
    'appointment': ('appointments', 'AppointmentService'),
    'business':    ('marketplace', 'Business'),
    'route':       ('rides', 'TransportRoute'),
}


def item_exists(item_type, item_id):
    """Return True if the referenced object exists, else False.
    Unknown item_type → False."""
    mapping = ITEM_TYPE_MODELS.get(item_type)
    if not mapping:
        return False
    app_label, model_name = mapping
    try:
        Model = apps.get_model(app_label, model_name)
    except LookupError:
        return False
    return Model.objects.filter(pk=item_id).exists()


def resolve_item(item_type, item_id):
    """Return the actual object or None (for enriching responses)."""
    mapping = ITEM_TYPE_MODELS.get(item_type)
    if not mapping:
        return None
    app_label, model_name = mapping
    try:
        Model = apps.get_model(app_label, model_name)
        return Model.objects.filter(pk=item_id).first()
    except LookupError:
        return None


def get_or_create_default_collection(user):
    """Every user has exactly one default collection ('My Wishlist')."""
    from .models import WishlistCollection
    collection, _ = WishlistCollection.objects.get_or_create(
        user=user, is_default=True,
        defaults={'name': 'My Wishlist'},
    )
    return collection