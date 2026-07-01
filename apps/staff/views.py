from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from django.utils import timezone
from datetime import timedelta
from .models import (
    Permission, Role, RolePermission, BusinessMember,
    StaffInvitation, StaffAccount, WorkSchedule,
    StaffActivityLog, Department, StaffShift,
    StaffAttendance, StaffDevice, TemporaryPermission,
    StaffNote, StaffLeave, StaffPIN,
)
from .serializers import (
    PermissionSerializer, RoleSerializer,
    BusinessMemberSerializer, StaffInvitationSerializer,
    WorkScheduleSerializer, StaffActivityLogSerializer,
    DepartmentSerializer, StaffAttendanceSerializer,
    StaffDeviceSerializer, TemporaryPermissionSerializer,
    StaffNoteSerializer, StaffPINSerializer
)
from .utils import (
    generate_invitation_token, generate_temp_password,
    send_staff_invitation, send_temp_password_notification,
    check_permission,
)


def get_business_or_403(request, business_id):
    """Helper — get business and verify requester is owner."""
    from apps.marketplace.models import Business
    try:
        business = Business.objects.get(pk=business_id)
        if business.owner != request.user:
            return None, api_response(
                'error', 'Only the business owner can do this',
                http_status=status.HTTP_403_FORBIDDEN
            )
        return business, None
    except Business.DoesNotExist:
        return None, api_response(
            'error', 'Business not found',
            http_status=status.HTTP_404_NOT_FOUND
        )


# ── Platform Permissions (admin only) ────────────────────

class PermissionListView(APIView):
    """
    GET  - List all platform permissions (public for owners)
    POST - Create permission (admin only)
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        permissions = Permission.objects.filter(
            is_active=True
        )
        category = request.query_params.get('category')
        if category:
            permissions = permissions.filter(category=category)

        # Group by category
        grouped = {}
        for perm in permissions:
            cat = perm.get_category_display()
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(
                PermissionSerializer(perm).data
            )

        return api_response(
            'success', 'Permissions retrieved',
            data={
                'total': permissions.count(),
                'grouped': grouped,
            }
        )

    def post(self, request):
        serializer = PermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Permission created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Roles (business owner manages) ───────────────────────

class RoleListCreateView(APIView):
    """
    GET  - List roles for a business
    POST - Create a new role
    GET/POST /api/v1/staff/businesses/<business_id>/roles/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            # Non-owners can view roles too
            from apps.marketplace.models import Business
            try:
                business = Business.objects.get(
                    pk=business_id
                )
            except Business.DoesNotExist:
                return api_response(
                    'error', 'Business not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

        roles = Role.objects.filter(
            business=business, is_active=True
        )
        return api_response(
            'success', 'Roles retrieved',
            data={
                'count': roles.count(),
                'results': RoleSerializer(
                    roles, many=True
                ).data
            }
        )

    def post(self, request, business_id):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        role = Role.objects.create(
            business=business,
            name=request.data.get('name'),
            description=request.data.get('description', ''),
            is_default=request.data.get('is_default', False),
        )

        # Assign permissions if provided
        permission_ids = request.data.get('permission_ids', [])
        if permission_ids:
            for perm_id in permission_ids:
                try:
                    perm = Permission.objects.get(
                        pk=perm_id,
                        is_owner_only=False
                    )
                    RolePermission.objects.create(
                        role=role,
                        permission=perm,
                        granted_by=request.user
                    )
                except Permission.DoesNotExist:
                    pass

        return api_response(
            'success', 'Role created',
            data=RoleSerializer(role).data,
            http_status=status.HTTP_201_CREATED
        )


class RoleDetailView(APIView):
    """PATCH/DELETE - Manage a specific role"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            role = Role.objects.get(
                pk=pk, business=business
            )
        except Role.DoesNotExist:
            return api_response(
                'error', 'Role not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if 'name' in request.data:
            role.name = request.data['name']
        if 'description' in request.data:
            role.description = request.data['description']
        if 'is_default' in request.data:
            role.is_default = request.data['is_default']
        role.save()

        # Update permissions if provided
        if 'permission_ids' in request.data:
            role.role_permissions.all().delete()
            for perm_id in request.data['permission_ids']:
                try:
                    perm = Permission.objects.get(
                        pk=perm_id, is_owner_only=False
                    )
                    RolePermission.objects.create(
                        role=role,
                        permission=perm,
                        granted_by=request.user
                    )
                except Permission.DoesNotExist:
                    pass

        return api_response(
            'success', 'Role updated',
            data=RoleSerializer(role).data
        )

    def delete(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            role = Role.objects.get(
                pk=pk, business=business
            )
        except Role.DoesNotExist:
            return api_response(
                'error', 'Role not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        role.is_active = False
        role.save()

        return api_response(
            'success', 'Role deleted'
        )


# ── Staff Members ─────────────────────────────────────────

class StaffListView(APIView):
    """
    GET - List all staff members of a business
    GET /api/v1/staff/businesses/<business_id>/members/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Must be owner or staff member to view
        is_owner = business.owner == request.user
        is_member = BusinessMember.objects.filter(
            business=business,
            user=request.user,
            status='active'
        ).exists()

        if not is_owner and not is_member:
            return api_response(
                'error', 'Not authorized',
                http_status=status.HTTP_403_FORBIDDEN
            )

        members = BusinessMember.objects.filter(
            business=business
        )
        member_status = request.query_params.get('status')
        if member_status:
            members = members.filter(status=member_status)

        return api_response(
            'success', 'Staff retrieved',
            data={
                'count': members.count(),
                'results': BusinessMemberSerializer(
                    members, many=True
                ).data
            }
        )


class StaffDetailView(APIView):
    """
    PATCH - Update staff member role/status
    DELETE - Remove staff member
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Staff member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if 'role_id' in request.data:
            try:
                role = Role.objects.get(
                    pk=request.data['role_id'],
                    business=business
                )
                member.role = role
            except Role.DoesNotExist:
                return api_response(
                    'error', 'Role not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

        if 'status' in request.data:
            member.status = request.data['status']

        if 'job_title' in request.data:
            member.job_title = request.data['job_title']

        # Update extra/denied permissions
        if 'extra_permission_ids' in request.data:
            member.extra_permissions.set(
                request.data['extra_permission_ids']
            )
        if 'denied_permission_ids' in request.data:
            member.denied_permissions.set(
                request.data['denied_permission_ids']
            )

        member.save()

        return api_response(
            'success', 'Staff member updated',
            data=BusinessMemberSerializer(member).data
        )

    def delete(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Staff member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Can't remove the owner
        if member.user == business.owner:
            return api_response(
                'error', 'Cannot remove the business owner',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        member.status = 'inactive'
        member.save()

        return api_response(
            'success', 'Staff member removed'
        )


# ── Invitations ───────────────────────────────────────────

class InviteStaffView(APIView):
    """
    POST - Invite a user to join as staff
    POST /api/v1/staff/businesses/<business_id>/invite/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        email = request.data.get('email')
        phone = request.data.get('phone')

        if not email and not phone:
            return api_response(
                'error', 'Email or phone is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        role_id = request.data.get('role_id')
        role = None
        if role_id:
            try:
                role = Role.objects.get(
                    pk=role_id, business=business
                )
            except Role.DoesNotExist:
                return api_response(
                    'error', 'Role not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

        # Check if already a member
        if email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            existing_user = User.objects.filter(
                email=email
            ).first()
            if existing_user:
                if BusinessMember.objects.filter(
                    business=business,
                    user=existing_user,
                    status='active'
                ).exists():
                    return api_response(
                        'error',
                        'This user is already a staff member',
                        http_status=status.HTTP_400_BAD_REQUEST
                    )

        # Cancel existing pending invitation
        StaffInvitation.objects.filter(
            business=business,
            email=email,
            status='pending'
        ).update(status='cancelled')

        invitation = StaffInvitation.objects.create(
            business=business,
            invited_by=request.user,
            role=role,
            email=email,
            phone=phone,
            name=request.data.get('name', ''),
            job_title=request.data.get('job_title', ''),
            token=generate_invitation_token(),
            message=request.data.get('message', ''),
            expires_at=timezone.now() + timedelta(days=7),
        )

        send_staff_invitation(invitation)

        return api_response(
            'success',
            f'Invitation sent to {email or phone}',
            data=StaffInvitationSerializer(invitation).data,
            http_status=status.HTTP_201_CREATED
        )


class AcceptInvitationView(APIView):
    """
    POST - Accept a staff invitation
    POST /api/v1/staff/invitations/accept/
    Body: { "token": "...", "user_id": 2 } (if already logged in)
    or body: { "token": "..." } with auth header
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return api_response(
                'error', 'Token is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invitation = StaffInvitation.objects.get(
                token=token
            )
        except StaffInvitation.DoesNotExist:
            return api_response(
                'error', 'Invalid invitation token',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if not invitation.is_valid():
            return api_response(
                'error',
                f'Invitation is {invitation.status}',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already a member
        if BusinessMember.objects.filter(
            business=invitation.business,
            user=request.user,
            status='active'
        ).exists():
            return api_response(
                'error',
                'You are already a member of this business',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Create membership
        member = BusinessMember.objects.create(
            business=invitation.business,
            user=request.user,
            role=invitation.role,
            invited_by=invitation.invited_by,
            job_title=invitation.job_title,
        )

        # Mark invitation as accepted
        invitation.status = 'accepted'
        invitation.accepted_by = request.user
        invitation.accepted_at = timezone.now()
        invitation.save()

        # Notify business owner
        try:
            from apps.notifications.utils import send_notification
            send_notification(
                user=invitation.invited_by,
                title='Staff Invitation Accepted ✅',
                message=(
                    f'{request.user.full_name} accepted '
                    f'your invitation to join '
                    f'{invitation.business.name}.'
                ),
                notification_type='system',
                data={'member_id': member.id}
            )
        except Exception as e:
            print(f"[STAFF] Accept notification error: {e}")

        return api_response(
            'success',
            f'You have joined {invitation.business.name}!',
            data=BusinessMemberSerializer(member).data
        )


class CreateStaffAccountView(APIView):
    """
    POST - Owner creates a staff account with temp password
    POST /api/v1/staff/businesses/<business_id>/create-account/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        email = request.data.get('email')
        phone = request.data.get('phone')
        full_name = request.data.get('full_name')

        if not email or not full_name:
            return api_response(
                'error',
                'email and full_name are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return api_response(
                'error',
                'A user with this email already exists. '
                'Use the invite flow instead.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        temp_password = generate_temp_password()

        # Create user
        user = User.objects.create_user(
            email=email,
            password=temp_password,
            full_name=full_name,
            phone=phone or '',
            is_active=True,
        )

        role_id = request.data.get('role_id')
        role = None
        if role_id:
            try:
                role = Role.objects.get(
                    pk=role_id, business=business
                )
            except Role.DoesNotExist:
                pass

        # Create membership
        member = BusinessMember.objects.create(
            business=business,
            user=user,
            role=role,
            invited_by=request.user,
            job_title=request.data.get('job_title', ''),
        )

        # Create staff account record
        StaffAccount.objects.create(
            business=business,
            user=user,
            created_by=request.user,
            must_change_password=True,
        )

        # Send credentials
        send_temp_password_notification(
            user, business, temp_password
        )

        return api_response(
            'success',
            f'Staff account created for {full_name}. '
            f'Credentials sent via email/SMS.',
            data=BusinessMemberSerializer(member).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Work Schedule ─────────────────────────────────────────

class WorkScheduleView(APIView):
    """
    GET/POST - Manage staff member's work schedule
    GET/POST /api/v1/staff/businesses/<business_id>/members/<pk>/schedule/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Staff member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        schedule = member.schedule.all()
        return api_response(
            'success', 'Schedule retrieved',
            data=WorkScheduleSerializer(
                schedule, many=True
            ).data
        )

    def post(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Staff member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        schedule_data = request.data.get('schedule', [])
        created = []
        for item in schedule_data:
            obj, _ = WorkSchedule.objects.update_or_create(
                member=member,
                day=item.get('day'),
                defaults={
                    'is_working': item.get('is_working', True),
                    'start_time': item.get('start_time'),
                    'end_time': item.get('end_time'),
                    'is_24_hours': item.get('is_24_hours', False),
                }
            )
            created.append(obj)

        return api_response(
            'success', 'Schedule updated',
            data=WorkScheduleSerializer(
                created, many=True
            ).data
        )


# ── Permission Check ──────────────────────────────────────

class CheckPermissionView(APIView):
    """
    GET - Check if current user has a permission in a business
    GET /api/v1/staff/check-permission/
        ?business_id=1&permission=view_bookings
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.marketplace.models import Business

        business_id = request.query_params.get('business_id')
        permission_code = request.query_params.get('permission')

        if not business_id or not permission_code:
            return api_response(
                'error',
                'business_id and permission are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        has_perm = check_permission(
            request.user, business, permission_code
        )

        return api_response(
            'success', 'Permission checked',
            data={
                'has_permission': has_perm,
                'permission': permission_code,
                'business_id': business_id,
                'is_owner': business.owner == request.user,
            }
        )


# ── My Businesses (staff member view) ────────────────────

class MyBusinessMembershipsView(APIView):
    """
    GET - List all businesses the current user is a member of
    GET /api/v1/staff/my-businesses/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = BusinessMember.objects.filter(
            user=request.user,
            status='active'
        ).select_related('business', 'role')

        results = []
        for m in memberships:
            results.append({
                'membership_id': m.id,
                'business_id': m.business.id,
                'business_name': m.business.name,
                'business_logo': (
                    request.build_absolute_uri(
                        m.business.logo.url
                    ) if m.business.logo else None
                ),
                'role': m.role.name if m.role else None,
                'job_title': m.job_title,
                'joined_at': m.joined_at,
                'permissions': BusinessMemberSerializer(
                    m
                ).data.get('permissions', []),
            })

        return api_response(
            'success', 'Business memberships retrieved',
            data={
                'count': len(results),
                'results': results
            }
        )


# ── Activity Log ──────────────────────────────────────────

class StaffActivityLogView(APIView):
    """
    GET - View staff activity log for a business (owner only)
    GET /api/v1/staff/businesses/<business_id>/activity/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        logs = StaffActivityLog.objects.filter(
            member__business=business
        )
        member_id = request.query_params.get('member_id')
        action = request.query_params.get('action')

        if member_id:
            logs = logs.filter(member__id=member_id)
        if action:
            logs = logs.filter(action=action)

        return api_response(
            'success', 'Activity logs retrieved',
            data={
                'count': logs.count(),
                'results': StaffActivityLogSerializer(
                    logs[:100], many=True
                ).data
            }
        )


# ── Invitations list ──────────────────────────────────────

class InvitationListView(APIView):
    """
    GET - List all invitations for a business
    GET /api/v1/staff/businesses/<business_id>/invitations/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        invitations = StaffInvitation.objects.filter(
            business=business
        )
        inv_status = request.query_params.get('status')
        if inv_status:
            invitations = invitations.filter(status=inv_status)

        return api_response(
            'success', 'Invitations retrieved',
            data={
                'count': invitations.count(),
                'results': StaffInvitationSerializer(
                    invitations, many=True
                ).data
            }
        )

    def delete(self, request, business_id):
        """Cancel a pending invitation."""
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        invitation_id = request.data.get('invitation_id')
        try:
            invitation = StaffInvitation.objects.get(
                pk=invitation_id,
                business=business,
                status='pending'
            )
            invitation.status = 'cancelled'
            invitation.save()
            return api_response(
                'success', 'Invitation cancelled'
            )
        except StaffInvitation.DoesNotExist:
            return api_response(
                'error', 'Invitation not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

# ── Department ────────────────────────────────────────────

class DepartmentListCreateView(APIView):
    """
    GET/POST - Manage departments for a business
    GET/POST /api/v1/staff/businesses/<business_id>/departments/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        departments = Department.objects.filter(
            business=business, is_active=True
        )
        return api_response(
            'success', 'Departments retrieved',
            data={
                'count': departments.count(),
                'results': DepartmentSerializer(
                    departments, many=True
                ).data
            }
        )

    def post(self, request, business_id):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        dept = Department.objects.create(
            business=business,
            name=request.data.get('name'),
            description=request.data.get('description', ''),
        )
        return api_response(
            'success', 'Department created',
            data=DepartmentSerializer(dept).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Shifts ────────────────────────────────────────────────

class StaffShiftView(APIView):
    """
    GET/POST - Manage shifts for a member
    GET/POST /api/v1/staff/businesses/<business_id>/members/<pk>/shifts/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        shifts = member.shifts.all()
        date = request.query_params.get('date')
        if date:
            shifts = shifts.filter(date=date)
        return api_response(
            'success', 'Shifts retrieved',
            data=StaffShiftSerializer(shifts, many=True).data
        )

    def post(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err
        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = StaffShiftSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(member=member)
            return api_response(
                'success', 'Shift created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Attendance ────────────────────────────────────────────

class AttendanceView(APIView):
    """
    GET  - View attendance records
    POST - Clock in
    PATCH - Clock out
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        attendance = member.attendance.all()
        return api_response(
            'success', 'Attendance retrieved',
            data=StaffAttendanceSerializer(
                attendance, many=True
            ).data
        )

    def post(self, request, business_id, pk):
        """Clock in."""
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id,
                user=request.user
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        from django.utils import timezone
        import datetime
        today = timezone.now().date()

        if member.attendance.filter(date=today).exists():
            return api_response(
                'error', 'Already clocked in today',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        attendance = StaffAttendance.objects.create(
            member=member,
            date=today,
            clock_in=timezone.now(),
            clock_in_lat=request.data.get('latitude'),
            clock_in_lng=request.data.get('longitude'),
            clock_in_device=request.data.get('device', ''),
        )

        # Check if late based on shift
        shift = member.shifts.filter(date=today).first()
        if shift:
            clock_in_time = timezone.now().time()
            if clock_in_time > shift.start_time:
                from datetime import datetime as dt
                late_mins = int(
                    (
                        dt.combine(today, clock_in_time)
                        - dt.combine(today, shift.start_time)
                    ).total_seconds() / 60
                )
                attendance.is_late = True
                attendance.late_minutes = late_mins
                attendance.save()

        return api_response(
            'success', 'Clocked in successfully',
            data=StaffAttendanceSerializer(attendance).data,
            http_status=status.HTTP_201_CREATED
        )

    def patch(self, request, business_id, pk):
        """Clock out."""
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id,
                user=request.user
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        from django.utils import timezone
        today = timezone.now().date()

        try:
            attendance = member.attendance.get(date=today)
        except StaffAttendance.DoesNotExist:
            return api_response(
                'error', 'No clock-in record found for today',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if attendance.clock_out:
            return api_response(
                'error', 'Already clocked out today',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        attendance.clock_out = timezone.now()
        attendance.clock_out_lat = request.data.get('latitude')
        attendance.clock_out_lng = request.data.get('longitude')

        # Calculate overtime
        shift = member.shifts.filter(date=today).first()
        if shift and attendance.clock_out:
            from datetime import datetime as dt
            clock_out_time = attendance.clock_out.time()
            if clock_out_time > shift.end_time:
                overtime_mins = int(
                    (
                        dt.combine(today, clock_out_time)
                        - dt.combine(today, shift.end_time)
                    ).total_seconds() / 60
                )
                attendance.overtime_minutes = overtime_mins

        attendance.save()

        return api_response(
            'success', 'Clocked out successfully',
            data=StaffAttendanceSerializer(attendance).data
        )


# ── Temporary Permissions ─────────────────────────────────

class TemporaryPermissionView(APIView):
    """
    GET/POST - Manage temporary permissions for a member
    GET/POST /api/v1/staff/businesses/<business_id>/members/<pk>/temp-permissions/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        perms = member.temporary_permissions.filter(
            is_active=True
        )
        return api_response(
            'success', 'Temporary permissions retrieved',
            data=TemporaryPermissionSerializer(
                perms, many=True
            ).data
        )

    def post(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        perm_id = request.data.get('permission_id')
        expires_at = request.data.get('expires_at')
        reason = request.data.get('reason', '')

        if not perm_id or not expires_at:
            return api_response(
                'error',
                'permission_id and expires_at are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            permission = Permission.objects.get(pk=perm_id)
        except Permission.DoesNotExist:
            return api_response(
                'error', 'Permission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        temp_perm = TemporaryPermission.objects.create(
            member=member,
            permission=permission,
            granted_by=request.user,
            reason=reason,
            expires_at=expires_at,
        )

        return api_response(
            'success', 'Temporary permission granted',
            data=TemporaryPermissionSerializer(temp_perm).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Staff Notes ───────────────────────────────────────────

class StaffNoteView(APIView):
    """
    GET/POST - Manager notes on a staff member
    GET/POST /api/v1/staff/businesses/<business_id>/members/<pk>/notes/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        notes = member.notes.all()
        return api_response(
            'success', 'Notes retrieved',
            data=StaffNoteSerializer(notes, many=True).data
        )

    def post(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        note = StaffNote.objects.create(
            member=member,
            written_by=request.user,
            note_type=request.data.get('note_type', 'general'),
            content=request.data.get('content', ''),
            is_private=request.data.get('is_private', True),
        )

        return api_response(
            'success', 'Note added',
            data=StaffNoteSerializer(note).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Leave Management ──────────────────────────────────────

class StaffLeaveListCreateView(APIView):
    """
    GET  - List leave requests
    POST - Request leave (staff member)
    GET/POST /api/v1/staff/businesses/<business_id>/leave/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Owner sees all, staff sees own
        if business.owner == request.user:
            leaves = StaffLeave.objects.filter(
                member__business=business
            )
        else:
            try:
                member = BusinessMember.objects.get(
                    business=business,
                    user=request.user
                )
                leaves = member.leave_requests.all()
            except BusinessMember.DoesNotExist:
                return api_response(
                    'error', 'Not authorized',
                    http_status=status.HTTP_403_FORBIDDEN
                )

        leave_status = request.query_params.get('status')
        if leave_status:
            leaves = leaves.filter(status=leave_status)

        return api_response(
            'success', 'Leave requests retrieved',
            data={
                'count': leaves.count(),
                'results': StaffLeaveSerializer(
                    leaves, many=True
                ).data
            }
        )

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
            member = BusinessMember.objects.get(
                business=business,
                user=request.user,
                status='active'
            )
        except (
            Business.DoesNotExist,
            BusinessMember.DoesNotExist
        ):
            return api_response(
                'error', 'Not authorized',
                http_status=status.HTTP_403_FORBIDDEN
            )

        leave = StaffLeave.objects.create(
            member=member,
            leave_type=request.data.get('leave_type'),
            start_date=request.data.get('start_date'),
            end_date=request.data.get('end_date'),
            reason=request.data.get('reason', ''),
        )

        # Notify business owner
        try:
            from apps.notifications.utils import send_notification
            send_notification(
                user=business.owner,
                title='Leave Request 📅',
                message=(
                    f'{request.user.full_name} requested '
                    f'{leave.leave_type} leave from '
                    f'{leave.start_date} to {leave.end_date}.'
                ),
                notification_type='system',
                data={'leave_id': leave.id}
            )
        except Exception as e:
            print(f"[STAFF] Leave notification error: {e}")

        return api_response(
            'success', 'Leave request submitted',
            data=StaffLeaveSerializer(leave).data,
            http_status=status.HTTP_201_CREATED
        )


class StaffLeaveReviewView(APIView):
    """
    PATCH - Owner approves or rejects leave request
    PATCH /api/v1/staff/businesses/<business_id>/leave/<pk>/review/
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            leave = StaffLeave.objects.get(
                pk=pk, member__business=business
            )
        except StaffLeave.DoesNotExist:
            return api_response(
                'error', 'Leave request not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get('action')
        if action not in ('approve', 'reject'):
            return api_response(
                'error', 'action must be approve or reject',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        leave.status = (
            'approved' if action == 'approve' else 'rejected'
        )
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        if action == 'reject':
            leave.rejection_reason = request.data.get(
                'reason', ''
            )
        leave.save()

        try:
            from apps.notifications.utils import send_notification
            send_notification(
                user=leave.member.user,
                title=(
                    'Leave Approved ✅'
                    if action == 'approve'
                    else 'Leave Rejected ❌'
                ),
                message=(
                    f'Your {leave.leave_type} leave request '
                    f'has been {leave.status}.'
                ),
                notification_type='system',
                data={'leave_id': leave.id}
            )
        except Exception as e:
            print(f"[STAFF] Leave review notification: {e}")

        return api_response(
            'success', f'Leave {action}d',
            data=StaffLeaveSerializer(leave).data
        )


# ── Staff PIN ─────────────────────────────────────────────

class StaffPINView(APIView):
    """
    POST - Set/update PIN for a member
    POST /api/v1/staff/businesses/<business_id>/members/<pk>/pin/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id, pk):
        from django.contrib.auth.hashers import make_password
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id,
                user=request.user
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        pin = request.data.get('pin', '').strip()
        if not pin or len(pin) != 4 or not pin.isdigit():
            return api_response(
                'error', 'PIN must be exactly 4 digits',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        staff_pin, _ = StaffPIN.objects.update_or_create(
            member=member,
            defaults={
                'pin_hash': make_password(pin),
                'pin_enabled': True,
                'failed_attempts': 0,
                'locked_until': None,
            }
        )

        return api_response(
            'success', 'PIN set successfully',
            data=StaffPINSerializer(staff_pin).data
        )


class VerifyPINView(APIView):
    """
    POST - Verify staff PIN for quick actions
    POST /api/v1/staff/businesses/<business_id>/members/<pk>/pin/verify/
    Body: { "pin": "1234" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id, pk):
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id,
                user=request.user
            )
            staff_pin = member.pin
        except (
            BusinessMember.DoesNotExist,
            StaffPIN.DoesNotExist
        ):
            return api_response(
                'error', 'PIN not set up',
                http_status=status.HTTP_404_NOT_FOUND
            )

        pin = request.data.get('pin', '').strip()
        is_valid, message = staff_pin.verify_pin(pin)

        if is_valid:
            return api_response(
                'success', 'PIN verified',
                data={'verified': True}
            )
        return api_response(
            'error', message,
            data={'verified': False},
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Device Management ─────────────────────────────────────

class StaffDeviceView(APIView):
    """
    GET  - List trusted devices for a member
    POST - Register a device
    PATCH - Trust/revoke a device (owner)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id,
                user=request.user
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        devices = member.devices.filter(is_active=True)
        return api_response(
            'success', 'Devices retrieved',
            data=StaffDeviceSerializer(devices, many=True).data
        )

    def post(self, request, business_id, pk):
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id,
                user=request.user
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        device = StaffDevice.objects.create(
            member=member,
            device_name=request.data.get('device_name', ''),
            browser=request.data.get('browser', ''),
            ip_address=request.META.get('REMOTE_ADDR'),
            device_fingerprint=request.data.get(
                'fingerprint', ''
            ),
            last_login=timezone.now(),
        )
        return api_response(
            'success', 'Device registered',
            data=StaffDeviceSerializer(device).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Impersonation ─────────────────────────────────────────

class ImpersonateStaffView(APIView):
    """
    POST - Owner starts impersonating a staff member
    POST /api/v1/staff/businesses/<business_id>/members/<pk>/impersonate/
    Returns a token scoped to the staff member's permissions.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id, pk):
        business, err = get_business_or_403(
            request, business_id
        )
        if err:
            return err

        try:
            member = BusinessMember.objects.get(
                pk=pk, business=business
            )
        except BusinessMember.DoesNotExist:
            return api_response(
                'error', 'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Set impersonation flag
        member.impersonated_by = request.user
        member.save()

        return api_response(
            'success',
            f'Now viewing as {member.user.full_name}. '
            f'Their permissions are shown below.',
            data={
                'impersonating': member.user.full_name,
                'member_id': member.id,
                'role': member.role.name if member.role else None,
                'permissions': BusinessMemberSerializer(
                    member
                ).data.get('permissions', []),
            }
        )

    def delete(self, request, business_id, pk):
        """Stop impersonating."""
        try:
            member = BusinessMember.objects.get(
                pk=pk, business__id=business_id
            )
            member.impersonated_by = None
            member.save()
        except BusinessMember.DoesNotExist:
            pass

        return api_response(
            'success', 'Stopped impersonating'
        )