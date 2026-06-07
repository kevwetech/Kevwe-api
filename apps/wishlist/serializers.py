from rest_framework import serializers
from .models import WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = (
            'id',
            'product_id',
            'product_type',
            'note',
            'created_at',
        )
        read_only_fields = (
            'id',
            'created_at',
        )


class AddToWishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = (
            'product_id',
            'product_type',
            'note',
        )