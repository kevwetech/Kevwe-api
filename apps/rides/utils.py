from apps.drivers.utils import calculate_distance


def calculate_ride_fare(
    pickup_lat, pickup_lng,
    destination_lat, destination_lng,
    vehicle_type=None
):
    """Calculate estimated ride fare"""

    # Calculate distance
    distance_km = calculate_distance(
        pickup_lat, pickup_lng,
        destination_lat, destination_lng
    )

    # Estimate duration (average 30km/h in city)
    duration_minutes = (distance_km / 30) * 60

    if vehicle_type:
        base_fare = float(vehicle_type.base_fare)
        per_km = float(vehicle_type.per_km_rate)
        per_min = float(vehicle_type.per_minute_rate)
        minimum = float(vehicle_type.minimum_fare)
    else:
        base_fare = 500
        per_km = 100
        per_min = 10
        minimum = 800

    fare = base_fare + (distance_km * per_km) + (duration_minutes * per_min)
    fare = max(fare, minimum)

    return {
        'distance_km': round(distance_km, 2),
        'duration_minutes': round(duration_minutes),
        'estimated_fare': round(fare, 2),
    }


def find_available_driver(
    pickup_lat,
    pickup_lng,
    vehicle_type=None
):
    """Find nearest available driver"""
    from apps.drivers.utils import find_nearby_drivers

    # Don't filter by vehicle type — find any available driver
    nearby = find_nearby_drivers(
        pickup_lat,
        pickup_lng,
        radius_km=10,
        vehicle_type=None  # ← remove vehicle type filter
    )

    if nearby:
        return nearby[0]['driver']
    return None