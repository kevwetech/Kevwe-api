from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from django.utils import timezone
from .models import (
    KYCProfile, KYCDocument, KYCSelfie, KYCReviewLog,
    KYCConfiguration, KYCRequirement, KYCSession,
    KYCIdentity, KYCDuplicateIdentity, KYCWatchlist,
    KYCConsent, KYCWebhook, BusinessKYC,
    BusinessKYCDocument, KYCAddress, KYCMatch,
)
from .serializers import (
    KYCProfileSerializer, KYCDocumentSerializer,
    KYCSelfieSerializer, KYCReviewLogSerializer,
    KYCConfigurationSerializer, KYCRequirementSerializer,
    KYCSessionSerializer, KYCIdentitySerializer,
    KYCDuplicateIdentitySerializer, KYCWatchlistSerializer,
    KYCConsentSerializer, KYCWebhookSerializer,
    BusinessKYCSerializer, BusinessKYCDocumentSerializer,
    KYCAddressSerializer, KYCMatchSerializer,
)


# ─── Customer Endpoints ──────────────────────────────────


class InitiateKYCView(APIView):
    """
    POST - Start KYC process.
    Returns Sumsub SDK token for frontend Web SDK.
    POST /api/v1/kyc/initiate/
    Body: { "use_case": "booking", "consent": true }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .utils import initiate_kyc

        use_case = request.data.get('use_case', 'booking')
        consent = request.data.get('consent', False)

        if not consent:
            return api_response(
                'error',
                'You must consent to identity verification '
                'to proceed.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check retry limit
        from .models import KYCConfiguration
        config = KYCConfiguration.get_active()
        max_retries = (
            config.max_retry_count if config else 3
        )

        try:
            existing = KYCProfile.objects.get(
                user=request.user, use_case=use_case
            )
            if existing.retry_count >= max_retries:
                return api_response(
                    'error',
                    f'Maximum verification attempts '
                    f'({max_retries}) reached. '
                    f'Please contact support.',
                    http_status=status.HTTP_400_BAD_REQUEST
                )
        except KYCProfile.DoesNotExist:
            pass

        profile, token, session = initiate_kyc(
            request.user, use_case, request
        )

        if token is None and session is None:
            # Check if already approved
            if profile.status in ('approved', 'auto_approved'):
                return api_response(
                    'success',
                    'KYC already approved.',
                    data=KYCProfileSerializer(profile).data
                )
            # Retry limit hit
            config = KYCConfiguration.get_active()
            max_retries = (
                config.max_retry_count if config else 3
            )
            return api_response(
                'error',
                f'Maximum verification attempts '
                f'({max_retries}) reached. '
                f'Please contact support.',
                data={
                    'retry_count': profile.retry_count,
                    'max_retries': max_retries,
                    'status': profile.status,
                },
                http_status=status.HTTP_403_FORBIDDEN
            )

        return api_response(
            'success',
            'KYC initiated. Use the SDK token to '
            'complete verification.',
        )

class KYCProfileView(APIView):
    """
    GET - Get current user's KYC profile
    GET /api/v1/kyc/profile/?use_case=booking
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        use_case = request.query_params.get(
            'use_case', 'booking'
        )
        try:
            profile = KYCProfile.objects.get(
                user=request.user, use_case=use_case
            )
            return api_response(
                'success', 'KYC profile retrieved',
                data=KYCProfileSerializer(profile).data
            )
        except KYCProfile.DoesNotExist:
            return api_response(
                'success', 'No KYC profile found',
                data={
                    'status': 'not_started',
                    'is_verified': False,
                    'use_case': use_case,
                }
            )


class UploadKYCDocumentView(APIView):
    """
    POST - Upload ID document
    POST /api/v1/kyc/documents/upload/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .utils import (
            get_or_create_kyc_profile,
            register_document_identity
        )
        from .sumsub import upload_document

        use_case = request.data.get('use_case', 'booking')
        document_type = request.data.get('document_type')
        document_number = request.data.get(
            'document_number', ''
        )
        file = request.FILES.get('file')

        if not document_type or not file:
            return api_response(
                'error',
                'document_type and file are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        profile, _ = get_or_create_kyc_profile(
            request.user, use_case
        )

        if not profile.sumsub_applicant_id:
            return api_response(
                'error',
                'Please initiate KYC first at '
                '/api/v1/kyc/initiate/',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Upload to Sumsub
        sumsub_doc_id = upload_document(
            profile.sumsub_applicant_id,
            file, document_type
        )

        # Save document — update if exists
        doc, created = KYCDocument.objects.update_or_create(
            kyc_profile=profile,
            document_type=document_type,
            defaults={
                'document_number': document_number,
                'file': file,
                'sumsub_document_id': sumsub_doc_id or '',
                'status': 'pending',
                'verified': False,
            }
        )

        # Hash and register identity for duplicate detection
        if document_number:
            try:
                identity, is_duplicate = (
                    register_document_identity(
                        document_type, document_number,
                        request.user, profile
                    )
                )
                if is_duplicate:
                    return api_response(
                        'success',
                        'Document uploaded. '
                        'Note: This document is associated '
                        'with another account and will be '
                        'reviewed.',
                        data=KYCDocumentSerializer(doc).data,
                        http_status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                print(f"[KYC] Identity registration error: {e}")

        return api_response(
            'success',
            'Document uploaded successfully',
            data=KYCDocumentSerializer(doc).data,
            http_status=status.HTTP_201_CREATED
        )


class UploadKYCSelfieView(APIView):
    """
    POST - Upload selfie for face match
    POST /api/v1/kyc/selfie/upload/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .utils import get_or_create_kyc_profile
        from .sumsub import upload_selfie

        use_case = request.data.get('use_case', 'booking')
        file = request.FILES.get('file')
        device = request.data.get('device', '')

        if not file:
            return api_response(
                'error', 'Selfie file is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        profile, _ = get_or_create_kyc_profile(
            request.user, use_case
        )

        if not profile.sumsub_applicant_id:
            return api_response(
                'error',
                'Please initiate KYC first at '
                '/api/v1/kyc/initiate/',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        result = upload_selfie(
            profile.sumsub_applicant_id, file
        )

        selfie = KYCSelfie.objects.create(
            kyc_profile=profile,
            file=file,
            device=device,
            captured_at=timezone.now(),
            sumsub_selfie_id=(
                result.get('id', '') if result else ''
            ),
            liveness_score=result.get(
                'livenessScore'
            ) if result else None,
            face_match_score=result.get(
                'faceMatchScore'
            ) if result else None,
        )

        # Update session if active
        active_session = profile.sessions.filter(
            status='started'
        ).first()
        if active_session:
            active_session.status = 'selfie_uploaded'
            active_session.save()

        return api_response(
            'success',
            'Selfie uploaded. Verification in progress.',
            data=KYCSelfieSerializer(selfie).data,
            http_status=status.HTTP_201_CREATED
        )


class SubmitKYCAddressView(APIView):
    """
    POST - Submit address verification
    POST /api/v1/kyc/address/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .utils import get_or_create_kyc_profile

        use_case = request.data.get('use_case', 'booking')
        profile, _ = get_or_create_kyc_profile(
            request.user, use_case
        )

        proof_document = request.FILES.get('proof_document')

        address, created = KYCAddress.objects.update_or_create(
            kyc_profile=profile,
            defaults={
                'street': request.data.get('street', ''),
                'city': request.data.get('city', ''),
                'state': request.data.get('state', ''),
                'country': request.data.get('country', 'NG'),
                'postal_code': request.data.get(
                    'postal_code', ''
                ),
                'proof_document': proof_document,
                'status': 'pending',
            }
        )

        return api_response(
            'success',
            'Address submitted for verification',
            data=KYCAddressSerializer(address).data,
            http_status=status.HTTP_201_CREATED
        )


class KYCSessionListView(APIView):
    """
    GET - Get all KYC sessions for current user
    GET /api/v1/kyc/sessions/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        use_case = request.query_params.get(
            'use_case', 'booking'
        )
        try:
            profile = KYCProfile.objects.get(
                user=request.user, use_case=use_case
            )
            sessions = profile.sessions.all()
            return api_response(
                'success', 'Sessions retrieved',
                data={
                    'count': sessions.count(),
                    'results': KYCSessionSerializer(
                        sessions, many=True
                    ).data
                }
            )
        except KYCProfile.DoesNotExist:
            return api_response(
                'success', 'No KYC profile found',
                data={'count': 0, 'results': []}
            )


class SumsubWebhookView(APIView):
    """
    POST - Receive Sumsub webhook results
    POST /api/v1/kyc/webhook/sumsub/
    """
    permission_classes = []

    def post(self, request):
        import json
        from .sumsub import verify_webhook_signature
        from .utils import process_sumsub_webhook

        signature = request.headers.get(
            'X-Payload-Digest', ''
        )
        raw_body = request.body

        if not verify_webhook_signature(raw_body, signature):
            return api_response(
                'error', 'Invalid webhook signature',
                http_status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return api_response(
                'error', 'Invalid JSON payload',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        profile = process_sumsub_webhook(payload)

        return api_response(
            'success', 'Webhook processed',
            data={
                'applicant_id': payload.get('applicantId'),
                'profile_id': profile.id if profile else None,
            }
        )


# ─── Business KYC Endpoints ──────────────────────────────


class BusinessKYCView(APIView):
    """
    GET  - Get business KYC status
    POST - Initiate business KYC
    GET/POST /api/v1/kyc/business/<business_id>/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        try:
            kyc = BusinessKYC.objects.get(business=business)
            return api_response(
                'success', 'Business KYC retrieved',
                data=BusinessKYCSerializer(kyc).data
            )
        except BusinessKYC.DoesNotExist:
            return api_response(
                'success', 'Business KYC not started',
                data={
                    'status': 'not_started',
                    'is_verified': False,
                }
            )

    def post(self, request, business_id):
        from apps.marketplace.models import Business
        from .sumsub import create_company_applicant

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        kyc, created = BusinessKYC.objects.get_or_create(
            business=business,
            defaults={'submitted_by': request.user}
        )

        if not kyc.sumsub_company_id:
            company_id = create_company_applicant(business)
            if company_id:
                kyc.sumsub_company_id = company_id
                kyc.status = 'pending'
                kyc.save()

        return api_response(
            'success',
            'Business KYC initiated',
            data=BusinessKYCSerializer(kyc).data,
            http_status=(
                status.HTTP_201_CREATED if created
                else status.HTTP_200_OK
            )
        )


class BusinessKYCDocumentUploadView(APIView):
    """
    POST - Upload a business KYC document
    POST /api/v1/kyc/business/<business_id>/documents/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, business_id):
        from apps.marketplace.models import Business

        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user
            )
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        try:
            kyc = BusinessKYC.objects.get(business=business)
        except BusinessKYC.DoesNotExist:
            return api_response(
                'error',
                'Please initiate Business KYC first',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        document_type = request.data.get('document_type')
        file = request.FILES.get('file')
        document_number = request.data.get(
            'document_number', ''
        )

        if not document_type or not file:
            return api_response(
                'error',
                'document_type and file are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        doc, created = (
            BusinessKYCDocument.objects.update_or_create(
                business_kyc=kyc,
                document_type=document_type,
                defaults={
                    'file': file,
                    'document_number': document_number,
                    'status': 'pending',
                    'verified': False,
                }
            )
        )

        return api_response(
            'success',
            'Business document uploaded',
            data=BusinessKYCDocumentSerializer(doc).data,
            http_status=status.HTTP_201_CREATED
        )


# ─── Admin Endpoints ─────────────────────────────────────


class AdminKYCListView(APIView):
    """
    GET - List all KYC profiles (admin)
    GET /api/v1/kyc/admin/?status=pending&use_case=booking
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        profiles = KYCProfile.objects.all()
        kyc_status = request.query_params.get('status')
        use_case = request.query_params.get('use_case')
        search = request.query_params.get('search')

        if kyc_status:
            profiles = profiles.filter(status=kyc_status)
        if use_case:
            profiles = profiles.filter(use_case=use_case)
        if search:
            profiles = profiles.filter(
                user__email__icontains=search
            )

        return api_response(
            'success', 'KYC profiles retrieved',
            data={
                'count': profiles.count(),
                'summary': {
                    'pending': profiles.filter(
                        status='pending'
                    ).count(),
                    'approved': profiles.filter(
                        status__in=[
                            'approved', 'auto_approved'
                        ]
                    ).count(),
                    'rejected': profiles.filter(
                        status='rejected'
                    ).count(),
                    'not_started': profiles.filter(
                        status='not_started'
                    ).count(),
                },
                'results': KYCProfileSerializer(
                    profiles[:50], many=True
                ).data
            }
        )


class AdminKYCDetailView(APIView):
    """
    GET - Get full KYC profile detail (admin)
    GET /api/v1/kyc/admin/<pk>/
    """
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            profile = KYCProfile.objects.get(pk=pk)
        except KYCProfile.DoesNotExist:
            return api_response(
                'error', 'KYC profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        sessions = profile.sessions.all()
        logs = profile.review_logs.all()
        watchlist = profile.watchlist_checks.all()

        return api_response(
            'success', 'KYC profile retrieved',
            data={
                'profile': KYCProfileSerializer(
                    profile
                ).data,
                'sessions': KYCSessionSerializer(
                    sessions, many=True
                ).data,
                'watchlist': KYCWatchlistSerializer(
                    watchlist, many=True
                ).data,
                'review_logs': KYCReviewLogSerializer(
                    logs[:20], many=True
                ).data,
            }
        )


class AdminKYCReviewView(APIView):
    """
    PATCH - Manually approve or reject a KYC profile (admin)
    PATCH /api/v1/kyc/admin/<pk>/review/
    Body: { "action": "approve"|"reject", "notes": "..." }
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            profile = KYCProfile.objects.get(pk=pk)
        except KYCProfile.DoesNotExist:
            return api_response(
                'error', 'KYC profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get('action')
        notes = request.data.get('notes', '')
        internal_notes = request.data.get('internal_notes', '')

        if action not in ('approve', 'reject'):
            return api_response(
                'error', 'action must be approve or reject',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()

        if action == 'approve':
            profile.status = 'approved'
            profile.approved_at = now
            profile.verification_method = 'manual'
            log_action = 'manual_approved'
            notif_title = 'KYC Approved ✅'
            notif_msg = (
                'Your identity has been manually verified. '
                'You can now complete your booking.'
            )

        
        else:
            profile.status = 'rejected'
            profile.rejection_reason = notes
            log_action = 'manual_rejected'
            notif_title = 'KYC Rejected ❌'
            notif_msg = (
                f'Your KYC was rejected. Reason: {notes}. '
                f'Please resubmit with valid documents.'
            )

        if internal_notes:
            profile.internal_notes = internal_notes

        profile.reviewed_by = request.user
        profile.reviewed_at = now
        profile.save()

        # Trigger auto-verification for service providers
        if action == 'approve':
            try:
                from apps.services.verification import (
                    trigger_auto_verification_for_user
                )
                trigger_auto_verification_for_user(profile.user)
            except Exception as e:
                print(f"[KYC→VERIFY] Error: {e}")


        KYCReviewLog.objects.create(
            kyc_profile=profile,
            action=log_action,
            performed_by=request.user,
            is_system_action=False,
            notes=notes,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        try:
            from apps.notifications.utils import (
                send_notification
            )
            send_notification(
                user=profile.user,
                title=notif_title,
                message=notif_msg,
                notification_type='system',
                data={'kyc_profile_id': profile.id}
            )
        except Exception as e:
            print(f"KYC notification error: {e}")

        return api_response(
            'success', f'KYC {action}d successfully',
            data=KYCProfileSerializer(profile).data
        )


class AdminKYCLogsView(APIView):
    """
    GET - View KYC audit logs for a profile (admin)
    GET /api/v1/kyc/admin/<pk>/logs/
    """
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            profile = KYCProfile.objects.get(pk=pk)
        except KYCProfile.DoesNotExist:
            return api_response(
                'error', 'KYC profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        logs = profile.review_logs.all()
        return api_response(
            'success', 'KYC review logs retrieved',
            data={
                'profile': KYCProfileSerializer(
                    profile
                ).data,
                'count': logs.count(),
                'results': KYCReviewLogSerializer(
                    logs, many=True
                ).data
            }
        )


class AdminDuplicateIdentityListView(APIView):
    """
    GET - List all duplicate identity flags (admin)
    GET /api/v1/kyc/admin/duplicates/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        duplicates = KYCDuplicateIdentity.objects.all()
        dup_status = request.query_params.get('status')
        if dup_status:
            duplicates = duplicates.filter(status=dup_status)

        return api_response(
            'success', 'Duplicate identities retrieved',
            data={
                'count': duplicates.count(),
                'results': KYCDuplicateIdentitySerializer(
                    duplicates, many=True
                ).data
            }
        )

    def patch(self, request, pk=None):
        """Resolve a duplicate identity flag."""
        if not pk:
            return api_response(
                'error', 'pk required',
                http_status=status.HTTP_400_BAD_REQUEST
            )
        try:
            duplicate = KYCDuplicateIdentity.objects.get(
                pk=pk
            )
        except KYCDuplicateIdentity.DoesNotExist:
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        if new_status not in (
            'investigating', 'resolved', 'false_positive'
        ):
            return api_response(
                'error', 'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        duplicate.status = new_status
        if new_status == 'resolved':
            duplicate.resolved_by = request.user
            duplicate.resolved_at = timezone.now()
        duplicate.notes = request.data.get(
            'notes', duplicate.notes
        )
        duplicate.save()

        return api_response(
            'success', 'Duplicate identity updated',
            data=KYCDuplicateIdentitySerializer(
                duplicate
            ).data
        )


class AdminWatchlistListView(APIView):
    """
    GET - List watchlist screening results (admin)
    GET /api/v1/kyc/admin/watchlist/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        checks = KYCWatchlist.objects.all()
        matched = request.query_params.get('matched')
        wl_type = request.query_params.get('type')

        if matched:
            checks = checks.filter(
                matched=matched == 'true'
            )
        if wl_type:
            checks = checks.filter(watchlist_type=wl_type)

        return api_response(
            'success', 'Watchlist checks retrieved',
            data={
                'count': checks.count(),
                'matched_count': checks.filter(
                    matched=True
                ).count(),
                'results': KYCWatchlistSerializer(
                    checks[:50], many=True
                ).data
            }
        )


class AdminWebhookListView(APIView):
    """
    GET - List all KYC webhooks (admin, for debugging)
    GET /api/v1/kyc/admin/webhooks/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        webhooks = KYCWebhook.objects.all()
        processed = request.query_params.get('processed')

        if processed:
            webhooks = webhooks.filter(
                processed=processed == 'true'
            )

        return api_response(
            'success', 'KYC webhooks retrieved',
            data={
                'count': webhooks.count(),
                'unprocessed': webhooks.filter(
                    processed=False
                ).count(),
                'results': KYCWebhookSerializer(
                    webhooks[:50], many=True
                ).data
            }
        )


class AdminBusinessKYCListView(APIView):
    """
    GET - List all business KYC profiles (admin)
    GET /api/v1/kyc/admin/businesses/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        kycs = BusinessKYC.objects.all()
        kyc_status = request.query_params.get('status')

        if kyc_status:
            kycs = kycs.filter(status=kyc_status)

        return api_response(
            'success', 'Business KYC profiles retrieved',
            data={
                'count': kycs.count(),
                'results': BusinessKYCSerializer(
                    kycs, many=True
                ).data
            }
        )


class AdminBusinessKYCReviewView(APIView):
    """
    PATCH - Approve or reject a business KYC (admin)
    PATCH /api/v1/kyc/admin/businesses/<pk>/review/
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            kyc = BusinessKYC.objects.get(pk=pk)
        except BusinessKYC.DoesNotExist:
            return api_response(
                'error', 'Business KYC not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get('action')
        notes = request.data.get('notes', '')

        if action not in ('approve', 'reject'):
            return api_response(
                'error', 'action must be approve or reject',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()
        if action == 'approve':
            kyc.status = 'approved'
            kyc.approved_at = now
        else:
            kyc.status = 'rejected'
            kyc.rejection_reason = notes

        kyc.reviewed_by = request.user
        kyc.reviewed_at = now
        if notes:
            kyc.internal_notes = notes
        kyc.save()

        # Trigger auto-verification for business providers
        if action == 'approve':
            try:
                from apps.services.verification import (
                    trigger_auto_verification_for_user
                )
                trigger_auto_verification_for_user(
                    kyc.submitted_by
                )
            except Exception as e:
                print(f"[BIZ KYC→VERIFY] Error: {e}")

        try:
            from apps.notifications.utils import (
                send_notification
            )
            send_notification(
                user=kyc.submitted_by,
                title=(
                    'Business KYC Approved ✅'
                    if action == 'approve'
                    else 'Business KYC Rejected ❌'
                ),
                message=(
                    f'Business KYC for {kyc.business.name} '
                    f'has been {action}d.'
                ),
                notification_type='system',
                data={'business_kyc_id': kyc.id}
            )
        except Exception as e:
            print(f"[KYC] Notification error: {e}")

        return api_response(
            'success',
            f'Business KYC {action}d successfully',
            data=BusinessKYCSerializer(kyc).data
        )


class KYCConfigurationView(APIView):
    """
    GET  - Get KYC configuration (admin)
    PATCH - Update KYC configuration (admin)
    GET/PATCH /api/v1/kyc/admin/config/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        from .models import KYCConfiguration
        config = KYCConfiguration.get_active()
        if not config:
            return api_response(
                'error', 'No active KYC configuration found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success', 'KYC configuration retrieved',
            data=KYCConfigurationSerializer(config).data
        )
    def post(self, request):
        from .models import KYCConfiguration
        # Only one active config allowed
        if KYCConfiguration.objects.filter(
            is_active=True
        ).exists():
            return api_response(
                'error',
                'Active configuration already exists. '
                'Use PATCH to update it.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = KYCConfigurationSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'KYC configuration created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request):
        from .models import KYCConfiguration
        config = KYCConfiguration.get_active()
        if not config:
            config = KYCConfiguration.objects.create()

        serializer = KYCConfigurationSerializer(
            config, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'KYC configuration updated',
                data=serializer.data
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class KYCRequirementView(APIView):
    """
    GET  - List requirements per use case (admin)
    POST - Create/update requirements (admin)
    GET/POST /api/v1/kyc/admin/requirements/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        requirements = KYCRequirement.objects.filter(
            is_active=True
        )
        return api_response(
            'success', 'KYC requirements retrieved',
            data={
                'count': requirements.count(),
                'results': KYCRequirementSerializer(
                    requirements, many=True
                ).data
            }
        )

    def post(self, request):
        use_case = request.data.get('use_case')
        serializer = KYCRequirementSerializer(data=request.data)
        if serializer.is_valid():
            obj, created = (
                KYCRequirement.objects.update_or_create(
                    use_case=use_case,
                    defaults=serializer.validated_data
                )
            )
            return api_response(
                'success',
                'KYC requirement saved',
                data=KYCRequirementSerializer(obj).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class KYCDashboardView(APIView):
    """
    GET - Admin KYC overview dashboard
    GET /api/v1/kyc/admin/dashboard/
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        from datetime import timedelta
        now = timezone.now()
        today = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        this_week = now - timedelta(days=7)

        profiles = KYCProfile.objects.all()
        business_kycs = BusinessKYC.objects.all()
        duplicates = KYCDuplicateIdentity.objects.filter(
            status='open'
        )
        watchlist_matches = KYCWatchlist.objects.filter(
            matched=True,
            status='potential_match'
        )

        return api_response(
            'success', 'KYC dashboard retrieved',
            data={
                'personal_kyc': {
                    'total': profiles.count(),
                    'pending': profiles.filter(
                        status='pending'
                    ).count(),
                    'approved': profiles.filter(
                        status__in=[
                            'approved', 'auto_approved'
                        ]
                    ).count(),
                    'rejected': profiles.filter(
                        status='rejected'
                    ).count(),
                    'not_started': profiles.filter(
                        status='not_started'
                    ).count(),
                    'today': profiles.filter(
                        created_at__gte=today
                    ).count(),
                    'this_week': profiles.filter(
                        created_at__gte=this_week
                    ).count(),
                },
                'business_kyc': {
                    'total': business_kycs.count(),
                    'pending': business_kycs.filter(
                        status='pending'
                    ).count(),
                    'approved': business_kycs.filter(
                        status='approved'
                    ).count(),
                    'rejected': business_kycs.filter(
                        status='rejected'
                    ).count(),
                },
                'alerts': {
                    'duplicate_identities': (
                        duplicates.count()
                    ),
                    'watchlist_matches': (
                        watchlist_matches.count()
                    ),
                    'unprocessed_webhooks': (
                        KYCWebhook.objects.filter(
                            processed=False
                        ).count()
                    ),
                },
                'by_use_case': {
                    'booking': profiles.filter(
                        use_case='booking'
                    ).count(),
                    'vendor': profiles.filter(
                        use_case='vendor'
                    ).count(),
                    'driver': profiles.filter(
                        use_case='driver'
                    ).count(),
                },
            }
        )