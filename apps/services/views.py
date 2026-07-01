from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from django.utils import timezone
from .models import (
    ServiceCategory, Service, ServiceProvider,
    ServiceProviderAvailability, ProviderSkill,
    ProviderCertification, ProviderVehicle,
    ServiceRequest, ServiceRequestAttachment,
    ServiceRequestOffer, ServiceQuote, ServicePart,
    CompletionEvidence, ServiceRequestTracking,
    ServiceRating,
)
from .serializers import (
    ServiceCategorySerializer, ServiceSerializer,
    ServiceProviderSerializer,
    ServiceProviderAvailabilitySerializer,
    ProviderSkillSerializer,
    ProviderCertificationSerializer,
    ProviderVehicleSerializer,
    ServiceRequestSerializer,
    ServiceRequestAttachmentSerializer,
    ServiceRequestOfferSerializer,
    ServiceQuoteSerializer, ServicePartSerializer,
    CompletionEvidenceSerializer,
    ServiceRatingSerializer,
    CreateServiceRequestSerializer,
)


# ── Browse ───────────────────────────────────────────────

class ServiceCategoryListView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        categories = ServiceCategory.objects.filter(
            is_active=True
        )
        return api_response(
            'success', 'Categories retrieved',
            data={
                'count': categories.count(),
                'results': ServiceCategorySerializer(
                    categories, many=True
                ).data
            }
        )

    def post(self, request):
        serializer = ServiceCategorySerializer(
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
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ServiceListView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        services = Service.objects.filter(is_active=True)
        category_id = request.query_params.get('category_id')
        if category_id:
            services = services.filter(
                category__id=category_id
            )
        return api_response(
            'success', 'Services retrieved',
            data={
                'count': services.count(),
                'results': ServiceSerializer(
                    services, many=True
                ).data
            }
        )

    def post(self, request):
        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Service created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class NearbyProvidersView(APIView):
    """
    GET - Find nearby providers for a service
    GET /api/v1/services/nearby/?service_id=1&lat=5.89&lng=5.68
    """
    permission_classes = []

    def get(self, request):
        from .utils import find_nearby_providers

        service_id = request.query_params.get('service_id')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        emergency = (
            request.query_params.get('emergency') == 'true'
        )

        if not all([service_id, lat, lng]):
            return api_response(
                'error',
                'service_id, lat and lng are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = Service.objects.get(
                pk=service_id, is_active=True
            )
        except Service.DoesNotExist:
            return api_response(
                'error', 'Service not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        providers = find_nearby_providers(
            service, lat, lng, emergency=emergency
        )

        results = [
            {
                'id': item['provider'].id,
                'name': (
                    item['provider'].business_name
                    or item['provider'].user.full_name
                ),
                'rating': str(item['provider'].rating),
                'jobs_completed': (
                    item['provider'].total_jobs_completed
                ),
                'distance_km': item['distance_km'],
                'is_emergency_available': (
                    item['provider'].is_emergency_available
                ),
            }
            for item in providers
        ]

        return api_response(
            'success',
            f'Found {len(results)} providers nearby',
            data={
                'count': len(results),
                'results': results
            }
        )


# ── Provider profile management ──────────────────────────

class RegisterServiceProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.common.utils import generate_reference

        service_ids = request.data.get('service_ids', [])
        provider = ServiceProvider.objects.create(
            user=request.user,
            provider_type=request.data.get(
                'provider_type', 'individual'
            ),
            business_name=request.data.get('business_name', ''),
            bio=request.data.get('bio', ''),
            years_experience=request.data.get(
                'years_experience', 0
            ),
            operating_address=request.data.get(
                'operating_address', ''
            ),
            operating_radius_km=request.data.get(
                'operating_radius_km', 15.00
            ),
            is_emergency_available=request.data.get(
                'is_emergency_available', False
            ),
        )
        if service_ids:
            provider.services.set(service_ids)

        return api_response(
            'success',
            'Registered. Complete KYC to get verified.',
            data=ServiceProviderSerializer(provider).data,
            http_status=status.HTTP_201_CREATED
        )


class ServiceProviderProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_provider(self, request, pk=None):
        if pk:
            try:
                return ServiceProvider.objects.get(
                    pk=pk, user=request.user
                )
            except ServiceProvider.DoesNotExist:
                return None
        return ServiceProvider.objects.filter(
            user=request.user
        ).first()

    def get(self, request, pk=None):
        provider = self._get_provider(request, pk)
        if not provider:
            return api_response(
                'error', 'Profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success', 'Profile retrieved',
            data=ServiceProviderSerializer(provider).data
        )

    def patch(self, request, pk=None):
        provider = self._get_provider(request, pk)
        if not provider:
            return api_response(
                'error', 'Profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ServiceProviderSerializer(
            provider, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Profile updated',
                data=serializer.data
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class UpdateProviderLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        try:
            if pk:
                provider = ServiceProvider.objects.get(
                    pk=pk, user=request.user
                )
            else:
                provider = ServiceProvider.objects.filter(
                    user=request.user
                ).first()
                if not provider:
                    raise ServiceProvider.DoesNotExist
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        provider.current_lat = request.data.get('latitude')
        provider.current_lng = request.data.get('longitude')
        provider.last_location_update = timezone.now()
        provider.save()

        return api_response(
            'success', 'Location updated',
            data={
                'latitude': str(provider.current_lat),
                'longitude': str(provider.current_lng),
            }
        )


class ProviderAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk=None):
        try:
            provider = ServiceProvider.objects.get(
                pk=pk, user=request.user
            ) if pk else ServiceProvider.objects.filter(
                user=request.user
            ).first()
            if not provider:
                raise ServiceProvider.DoesNotExist
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if not provider.is_verified:
            return api_response(
                'error',
                'Complete KYC before going online',
                http_status=status.HTTP_403_FORBIDDEN
            )

        if 'is_available' in request.data:
            provider.is_available = request.data['is_available']
        if 'is_online' in request.data:
            provider.is_online = request.data['is_online']
        provider.save()

        return api_response(
            'success', 'Availability updated',
            data={
                'is_available': provider.is_available,
                'is_online': provider.is_online,
            }
        )


class ProviderAvailabilityScheduleView(APIView):
    """
    GET/POST - Manage weekly availability schedule
    GET/POST /api/v1/services/providers/<pk>/schedule/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(
                pk=pk, user=request.user
            )
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        schedule = provider.availability_schedule.all()
        return api_response(
            'success', 'Schedule retrieved',
            data=ServiceProviderAvailabilitySerializer(
                schedule, many=True
            ).data
        )

    def post(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(
                pk=pk, user=request.user
            )
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Bulk set schedule — accepts a list
        schedule_data = request.data.get('schedule', [])
        created = []
        for item in schedule_data:
            obj, _ = (
                ServiceProviderAvailability.objects.update_or_create(
                    provider=provider,
                    day=item.get('day'),
                    defaults={
                        'is_available': item.get(
                            'is_available', True
                        ),
                        'is_24_hours': item.get(
                            'is_24_hours', False
                        ),
                        'opening_time': item.get(
                            'opening_time'
                        ),
                        'closing_time': item.get(
                            'closing_time'
                        ),
                    }
                )
            )
            created.append(obj)

        return api_response(
            'success', 'Schedule updated',
            data=ServiceProviderAvailabilitySerializer(
                created, many=True
            ).data
        )


class ProviderSkillView(APIView):
    """POST - Add skills to provider profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(pk=pk)
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success', 'Skills retrieved',
            data=ProviderSkillSerializer(
                provider.skills.all(), many=True
            ).data
        )

    def post(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(
                pk=pk, user=request.user
            )
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        name = request.data.get('name')
        if not name:
            return api_response(
                'error', 'Skill name is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        skill, created = ProviderSkill.objects.get_or_create(
            provider=provider,
            name=name,
            defaults={
                'description': request.data.get(
                    'description', ''
                )
            }
        )
        return api_response(
            'success',
            'Skill added' if created else 'Skill already exists',
            data=ProviderSkillSerializer(skill).data,
            http_status=(
                status.HTTP_201_CREATED if created
                else status.HTTP_200_OK
            )
        )


class ProviderCertificationView(APIView):
    """Upload certifications"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(pk=pk)
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success', 'Certifications retrieved',
            data=ProviderCertificationSerializer(
                provider.certifications.all(), many=True
            ).data
        )

    def post(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(
                pk=pk, user=request.user
            )
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        file = request.FILES.get('document')
        if not file or not request.data.get('name'):
            return api_response(
                'error',
                'name and document are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        cert = ProviderCertification.objects.create(
            provider=provider,
            name=request.data.get('name'),
            issuing_body=request.data.get('issuing_body', ''),
            certificate_number=request.data.get(
                'certificate_number'
            ),
            document=file,
            issued_at=request.data.get('issued_at'),
            expires_at=request.data.get('expires_at'),
        )
        return api_response(
            'success', 'Certification uploaded',
            data=ProviderCertificationSerializer(cert).data,
            http_status=status.HTTP_201_CREATED
        )


class ProviderVehicleView(APIView):
    """Manage provider vehicles"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(pk=pk)
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success', 'Vehicles retrieved',
            data=ProviderVehicleSerializer(
                provider.vehicles.filter(is_active=True),
                many=True
            ).data
        )

    def post(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(
                pk=pk, user=request.user
            )
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProviderVehicleSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(provider=provider)
            return api_response(
                'success', 'Vehicle added',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ── Service Requests ─────────────────────────────────────

class ServiceRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests_qs = ServiceRequest.objects.filter(
            customer=request.user
        )
        req_status = request.query_params.get('status')
        if req_status:
            requests_qs = requests_qs.filter(status=req_status)

        return api_response(
            'success', 'Requests retrieved',
            data={
                'count': requests_qs.count(),
                'results': ServiceRequestSerializer(
                    requests_qs, many=True
                ).data
            }
        )

    def post(self, request):
        from apps.common.utils import generate_reference
        from .utils import find_nearby_providers, create_offers

        serializer = CreateServiceRequestSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            return api_response(
                'error', 'Invalid data',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            service = Service.objects.get(
                pk=data['service_id'], is_active=True
            )
        except Service.DoesNotExist:
            return api_response(
                'error', 'Service not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        sr = ServiceRequest.objects.create(
            reference=generate_reference('SRV'),
            customer=request.user,
            service=service,
            description=data['description'],
            urgency=data.get('urgency', 'medium'),
            budget=data.get('budget'),
            location_address=data['location_address'],
            location_lat=data['location_lat'],
            location_lng=data['location_lng'],
            scheduled_date=data.get('scheduled_date'),
            scheduled_time=data.get('scheduled_time'),
            pricing_type=service.default_pricing_type,
            inspection_fee=(
                service.default_inspection_fee
                if service.inspection_fee_required
                else 0
            ),
        )

        ServiceRequestTracking.objects.create(
            service_request=sr,
            status='pending',
            description='Service request created',
            updated_by=request.user,
        )

        # Dispatch to nearby providers
        matched_count = 0
        if service.dispatch_type == 'on_demand':
            emergency = data.get('urgency') == 'emergency'
            providers = find_nearby_providers(
                service,
                data['location_lat'],
                data['location_lng'],
                emergency=emergency
            )
            if providers:
                offers = create_offers(sr, providers)
                matched_count = len(offers)
                sr.status = 'offers_sent'
                sr.save()
            else:
                sr.status = 'no_provider_found'
                sr.save()

        return api_response(
            'success',
            f'Request created. {matched_count} provider(s) notified.',
            data=ServiceRequestSerializer(sr).data,
            http_status=status.HTTP_201_CREATED
        )


class ServiceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            sr = ServiceRequest.objects.get(pk=pk)
        except ServiceRequest.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        is_customer = sr.customer == request.user
        is_provider = ServiceProvider.objects.filter(
            user=request.user, requests=sr
        ).exists()

        if not is_customer and not is_provider:
            return api_response(
                'error', 'Not authorized',
                http_status=status.HTTP_403_FORBIDDEN
            )

        return api_response(
            'success', 'Request retrieved',
            data=ServiceRequestSerializer(sr).data
        )


class UploadAttachmentView(APIView):
    """POST - Upload photo/video to a service request"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            sr = ServiceRequest.objects.get(pk=pk)
        except ServiceRequest.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        file = request.FILES.get('file')
        if not file:
            return api_response(
                'error', 'File is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        attachment = ServiceRequestAttachment.objects.create(
            service_request=sr,
            file=file,
            file_type=request.data.get('file_type', 'image'),
            uploaded_by=request.user,
            caption=request.data.get('caption', ''),
        )

        return api_response(
            'success', 'Attachment uploaded',
            data=ServiceRequestAttachmentSerializer(
                attachment
            ).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Offer management ─────────────────────────────────────

class RespondToOfferView(APIView):
    """
    POST - Provider accepts or declines an offer
    POST /api/v1/services/offers/<pk>/respond/
    Body: { "action": "accept"|"decline", "reason": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            offer = ServiceRequestOffer.objects.get(pk=pk)
        except ServiceRequestOffer.DoesNotExist:
            return api_response(
                'error', 'Offer not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if offer.provider.user != request.user:
            return api_response(
                'error', 'Not authorized',
                http_status=status.HTTP_403_FORBIDDEN
            )

        if offer.status != 'pending':
            return api_response(
                'error',
                f'Offer already {offer.status}',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check if expired
        if (
            offer.expires_at
            and timezone.now() > offer.expires_at
        ):
            offer.status = 'expired'
            offer.save()
            return api_response(
                'error', 'Offer has expired',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        action = request.data.get('action')
        sr = offer.service_request
        now = timezone.now()

        if action == 'accept':
            # Check request still available
            if sr.status not in ('pending', 'offers_sent'):
                offer.status = 'cancelled'
                offer.responded_at = now
                offer.save()
                return api_response(
                    'error',
                    'Request already accepted by another provider',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            offer.status = 'accepted'
            offer.responded_at = now
            offer.save()

            # Assign provider to request
            sr.provider = offer.provider
            sr.status = 'accepted'
            sr.accepted_at = now
            sr.save()

            # Cancel all other pending offers
            ServiceRequestOffer.objects.filter(
                service_request=sr,
                status='pending'
            ).exclude(pk=pk).update(status='cancelled')

            ServiceRequestTracking.objects.create(
                service_request=sr,
                status='accepted',
                description=(
                    f'{offer.provider.business_name or offer.provider.user.full_name} '
                    f'accepted the request'
                ),
                updated_by=request.user,
            )

            from apps.notifications.utils import send_notification
            send_notification(
                user=sr.customer,
                title='Provider Found! 🔧',
                message=(
                    f'{offer.provider.business_name or offer.provider.user.full_name} '
                    f'accepted your {sr.service.name} request. '
                    f'They are on their way.'
                ),
                notification_type='system',
                data={'service_request_id': sr.id}
            )

        elif action == 'decline':
            offer.status = 'declined'
            offer.responded_at = now
            offer.decline_reason = request.data.get('reason', '')
            offer.save()

        else:
            return api_response(
                'error', 'action must be accept or decline',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        return api_response(
            'success', f'Offer {action}d',
            data=ServiceRequestOfferSerializer(offer).data
        )


# ── Quote management ─────────────────────────────────────

class SubmitQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from .utils import calculate_quote_total

        try:
            provider = ServiceProvider.objects.get(
                user=request.user, requests__id=pk
            )
            sr = ServiceRequest.objects.get(
                pk=pk, provider=provider
            )
        except (
            ServiceProvider.DoesNotExist,
            ServiceRequest.DoesNotExist
        ):
            return api_response(
                'error', 'Not found or not authorized',
                http_status=status.HTTP_404_NOT_FOUND
            )

        labour = request.data.get('labour_cost', 0)
        parts = request.data.get('parts_cost', 0)
        other = request.data.get('other_costs', 0)
        total = calculate_quote_total(labour, parts, other)

        # Mark previous quote as superseded if revising
        previous_quote = sr.quotes.filter(
            status='pending'
        ).first()
        revision_number = 1
        if previous_quote:
            previous_quote.status = 'superseded'
            previous_quote.save()
            revision_number = previous_quote.revision_number + 1

        quote = ServiceQuote.objects.create(
            service_request=sr,
            parent_quote=previous_quote,
            revision_number=revision_number,
            diagnosis=request.data.get('diagnosis', ''),
            labour_cost=labour,
            parts_cost=parts,
            other_costs=other,
            total=total,
            line_items=request.data.get('line_items', []),
            estimated_duration_hours=request.data.get(
                'estimated_duration_hours'
            ),
            revision_note=request.data.get('revision_note', ''),
        )

        # Create parts if provided
        parts_data = request.data.get('parts', [])
        for part in parts_data:
            ServicePart.objects.create(
                quote=quote,
                name=part.get('name'),
                quantity=part.get('quantity', 1),
                unit_price=part.get('unit_price', 0),
                supplier=part.get('supplier', ''),
                warranty_days=part.get('warranty_days', 0),
                part_number=part.get('part_number', ''),
                is_genuine=part.get('is_genuine', True),
            )

        sr.status = 'quote_sent'
        sr.save()

        ServiceRequestTracking.objects.create(
            service_request=sr,
            status='quote_sent',
            description=(
                f'Quote v{revision_number} sent: ₦{total}'
            ),
            updated_by=request.user,
        )

        from apps.notifications.utils import send_notification
        send_notification(
            user=sr.customer,
            title='Quote Ready 💰',
            message=(
                f'Quote v{revision_number}: ₦{total} for '
                f'{sr.service.name}. Tap to review.'
            ),
            notification_type='system',
            data={
                'service_request_id': sr.id,
                'quote_id': quote.id,
                'revision': revision_number,
            }
        )

        return api_response(
            'success', f'Quote v{revision_number} submitted',
            data=ServiceQuoteSerializer(quote).data,
            http_status=status.HTTP_201_CREATED
        )


class RespondToQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from .utils import calculate_commission_split

        try:
            quote = ServiceQuote.objects.get(
                pk=pk,
                service_request__customer=request.user
            )
        except ServiceQuote.DoesNotExist:
            return api_response(
                'error', 'Quote not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get('action')
        if action not in ('approve', 'reject'):
            return api_response(
                'error', 'action must be approve or reject',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        sr = quote.service_request
        now = timezone.now()

        if action == 'approve':
            quote.status = 'approved'
            quote.responded_at = now
            quote.save()

            commission, earnings = calculate_commission_split(
                quote.total, sr.service.commission_rate
            )

            sr.status = 'quote_approved'
            sr.final_total = quote.total
            sr.platform_commission = commission
            sr.provider_earnings = earnings
            sr.save()

            notif_title = 'Quote Approved ✅'
            notif_msg = (
                f'Quote approved. Begin the work on '
                f'{sr.service.name}.'
            )
        else:
            quote.status = 'rejected'
            quote.responded_at = now
            quote.rejection_reason = request.data.get(
                'reason', ''
            )
            quote.save()

            sr.status = 'quote_rejected'
            sr.save()

            notif_title = 'Quote Rejected'
            notif_msg = (
                f'Quote rejected. '
                f'Reason: {quote.rejection_reason or "None given"}.'
            )

        ServiceRequestTracking.objects.create(
            service_request=sr,
            status=sr.status,
            description=f'Customer {action}d the quote',
            updated_by=request.user,
        )

        if sr.provider:
            from apps.notifications.utils import send_notification
            send_notification(
                user=sr.provider.user,
                title=notif_title,
                message=notif_msg,
                notification_type='system',
                data={'service_request_id': sr.id}
            )

        return api_response(
            'success', f'Quote {action}d',
            data=ServiceQuoteSerializer(quote).data
        )


# ── Job execution ─────────────────────────────────────────

class StartJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(
                user=request.user
            )
            sr = ServiceRequest.objects.get(
                pk=pk, provider=provider
            )
        except (
            ServiceProvider.DoesNotExist,
            ServiceRequest.DoesNotExist
        ):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        allowed_statuses = ['quote_approved', 'accepted']
        if (
            sr.pricing_type == 'fixed_price'
            or sr.pricing_type in ('hourly', 'daily')
        ):
            allowed_statuses.append('accepted')

        if sr.status not in allowed_statuses:
            return api_response(
                'error',
                f'Cannot start job with status: {sr.status}',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        sr.status = 'in_progress'
        sr.started_at = timezone.now()
        sr.save()

        ServiceRequestTracking.objects.create(
            service_request=sr,
            status='in_progress',
            description='Provider started the job',
            updated_by=request.user,
        )

        return api_response(
            'success', 'Job started',
            data=ServiceRequestSerializer(sr).data
        )


class CompleteJobView(APIView):
    """
    POST - Provider marks job as complete and sends OTP
    to customer for confirmation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from .utils import generate_completion_otp

        try:
            provider = ServiceProvider.objects.get(
                user=request.user
            )
            sr = ServiceRequest.objects.get(
                pk=pk, provider=provider
            )
        except (
            ServiceProvider.DoesNotExist,
            ServiceRequest.DoesNotExist
        ):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if sr.status != 'in_progress':
            return api_response(
                'error',
                'Job must be in progress to complete',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Generate completion OTP
        otp = generate_completion_otp()
        evidence, _ = CompletionEvidence.objects.get_or_create(
            service_request=sr,
            defaults={
                'before_photos': request.data.get(
                    'before_photos', []
                ),
                'after_photos': request.data.get(
                    'after_photos', []
                ),
                'notes': request.data.get('notes', ''),
            }
        )
        evidence.completion_otp = otp
        evidence.save()

        sr.status = 'completed'
        sr.completed_at = timezone.now()
        sr.save()

        provider.total_jobs_completed += 1
        provider.save()

        ServiceRequestTracking.objects.create(
            service_request=sr,
            status='completed',
            description='Job completed — OTP sent to customer',
            updated_by=request.user,
        )

        from apps.notifications.utils import send_notification
        send_notification(
            user=sr.customer,
            title='Job Completed ✅',
            message=(
                f'Your {sr.service.name} job is done. '
                f'Confirmation code: {otp}. '
                f'Give this to your provider to confirm.'
            ),
            notification_type='system',
            data={
                'service_request_id': sr.id,
                'otp': otp,
            }
        )

        return api_response(
            'success',
            'Job marked complete. OTP sent to customer.',
            data=ServiceRequestSerializer(sr).data
        )


class ConfirmCompletionView(APIView):
    """
    POST - Customer confirms job with OTP
    POST /api/v1/services/requests/<pk>/confirm/
    Body: { "otp": "123456" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            sr = ServiceRequest.objects.get(
                pk=pk, customer=request.user
            )
        except ServiceRequest.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        try:
            evidence = sr.completion_evidence
        except CompletionEvidence.DoesNotExist:
            return api_response(
                'error', 'No completion evidence found',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        otp = request.data.get('otp', '').strip()
        if otp != evidence.completion_otp:
            return api_response(
                'error', 'Invalid OTP',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        evidence.otp_verified = True
        evidence.otp_verified_at = timezone.now()
        evidence.completion_otp = None
        evidence.save()

        return api_response(
            'success', 'Job confirmed successfully!',
            data=ServiceRequestSerializer(sr).data
        )


class CancelServiceRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            sr = ServiceRequest.objects.get(
                pk=pk, customer=request.user
            )
        except ServiceRequest.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if sr.status in ('completed', 'cancelled'):
            return api_response(
                'error',
                f'Cannot cancel a {sr.status} request',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        sr.status = 'cancelled'
        sr.cancelled_at = timezone.now()
        sr.cancellation_reason = request.data.get('reason', '')
        sr.save()

        # Cancel all pending offers
        sr.offers.filter(status='pending').update(
            status='cancelled'
        )

        ServiceRequestTracking.objects.create(
            service_request=sr,
            status='cancelled',
            description=(
                f'Cancelled: {sr.cancellation_reason}'
            ),
            updated_by=request.user,
        )

        if sr.provider:
            from apps.notifications.utils import send_notification
            send_notification(
                user=sr.provider.user,
                title='Request Cancelled',
                message=(
                    f'Customer cancelled the '
                    f'{sr.service.name} request.'
                ),
                notification_type='system',
                data={'service_request_id': sr.id}
            )

        return api_response(
            'success', 'Request cancelled',
            data=ServiceRequestSerializer(sr).data
        )


class RateServiceRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            sr = ServiceRequest.objects.get(
                pk=pk, customer=request.user
            )
        except ServiceRequest.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if sr.status != 'completed':
            return api_response(
                'error', 'Can only rate completed jobs',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        rating_value = request.data.get('rating')
        review = request.data.get('review', '')

        rating_obj, _ = ServiceRating.objects.update_or_create(
            service_request=sr,
            defaults={
                'customer_rating': rating_value,
                'customer_review': review,
            }
        )

        if sr.provider and rating_value:
            provider = sr.provider
            total_score = (
                float(provider.rating) * provider.total_ratings
                + int(rating_value)
            )
            provider.total_ratings += 1
            provider.rating = round(
                total_score / provider.total_ratings, 2
            )
            provider.save()

        return api_response(
            'success', 'Rating submitted',
            data=ServiceRatingSerializer(rating_obj).data
        )


# ── Provider's request list ───────────────────────────────

class ProviderRequestListView(APIView):
    """GET - List all requests assigned to a provider"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        try:
            if pk:
                provider = ServiceProvider.objects.get(
                    pk=pk, user=request.user
                )
            else:
                provider = ServiceProvider.objects.filter(
                    user=request.user
                ).first()
                if not provider:
                    raise ServiceProvider.DoesNotExist
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Provider profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        requests_qs = ServiceRequest.objects.filter(
            provider=provider
        )
        req_status = request.query_params.get('status')
        if req_status:
            requests_qs = requests_qs.filter(status=req_status)

        return api_response(
            'success', 'Requests retrieved',
            data={
                'count': requests_qs.count(),
                'results': ServiceRequestSerializer(
                    requests_qs, many=True
                ).data
            }
        )


class ProviderOfferListView(APIView):
    """GET - List all pending offers for a provider"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        try:
            if pk:
                provider = ServiceProvider.objects.get(
                    pk=pk, user=request.user
                )
            else:
                provider = ServiceProvider.objects.filter(
                    user=request.user
                ).first()
                if not provider:
                    raise ServiceProvider.DoesNotExist
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Provider profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        offers = provider.offers.filter(status='pending')
        return api_response(
            'success', 'Pending offers retrieved',
            data={
                'count': offers.count(),
                'results': ServiceRequestOfferSerializer(
                    offers, many=True
                ).data
            }
        )


# ── Admin ─────────────────────────────────────────────────

class AdminProviderListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        providers = ServiceProvider.objects.all()
        provider_status = request.query_params.get('status')
        if provider_status:
            providers = providers.filter(status=provider_status)

        return api_response(
            'success', 'Providers retrieved',
            data={
                'count': providers.count(),
                'results': ServiceProviderSerializer(
                    providers, many=True
                ).data
            }
        )


class AdminVerifyProviderView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            provider = ServiceProvider.objects.get(pk=pk)
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Provider not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        if new_status not in (
            'verified', 'rejected', 'suspended'
        ):
            return api_response(
                'error', 'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        provider.status = new_status
        provider.save()

        try:
            from apps.notifications.utils import send_notification
            send_notification(
                user=provider.user,
                title=(
                    'Provider Verified ✅'
                    if new_status == 'verified'
                    else f'Provider {new_status.capitalize()}'
                ),
                message=(
                    'You are now verified and can accept '
                    'service requests.'
                    if new_status == 'verified'
                    else f'Your provider account has been {new_status}.'
                ),
                notification_type='system',
                data={'provider_id': provider.id}
            )
        except Exception as e:
            print(f"[SERVICES] Notification error: {e}")

        return api_response(
            'success', f'Provider {new_status}',
            data=ServiceProviderSerializer(provider).data
        )


class AdminVerifyCertificationView(APIView):
    """PATCH - Admin verifies a provider certification"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            cert = ProviderCertification.objects.get(pk=pk)
        except ProviderCertification.DoesNotExist:
            return api_response(
                'error', 'Certification not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        if new_status not in ('verified', 'rejected'):
            return api_response(
                'error', 'status must be verified or rejected',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        cert.status = new_status
        cert.verified_by = request.user
        cert.verified_at = timezone.now()
        cert.save()

        return api_response(
            'success', f'Certification {new_status}',
            data=ProviderCertificationSerializer(cert).data
        )

class AdminCheckProviderVerificationView(APIView):
    """
    POST - Re-run auto-verification check for a provider (admin)
    POST /api/v1/services/admin/providers/<pk>/check-verify/
    """
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        from .verification import (
            check_provider_verification,
            auto_verify_provider
        )

        try:
            provider = ServiceProvider.objects.get(pk=pk)
        except ServiceProvider.DoesNotExist:
            return api_response(
                'error', 'Provider not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        is_eligible, reason = check_provider_verification(
            provider
        )

        if is_eligible:
            was_verified, msg = auto_verify_provider(provider)
            return api_response(
                'success' if was_verified else 'error',
                msg,
                data={
                    'provider_id': provider.id,
                    'status': provider.status,
                    'is_eligible': is_eligible,
                    'reason': reason,
                }
            )

        return api_response(
            'success',
            'Provider not yet eligible for verification',
            data={
                'provider_id': provider.id,
                'status': provider.status,
                'is_eligible': False,
                'reason': reason,
                'checklist': {
                    'kyc_approved': None,
                    'id_document_approved': None,
                    'selfie_approved': None,
                    'business_kyc_approved': (
                        provider.provider_type == 'business'
                    ),
                    'certification_required': (
                        provider.services.filter(
                            requires_certification=True
                        ).exists()
                    ),
                }
            }
        )