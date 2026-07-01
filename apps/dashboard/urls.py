from django.urls import path
from .views import (
    DashboardView,
    AdminUserListView,
    AdminUserDetailView,
    AdminRevenueView,
    BusinessDashboardView,
    BusinessOrdersSectionView,
    BusinessBookingsSectionView,
    BusinessRevenueSectionView,
    BusinessCustomersSectionView,
    BusinessStaffSectionView,
    BusinessWalletSectionView,
    BusinessReviewsSectionView,
)
from .user_views import UserDashboardView

urlpatterns = [
    # ── Super Admin ───────────────────────────────────────
    path(
        '',
        DashboardView.as_view(),
        name='dashboard'
    ),
    path(
        'admin/revenue/',
        AdminRevenueView.as_view(),
        name='admin_revenue'
    ),
    path(
        'users/',
        AdminUserListView.as_view(),
        name='admin_users'
    ),
    path(
        'users/<int:pk>/',
        AdminUserDetailView.as_view(),
        name='admin_user_detail'
    ),

    # ── Business Owner ────────────────────────────────────
    path(
        'business/<int:business_id>/',
        BusinessDashboardView.as_view(),
        name='business_dashboard'
    ),
    path(
        'business/<int:business_id>/orders/',
        BusinessOrdersSectionView.as_view(),
        name='business_orders_section'
    ),
    path(
        'business/<int:business_id>/bookings/',
        BusinessBookingsSectionView.as_view(),
        name='business_bookings_section'
    ),
    path(
        'business/<int:business_id>/revenue/',
        BusinessRevenueSectionView.as_view(),
        name='business_revenue_section'
    ),
    path(
        'business/<int:business_id>/customers/',
        BusinessCustomersSectionView.as_view(),
        name='business_customers_section'
    ),
    path(
        'business/<int:business_id>/staff-summary/',
        BusinessStaffSectionView.as_view(),
        name='business_staff_section'
    ),
    path(
        'business/<int:business_id>/wallet-summary/',
        BusinessWalletSectionView.as_view(),
        name='business_wallet_section'
    ),
    path(
        'business/<int:business_id>/reviews-summary/',
        BusinessReviewsSectionView.as_view(),
        name='business_reviews_section'
    ),

    # ── User ──────────────────────────────────────────────
    path(
        'user/',
        UserDashboardView.as_view(),
        name='user_dashboard'
    ),
]