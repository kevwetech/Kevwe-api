from django.utils import timezone


def get_or_create_kyc_profile(user, use_case='booking'):
    """Get or create a KYC profile for a user."""
    from .models import KYCProfile
    profile, created = KYCProfile.objects.get_or_create(
        user=user,
        use_case=use_case,
    )
    return profile, created


def record_consent(kyc_profile, ip_address=None,
                   user_agent=None, version='v1'):
    """Record user's KYC consent."""
    from .models import KYCConsent
    consent, created = KYCConsent.objects.get_or_create(
        kyc_profile=kyc_profile,
        defaults={
            'accepted': True,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'consent_version': version,
            'accepted_at': timezone.now(),
            'consent_text': (
                'I consent to identity verification '
                'of my personal information.'
            ),
        }
    )
    if not created and not consent.accepted:
        consent.accepted = True
        consent.accepted_at = timezone.now()
        consent.ip_address = ip_address
        consent.save()
    return consent


def start_kyc_session(kyc_profile, request=None):
    """Create a new KYC session for this attempt."""
    from .models import KYCSession
    ip = None
    ua = None
    if request:
        ip = request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')

    session = KYCSession.objects.create(
        kyc_profile=kyc_profile,
        ip_address=ip,
        user_agent=ua,
        status='started',
    )
    return session


def initiate_kyc(user, use_case='booking', request=None):
    """
    Create Sumsub applicant, start session, record consent.
    Returns (profile, access_token, session).
    """
    from .models import KYCProfile, KYCReviewLog, KYCConfiguration
    from .sumsub import create_applicant, get_access_token

    config = KYCConfiguration.get_active()
    max_retries = config.max_retry_count if config else 3

    profile, _ = get_or_create_kyc_profile(user, use_case)
    profile.refresh_from_db()

    # Check retry limit — but don't block if already approved
    if profile.status in ('approved', 'auto_approved'):
        # Already verified — return existing token if session active
        active_session = profile.sessions.filter(
            status__in=['started', 'documents_uploaded',
                       'selfie_uploaded', 'submitted']
        ).order_by('-started_at').first()
        token = (
            active_session.sumsub_sdk_token
            if active_session else None
        )
        return profile, token, active_session

    if profile.retry_count >= max_retries:
        return profile, None, None


    # Record consent
    ip = request.META.get('REMOTE_ADDR') if request else None
    ua = request.META.get(
        'HTTP_USER_AGENT', ''
    ) if request else None
    record_consent(profile, ip_address=ip, user_agent=ua)

    # Create Sumsub applicant if not already created
    if not profile.sumsub_applicant_id:
        applicant_id = create_applicant(user, use_case)
        if applicant_id:
            profile.sumsub_applicant_id = applicant_id
            profile.status = 'pending'
            profile.submitted_at = timezone.now()
            profile.retry_count += 1
            profile.save()
            profile.refresh_from_db()
    
            KYCReviewLog.objects.create(
                kyc_profile=profile,
                action='submitted',
                is_system_action=True,
                ip_address=ip,
                user_agent=ua,
                notes='KYC initiated — Sumsub applicant created',
                metadata={'applicant_id': applicant_id}
            )
    else:
        # Retry — increment count
        profile.retry_count += 1
        profile.status = 'pending'
        profile.save()

        KYCReviewLog.objects.create(
            kyc_profile=profile,
            action='resubmitted',
            is_system_action=True,
            ip_address=ip,
            user_agent=ua,
            notes=f'KYC retry #{profile.retry_count}',
        )

    # Reuse active session if one exists
    active_session = profile.sessions.filter(
        status__in=[
            'started',
            'documents_uploaded',
            'selfie_uploaded',
            'submitted'
        ]
    ).order_by('-started_at').first()

    if active_session and active_session.sumsub_sdk_token:
        print(
            f"[KYC] Reusing existing session "
            f"{active_session.id} for {user.email}"
        )
        return profile, active_session.sumsub_sdk_token, active_session

    # No active session — create a new one
    session = start_kyc_session(profile, request)

    # Get SDK access token for frontend
    token = get_access_token(
        profile.sumsub_applicant_id,
        user.id,
        use_case
    )

    if token:
        session.sumsub_sdk_token = token
        session.save()

    return profile, token, session

def check_kyc_required(bookable_item, user):
    """
    Check if KYC is required and whether user has passed it.
    Returns (is_required, is_verified, profile).
    """
    from .models import KYCProfile

    if not getattr(bookable_item, 'requires_kyc', False):
        return False, True, None

    try:
        profile = KYCProfile.objects.get(
            user=user, use_case='booking'
        )
        return True, profile.is_verified, profile
    except KYCProfile.DoesNotExist:
        return True, False, None


def register_document_identity(
    document_type, document_number, user, kyc_profile
):
    """
    Hash and register a document number.
    Detect duplicates and fire fraud alert if found.
    Returns (identity, is_duplicate).
    """
    from .models import KYCIdentity, KYCDuplicateIdentity, KYCReviewLog

    identity, is_duplicate = KYCIdentity.check_and_register(
        document_type, document_number, user
    )

    if is_duplicate:
        # Create duplicate record
        duplicate, created = (
            KYCDuplicateIdentity.objects.get_or_create(
                identity=identity,
                defaults={'confidence': 100.0}
            )
        )
        duplicate.users.add(user)
        duplicate.save()

        # Fire fraud alert
        try:
            from apps.fraud.utils import create_alert
            alert = create_alert(
                alert_type='account',
                title='Duplicate Identity Detected',
                description=(
                    f'Document {document_type} '
                    f'({identity.document_number_masked}) '
                    f'used by {identity.users.count()} accounts'
                ),
                risk_score=70,
                triggered_rules=['duplicate_identity'],
                user=user,
                metadata={
                    'document_type': document_type,
                    'document_hash': identity.document_hash,
                    'accounts_count': identity.users.count(),
                }
            )
            if not duplicate.fraud_alert:
                duplicate.fraud_alert = alert
                duplicate.save()
        except Exception as e:
            print(f"[KYC] Fraud alert error: {e}")

        KYCReviewLog.objects.create(
            kyc_profile=kyc_profile,
            action='duplicate_detected',
            is_system_action=True,
            notes=(
                f'Document {document_type} already '
                f'registered to another account'
            ),
            metadata={
                'document_hash': identity.document_hash,
                'accounts': list(
                    identity.users.values_list('id', flat=True)
                )
            }
        )

    return identity, is_duplicate


def run_watchlist_check(kyc_profile):
    """
    Run PEP/sanctions/AML watchlist check via Sumsub.
    Creates KYCWatchlist records for any matches.
    """
    from .models import KYCWatchlist, KYCReviewLog
    from .sumsub import check_watchlist

    if not kyc_profile.sumsub_applicant_id:
        return []

    result = check_watchlist(kyc_profile.sumsub_applicant_id)
    items = result.get('items', []) if result else []
    created_checks = []

    if not items:
        # Record clear result
        check = KYCWatchlist.objects.create(
            kyc_profile=kyc_profile,
            watchlist_type='sanction',
            status='clear',
            matched=False,
            source='sumsub',
            match_details=result or {}
        )
        created_checks.append(check)
    else:
        for item in items:
            check = KYCWatchlist.objects.create(
                kyc_profile=kyc_profile,
                watchlist_type=item.get('type', 'sanction'),
                status='potential_match',
                matched=True,
                confidence=item.get('score', 0),
                source=item.get('source', 'sumsub'),
                match_details=item
            )
            created_checks.append(check)

            # Flag in review log
            KYCReviewLog.objects.create(
                kyc_profile=kyc_profile,
                action='watchlist_flagged',
                is_system_action=True,
                notes=(
                    f'Watchlist match: {item.get("type")} '
                    f'from {item.get("source")}'
                ),
                metadata=item
            )

            # Fraud alert for watchlist match
            try:
                from apps.fraud.utils import create_alert
                create_alert(
                    alert_type='account',
                    title=(
                        f'KYC Watchlist Match: '
                        f'{item.get("type", "").upper()}'
                    ),
                    description=(
                        f'User matched on '
                        f'{item.get("source")} watchlist. '
                        f'Confidence: {item.get("score")}%'
                    ),
                    risk_score=80,
                    triggered_rules=['watchlist_match'],
                    user=kyc_profile.user,
                    metadata=item
                )
            except Exception as e:
                print(f"[KYC] Watchlist fraud alert error: {e}")

    return created_checks


def process_sumsub_webhook(payload):
    """
    Process incoming Sumsub webhook.
    Updates KYC profile, fires fraud alerts if needed.
    """
    from .models import (
        KYCProfile, KYCReviewLog, KYCWebhook,
        KYCConfiguration
    )
    from .sumsub import get_applicant_data

    applicant_id = payload.get('applicantId')
    review_status = payload.get('reviewStatus')
    review_result = payload.get('reviewResult', {})
    review_answer = review_result.get('reviewAnswer')

    # Always store the raw webhook
    webhook = KYCWebhook.objects.create(
        source='sumsub',
        event_type=payload.get('type', 'review.completed'),
        applicant_id=applicant_id or '',
        payload=payload,
        signature='',
    )

    try:
        profile = KYCProfile.objects.get(
            sumsub_applicant_id=applicant_id
        )
    except KYCProfile.DoesNotExist:
        print(
            f"[KYC] No profile for applicant {applicant_id}"
        )
        webhook.processing_error = 'Profile not found'
        webhook.save()
        return None

    webhook.kyc_profile = profile
    profile.sumsub_review_result = review_result
    profile.last_webhook = payload

    config = KYCConfiguration.get_active()
    auto_threshold = (
        float(config.auto_approve_threshold)
        if config else 90.0
    )
    manual_threshold = (
        float(config.manual_review_threshold)
        if config else 65.0
    )

    # Extract confidence score
    confidence = review_result.get('score')
    if confidence:
        profile.confidence_score = confidence

    if review_answer == 'GREEN':
        profile.status = 'auto_approved'
        profile.approved_at = timezone.now()
        action = 'auto_approved'

        # Pull verified identity fields from Sumsub
        try:
            data = get_applicant_data(applicant_id)
            if data:
                info = data.get('info', {})
                profile.verified_first_name = info.get(
                    'firstNameEn', ''
                )
                profile.verified_last_name = info.get(
                    'lastNameEn', ''
                )
                profile.verified_dob = info.get('dob')
                profile.verified_gender = info.get('gender')
                profile.verified_nationality = info.get(
                    'nationality'
                )
            
        except Exception as e:
            print(f"[KYC] Extract identity error: {e}")

    elif review_answer == 'RED':
        profile.status = 'rejected'
        profile.rejection_reason = str(
            review_result.get('rejectLabels', [])
        )
        profile.rejection_labels = review_result.get(
            'rejectLabels', []
        )
        action = 'auto_rejected'

        # Fraud alert for rejection
        try:
            from apps.fraud.utils import create_alert, log_action
            alert = create_alert(
                alert_type='account',
                title='KYC Verification Failed',
                description=(
                    f'KYC rejected for '
                    f'{profile.user.email}. '
                    f'Labels: {profile.rejection_labels}'
                ),
                risk_score=30,
                triggered_rules=['kyc_rejected'],
                user=profile.user,
                metadata={
                    'kyc_profile_id': profile.id,
                    'rejection_labels': profile.rejection_labels,
                }
            )
        except Exception as e:
            print(f"[KYC] Rejection fraud alert error: {e}")

    else:
        profile.status = 'pending'
        profile.processing_started_at = timezone.now()
        action = 'webhook_received'

    profile.save()

    KYCReviewLog.objects.create(
        kyc_profile=profile,
        action=action,
        is_system_action=True,
        notes=f'Sumsub webhook: {review_answer}',
        metadata=payload
    )

    # Mark webhook as processed
    webhook.processed = True
    webhook.processed_at = timezone.now()
    webhook.save()

    # Run watchlist check on approval
    if review_answer == 'GREEN':
        try:
            run_watchlist_check(profile)
        except Exception as e:
            print(f"[KYC] Watchlist check error: {e}")

    # Trigger auto-verification for service providers
    if review_answer == 'GREEN':
        try:
            from apps.services.verification import (
                trigger_auto_verification_for_user
            )
            results = trigger_auto_verification_for_user(
                profile.user
            )
            if results:
                print(
                    f"[KYC→VERIFY] Auto-verify results "
                    f"for {profile.user.email}: {results}"
                )
        except Exception as e:
            print(f"[KYC→VERIFY] Error: {e}")

    # Notify user
    try:
        from apps.notifications.utils import send_notification
        if review_answer == 'GREEN':
            send_notification(
                user=profile.user,
                title='Identity Verified ✅',
                message=(
                    'Your identity has been verified. '
                    'You can now complete your booking.'
                ),
                notification_type='system',
                data={'kyc_profile_id': profile.id}
            )
        elif review_answer == 'RED':
            send_notification(
                user=profile.user,
                title='Verification Failed ❌',
                message=(
                    'Your identity verification failed. '
                    'Please resubmit with valid documents.'
                ),
                notification_type='system',
                data={'kyc_profile_id': profile.id}
            )
    except Exception as e:
        print(f"[KYC] Notification error: {e}")

    return profile