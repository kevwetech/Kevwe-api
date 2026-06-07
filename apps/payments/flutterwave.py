import requests
import os
import hashlib
import hmac
from decimal import Decimal


FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY')
FLUTTERWAVE_PUBLIC_KEY = os.getenv('FLUTTERWAVE_PUBLIC_KEY')
FLUTTERWAVE_ENCRYPTION_KEY = os.getenv('FLUTTERWAVE_ENCRYPTION_KEY')
FLUTTERWAVE_BASE_URL = 'https://api.flutterwave.com/v3'


def get_headers():
    return {
        'Authorization': f'Bearer {FLUTTERWAVE_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def initialize_payment(
    email,
    amount,
    reference,
    name,
    phone=None,
    callback_url=None,
    redirect_url=None,
    metadata=None
):
    """Initialize a Flutterwave payment"""
    payload = {
        'tx_ref': reference,
        'amount': float(amount),
        'currency': 'NGN',
        'redirect_url': redirect_url or callback_url or 'http://localhost:8000',
        'customer': {
            'email': email,
            'name': name,
            'phonenumber': phone or '',
        },
        'customizations': {
            'title': 'Kevwe API Payment',
            'description': 'Payment for services',
        },
        'meta': metadata or {},
    }

    try:
        response = requests.post(
            f'{FLUTTERWAVE_BASE_URL}/payments',
            json=payload,
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def verify_payment(transaction_id):
    """Verify a Flutterwave payment by transaction ID"""
    try:
        response = requests.get(
            f'{FLUTTERWAVE_BASE_URL}/transactions/{transaction_id}/verify',
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def verify_payment_by_reference(reference):
    """Verify a Flutterwave payment by reference"""
    try:
        response = requests.get(
            f'{FLUTTERWAVE_BASE_URL}/transactions?tx_ref={reference}',
            headers=get_headers()
        )
        print(f"Flutterwave verify response: {response.json()}")  # ← debug
        return response.json()
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def refund_payment(transaction_id, amount=None):
    """Refund a Flutterwave payment"""
    payload = {}
    if amount:
        payload['amount'] = float(amount)

    try:
        response = requests.post(
            f'{FLUTTERWAVE_BASE_URL}/transactions/{transaction_id}/refund',
            json=payload,
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def verify_webhook(payload, signature):
    """Verify Flutterwave webhook signature"""
    secret = FLUTTERWAVE_SECRET_KEY
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def get_banks():
    """Get list of Nigerian banks"""
    try:
        response = requests.get(
            f'{FLUTTERWAVE_BASE_URL}/banks/NG',
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }