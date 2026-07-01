def find_nearby_providers(
    service, lat, lng, radius_km=15, emergency=False
):
    """
    Find available verified providers for a service.
    Returns list sorted by distance.
    """
    from .models import ServiceProvider
    from apps.drivers.utils import calculate_distance

    filters = {
        'services': service,
        'status': 'verified',
        'is_available': True,
        'is_online': True,
        'current_lat__isnull': False,
        'current_lng__isnull': False,
    }
    if emergency:
        filters['is_emergency_available'] = True

    providers = ServiceProvider.objects.filter(**filters)

    results = []
    for provider in providers:
        distance = calculate_distance(
            float(lat), float(lng),
            float(provider.current_lat),
            float(provider.current_lng),
        )
        max_radius = float(provider.operating_radius_km)
        if distance <= min(radius_km, max_radius):
            results.append({
                'provider': provider,
                'distance_km': round(distance, 2),
            })

    results.sort(key=lambda x: x['distance_km'])
    return results


def create_offers(service_request, providers):
    """
    Create ServiceRequestOffer records for nearby providers
    and notify them. Returns list of created offers.
    """
    from .models import ServiceRequestOffer
    from apps.notifications.utils import send_notification
    from django.utils import timezone
    from datetime import timedelta

    offers = []
    expires_at = timezone.now() + timedelta(minutes=10)

    for item in providers:
        provider = item['provider']
        offer, created = ServiceRequestOffer.objects.get_or_create(
            service_request=service_request,
            provider=provider,
            defaults={
                'distance_km': item['distance_km'],
                'expires_at': expires_at,
            }
        )
        if created:
            offers.append(offer)
            try:
                send_notification(
                    user=provider.user,
                    title='New Service Request 🔧',
                    message=(
                        f'{service_request.service.name} '
                        f'request {round(item["distance_km"], 1)}km '
                        f'away. '
                        f'{service_request.get_urgency_display()} '
                        f'priority. Tap to accept.'
                    ),
                    notification_type='system',
                    data={
                        'service_request_id': service_request.id,
                        'offer_id': offer.id,
                        'distance_km': item['distance_km'],
                    }
                )
            except Exception as e:
                print(f"[SERVICES] Notify error: {e}")

    return offers


def calculate_quote_total(labour_cost, parts_cost, other=0):
    from decimal import Decimal
    return (
        Decimal(str(labour_cost))
        + Decimal(str(parts_cost))
        + Decimal(str(other))
    )


def calculate_commission_split(total, commission_rate):
    from decimal import Decimal
    rate = Decimal(str(commission_rate)) / 100
    commission = Decimal(str(total)) * rate
    earnings = Decimal(str(total)) - commission
    return commission, earnings


def generate_completion_otp():
    import random
    return ''.join(random.choices('0123456789', k=6))