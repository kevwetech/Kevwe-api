from django.urls import path
from .views import (
    CurrencyListView,
    CurrencyDetailView,
    UpdateExchangeRatesView,
    ManualRateUpdateView,
    ResetAutoUpdateView,
    ConvertCurrencyView,
    SetCountryCurrencyView,
    CountryCurrencyListView,
)

urlpatterns = [
    path('', CurrencyListView.as_view(), name='currencies'),
    path('convert/', ConvertCurrencyView.as_view(), name='convert_currency'),
    path('rates/update/', UpdateExchangeRatesView.as_view(), name='update_rates'),
    path('countries/', CountryCurrencyListView.as_view(), name='country_currencies'),
    path('countries/<str:country_code>/set-currency/', SetCountryCurrencyView.as_view(), name='set_country_currency'),
    path('<str:code>/', CurrencyDetailView.as_view(), name='currency_detail'),
    path('<str:code>/set-rate/', ManualRateUpdateView.as_view(), name='manual_rate_update'),
    path('<str:code>/reset-auto/', ResetAutoUpdateView.as_view(), name='reset_auto_update'),
]