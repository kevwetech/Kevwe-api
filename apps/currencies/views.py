from rest_framework.views import APIView
from rest_framework import status
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import Currency
from .serializers import CurrencySerializer
from .utils import update_exchange_rates, convert
from decimal import Decimal, InvalidOperation


class CurrencyListView(APIView):
    """
    GET  - List all active currencies (public)
    POST - Create currency (admin)
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        currencies = Currency.objects.filter(is_active=True)
        serializer = CurrencySerializer(currencies, many=True)
        return api_response(
            'success',
            'Currencies retrieved successfully',
            data={
                'count': currencies.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CurrencySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Currency created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CurrencyDetailView(APIView):
    """
    GET   - Get currency detail
    PATCH - Update currency (admin)
    """
    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdmin()]
        return []

    def get_object(self, code):
        try:
            return Currency.objects.get(
                code=code.upper()
            )
        except Currency.DoesNotExist:
            return None

    def get(self, request, code):
        currency = self.get_object(code)
        if not currency:
            return api_response(
                'error', 'Currency not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        return api_response(
            'success',
            'Currency retrieved successfully',
            data=CurrencySerializer(currency).data
        )

    def patch(self, request, code):
        currency = self.get_object(code)
        if not currency:
            return api_response(
                'error', 'Currency not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CurrencySerializer(
            currency, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Currency updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class UpdateExchangeRatesView(APIView):
    """
    POST - Trigger live exchange rate update (admin)
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        result = update_exchange_rates()
        if result['success']:
            return api_response(
                'success',
                f"Rates updated for {result['total_updated']} currencies",
                data=result
            )
        return api_response(
            'error',
            result['message'],
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class ManualRateUpdateView(APIView):
    """
    PATCH - Manually set exchange rate for a currency (admin)
    Enables manual_override so auto-fetch skips it.
    """
    permission_classes = [IsAdmin]

    def patch(self, request, code):
        from django.utils import timezone

        try:
            currency = Currency.objects.get(code=code.upper())
        except Currency.DoesNotExist:
            return api_response(
                'error', 'Currency not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        rate = request.data.get('rate_to_ngn')
        if not rate:
            return api_response(
                'error', 'rate_to_ngn is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            currency.rate_to_ngn = Decimal(str(rate))
            currency.manual_override = True
            currency.rate_source = 'override'
            currency.rate_updated_at = timezone.now()
            currency.save()

            # Record rate history
            try:
                from .models import CurrencyRateHistory
                CurrencyRateHistory.objects.create(
                    currency=currency,
                    rate_to_ngn=currency.rate_to_ngn,
                    convert_from_ngn=currency.convert_from_ngn,
                    source='override',
                    recorded_by=request.user,
                    note=request.data.get('note', ''),
                )
            except Exception as e:
                print(f"Rate history error: {e}")

        except InvalidOperation:
            return api_response(
                'error', 'Invalid rate value',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        return api_response(
            'success',
            f'{currency.code} rate manually set to {rate} NGN',
            data=CurrencySerializer(currency).data
        )

class ResetAutoUpdateView(APIView):
    """
    POST - Remove manual override, re-enable auto-fetch (admin)
    """
    permission_classes = [IsAdmin]

    def post(self, request, code):
        try:
            currency = Currency.objects.get(code=code.upper())
        except Currency.DoesNotExist:
            return api_response(
                'error', 'Currency not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        currency.manual_override = False
        currency.save()

        return api_response(
            'success',
            f'{currency.code} will now auto-update rates',
            data=CurrencySerializer(currency).data
        )


class ConvertCurrencyView(APIView):
    """
    GET - Convert amount between currencies (public)
    ?from=USD&to=NGN&amount=100
    """
    def get(self, request):
        from_code = request.query_params.get('from', 'USD')
        to_code = request.query_params.get('to', 'NGN')
        amount = request.query_params.get('amount', '1')

        try:
            amount_decimal = Decimal(str(amount))
        except InvalidOperation:
            return api_response(
                'error', 'Invalid amount',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            converted = convert(amount_decimal, from_code, to_code)
        except ValueError as e:
            return api_response(
                'error', str(e),
                http_status=status.HTTP_400_BAD_REQUEST
            )

        return api_response(
            'success',
            f'{amount} {from_code} = {converted} {to_code}',
            data={
                'from_currency': from_code.upper(),
                'to_currency': to_code.upper(),
                'amount': str(amount_decimal),
                'converted': str(converted),
            }
        )

class SetCountryCurrencyView(APIView):
    """
    Admin sets the default currency for a country.
    PATCH /api/v1/currencies/countries/<country_code>/set-currency/
    Body: { "currency_code": "GHS" }
    """
    permission_classes = [IsAdmin]

    def patch(self, request, country_code):
        from apps.locations.models import Country

        try:
            country = Country.objects.get(
                code=country_code.upper()
            )
        except Country.DoesNotExist:
            return api_response(
                'error', 'Country not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        currency_code = request.data.get('currency_code')
        if not currency_code:
            return api_response(
                'error', 'currency_code is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            currency = Currency.objects.get(
                code=currency_code.upper(),
                is_active=True
            )
        except Currency.DoesNotExist:
            return api_response(
                'error',
                f'Currency {currency_code} not found or inactive',
                http_status=status.HTTP_404_NOT_FOUND
            )

        country.default_currency = currency
        country.currency_code = currency.code
        country.currency_symbol = currency.symbol
        country.save()

        return api_response(
            'success',
            f'{country.name} default currency set to '
            f'{currency.code} ({currency.symbol})',
            data={
                'country': country.name,
                'country_code': country.code,
                'currency': currency.code,
                'currency_name': currency.name,
                'currency_symbol': currency.symbol,
                'rate_to_ngn': str(currency.rate_to_ngn),
            }
        )


class CountryCurrencyListView(APIView):
    """
    GET - List all countries with their default currencies (public)
    GET /api/v1/currencies/countries/
    """
    def get(self, request):
        from apps.locations.models import Country

        countries = Country.objects.filter(
            is_active=True
        ).select_related('default_currency')

        results = []
        for c in countries:
            results.append({
                'country': c.name,
                'country_code': c.code,
                'phone_code': c.phone_code,
                'currency_code': (
                    c.default_currency.code
                    if c.default_currency
                    else c.currency_code or 'NGN'
                ),
                'currency_name': (
                    c.default_currency.name
                    if c.default_currency
                    else None
                ),
                'currency_symbol': (
                    c.default_currency.symbol
                    if c.default_currency
                    else c.currency_symbol or '₦'
                ),
                'rate_to_ngn': (
                    str(c.default_currency.rate_to_ngn)
                    if c.default_currency
                    else '1.000000'
                ),
            })

        return api_response(
            'success',
            'Country currencies retrieved',
            data={
                'count': len(results),
                'results': results
            }
        )

class CurrencyRateHistoryView(APIView):
    """
    GET - View rate history for a currency (admin)
    GET /api/v1/currencies/<code>/history/
    """
    permission_classes = [IsAdmin]

    def get(self, request, code):
        from .models import CurrencyRateHistory
        from .serializers import CurrencyRateHistorySerializer

        try:
            currency = Currency.objects.get(code=code.upper())
        except Currency.DoesNotExist:
            return api_response(
                'error', 'Currency not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        history = CurrencyRateHistory.objects.filter(
            currency=currency
        )[:50]  # last 50 entries

        return api_response(
            'success',
            f'Rate history for {currency.code}',
            data={
                'currency': code.upper(),
                'current_rate': str(currency.rate_to_ngn),
                'count': history.count(),
                'results': CurrencyRateHistorySerializer(
                    history, many=True
                ).data
            }
        )