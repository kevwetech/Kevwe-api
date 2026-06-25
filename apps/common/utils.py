import random
import string
import math


def generate_otp(length=6):
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))


def generate_reference(prefix='REF', length=10):
    """Generate a unique reference number"""
    chars = string.ascii_uppercase + string.digits
    random_str = ''.join(random.choices(chars, k=length))
    return f"{prefix}-{random_str}"


def format_price(price):
    """Format price with currency"""
    return f"₦{price:,.2f}"

def generate_order_number():
    chars = string.digits
    return 'ORD-' + ''.join(random.choices(chars, k=8))


def calculate_distance_km(lat1, lng1, lat2, lng2):
    """
    Calculate the distance in kilometers between two
    lat/lng points using the Haversine formula.
    Returns None if any coordinate is missing.
    """
    if None in (lat1, lng1, lat2, lng2):
        return None

    lat1, lng1, lat2, lng2 = map(
        float, [lat1, lng1, lat2, lng2]
    )

    R = 6371  # Earth radius in km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c