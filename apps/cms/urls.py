from django.urls import path
from .views import (
    SiteSettingsView,
    HomePageView,
    AboutPageView,
    ServiceListCreateView,
    ServiceDetailView,
    ContactInfoView,
    ContactMessageListView,
    ContactMessageDetailView,
    FAQListCreateView,
    FAQDetailView,
    TestimonialListCreateView,
    TestimonialDetailView,
    TeamMemberListCreateView,
    TeamMemberDetailView,
    FeatureListCreateView,
    GalleryListCreateView,
    FullSiteView,
)

urlpatterns = [
    # Full site content
    path('', FullSiteView.as_view(), name='full_site'),

    # Site settings
    path('settings/', SiteSettingsView.as_view(), name='site_settings'),

    # Pages
    path('homepage/', HomePageView.as_view(), name='homepage'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('contact/', ContactInfoView.as_view(), name='contact'),

    # Services
    path('services/', ServiceListCreateView.as_view(), name='services'),
    path('services/<int:pk>/', ServiceDetailView.as_view(), name='service_detail'),

    # Contact messages
    path('messages/', ContactMessageListView.as_view(), name='contact_messages'),
    path('messages/<int:pk>/', ContactMessageDetailView.as_view(), name='contact_message_detail'),

    # FAQs
    path('faqs/', FAQListCreateView.as_view(), name='faqs'),
    path('faqs/<int:pk>/', FAQDetailView.as_view(), name='faq_detail'),

    # Testimonials
    path('testimonials/', TestimonialListCreateView.as_view(), name='testimonials'),
    path('testimonials/<int:pk>/', TestimonialDetailView.as_view(), name='testimonial_detail'),

    # Team
    path('team/', TeamMemberListCreateView.as_view(), name='team'),
    path('team/<int:pk>/', TeamMemberDetailView.as_view(), name='team_detail'),

    # Features
    path('features/', FeatureListCreateView.as_view(), name='features'),

    # Gallery
    path('gallery/', GalleryListCreateView.as_view(), name='gallery'),
]