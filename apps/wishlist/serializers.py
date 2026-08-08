from rest_framework import serializers
from .models import WishlistItem, WishlistCollection, WISHLIST_ITEM_TYPES
from .services import item_exists, resolve_item


# ── Collections ───────────────────────────────────
class WishlistCollectionSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = WishlistCollection
        fields = (
            'id', 'name', 'description', 'is_default',
            'items_count', 'created_at',
        )
        read_only_fields = ('id', 'is_default', 'items_count', 'created_at')


# ── Wishlist items ────────────────────────────────
class WishlistItemSerializer(serializers.ModelSerializer):
    """Read serializer — enriches with a light snapshot of the item."""
    item = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = (
            'id', 'collection', 'item_id', 'item_type',
            'note', 'item', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_item(self, obj):
        """Light snapshot of the referenced object for the UI."""
        target = resolve_item(obj.item_type, obj.item_id)
        if not target:
            return None
        return {
            'id': target.pk,
            'name': getattr(target, 'name', str(target)),
            'exists': True,
        }


class AddToWishlistSerializer(serializers.ModelSerializer):
    item_type = serializers.ChoiceField(
        choices=WISHLIST_ITEM_TYPES, default='product')

    class Meta:
        model = WishlistItem
        fields = ('collection', 'item_id', 'item_type', 'note')

    def validate(self, attrs):
        item_type = attrs.get('item_type', 'product')
        item_id = attrs['item_id']
        # Polymorphic FK check — the object must actually exist
        if not item_exists(item_type, item_id):
            raise serializers.ValidationError(
                f"No {item_type} found with id {item_id}."
            )
        return attrs

    def validate_collection(self, collection):
        # Users can only file into their own collections
        if collection is None:
            return collection
        request = self.context.get('request')
        if request and collection.user_id != request.user.id:
            raise serializers.ValidationError(
                "That collection isn't yours.")
        return collection