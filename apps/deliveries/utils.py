import random
import string


def generate_tracking_number():
    """Generate unique delivery tracking number"""
    chars = string.ascii_uppercase + string.digits
    return 'DLV' + ''.join(random.choices(chars, k=10))


def calculate_delivery_price(
    pickup_state,
    dropoff_state,
    pickup_city,
    dropoff_city,
    package_size,
    weight
):
    """Calculate delivery price"""
    BASE_PRICE = 800

    # Size pricing
    size_price = {
        'small': 0,
        'medium': 500,
        'large': 1000,
    }.get(package_size, 0)

    # Weight pricing
    weight_price = float(weight) * 50

    # Distance pricing
    if pickup_state == dropoff_state:
        if pickup_city == dropoff_city:
            distance_price = 500   # same city
        else:
            distance_price = 1000  # same state different city
    else:
        distance_price = 2500      # different state

    total = BASE_PRICE + size_price + weight_price + distance_price
    return round(total, 2)


DELIVERY_STEPS = [
    {
        'status': 'pending',
        'label': 'Delivery Requested',
        'description': 'Your delivery request has been received',
        'icon': '📦'
    },
    {
        'status': 'assigned',
        'label': 'Dispatcher Assigned',
        'description': 'A dispatcher has been assigned',
        'icon': '🏍️'
    },
    {
        'status': 'picked_up',
        'label': 'Package Picked Up',
        'description': 'Package has been picked up',
        'icon': '✅'
    },
    {
        'status': 'in_transit',
        'label': 'In Transit',
        'description': 'Package is on the way',
        'icon': '🚀'
    },
    {
        'status': 'delivered',
        'label': 'Delivered',
        'description': 'Package has been delivered',
        'icon': '🎉'
    },
]