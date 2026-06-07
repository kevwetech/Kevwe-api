import requests
import os
from decimal import Decimal


PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_BASE_URL = 'https://api.paystack.co'


def get_headers():
    return {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def initialize_payment(
    email,
    amount,
    reference,
    callback_url=None,
    metadata=None
):
    """
    Initialize a Paystack payment
    Amount should be in Naira - we convert to kobo
    """
    # Convert to kobo (Paystack uses kobo)
    amount_kobo = int(Decimal(str(amount)) * 100)

    payload = {
        'email': email,
        'amount': amount_kobo,
        'reference': reference,
        'currency': 'NGN',
        'metadata': metadata or {},
    }

    if callback_url:
        payload['callback_url'] = callback_url

    try:
        response = requests.post(
            f'{PAYSTACK_BASE_URL}/transaction/initialize',
            json=payload,
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': False,
            'message': str(e)
        }


def verify_payment(reference):
    """Verify a Paystack payment"""
    try:
        response = requests.get(
            f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': False,
            'message': str(e)
        }


def refund_payment(reference, amount=None):
    """Refund a Paystack payment"""
    payload = {'transaction': reference}
    if amount:
        payload['amount'] = int(Decimal(str(amount)) * 100)

    try:
        response = requests.post(
            f'{PAYSTACK_BASE_URL}/refund',
            json=payload,
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': False,
            'message': str(e)
        }


def get_banks():
    """Get list of Nigerian banks"""
    try:
        response = requests.get(
            f'{PAYSTACK_BASE_URL}/bank?currency=NGN',
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': False,
            'message': str(e)
        }


def verify_account(account_number, bank_code):
    """Verify a bank account number"""
    try:
        response = requests.get(
            f'{PAYSTACK_BASE_URL}/bank/resolve?account_number={account_number}&bank_code={bank_code}',
            headers=get_headers()
        )
        return response.json()
    except Exception as e:
        return {
            'status': False,
            'message': str(e)
        }