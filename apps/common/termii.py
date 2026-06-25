import os
import requests


TERMII_API_KEY = os.environ.get('TERMII_API_KEY', '')
TERMII_SENDER_ID = os.environ.get('TERMII_SENDER_ID', 'KevweTech')
TERMII_BASE_URL = os.environ.get(
    'TERMII_BASE_URL', 'https://api.ng.termii.com'
)


def send_sms(phone, message):
    """
    Send SMS via Termii.
    Falls back to console print if TERMII_API_KEY is not set.
    """
    if not TERMII_API_KEY:
        print(f"[TERMII SMS STUB] To: {phone} | Message: {message}")
        return {'status': 'stubbed', 'phone': phone}

    payload = {
        "to": phone,
        "from": TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": TERMII_API_KEY,
    }

    try:
        response = requests.post(
            f"{TERMII_BASE_URL}/api/sms/send",
            json=payload,
            timeout=10
        )
        return response.json()
    except Exception as e:
        print(f"Termii SMS error: {e}")
        return {'status': 'error', 'error': str(e)}


def send_whatsapp(phone, message):
    """
    Send WhatsApp message via Termii.
    Falls back to console print if TERMII_API_KEY is not set.
    """
    if not TERMII_API_KEY:
        print(
            f"[TERMII WHATSAPP STUB] To: {phone} | Message: {message}"
        )
        return {'status': 'stubbed', 'phone': phone}

    payload = {
        "to": phone,
        "from": TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": "whatsapp",
        "api_key": TERMII_API_KEY,
    }

    try:
        response = requests.post(
            f"{TERMII_BASE_URL}/api/sms/send",
            json=payload,
            timeout=10
        )
        return response.json()
    except Exception as e:
        print(f"Termii WhatsApp error: {e}")
        return {'status': 'error', 'error': str(e)}



def send_booking_confirmation_sms(phone, booking, maps_link):
    """Send booking check-in code + directions via SMS."""
    message = (
        f"Booking Confirmed! ✅\n"
        f"Property: {booking.item.name}\n"
        f"Check-in: {booking.check_in}\n"
        f"Check-in Code: {booking.checkin_code}\n"
        f"Show this code at the front desk.\n"
        f"View on Map: {maps_link or 'See your email for details'}"
    )
    return send_sms(phone, message)


def send_booking_confirmation_whatsapp(phone, booking, maps_link):
    """Send booking check-in code + directions via WhatsApp."""
    message = (
        f"Booking Confirmed! ✅\n"
        f"Property: {booking.item.name}\n"
        f"Check-in: {booking.check_in}\n"
        f"Check-in Code: *{booking.checkin_code}*\n"
        f"Show this code at the front desk.\n"
        f"View on Map: {maps_link or 'See your email for details'}"
    )
    return send_whatsapp(phone, message)