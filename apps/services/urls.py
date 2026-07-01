from django.urls import path
from .views import (
    ServiceCategoryListView, ServiceListView,
    NearbyProvidersView,
    RegisterServiceProviderView,
    ServiceProviderProfileView,
    UpdateProviderLocationView,
    ProviderAvailabilityView,
    ProviderAvailabilityScheduleView,
    ProviderSkillView, ProviderCertificationView,
    ProviderVehicleView,
    ServiceRequestListCreateView,
    ServiceRequestDetailView,
    UploadAttachmentView,
    RespondToOfferView,
    SubmitQuoteView, RespondToQuoteView,
    StartJobView, CompleteJobView,
    ConfirmCompletionView,
    CancelServiceRequestView,
    RateServiceRequestView,
    ProviderRequestListView,
    ProviderOfferListView,
    AdminProviderListView,
    AdminVerifyProviderView,
    AdminVerifyCertificationView,
    AdminCheckProviderVerificationView
)

urlpatterns = [
    # ── Browse ──────────────────────────────────────────
    path(
        'categories/',
        ServiceCategoryListView.as_view(),
        name='service_categories'
    ),
    path(
        'list/',
        ServiceListView.as_view(),
        name='services_list'
    ),
    path(
        'nearby/',
        NearbyProvidersView.as_view(),
        name='nearby_providers'
    ),

    # ── Provider registration & profile ─────────────────
    path(
        'providers/register/',
        RegisterServiceProviderView.as_view(),
        name='register_provider'
    ),
    path(
        'providers/profile/',
        ServiceProviderProfileView.as_view(),
        name='provider_profile'
    ),
    path(
        'providers/<int:pk>/profile/',
        ServiceProviderProfileView.as_view(),
        name='provider_profile_pk'
    ),
    path(
        'providers/<int:pk>/location/',
        UpdateProviderLocationView.as_view(),
        name='provider_location'
    ),
    path(
        'providers/<int:pk>/availability/',
        ProviderAvailabilityView.as_view(),
        name='provider_availability'
    ),
    path(
        'providers/<int:pk>/schedule/',
        ProviderAvailabilityScheduleView.as_view(),
        name='provider_schedule'
    ),
    path(
        'providers/<int:pk>/skills/',
        ProviderSkillView.as_view(),
        name='provider_skills'
    ),
    path(
        'providers/<int:pk>/certifications/',
        ProviderCertificationView.as_view(),
        name='provider_certifications'
    ),
    path(
        'providers/<int:pk>/vehicles/',
        ProviderVehicleView.as_view(),
        name='provider_vehicles'
    ),
    path(
        'providers/<int:pk>/requests/',
        ProviderRequestListView.as_view(),
        name='provider_requests'
    ),
    path(
        'providers/<int:pk>/offers/',
        ProviderOfferListView.as_view(),
        name='provider_offers'
    ),

    # ── Service Requests (customer) ──────────────────────
    path(
        'requests/',
        ServiceRequestListCreateView.as_view(),
        name='service_requests'
    ),
    path(
        'requests/<int:pk>/',
        ServiceRequestDetailView.as_view(),
        name='service_request_detail'
    ),
    path(
        'requests/<int:pk>/attachments/',
        UploadAttachmentView.as_view(),
        name='upload_attachment'
    ),
    path(
        'requests/<int:pk>/quote/',
        SubmitQuoteView.as_view(),
        name='submit_quote'
    ),
    path(
        'requests/<int:pk>/start/',
        StartJobView.as_view(),
        name='start_job'
    ),
    path(
        'requests/<int:pk>/complete/',
        CompleteJobView.as_view(),
        name='complete_job'
    ),
    path(
        'requests/<int:pk>/confirm/',
        ConfirmCompletionView.as_view(),
        name='confirm_completion'
    ),
    path(
        'requests/<int:pk>/rate/',
        RateServiceRequestView.as_view(),
        name='rate_request'
    ),
    path(
        'requests/<int:pk>/cancel/',
        CancelServiceRequestView.as_view(),
        name='cancel_request'
    ),

    # ── Offers ───────────────────────────────────────────
    path(
        'offers/<int:pk>/respond/',
        RespondToOfferView.as_view(),
        name='respond_offer'
    ),

    # ── Quotes ───────────────────────────────────────────
    path(
        'quotes/<int:pk>/respond/',
        RespondToQuoteView.as_view(),
        name='respond_quote'
    ),

    # ── Admin ────────────────────────────────────────────
    path(
        'admin/providers/',
        AdminProviderListView.as_view(),
        name='admin_providers'
    ),
    path(
        'admin/providers/<int:pk>/verify/',
        AdminVerifyProviderView.as_view(),
        name='admin_verify_provider'
    ),
    path(
        'admin/certifications/<int:pk>/verify/',
        AdminVerifyCertificationView.as_view(),
        name='admin_verify_cert'
    ),
    path(
        'admin/providers/<int:pk>/check-verify/',
        AdminCheckProviderVerificationView.as_view(),
        name='check_provider_verify'
    ),

]