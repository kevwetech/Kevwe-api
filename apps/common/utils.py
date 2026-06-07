import random
import string


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