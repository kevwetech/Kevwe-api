from rest_framework import serializers
from apps.common.serializers import BaseItemSerializer, BaseCategorySerializer
from .models import Product, Category


class CategorySerializer(BaseCategorySerializer):
    class Meta(BaseCategorySerializer.Meta):
        model = Category


class ProductSerializer(BaseItemSerializer):
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta(BaseItemSerializer.Meta):
        model = Product
        fields = BaseItemSerializer.Meta.fields + (
            'category',
            'category_name',
            'stock',
            'sku',
        )