from django.urls import path
from .views import (
    PermissionListView,
    RoleListCreateView, RoleDetailView,
    StaffListView, StaffDetailView,
    InviteStaffView, AcceptInvitationView,
    CreateStaffAccountView,
    WorkScheduleView,
    CheckPermissionView,
    MyBusinessMembershipsView,
    StaffActivityLogView,
    InvitationListView,
    DepartmentListCreateView,
    StaffShiftView,
    AttendanceView,
    TemporaryPermissionView,
    StaffNoteView,
    StaffLeaveListCreateView,
    StaffLeaveReviewView,
    StaffPINView,
    VerifyPINView,
    StaffDeviceView,
    ImpersonateStaffView,
)

urlpatterns = [
    # Platform permissions
    path(
        'permissions/',
        PermissionListView.as_view(),
        name='permissions'
    ),

    # My businesses
    path(
        'my-businesses/',
        MyBusinessMembershipsView.as_view(),
        name='my_businesses'
    ),

    # Permission check
    path(
        'check-permission/',
        CheckPermissionView.as_view(),
        name='check_permission'
    ),

    # Accept invitation
    path(
        'invitations/accept/',
        AcceptInvitationView.as_view(),
        name='accept_invitation'
    ),

    # ── Business-scoped endpoints ──────────────────────────

    # Roles
    path(
        'businesses/<int:business_id>/roles/',
        RoleListCreateView.as_view(),
        name='roles'
    ),
    path(
        'businesses/<int:business_id>/roles/<int:pk>/',
        RoleDetailView.as_view(),
        name='role_detail'
    ),

    # Members
    path(
        'businesses/<int:business_id>/members/',
        StaffListView.as_view(),
        name='staff_list'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/',
        StaffDetailView.as_view(),
        name='staff_detail'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/schedule/',
        WorkScheduleView.as_view(),
        name='work_schedule'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/shifts/',
        StaffShiftView.as_view(),
        name='staff_shifts'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/attendance/',
        AttendanceView.as_view(),
        name='attendance'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/temp-permissions/',
        TemporaryPermissionView.as_view(),
        name='temp_permissions'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/notes/',
        StaffNoteView.as_view(),
        name='staff_notes'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/pin/',
        StaffPINView.as_view(),
        name='staff_pin'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/pin/verify/',
        VerifyPINView.as_view(),
        name='verify_pin'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/devices/',
        StaffDeviceView.as_view(),
        name='staff_devices'
    ),
    path(
        'businesses/<int:business_id>/members/<int:pk>/impersonate/',
        ImpersonateStaffView.as_view(),
        name='impersonate_staff'
    ),

    # Invitations
    path(
        'businesses/<int:business_id>/invite/',
        InviteStaffView.as_view(),
        name='invite_staff'
    ),
    path(
        'businesses/<int:business_id>/invitations/',
        InvitationListView.as_view(),
        name='invitations'
    ),

    # Create account
    path(
        'businesses/<int:business_id>/create-account/',
        CreateStaffAccountView.as_view(),
        name='create_staff_account'
    ),

    # Departments
    path(
        'businesses/<int:business_id>/departments/',
        DepartmentListCreateView.as_view(),
        name='departments'
    ),

    # Leave
    path(
        'businesses/<int:business_id>/leave/',
        StaffLeaveListCreateView.as_view(),
        name='staff_leave'
    ),
    path(
        'businesses/<int:business_id>/leave/<int:pk>/review/',
        StaffLeaveReviewView.as_view(),
        name='leave_review'
    ),

    # Activity log
    path(
        'businesses/<int:business_id>/activity/',
        StaffActivityLogView.as_view(),
        name='staff_activity'
    ),
]