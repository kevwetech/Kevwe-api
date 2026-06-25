from django.urls import path
from .views import (
    CountryListCreateView,
    CountryDetailView,
    StateListCreateView,
    StateDetailView,
    CityListCreateView,
    CityDetailView,
    ZoneListCreateView,
    ZoneDetailView,
    AddressListCreateView,
    AddressDetailView,
    SetDefaultAddressView,
    LocationHierarchyView,
    NearbyBusinessesView,
)

urlpatterns = [
    # Location hierarchy helper
    path('hierarchy/', LocationHierarchyView.as_view(), name='location_hierarchy'),

    # Countries
    path('countries/', CountryListCreateView.as_view(), name='countries'),
    path('countries/<int:pk>/', CountryDetailView.as_view(), name='country_detail'),

    # States
    path('states/', StateListCreateView.as_view(), name='states'),
    path('states/<int:pk>/', StateDetailView.as_view(), name='state_detail'),
    path('discover/', NearbyBusinessesView.as_view(), name='nearby_businesses'),
    
    # Cities
    path('cities/', CityListCreateView.as_view(), name='cities'),
    path('cities/<int:pk>/', CityDetailView.as_view(), name='city_detail'),

    # Zones
    path('zones/', ZoneListCreateView.as_view(), name='zones'),
    path('zones/<int:pk>/', ZoneDetailView.as_view(), name='zone_detail'),

    # Addresses
    path('addresses/', AddressListCreateView.as_view(), name='addresses'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(), name='address_detail'),
    path('addresses/<int:pk>/set-default/', SetDefaultAddressView.as_view(), name='set_default_address'),
    
]