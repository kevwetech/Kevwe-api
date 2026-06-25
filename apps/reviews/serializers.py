from rest_framework import serializers
from .models import Review, ReviewHelpfulness, ReviewReport


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )
    user_avatar = serializers.ImageField(
        source='user.avatar',
        read_only=True
    )
    replied_by_name = serializers.CharField(
        source='replied_by.full_name',
        read_only=True
    )
    average_sub_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Review
        fields = (
            'id',
            'user',
            'user_name',
            'user_avatar',
            'objects_id',
            'objects_type',
            'rating',
            'title',
            'comment',
            'food_rating',
            'delivery_rating',
            'service_rating',
            'value_rating',
            'average_sub_rating',
            'images',
            'order',
            'is_verified',
            'reply',
            'replied_by',
            'replied_by_name',
            'replied_at',
            'status',
            'is_featured',
            'helpful_count',
            'not_helpful_count',
            'created_at',
        )
        read_only_fields = (
            'id',
            'user',
            'is_verified',
            'reply',
            'replied_by',
            'replied_at',
            'status',
            'helpful_count',
            'not_helpful_count',
            'average_sub_rating',
            'created_at',
        )


class CreateReviewSerializer(serializers.Serializer):
    objects_id = serializers.IntegerField()
    objects_type = serializers.ChoiceField(
        choices=[
            'product', 'business', 'driver',
            'order', 'delivery', 'ride', 'booking'
        ]
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(
        required=False,
        allow_blank=True
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True
    )
    food_rating = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5
    )
    delivery_rating = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5
    )
    service_rating = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5
    )
    value_rating = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5
    )
    order_id = serializers.IntegerField(required=False)


class ReplyReviewSerializer(serializers.Serializer):
    reply = serializers.CharField()


class ReviewHelpfulnessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewHelpfulness
        fields = ('id', 'review', 'user', 'is_helpful', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')


class ReviewReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReport
        fields = (
            'id',
            'review',
            'reported_by',
            'reason',
            'description',
            'is_resolved',
            'created_at',
        )
        read_only_fields = (
            'id',
            'reported_by',
            'is_resolved',
            'created_at',
        )