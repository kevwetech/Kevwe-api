def calculate_shipment_price(weight, pickup_state, delivery_state, package_size):
    """
    Calculate shipment price based on
    weight, distance and package size
    """
    BASE_PRICE = 1000

    # Weight pricing
    weight_price = float(weight) * 100

    # Size multiplier
    size_multiplier = {
        'small': 1.0,
        'medium': 1.5,
        'large': 2.0,
        'extra_large': 3.0,
    }.get(package_size, 1.0)

    # State pricing
    if pickup_state == delivery_state:
        state_price = 500  # same state
    else:
        state_price = 1500  # different state

    total = (BASE_PRICE + weight_price + state_price) * size_multiplier
    return round(total, 2)


def generate_tracking_number():
    """Generate unique tracking number"""
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return 'TRK' + ''.join(random.choices(chars, k=10))


SHIPMENT_STEPS = [
    {
        'status': 'pending',
        'label': 'Shipment Created',
        'description': 'Your shipment has been created',
        'icon': '📦'
    },
    {
        'status': 'assigned',
        'label': 'Driver Assigned',
        'description': 'A driver has been assigned',
        'icon': '🚗'
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
        'icon': '🚚'
    },
    {
        'status': 'out_for_delivery',
        'label': 'Out for Delivery',
        'description': 'Package is out for delivery',
        'icon': '🏃'
    },
    {
        'status': 'delivered',
        'label': 'Delivered',
        'description': 'Package has been delivered',
        'icon': '🎉'
    },
]