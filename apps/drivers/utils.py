import math
from .models import DriverProfile



def calculate_distance(lat1, lng1, lat2, lng2):
    """
    Calculate distance between two coordinates
    using Haversine formula
    Returns distance in kilometers
    """
    R = 6371  # Earth's radius in km

    lat1, lng1, lat2, lng2 = map(math.radians, [
        float(lat1), float(lng1),
        float(lat2), float(lng2)
    ])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def find_nearby_drivers(lat, lng, radius_km=5, vehicle_type=None):
    """
    Find available drivers within radius
    """
    
    drivers = DriverProfile.objects.filter(
        is_available=True,
        is_online=True,
        status='verified',
        current_lat__isnull=False,
        current_lng__isnull=False,
    )

    if vehicle_type:
        drivers = drivers.filter(
            active_vehicle__vehicle_type=vehicle_type
        )

    nearby = []
    for driver in drivers:
        distance = calculate_distance(
            lat, lng,
            driver.current_lat,
            driver.current_lng
        )
        if distance <= radius_km:
            nearby.append({
                'driver': driver,
                'distance_km': round(distance, 2),
                'eta_minutes': round(distance * 3)
            })

    # Sort by distance
    nearby.sort(key=lambda x: x['distance_km'])
    return nearby


def calculate_fare(distance_km, duration_minutes, vehicle_type=None):
    """
    Calculate ride/delivery fare
    """
    BASE_FARE = 500
    PER_KM_RATE = 100
    PER_MINUTE_RATE = 10
    MINIMUM_FARE = 800

    if vehicle_type:
        rates = {
            'bike': {'base': 300, 'per_km': 70, 'per_min': 5},
            'car': {'base': 500, 'per_km': 100, 'per_min': 10},
            'van': {'base': 800, 'per_km': 150, 'per_min': 15},
            'truck': {'base': 1500, 'per_km': 250, 'per_min': 20},
        }
        rate = rates.get(vehicle_type, rates['car'])
        BASE_FARE = rate['base']
        PER_KM_RATE = rate['per_km']
        PER_MINUTE_RATE = rate['per_min']

    fare = (
        BASE_FARE +
        (distance_km * PER_KM_RATE) +
        (duration_minutes * PER_MINUTE_RATE)
    )

    return max(fare, MINIMUM_FARE)