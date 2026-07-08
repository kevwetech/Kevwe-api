from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SavedAddress, UserProfile



User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'full_name',
            'phone',
            'avatar',
            'role',
            'is_verified',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'email',
            'role',
            'is_verified',
            'created_at',
            'updated_at',
        )


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'full_name',
            'phone',
        )

    def validate_full_name(self, value):
        if len(value) < 2:
            raise serializers.ValidationError(
                'Full name must be at least 2 characters'
            )
        return value


class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('avatar',)

    def validate_avatar(self, value):
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError(
                'Image size must not exceed 2MB'
            )
        return value

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if instance.avatar and request:
            rep['avatar'] = request.build_absolute_uri(
                instance.avatar.url
            )
        return rep


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'password': 'Passwords do not match'}
            )
        return attrs


class SavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAddress
        fields = [
            'id', 'label', 'name', 'address',
            'city', 'state', 'latitude', 'longitude',
            'is_default', 'is_active', 'created_at',
        ]
        read_only_fields = ('id', 'created_at')


class CreateSavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAddress
        fields = [
            'label', 'name', 'address',
            'city', 'state', 'latitude', 'longitude',
            'is_default',
        ]


class ValidateAddressSerializer(serializers.Serializer):
    current_lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    current_lng = serializers.DecimalField(max_digits=9, decimal_places=6)