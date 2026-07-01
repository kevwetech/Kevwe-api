def check_provider_verification(provider):
    """
    Check if a provider meets all requirements for auto-verification.
    Returns (is_eligible, reason).
    """
    from apps.kyc.models import (
        KYCProfile, KYCDocument, KYCSelfie, BusinessKYC,
        BusinessKYCDocument
    )
    from .models import ProviderCertification

    user = provider.user

    # ── Step 1: Personal KYC must be approved ──
    try:
        kyc = KYCProfile.objects.get(
            user=user, use_case='booking'
        )
        if kyc.status not in ('approved', 'auto_approved'):
            return False, 'Personal KYC not yet approved'
    except KYCProfile.DoesNotExist:
        return False, 'Personal KYC not started'

    # ── Step 2: At least 1 approved ID document ──
    approved_docs = KYCDocument.objects.filter(
        kyc_profile__user=user,
        status='approved',
        verified=True,
    ).exclude(
        document_type__in=['cac', 'tin']
    )
    if not approved_docs.exists():
        return False, 'No approved ID document found'

    # ── Step 3: Approved selfie ──
    approved_selfie = KYCSelfie.objects.filter(
        kyc_profile__user=user,
        status='approved',
    ).exists()
    if not approved_selfie:
        return False, 'No approved selfie found'

    # ── Step 4: Business provider needs BusinessKYC ──
    if provider.provider_type == 'business':
        if not provider.business:
            return False, 'No business linked to provider'

        try:
            biz_kyc = BusinessKYC.objects.get(
                business=provider.business
            )
            if biz_kyc.status != 'approved':
                return (
                    False,
                    'Business KYC not approved'
                )
        except BusinessKYC.DoesNotExist:
            return False, 'Business KYC not started'

        approved_biz_docs = BusinessKYCDocument.objects.filter(
            business_kyc__business=provider.business,
            status='approved',
            verified=True,
        ).exists()
        if not approved_biz_docs:
            return (
                False,
                'No approved business documents found'
            )

    # ── Step 5: Check if any service requires certification ──
    services_requiring_cert = provider.services.filter(
        requires_certification=True,
        is_active=True
    )
    if services_requiring_cert.exists():
        verified_cert = ProviderCertification.objects.filter(
            provider=provider,
            status='verified',
        ).exists()
        if not verified_cert:
            service_names = ', '.join(
                services_requiring_cert.values_list(
                    'name', flat=True
                )
            )
            return (
                False,
                f'Verified certification required for: '
                f'{service_names}'
            )

    return True, 'All requirements met'


def auto_verify_provider(provider):
    """
    Run eligibility check and auto-verify if all requirements met.
    Returns (was_verified, reason).
    """
    from apps.notifications.utils import send_notification
    from django.utils import timezone

    if provider.status == 'verified':
        return False, 'Already verified'

    if provider.status == 'suspended':
        return False, 'Provider is suspended'

    is_eligible, reason = check_provider_verification(provider)

    if is_eligible:
        provider.status = 'verified'
        provider.save()

        try:
            send_notification(
                user=provider.user,
                title='Provider Account Verified ✅',
                message=(
                    f'Your provider profile '
                    f'"{provider.business_name or provider.user.full_name}" '
                    f'has been automatically verified. '
                    f'You can now go online and accept requests.'
                ),
                notification_type='system',
                data={'provider_id': provider.id}
            )
        except Exception as e:
            print(f"[VERIFY] Notification error: {e}")

        print(
            f"[VERIFY] Auto-verified provider "
            f"{provider.id} — "
            f"{provider.business_name or provider.user.full_name}"
        )
        return True, 'Auto-verified successfully'

    print(
        f"[VERIFY] Provider {provider.id} not eligible: {reason}"
    )
    return False, reason


def trigger_auto_verification_for_user(user):
    """
    Called when a user's KYC is approved.
    Checks all their provider profiles for auto-verification.
    Returns list of (provider, was_verified, reason).
    """
    from .models import ServiceProvider

    providers = ServiceProvider.objects.filter(
        user=user,
        status='pending'
    )

    results = []
    for provider in providers:
        was_verified, reason = auto_verify_provider(provider)
        results.append({
            'provider_id': provider.id,
            'provider_name': (
                provider.business_name
                or provider.user.full_name
            ),
            'was_verified': was_verified,
            'reason': reason,
        })

    return results