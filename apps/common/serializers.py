from rest_framework import serializers


class BaseItemSerializer(serializers.ModelSerializer):
    """
    Base serializer for any item
    Extend this for products, rooms etc
    """

    class Meta:
        fields = (
            'id',
            'name',
            'description',
            'price',
            'image',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class BaseCategorySerializer(serializers.ModelSerializer):
    """
    Base serializer for any category
    """

    class Meta:
        fields = (
            'id',
            'name',
            'description',
            'image',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')