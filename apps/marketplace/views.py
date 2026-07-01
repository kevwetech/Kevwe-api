from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin, IsVendor
from apps.locations.models import City, State, Country
from apps.notifications.utils import send_notification
from .models import (
    Industry, BusinessCategory, Business,
    BusinessHours, BusinessImage, BusinessDocument,
    BusinessSettings, OrderSettings,
    BookingSettings, ServiceSettings,
)


# ── Industry ──────────────────────────────────────────────

class IndustryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        industries = Industry.objects.filter(
            status__in=['active', 'coming_soon']
        )
        from .serializers import IndustrySerializer
        return api_response(
            'success', 'Industries retrieved',
            data={
                'count': industries.count(),
                'results': IndustrySerializer(
                    industries, many=True,
                    context={'request': request}
                ).data
            }
        )

    def post(self, request):
        from .serializers import IndustrySerializer
        serializer = IndustrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Industry created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class IndustryDetailView(APIView):
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
        from .serializers import IndustrySerializer
        return api_response(
            'success', 'Industry retrieved',
            data=IndustrySerializer(
                industry, context={'request': request}
            ).data
        )

    def patch(self, request, pk):
        industry = self.get_object(pk)
        if not industry:
            return api_response(
                'error', 'Industry not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        from .serializers import IndustrySerializer
        serializer = IndustrySerializer(
            industry, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Industry updated',
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
        return api_response('success', 'Industry deactivated')


# ── Business Category ─────────────────────────────────────

class BusinessCategoryListView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        from .serializers import BusinessCategorySerializer
        industry_id = request.query_params.get('industry_id')
        categories = BusinessCategory.objects.filter(
            is_active=True
        )
        if industry_id:
            categories = categories.filter(
                industry__id=industry_id
            )
        return api_response(
            'success', 'Categories retrieved',
            data={
                'count': categories.count(),
                'results': BusinessCategorySerializer(
                    categories, many=True
                ).data
            }
        )

    def post(self, request):
        from .serializers import BusinessCategorySerializer
        serializer = BusinessCategorySerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Category created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Business ──────────────────────────────────────────────

class BusinessListView(APIView):
    permission_classes = []

    def get(self, request):
        from .serializers import BusinessSerializer
        businesses = Business.objects.filter(
            status='active', is_active=True
        )
        industry_id = request.query_params.get('industry')
        category_id = request.query_params.get('category')
        city_id = request.query_params.get('city')
        state_id = request.query_params.get('state')
        search = request.query_params.get('search')
        is_featured = request.query_params.get('featured')

        if industry_id:
            businesses = businesses.filter(
                industry__id=industry_id
            )
        if category_id:
            businesses = businesses.filter(
                category__id=category_id
            )
        if city_id:
            businesses = businesses.filter(city__id=city_id)
        if state_id:
            businesses = businesses.filter(
                state__id=state_id
            )
        if search:
            from django.db.models import Q
            businesses = businesses.filter(
                Q(name__icontains=search) |
                Q(tags__icontains=search)
            )
        if is_featured:
            businesses = businesses.filter(is_featured=True)

        return api_response(
            'success', 'Businesses retrieved',
            data={
                'count': businesses.count(),
                'results': BusinessSerializer(
                    businesses, many=True,
                    context={'request': request}
                ).data
            }
        )


class BusinessDetailView(APIView):
    permission_classes = []

    def get(self, request, pk):
        from .serializers import BusinessSerializer
        try:
            business = Business.objects.get(
                pk=pk, status='active', is_active=True
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success', 'Business retrieved',
            data=BusinessSerializer(
                business, context={'request': request}
            ).data
        )


class RegisterBusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import (
            CreateBusinessSerializer, BusinessSerializer
        )
        serializer = CreateBusinessSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            return api_response(
                'error', 'Registration failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

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

        category = None
        if data.get('category_id'):
            category = BusinessCategory.objects.filter(
                pk=data['category_id'],
                industry=industry
            ).first()

        city = City.objects.filter(
            pk=data.get('city_id')
        ).first()
        state = State.objects.filter(
            pk=data.get('state_id')
        ).first()
        country = Country.objects.filter(
            pk=data.get('country_id')
        ).first()

        business = Business.objects.create(
            owner=request.user,
            industry=industry,
            category=category,
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
            tags=data.get('tags', []),
            status='pending',
        )

        # Create default BusinessSettings
        BusinessSettings.objects.create(business=business)

        # Create industry-specific settings based on
        # interaction type
        interaction = industry.default_interaction_type
        if interaction == 'orders':
            OrderSettings.objects.create(business=business)
        elif interaction == 'bookings':
            BookingSettings.objects.create(business=business)
        elif interaction == 'services':
            ServiceSettings.objects.create(business=business)

        # Update user role to vendor
        request.user.role = 'vendor'
        request.user.save()

        # Notify admins
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for admin in User.objects.filter(role='admin'):
            send_notification(
                user=admin,
                title='New Business Registration',
                message=(
                    f'{business.name} ({industry.name}) '
                    f'registered and awaiting approval.'
                ),
                notification_type='system',
                data={'business_id': business.id}
            )

        return api_response(
            'success',
            'Business registered! Awaiting admin approval.',
            data=BusinessSerializer(
                business, context={'request': request}
            ).data,
            http_status=status.HTTP_201_CREATED
        )


class MyBusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import BusinessSerializer
        businesses = Business.objects.filter(
            owner=request.user
        )
        return api_response(
            'success', 'Your businesses retrieved',
            data={
                'count': businesses.count(),
                'results': BusinessSerializer(
                    businesses, many=True,
                    context={'request': request}
                ).data
            }
        )

    def patch(self, request, pk):
        from .serializers import BusinessSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
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
                'success', 'Business updated',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Business Settings ─────────────────────────────────────

class BusinessSettingsView(APIView):
    """
    GET/PATCH - Common settings for a business
    GET/PATCH /api/v1/marketplace/businesses/<pk>/settings/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .serializers import BusinessSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = BusinessSettings.objects.get_or_create(
            business=business
        )
        return api_response(
            'success', 'Settings retrieved',
            data=BusinessSettingsSerializer(settings_obj).data
        )

    def patch(self, request, pk):
        from .serializers import BusinessSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = BusinessSettings.objects.get_or_create(
            business=business
        )
        serializer = BusinessSettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Settings updated',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class OrderSettingsView(APIView):
    """
    GET/PATCH - Order settings (delivery, pickup, fees)
    GET/PATCH /api/v1/marketplace/businesses/<pk>/order-settings/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .serializers import OrderSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = OrderSettings.objects.get_or_create(
            business=business
        )
        return api_response(
            'success', 'Order settings retrieved',
            data=OrderSettingsSerializer(settings_obj).data
        )

    def patch(self, request, pk):
        from .serializers import OrderSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = OrderSettings.objects.get_or_create(
            business=business
        )
        serializer = OrderSettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Order settings updated',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BookingSettingsView(APIView):
    """
    GET/PATCH - Booking settings (check-in/out, cancellation)
    GET/PATCH /api/v1/marketplace/businesses/<pk>/booking-settings/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .serializers import BookingSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = BookingSettings.objects.get_or_create(
            business=business
        )
        return api_response(
            'success', 'Booking settings retrieved',
            data=BookingSettingsSerializer(settings_obj).data
        )

    def patch(self, request, pk):
        from .serializers import BookingSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = BookingSettings.objects.get_or_create(
            business=business
        )
        serializer = BookingSettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Booking settings updated',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ServiceSettingsView(APIView):
    """
    GET/PATCH - Service settings (inspection fee, emergency, radius)
    GET/PATCH /api/v1/marketplace/businesses/<pk>/service-settings/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .serializers import ServiceSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = ServiceSettings.objects.get_or_create(
            business=business
        )
        return api_response(
            'success', 'Service settings retrieved',
            data=ServiceSettingsSerializer(settings_obj).data
        )

    def patch(self, request, pk):
        from .serializers import ServiceSettingsSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        settings_obj, _ = ServiceSettings.objects.get_or_create(
            business=business
        )
        serializer = ServiceSettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Service settings updated',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Business Hours ────────────────────────────────────────

class BusinessHoursView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .serializers import BusinessHoursSerializer
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        hours = BusinessHours.objects.filter(business=business)
        return api_response(
            'success', 'Business hours retrieved',
            data=BusinessHoursSerializer(hours, many=True).data
        )

    def post(self, request, pk):
        from .serializers import BusinessHoursSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
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
                    'is_24_hours': hour.get(
                        'is_24_hours', False
                    ),
                    'opening_time': hour.get('opening_time'),
                    'closing_time': hour.get('closing_time'),
                }
            )
            created.append(BusinessHoursSerializer(obj).data)
        return api_response(
            'success', 'Business hours updated',
            data=created
        )


# ── Business Images ───────────────────────────────────────

class BusinessImageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        from .serializers import BusinessImageSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
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
            'success', 'Image uploaded',
            data=BusinessImageSerializer(
                business_image, context={'request': request}
            ).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Business Documents ────────────────────────────────────

class BusinessDocumentView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        from .serializers import BusinessDocumentSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        documents = BusinessDocument.objects.filter(
            business=business
        )
        return api_response(
            'success', 'Documents retrieved',
            data=BusinessDocumentSerializer(
                documents, many=True,
                context={'request': request}
            ).data
        )

    def post(self, request, pk):
        from .serializers import BusinessDocumentSerializer
        try:
            business = Business.objects.get(
                pk=pk, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessDocumentSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(business=business)
            return api_response(
                'success', 'Document uploaded',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Upload failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Nearby Businesses ─────────────────────────────────────

class NearbyBusinessesView(APIView):
    permission_classes = []

    def get(self, request):
        from .serializers import BusinessSerializer
        import math

        latitude = request.query_params.get('lat')
        longitude = request.query_params.get('lng')
        radius_km = float(
            request.query_params.get('radius_km', 5)
        )
        industry_id = request.query_params.get('industry_id')
        category_id = request.query_params.get('category_id')

        if not latitude or not longitude:
            return api_response(
                'error', 'lat and lng are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            lat1, lng1, lat2, lng2 = map(
                math.radians,
                [float(lat1), float(lng1),
                 float(lat2), float(lng2)]
            )
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = (
                math.sin(dlat/2)**2
                + math.cos(lat1) * math.cos(lat2)
                * math.sin(dlng/2)**2
            )
            return R * 2 * math.asin(math.sqrt(a))

        businesses = Business.objects.filter(
            status='active', is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        if industry_id:
            businesses = businesses.filter(
                industry__id=industry_id
            )
        if category_id:
            businesses = businesses.filter(
                category__id=category_id
            )

        nearby = []
        for biz in businesses:
            distance = haversine(
                latitude, longitude,
                biz.latitude, biz.longitude
            )
            if distance <= radius_km:
                nearby.append({
                    'business': biz,
                    'distance_km': round(distance, 2)
                })

        nearby.sort(key=lambda x: x['distance_km'])

        results = []
        for item in nearby:
            data = BusinessSerializer(
                item['business'],
                context={'request': request}
            ).data
            data['distance_km'] = item['distance_km']
            results.append(data)

        return api_response(
            'success',
            f'Found {len(results)} nearby businesses',
            data={'count': len(results), 'results': results}
        )


# ── Admin Views ───────────────────────────────────────────

class AdminBusinessListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from .serializers import BusinessSerializer
        businesses = Business.objects.all()
        biz_status = request.query_params.get('status')
        industry_id = request.query_params.get('industry')
        if biz_status:
            businesses = businesses.filter(status=biz_status)
        if industry_id:
            businesses = businesses.filter(
                industry__id=industry_id
            )
        return api_response(
            'success', 'All businesses retrieved',
            data={
                'count': businesses.count(),
                'pending': businesses.filter(
                    status='pending'
                ).count(),
                'active': businesses.filter(
                    status='active'
                ).count(),
                'suspended': businesses.filter(
                    status='suspended'
                ).count(),
                'results': BusinessSerializer(
                    businesses, many=True,
                    context={'request': request}
                ).data
            }
        )


class AdminBusinessApproveView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        from .serializers import BusinessSerializer
        try:
            business = Business.objects.get(pk=pk)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        rejection_reason = request.data.get(
            'rejection_reason', ''
        )

        if new_status not in [
            'active', 'rejected', 'suspended', 'closed'
        ]:
            return api_response(
                'error', 'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        business.status = new_status
        if new_status == 'active':
            business.approved_at = timezone.now()
            business.approved_by = request.user
            business.is_verified = True
        if rejection_reason:
            business.rejection_reason = rejection_reason
        business.save()

        messages = {
            'active': (
                f'Congratulations! {business.name} '
                f'has been approved!'
            ),
            'rejected': (
                f'{business.name} was rejected. '
                f'Reason: {rejection_reason}'
            ),
            'suspended': (
                f'{business.name} has been suspended.'
            ),
        }

        send_notification(
            user=business.owner,
            title=f'Business {new_status.capitalize()}',
            message=messages.get(
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
            'success', f'Business {new_status}',
            data=BusinessSerializer(
                business, context={'request': request}
            ).data
        )


class AdminVerifyBusinessDocumentView(APIView):
    """
    PATCH - Admin approves or rejects a business document
    PATCH /api/v1/marketplace/documents/<pk>/verify/
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        from .serializers import BusinessDocumentSerializer
        try:
            doc = BusinessDocument.objects.get(pk=pk)
        except BusinessDocument.DoesNotExist:
            return api_response(
                'error', 'Document not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        if new_status not in ('approved', 'rejected'):
            return api_response(
                'error', 'status must be approved or rejected',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        doc.status = new_status
        doc.notes = request.data.get('notes', '')
        doc.verified_by = request.user
        doc.verified_at = timezone.now()
        doc.save()

        return api_response(
            'success', f'Document {new_status}',
            data=BusinessDocumentSerializer(doc).data
        )