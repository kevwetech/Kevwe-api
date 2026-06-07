from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Review

User = get_user_model()


class ReviewerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'full_name', 'avatar')


class ReviewSerializer(serializers.ModelSerializer):
    user = ReviewerSerializer(read_only=True)
    rating_display = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            'id',
            'user',
            'product_id',
            'product_type',
            'rating',
            'rating_display',
            'title',
            'comment',
            'is_verified',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'user',
            'product_id',
            'product_type',
            'is_verified',
            'created_at',
            'updated_at',
        )

    def get_rating_display(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)


class CreateReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = (
            'rating',
            'title',
            'comment',
        )

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError(
                'Rating must be between 1 and 5'
            )
        return value