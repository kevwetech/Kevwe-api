import requests
import os
from decimal import Decimal
from django.utils import timezone


EXCHANGE_API_KEY = os.environ.get('EXCHANGE_RATE_API_KEY', '')
EXCHANGE_API_URL = (
    'https://v6.exchangerate-api.com/v6'
    f'/{EXCHANGE_API_KEY}/latest/NGN'
)


def fetch_live_rates():
    """
    Fetch live exchange rates from exchangerate-api.com
    Base currency: NGN
    Returns dict of {currency_code: rate_to_ngn} or None on failure.
    """
    if not EXCHANGE_API_KEY:
        print("[EXCHANGE RATE] No API key set — skipping auto-fetch")
        return None

    try:
        response = requests.get(EXCHANGE_API_URL, timeout=10)
        data = response.json()

        if data.get('result') != 'success':
            print(f"[EXCHANGE RATE] API error: {data}")
            return None

        # rates are NGN→X, we need X→NGN
        # if 1 NGN = 0.00065 USD, then 1 USD = 1/0.00065 NGN
        ngn_rates = data['conversion_rates']
        rates_to_ngn = {}
        for code, rate in ngn_rates.items():
            if rate > 0:
                rates_to_ngn[code] = Decimal(
                    str(1 / rate)
                ).quantize(Decimal('0.000001'))

        return rates_to_ngn

    except Exception as e:
        print(f"[EXCHANGE RATE] Fetch error: {e}")
        return None


def update_exchange_rates():
    """
    Update all non-manual-override currencies with live rates.
    Called by admin or scheduled task.
    Returns summary dict.
    """
    from .models import Currency

    rates = fetch_live_rates()
    if not rates:
        return {
            'success': False,
            'message': 'Failed to fetch live rates'
        }

    updated = []
    skipped = []
    not_found = []

    currencies = Currency.objects.filter(
        is_active=True,
        manual_override=False,
        auto_update=True,
    ).exclude(code='NGN')

    for currency in currencies:
        if currency.code in rates:
            old_rate = currency.rate_to_ngn
            currency.rate_to_ngn = rates[currency.code]
            currency.rate_updated_at = timezone.now()
            currency.rate_source = 'api'
            currency.save()

            # Record rate history
            try:
                from .models import CurrencyRateHistory
                CurrencyRateHistory.objects.create(
                    currency=currency,
                    rate_to_ngn=currency.rate_to_ngn,
                    convert_from_ngn=currency.convert_from_ngn,
                    source='api',
                )
            except Exception as e:
                print(f"Rate history error: {e}")

            updated.append(currency.code)
        else:
            not_found.append(currency.code)

    return {
        'success': True,
        'updated': updated,
        'skipped': skipped,
        'not_found': not_found,
        'total_updated': len(updated),
    }


def get_currency(code):
    """Get a currency by code, returns None if not found/inactive."""
    from .models import Currency
    try:
        return Currency.objects.get(code=code.upper(), is_active=True)
    except Currency.DoesNotExist:
        return None


def get_default_currency():
    """Get the default currency (NGN)."""
    from .models import Currency
    return Currency.objects.filter(is_default=True).first()


def convert(amount, from_code, to_code='NGN'):
    """
    Convert amount from one currency to another.
    All conversions go through NGN as base.
    """
    from_code = from_code.upper()
    to_code = to_code.upper()

    if from_code == to_code:
        return Decimal(str(amount))

    from_currency = get_currency(from_code)
    if not from_currency:
        raise ValueError(f"Currency {from_code} not found")

    # Convert to NGN first
    amount_ngn = from_currency.to_ngn(amount)

    if to_code == 'NGN':
        return amount_ngn

    to_currency = get_currency(to_code)
    if not to_currency:
        raise ValueError(f"Currency {to_code} not found")

    return to_currency.from_ngn(amount_ngn)

def get_currency_for_country(country_code):
    """
    Get the default currency for a country by country code.
    Falls back to NGN if not set.
    """
    from apps.locations.models import Country
    try:
        country = Country.objects.select_related(
            'default_currency'
        ).get(code=country_code.upper())
        if country.default_currency:
            return country.default_currency
    except Country.DoesNotExist:
        pass
    return get_default_currency()