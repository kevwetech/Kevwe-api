from decimal import Decimal


PLATFORM_COMMISSION = Decimal('0.20')
DRIVER_EARNINGS_PERCENT = Decimal('0.80')

ZONE_MULTIPLIER = {
    'same_city': Decimal('1.0'),
    'same_state': Decimal('1.3'),
    'interstate': Decimal('1.8'),
}

PACKAGE_SIZE_SURCHARGE = {
    'small': Decimal('0'),
    'medium': Decimal('500'),
    'large': Decimal('1000'),
    'extra_large': Decimal('2000'),
}


def get_vehicle_type(vehicle_type_id=None, vehicle_type_name=None):
    """Get vehicle type from database"""
    from apps.drivers.models import VehicleType
    try:
        if vehicle_type_id:
            return VehicleType.objects.get(
                pk=vehicle_type_id,
                is_active=True
            )
        elif vehicle_type_name:
            return VehicleType.objects.get(
                name__iexact=vehicle_type_name,
                is_active=True
            )
    except Exception:
        return None


def calculate_logistics_price(
    distance_km,
    weight_kg,
    package_size='small',
    vehicle_type_id=None,
    vehicle_type_name=None,
    service_type='standard',
    pickup_city=None,
    pickup_state=None,
    dropoff_city=None,
    dropoff_state=None,
    pickup_zone_id=None,  
    dropoff_zone_id=None,
):
    """
    Calculate logistics price using
    vehicle type rates from database
    """
    # Get vehicle type from DB
    vtype = get_vehicle_type(
        vehicle_type_id=vehicle_type_id,
        vehicle_type_name=vehicle_type_name
    )

    if not vtype:
        # Default rates if no vehicle type found
        base_price = Decimal('500') if service_type == 'standard' else Decimal('1000')
        per_km = Decimal('100')
        per_kg = Decimal('30')
        minimum = Decimal('800') if service_type == 'standard' else Decimal('1500')
    else:
        base_price = (
            vtype.base_price_standard
            if service_type == 'standard'
            else vtype.base_price_express
        )
        per_km = vtype.per_km_rate
        per_kg = vtype.per_kg_rate
        minimum = (
            vtype.minimum_fare_standard
            if service_type == 'standard'
            else vtype.minimum_fare_express
        )

    # Package size surcharge
    size_charge = PACKAGE_SIZE_SURCHARGE.get(
        package_size,
        Decimal('0')
    )

    # Zone multiplier
    if pickup_city and dropoff_city and pickup_city.lower() == dropoff_city.lower():
        zone = 'same_city'
    elif pickup_state and dropoff_state and pickup_state.lower() == dropoff_state.lower():
        zone = 'same_state'
    else:
        zone = 'interstate'

    zone_multiplier = ZONE_MULTIPLIER[zone]

    # Calculate
    distance_charge = Decimal(str(distance_km)) * per_km
    weight_charge = Decimal(str(weight_kg)) * per_kg
    subtotal = base_price + distance_charge + weight_charge + size_charge
    total = subtotal * zone_multiplier
    total = max(total, minimum)

    # Earnings split
    platform_fee = total * PLATFORM_COMMISSION
    driver_earnings = total * DRIVER_EARNINGS_PERCENT

    return {
        'total': round(total, 2),
        'breakdown': {
            'base_price': str(round(base_price, 2)),
            'distance_km': round(distance_km, 2),
            'distance_charge': str(round(distance_charge, 2)),
            'weight_kg': float(weight_kg),
            'weight_charge': str(round(weight_charge, 2)),
            'size_charge': str(round(size_charge, 2)),
            'zone': zone,
            'zone_multiplier': str(zone_multiplier),
            'service_type': service_type,
            'vehicle_type': vtype.name if vtype else 'default',
            'per_km_rate': str(per_km),
            'per_kg_rate': str(per_kg),
        },
        'platform_fee': round(platform_fee, 2),
        'driver_earnings': round(driver_earnings, 2),
    }


def get_price_estimate(
    pickup_lat, pickup_lng,
    dropoff_lat, dropoff_lng,
    weight_kg,
    package_size='small',
    pickup_city=None,
    pickup_state=None,
    dropoff_city=None,
    dropoff_state=None,
):
    """
    Get price estimates for ALL
    active vehicle types from database
    """
    from apps.drivers.models import VehicleType
    from apps.drivers.utils import calculate_distance

    distance_km = calculate_distance(
        pickup_lat, pickup_lng,
        dropoff_lat, dropoff_lng
    )

    # Get all active vehicle types from DB
    vehicle_types = VehicleType.objects.filter(is_active=True)

    estimates = []
    for vtype in vehicle_types:
        for service_type in ['standard', 'express']:
            price_data = calculate_logistics_price(
                distance_km=distance_km,
                weight_kg=weight_kg,
                package_size=package_size,
                vehicle_type_id=vtype.id,
                service_type=service_type,
                pickup_city=pickup_city,
                pickup_state=pickup_state,
                dropoff_city=dropoff_city,
                dropoff_state=dropoff_state,
            )
            estimates.append({
                'vehicle_type_id': vtype.id,
                'vehicle_type': vtype.name,
                'service_type': service_type,
                'price': str(price_data['total']),
                'platform_fee': str(price_data['platform_fee']),
                'driver_earnings': str(price_data['driver_earnings']),
                'breakdown': price_data['breakdown'],
                'eta_minutes': round(distance_km / 30 * 60),
                'max_weight_kg': str(vtype.max_weight_kg),
            })

    return {
        'distance_km': round(distance_km, 2),
        'weight_kg': float(weight_kg),
        'estimates': estimates,
    }