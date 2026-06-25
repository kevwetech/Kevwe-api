from django.urls import path
from .views import (
    IndustryListCreateView,
    IndustryDetailView,
    BusinessListView,
    BusinessDetailView,
    RegisterBusinessView,
    MyBusinessView,
    BusinessHoursView,
    BusinessImageView,
    BusinessDocumentView,
    PermissionListCreateView,
    PermissionDetailView,
    BusinessRoleListCreateView,
    BusinessRoleDetailView,
    BusinessStaffListView,
    InviteStaffView,
    AcceptStaffInvitationView,
    BusinessStaffDetailView,
    MyStaffProfileView,
    NearbyBusinessesView,
    AdminBusinessListView,
    AdminBusinessApproveView,
)

urlpatterns = [
    # Industries
    path('industries/', IndustryListCreateView.as_view(), name='industries'),
    path('industries/<int:pk>/', IndustryDetailView.as_view(), name='industry_detail'),

    # Businesses - public
    path('businesses/', BusinessListView.as_view(), name='businesses'),
    path('businesses/nearby/', NearbyBusinessesView.as_view(), name='nearby_businesses'),
    path('businesses/<int:pk>/', BusinessDetailView.as_view(), name='business_detail'),

    # Business - vendor
    path('businesses/register/', RegisterBusinessView.as_view(), name='register_business'),
    path('businesses/my/', MyBusinessView.as_view(), name='my_businesses'),
    path('businesses/<int:pk>/my/', MyBusinessView.as_view(), name='my_business_update'),
    path('businesses/<int:pk>/hours/', BusinessHoursView.as_view(), name='business_hours'),
    path('businesses/<int:pk>/images/', BusinessImageView.as_view(), name='business_images'),
    path('businesses/<int:pk>/documents/', BusinessDocumentView.as_view(), name='business_documents'),

    # Permissions (admin only)
    path('permissions/', PermissionListCreateView.as_view(), name='permissions'),
    path('permissions/<int:pk>/', PermissionDetailView.as_view(), name='permission_detail'),

    # Roles
    path('businesses/<int:pk>/roles/', BusinessRoleListCreateView.as_view(), name='business_roles'),
    path('businesses/<int:pk>/roles/<int:role_id>/', BusinessRoleDetailView.as_view(), name='business_role_detail'),

    # Staff
    path('businesses/<int:pk>/staff/', BusinessStaffListView.as_view(), name='business_staff'),
    path('businesses/<int:pk>/staff/invite/', InviteStaffView.as_view(), name='invite_staff'),
    path('businesses/<int:pk>/staff/<int:staff_id>/', BusinessStaffDetailView.as_view(), name='staff_detail'),
    path('staff/accept-invitation/', AcceptStaffInvitationView.as_view(), name='accept_staff_invitation'),
    path('staff/my/', MyStaffProfileView.as_view(), name='my_staff_profile'),

    # Admin
    path('admin/businesses/', AdminBusinessListView.as_view(), name='admin_businesses'),
    path('admin/businesses/<int:pk>/', AdminBusinessApproveView.as_view(), name='admin_business_approve'),
]