from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from datetime import timedelta
import secrets
from apps.common.views import api_response
from apps.common.permissions import IsAdmin, IsVendor
from apps.locations.models import City, State, Country
from apps.notifications.utils import send_notification
from .models import (
    Industry, Business, BusinessHours,
    BusinessImage, BusinessDocument,
    Permission, BusinessRole, BusinessStaff,
)
from .serializers import (
    IndustrySerializer, BusinessSerializer,
    CreateBusinessSerializer, BusinessHoursSerializer,
    BusinessImageSerializer, BusinessDocumentSerializer,
    PermissionSerializer, BusinessRoleSerializer,
    BusinessStaffSerializer, InviteStaffSerializer,
)


# ─── Industry Views ──────────────────────────────

class IndustryListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        industries = Industry.objects.filter(
            status__in=['active', 'coming_soon']
        )
        serializer = IndustrySerializer(
            industries, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Industries retrieved successfully',
            data={
                'count': industries.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = IndustrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Industry created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class IndustryDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return Industry.objects.get(pk=pk)
        except Industry.DoesNotExist:
            return None

    def get(self, request, pk):
        industry = self.get_object(pk)
        if not industry:
            return api_response(
                'error', 'Industry not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = IndustrySerializer(
            industry, context={'request': request}
        )
        return api_response(
            'success',
            'Industry retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        industry = self.get_object(pk)
        if not industry:
            return api_response(
                'error', 'Industry not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = IndustrySerializer(
            industry, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Industry updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        industry = self.get_object(pk)
        if not industry:
            return api_response(
                'error', 'Industry not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        industry.status = 'inactive'
        industry.save()
        return api_response(
            'success', 'Industry deleted successfully'
        )


# ─── Business Views ──────────────────────────────

class BusinessListView(APIView):
    permission_classes = []

    def get(self, request):
        businesses = Business.objects.filter(
            status='active', is_active=True
        )
        industry_id  = request.query_params.get('industry')
        city_id      = request.query_params.get('city')
        state_id     = request.query_params.get('state')
        search       = request.query_params.get('search')
        is_featured  = request.query_params.get('featured')
        is_open      = request.query_params.get('open')
        delivery     = request.query_params.get('delivery')

        if industry_id:
            businesses = businesses.filter(industry__id=industry_id)
        if city_id:
            businesses = businesses.filter(city__id=city_id)
        if state_id:
            businesses = businesses.filter(state__id=state_id)
        if search:
            businesses = (
                businesses.filter(name__icontains=search) |
                businesses.filter(tags__icontains=search)
            )
        if is_featured:
            businesses = businesses.filter(is_featured=True)
        if is_open:
            businesses = businesses.filter(is_open_now=True)
        if delivery:
            businesses = businesses.filter(delivery_available=True)

        serializer = BusinessSerializer(
            businesses, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Businesses retrieved successfully',
            data={
                'count': businesses.count(),
                'results': serializer.data
            }
        )


class BusinessDetailView(APIView):
    permission_classes = []

    def get(self, request, pk):
        try:
            business = Business.objects.get(
                pk=pk, status='active', is_active=True
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessSerializer(
            business, context={'request': request}
        )
        return api_response(
            'success',
            'Business retrieved successfully',
            data=serializer.data
        )


class RegisterBusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateBusinessSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            if Business.objects.filter(slug=data['slug']).exists():
                return api_response(
                    'error', 'Business slug already taken',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            try:
                industry = Industry.objects.get(
                    pk=data['industry_id'], status='active'
                )
            except Industry.DoesNotExist:
                return api_response(
                    'error', 'Industry not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            city    = City.objects.filter(pk=data.get('city_id')).first()
            state   = State.objects.filter(pk=data.get('state_id')).first()
            country = Country.objects.filter(pk=data.get('country_id')).first()

            business = Business.objects.create(
                owner=request.user,
                industry=industry,
                name=data['name'],
                slug=data['slug'],
                description=data.get('description', ''),
                tagline=data.get('tagline', ''),
                email=data.get('email', ''),
                phone=data['phone'],
                whatsapp=data.get('whatsapp', ''),
                address=data['address'],
                city=city,
                state=state,
                country=country,
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                delivery_available=data.get('delivery_available', True),
                pickup_available=data.get('pickup_available', True),
                min_order_amount=data.get('min_order_amount', 0),
                delivery_fee=data.get('delivery_fee', 0),
                delivery_time_minutes=data.get('delivery_time_minutes', 30),
                delivery_radius_km=data.get('delivery_radius_km', 5.00),
                tags=data.get('tags', []),
                status='pending',
            )

            # Update user role to vendor
            request.user.role = 'vendor'
            request.user.save()

            # Create owner role for this business
            owner_role, _ = BusinessRole.objects.get_or_create(
                business=business,
                name='Owner',
                defaults={
                    'description': 'Business owner with full access',
                    'is_default': True,
                }
            )
            # Give owner all permissions
            all_perms = Permission.objects.filter(is_active=True)
            owner_role.permissions.set(all_perms)

            # Add owner as staff
            BusinessStaff.objects.create(
                business=business,
                user=request.user,
                role=owner_role,
                status='active',
                invitation_status='accepted',
                joined_at=timezone.now(),
            )

            # Notify admins
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(role='admin')
            for admin in admins:
                send_notification(
                    user=admin,
                    title='New Business Registration',
                    message=f'{business.name} ({industry.name}) registered and awaiting approval.',
                    notification_type='system',
                    data={
                        'business_id': business.id,
                        'business_name': business.name,
                    }
                )

            return api_response(
                'success',
                'Business registered successfully! Awaiting admin approval.',
                data=BusinessSerializer(
                    business, context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error', 'Registration failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class MyBusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        businesses = Business.objects.filter(owner=request.user)
        serializer = BusinessSerializer(
            businesses, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Your businesses retrieved successfully',
            data={
                'count': businesses.count(),
                'results': serializer.data
            }
        )

    def patch(self, request, pk):
        try:
            business = Business.objects.get(pk=pk, owner=request.user)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessSerializer(
            business, data=request.data,
            partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Business updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BusinessHoursView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        hours = BusinessHours.objects.filter(business=business)
        serializer = BusinessHoursSerializer(hours, many=True)
        return api_response(
            'success',
            'Business hours retrieved successfully',
            data=serializer.data
        )

    def post(self, request, pk):
        try:
            business = Business.objects.get(pk=pk, owner=request.user)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        hours_data = request.data.get('hours', [])
        created = []
        for hour in hours_data:
            obj, _ = BusinessHours.objects.update_or_create(
                business=business,
                day=hour['day'],
                defaults={
                    'is_open': hour.get('is_open', True),
                    'opening_time': hour.get('opening_time'),
                    'closing_time': hour.get('closing_time'),
                }
            )
            created.append(BusinessHoursSerializer(obj).data)
        return api_response(
            'success',
            'Business hours updated successfully',
            data=created
        )


class BusinessImageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            business = Business.objects.get(pk=pk, owner=request.user)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        image = request.FILES.get('image')
        if not image:
            return api_response(
                'error', 'No image provided',
                http_status=status.HTTP_400_BAD_REQUEST
            )
        business_image = BusinessImage.objects.create(
            business=business,
            image=image,
            caption=request.data.get('caption', ''),
            is_primary=request.data.get('is_primary', False),
        )
        return api_response(
            'success', 'Image uploaded successfully',
            data=BusinessImageSerializer(
                business_image, context={'request': request}
            ).data,
            http_status=status.HTTP_201_CREATED
        )


class BusinessDocumentView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        try:
            business = Business.objects.get(pk=pk, owner=request.user)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        documents = BusinessDocument.objects.filter(business=business)
        serializer = BusinessDocumentSerializer(
            documents, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Documents retrieved successfully',
            data=serializer.data
        )

    def post(self, request, pk):
        try:
            business = Business.objects.get(pk=pk, owner=request.user)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(business=business)
            return api_response(
                'success', 'Document uploaded successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Upload failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ─── Permission Views ─────────────────────────────

class PermissionListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        perms = Permission.objects.filter(is_active=True)
        category = request.query_params.get('category')
        if category:
            perms = perms.filter(category=category)
        serializer = PermissionSerializer(perms, many=True)
        return api_response(
            'success',
            'Permissions retrieved successfully',
            data={
                'count': perms.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = PermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Permission created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PermissionDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Permission.objects.get(pk=pk)
        except Permission.DoesNotExist:
            return None

    def patch(self, request, pk):
        perm = self.get_object(pk)
        if not perm:
            return api_response(
                'error', 'Permission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = PermissionSerializer(
            perm, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Permission updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        perm = self.get_object(pk)
        if not perm:
            return api_response(
                'error', 'Permission not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        perm.is_active = False
        perm.save()
        return api_response(
            'success', 'Permission deleted successfully'
        )


# ─── Business Role Views ──────────────────────────

class BusinessRoleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        roles = BusinessRole.objects.filter(
            business=business,
            is_active=True
        )
        serializer = BusinessRoleSerializer(roles, many=True)
        return api_response(
            'success',
            'Roles retrieved successfully',
            data={
                'count': roles.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessRoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(business=business)
            return api_response(
                'success', 'Role created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BusinessRoleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, business_pk):
        try:
            return BusinessRole.objects.get(
                pk=pk, business__id=business_pk
            )
        except BusinessRole.DoesNotExist:
            return None

    def get(self, request, pk, role_id):
        role = self.get_object(role_id, pk)
        if not role:
            return api_response(
                'error', 'Role not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessRoleSerializer(role)
        return api_response(
            'success', 'Role retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk, role_id):
        role = self.get_object(role_id, pk)
        if not role:
            return api_response(
                'error', 'Role not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessRoleSerializer(
            role, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Role updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, role_id):
        role = self.get_object(role_id, pk)
        if not role:
            return api_response(
                'error', 'Role not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        role.is_active = False
        role.save()
        return api_response(
            'success', 'Role deleted successfully'
        )


# ─── Staff Views ──────────────────────────────────

class BusinessStaffListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Only owner or staff with can_manage_staff
        is_owner = business.owner == request.user
        is_manager = BusinessStaff.objects.filter(
            business=business,
            user=request.user,
            status='active'
        ).filter(
            role__permissions__codename='can_manage_staff'
        ).exists()

        if not is_owner and not is_manager:
            return api_response(
                'error',
                'You do not have permission to view staff',
                http_status=status.HTTP_403_FORBIDDEN
            )

        staff = BusinessStaff.objects.filter(business=business)
        serializer = BusinessStaffSerializer(
            staff, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Staff retrieved successfully',
            data={
                'count': staff.count(),
                'active': staff.filter(status='active').count(),
                'results': serializer.data
            }
        )


class InviteStaffView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        is_owner = business.owner == request.user
        is_manager = BusinessStaff.objects.filter(
            business=business,
            user=request.user,
            status='active'
        ).filter(
            role__permissions__codename='can_manage_staff'
        ).exists()

        if not is_owner and not is_manager:
            return api_response(
                'error',
                'You do not have permission to invite staff',
                http_status=status.HTTP_403_FORBIDDEN
            )

        serializer = InviteStaffSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            email = data['email']
            role = data['role_id']

            # Validate role belongs to this business
            if role.business and role.business != business:
                return api_response(
                    'error',
                    'Role does not belong to this business',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(email=email).first()

            if not user:
                return api_response(
                    'error',
                    f'No account found with {email}. Ask them to register first.',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            if BusinessStaff.objects.filter(
                business=business, user=user
            ).exists():
                return api_response(
                    'error',
                    'This user is already a staff member',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            token = secrets.token_urlsafe(32)

            staff = BusinessStaff.objects.create(
                business=business,
                user=user,
                role=role,
                invitation_token=token,
                invitation_status='pending',
                invited_by=request.user,
                invitation_expires_at=(
                    timezone.now() + timedelta(days=7)
                ),
                notes=data.get('notes', ''),
            )

            # Notify user
            from apps.notifications.utils import send_notification
            send_notification(
                user=user,
                title='Staff Invitation 🎉',
                message=f'You have been invited to join {business.name} as {role.name}. Token: {token}',
                notification_type='system',
                data={
                    'business_id': business.id,
                    'business_name': business.name,
                    'token': token,
                    'role': role.name,
                }
            )

            return api_response(
                'success',
                f'Invitation sent to {email}',
                data=BusinessStaffSerializer(
                    staff, context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error', 'Invitation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AcceptStaffInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return api_response(
                'error', 'Token is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            staff = BusinessStaff.objects.get(
                invitation_token=token,
                invitation_status='pending'
            )
        except BusinessStaff.DoesNotExist:
            return api_response(
                'error', 'Invalid or expired invitation',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (staff.invitation_expires_at and
                timezone.now() > staff.invitation_expires_at):
            staff.invitation_status = 'expired'
            staff.save()
            return api_response(
                'error', 'Invitation has expired',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if staff.user != request.user:
            return api_response(
                'error',
                'This invitation was sent to a different user',
                http_status=status.HTTP_403_FORBIDDEN
            )

        staff.invitation_status = 'accepted'
        staff.status = 'active'
        staff.joined_at = timezone.now()
        staff.save()

        from apps.notifications.utils import send_notification
        send_notification(
            user=staff.business.owner,
            title='Staff Member Joined! 🎉',
            message=f'{staff.user.full_name} accepted the invitation to join {staff.business.name} as {staff.role.name if staff.role else "Staff"}.',
            notification_type='system'
        )

        return api_response(
            'success',
            f'Welcome to {staff.business.name}! 🎉',
            data=BusinessStaffSerializer(
                staff, context={'request': request}
            ).data
        )


class BusinessStaffDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, staff_id):
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if business.owner != request.user:
            return api_response(
                'error',
                'Only the business owner can update staff',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            staff = BusinessStaff.objects.get(
                pk=staff_id, business=business
            )
        except BusinessStaff.DoesNotExist:
            return api_response(
                'error', 'Staff member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = BusinessStaffSerializer(
            staff, data=request.data,
            partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Staff member updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, staff_id):
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if business.owner != request.user:
            return api_response(
                'error',
                'Only the business owner can remove staff',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            staff = BusinessStaff.objects.get(
                pk=staff_id, business=business
            )
        except BusinessStaff.DoesNotExist:
            return api_response(
                'error', 'Staff member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check not removing owner role
        if staff.role and staff.role.name.lower() == 'owner':
            return api_response(
                'error',
                'Cannot remove the business owner',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        staff.status = 'inactive'
        staff.save()

        from apps.notifications.utils import send_notification
        send_notification(
            user=staff.user,
            title='Removed from Business',
            message=f'You have been removed from {business.name}.',
            notification_type='system'
        )

        return api_response(
            'success', 'Staff member removed successfully'
        )


class MyStaffProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profiles = BusinessStaff.objects.filter(
            user=request.user, status='active'
        )
        serializer = BusinessStaffSerializer(
            profiles, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Your staff profiles retrieved successfully',
            data={
                'count': profiles.count(),
                'results': serializer.data
            }
        )


# ─── Nearby Businesses ────────────────────────────

class NearbyBusinessesView(APIView):
    permission_classes = []

    def post(self, request):
        latitude    = request.data.get('latitude')
        longitude   = request.data.get('longitude')
        radius_km   = float(request.data.get('radius_km', 5))
        industry_id = request.data.get('industry_id')

        if not latitude or not longitude:
            return api_response(
                'error',
                'Latitude and longitude are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        import math

        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            lat1, lng1, lat2, lng2 = map(
                math.radians,
                [float(lat1), float(lng1),
                 float(lat2), float(lng2)]
            )
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = (math.sin(dlat/2)**2 +
                 math.cos(lat1) * math.cos(lat2) *
                 math.sin(dlng/2)**2)
            return R * 2 * math.asin(math.sqrt(a))

        businesses = Business.objects.filter(
            status='active', is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        if industry_id:
            businesses = businesses.filter(industry__id=industry_id)

        nearby = []
        for business in businesses:
            distance = haversine(
                latitude, longitude,
                business.latitude, business.longitude
            )
            if distance <= radius_km:
                nearby.append({
                    'business': business,
                    'distance_km': round(distance, 2)
                })

        nearby.sort(key=lambda x: x['distance_km'])

        results = []
        for item in nearby:
            data = BusinessSerializer(
                item['business'], context={'request': request}
            ).data
            data['distance_km'] = item['distance_km']
            results.append(data)

        return api_response(
            'success',
            f'Found {len(results)} nearby businesses',
            data={
                'count': len(results),
                'results': results
            }
        )


# ─── Admin Views ──────────────────────────────────

class AdminBusinessListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        businesses = Business.objects.all()
        business_status = request.query_params.get('status')
        industry_id     = request.query_params.get('industry')
        if business_status:
            businesses = businesses.filter(status=business_status)
        if industry_id:
            businesses = businesses.filter(industry__id=industry_id)

        serializer = BusinessSerializer(
            businesses, many=True, context={'request': request}
        )
        return api_response(
            'success', 'All businesses retrieved',
            data={
                'count':     businesses.count(),
                'pending':   businesses.filter(status='pending').count(),
                'active':    businesses.filter(status='active').count(),
                'suspended': businesses.filter(status='suspended').count(),
                'results':   serializer.data
            }
        )


class AdminBusinessApproveView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status       = request.data.get('status')
        rejection_reason = request.data.get('rejection_reason', '')

        if new_status not in ['active', 'rejected', 'suspended', 'closed']:
            return api_response(
                'error', 'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        business.status = new_status
        if new_status == 'active':
            business.approved_at = timezone.now()
            business.approved_by = request.user
        if rejection_reason:
            business.rejection_reason = rejection_reason
        business.save()

        messages_map = {
            'active':    f'Congratulations! {business.name} has been approved!',
            'rejected':  f'{business.name} was rejected. Reason: {rejection_reason}',
            'suspended': f'{business.name} has been suspended.',
        }

        from apps.notifications.utils import send_notification
        send_notification(
            user=business.owner,
            title=f'Business {new_status.capitalize()}',
            message=messages_map.get(
                new_status,
                f'Business status updated to {new_status}'
            ),
            notification_type='system',
            data={
                'business_id': business.id,
                'status': new_status,
            }
        )

        return api_response(
            'success',
            f'Business {new_status} successfully',
            data=BusinessSerializer(
                business, context={'request': request}
            ).data
        )