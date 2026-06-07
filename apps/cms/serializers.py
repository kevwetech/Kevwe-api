from rest_framework import serializers
from .models import (
    SiteSettings,
    HomePage,
    AboutPage,
    Service,
    ContactInfo,
    ContactMessage,
    FAQ,
    Testimonial,
    TeamMember,
    Feature,
    Gallery,
)


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class HomePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomePage
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AboutPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutPage
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            'id',
            'title',
            'slug',
            'short_description',
            'description',
            'icon_type',
            'icon',
            'image',
            'show_price',
            'starting_price',
            'price_label',
            'cta_text',
            'cta_url',
            'is_featured',
            'is_active',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = (
            'id',
            'name',
            'email',
            'phone',
            'subject',
            'message',
            'status',
            'created_at',
        )
        read_only_fields = (
            'id',
            'status',
            'created_at',
        )


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = (
            'id',
            'question',
            'answer',
            'category',
            'is_featured',
            'is_active',
            'order',
            'views',
            'created_at',
        )
        read_only_fields = ('id', 'views', 'created_at')


class TestimonialSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(
        source='service.title',
        read_only=True
    )

    class Meta:
        model = Testimonial
        fields = (
            'id',
            'name',
            'title',
            'company',
            'avatar',
            'content',
            'rating',
            'service',
            'service_name',
            'status',
            'is_featured',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'status', 'created_at')


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = (
            'id',
            'name',
            'title',
            'bio',
            'avatar',
            'email',
            'phone',
            'linkedin',
            'twitter',
            'instagram',
            'is_active',
            'order',
            'created_at',
        )
        


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = (
            'id',
            'title',
            'description',
            'icon',
            'image',
            'is_active',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = (
            'id',
            'title',
            'description',
            'image',
            'gallery_type',
            'is_active',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')