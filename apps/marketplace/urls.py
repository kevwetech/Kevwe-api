from django.urls import path
from .views import (
    IndustryListCreateView, IndustryDetailView,
    BusinessCategoryListView,
    BusinessListView, BusinessDetailView,
    RegisterBusinessView, MyBusinessView,
    BusinessSettingsView,
    OrderSettingsView, BookingSettingsView,
    ServiceSettingsView,
    BusinessHoursView, BusinessImageView,
    BusinessDocumentView,
    NearbyBusinessesView,
    AdminBusinessListView, AdminBusinessApproveView,
    AdminVerifyBusinessDocumentView,
    AppointmentSettingsView, RideSettingsView, UniversalSearchView,
    BusinessContentBlockDetail, BusinessFAQListCreate,
    BusinessContentBlockListCreate, BusinessFAQDetail,
    BusinessPolicyDetail, BusinessPromotionListCreate,
    BusinessPolicyListCreate, BusinessPromotionDetail,
    InteractionFormListCreate, InteractionFormResolveView,
    InteractionFormDetail
)

urlpatterns = [
    # Industries
    path(
        'industries/',
        IndustryListCreateView.as_view(),
        name='industries'
    ),
    path(
        'industries/<int:pk>/',
        IndustryDetailView.as_view(),
        name='industry_detail'
    ),

    # Categories
    path(
        'categories/',
        BusinessCategoryListView.as_view(),
        name='business_categories'
    ),

    # Public business browse
    path(
        'businesses/',
        BusinessListView.as_view(),
        name='businesses'
    ),
    path(
        'businesses/<int:pk>/',
        BusinessDetailView.as_view(),
        name='business_detail'
    ),
    path(
        'businesses/nearby/',
        NearbyBusinessesView.as_view(),
        name='nearby_businesses'
    ),

    # Business registration & management
    path(
        'businesses/register/',
        RegisterBusinessView.as_view(),
        name='register_business'
    ),
    path(
        'businesses/mine/',
        MyBusinessView.as_view(),
        name='my_businesses'
    ),
    path(
        'businesses/<int:pk>/update/',
        MyBusinessView.as_view(),
        name='update_business'
    ),

    # Settings
    path(
        'businesses/<int:pk>/settings/',
        BusinessSettingsView.as_view(),
        name='business_settings'
    ),
    path(
        'businesses/<int:pk>/order-settings/',
        OrderSettingsView.as_view(),
        name='order_settings'
    ),
    path(
        'businesses/<int:pk>/booking-settings/',
        BookingSettingsView.as_view(),
        name='booking_settings'
    ),
    path(
        'businesses/<int:pk>/service-settings/',
        ServiceSettingsView.as_view(),
        name='service_settings'
    ),
    path(
        'businesses/<int:business_id>/faqs/',
        BusinessFAQListCreate.as_view(), 
        name='business_faqs'
    ),
    path(
        'businesses/<int:business_id>/faqs/<int:pk>/',
        BusinessFAQDetail.as_view(), 
        name='business_faq_detail'
    ),

    path(
        'businesses/<int:business_id>/promotions/',
        BusinessPromotionListCreate.as_view(), 
        name='business_promotions'
    ),
    path(
        'businesses/<int:business_id>/promotions/<int:pk>/',
        BusinessPromotionDetail.as_view(), 
        name='business_promotion_detail'
    ),

    path(
        'businesses/<int:business_id>/policies/',
        BusinessPolicyListCreate.as_view(), 
        name='business_policies'
    ),
    path(
        'businesses/<int:business_id>/policies/<int:pk>/',
        BusinessPolicyDetail.as_view(),
        name='business_policy_detail'
    ),

    path(
        'businesses/<int:business_id>/blocks/',
        BusinessContentBlockListCreate.as_view(),
        name='business_blocks'
    ),
    path(
        'businesses/<int:business_id>/blocks/<int:pk>/',
        BusinessContentBlockDetail.as_view(), 
        name='business_block_detail'
    ),


    # Hours, images, documents
    path(
        'businesses/<int:pk>/hours/',
        BusinessHoursView.as_view(),
        name='business_hours'
    ),
    path(
        'businesses/<int:pk>/images/',
        BusinessImageView.as_view(),
        name='business_images'
    ),
    path(
        'businesses/<int:pk>/documents/',
        BusinessDocumentView.as_view(),
        name='business_documents'
    ),
     path(
        'interaction-forms/', 
        InteractionFormListCreate.as_view(),
        name='interaction_form_list'   
    ),
    path(
        'interaction-forms/resolve/', 
        InteractionFormResolveView.as_view(),
        name='interaction_form_resolve'
    ),
    path(
        'interaction-forms/<int:pk>/', 
        InteractionFormDetail.as_view(),
        name='interaction_form_detail'
    ),

    # Admin
    path(
        'admin/businesses/',
        AdminBusinessListView.as_view(),
        name='admin_businesses'
    ),
    path(
        'admin/businesses/<int:pk>/approve/',
        AdminBusinessApproveView.as_view(),
        name='admin_approve_business'
    ),
    path(
        'admin/documents/<int:pk>/verify/',
        AdminVerifyBusinessDocumentView.as_view(),
        name='admin_verify_document'
    ),
    path('businesses/<int:pk>/appointment-settings/',
    AppointmentSettingsView.as_view(),
    name='appointment-settings'
    ),
    path('businesses/<int:pk>/ride-settings/',
    RideSettingsView.as_view(),
    name='ride-settings'
    ),
    path('search/', UniversalSearchView.as_view(), name='universal_search'),
]