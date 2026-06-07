from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import Country, State, City, Zone, Address
from .serializers import (
    CountrySerializer,
    StateSerializer,
    CitySerializer,
    ZoneSerializer,
    AddressSerializer,
)


# ─── Country Views ───────────────────────────────

class CountryListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        countries = Country.objects.filter(is_active=True)
        search = request.query_params.get('search')
        if search:
            countries = countries.filter(name__icontains=search)
        serializer = CountrySerializer(countries, many=True)
        return api_response(
            'success',
            'Countries retrieved successfully',
            data={
                'count': countries.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CountrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Country created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CountryDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return Country.objects.get(pk=pk)
        except Country.DoesNotExist:
            return None

    def get(self, request, pk):
        country = self.get_object(pk)
        if not country:
            return api_response(
                'error',
                'Country not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CountrySerializer(country)
        return api_response(
            'success',
            'Country retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        country = self.get_object(pk)
        if not country:
            return api_response(
                'error',
                'Country not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CountrySerializer(
            country,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Country updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        country = self.get_object(pk)
        if not country:
            return api_response(
                'error',
                'Country not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        country.is_active = False
        country.save()
        return api_response(
            'success',
            'Country deleted successfully'
        )


# ─── State Views ───────────────────────────────

class StateListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        states = State.objects.filter(is_active=True)
        country_id = request.query_params.get('country')
        search = request.query_params.get('search')
        if country_id:
            states = states.filter(country__id=country_id)
        if search:
            states = states.filter(name__icontains=search)
        serializer = StateSerializer(states, many=True)
        return api_response(
            'success',
            'States retrieved successfully',
            data={
                'count': states.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = StateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'State created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class StateDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return State.objects.get(pk=pk)
        except State.DoesNotExist:
            return None

    def get(self, request, pk):
        state = self.get_object(pk)
        if not state:
            return api_response(
                'error',
                'State not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = StateSerializer(state)
        return api_response(
            'success',
            'State retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        state = self.get_object(pk)
        if not state:
            return api_response(
                'error',
                'State not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = StateSerializer(
            state,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'State updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        state = self.get_object(pk)
        if not state:
            return api_response(
                'error',
                'State not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        state.is_active = False
        state.save()
        return api_response(
            'success',
            'State deleted successfully'
        )


# ─── City Views ───────────────────────────────

class CityListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        cities = City.objects.filter(is_active=True)
        state_id = request.query_params.get('state')
        country_id = request.query_params.get('country')
        search = request.query_params.get('search')
        if state_id:
            cities = cities.filter(state__id=state_id)
        if country_id:
            cities = cities.filter(state__country__id=country_id)
        if search:
            cities = cities.filter(name__icontains=search)
        serializer = CitySerializer(cities, many=True)
        return api_response(
            'success',
            'Cities retrieved successfully',
            data={
                'count': cities.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'City created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CityDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return City.objects.get(pk=pk)
        except City.DoesNotExist:
            return None

    def get(self, request, pk):
        city = self.get_object(pk)
        if not city:
            return api_response(
                'error',
                'City not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CitySerializer(city)
        return api_response(
            'success',
            'City retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        city = self.get_object(pk)
        if not city:
            return api_response(
                'error',
                'City not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CitySerializer(
            city,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'City updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        city = self.get_object(pk)
        if not city:
            return api_response(
                'error',
                'City not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        city.is_active = False
        city.save()
        return api_response(
            'success',
            'City deleted successfully'
        )


# ─── Zone Views ───────────────────────────────

class ZoneListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        zones = Zone.objects.filter(is_active=True)
        city_id = request.query_params.get('city')
        state_id = request.query_params.get('state')
        search = request.query_params.get('search')
        if city_id:
            zones = zones.filter(city__id=city_id)
        if state_id:
            zones = zones.filter(city__state__id=state_id)
        if search:
            zones = zones.filter(name__icontains=search)
        serializer = ZoneSerializer(zones, many=True)
        return api_response(
            'success',
            'Zones retrieved successfully',
            data={
                'count': zones.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = ZoneSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Zone created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ZoneDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return Zone.objects.get(pk=pk)
        except Zone.DoesNotExist:
            return None

    def get(self, request, pk):
        zone = self.get_object(pk)
        if not zone:
            return api_response(
                'error',
                'Zone not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ZoneSerializer(zone)
        return api_response(
            'success',
            'Zone retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        zone = self.get_object(pk)
        if not zone:
            return api_response(
                'error',
                'Zone not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ZoneSerializer(
            zone,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Zone updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        zone = self.get_object(pk)
        if not zone:
            return api_response(
                'error',
                'Zone not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        zone.is_active = False
        zone.save()
        return api_response(
            'success',
            'Zone deleted successfully'
        )


# ─── Address Views ───────────────────────────────

class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        serializer = AddressSerializer(addresses, many=True)
        return api_response(
            'success',
            'Addresses retrieved successfully',
            data={
                'count': addresses.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return api_response(
                'success',
                'Address added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Failed to add address',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Address.objects.get(pk=pk, user=user)
        except Address.DoesNotExist:
            return None

    def get(self, request, pk):
        address = self.get_object(pk, request.user)
        if not address:
            return api_response(
                'error',
                'Address not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = AddressSerializer(address)
        return api_response(
            'success',
            'Address retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        address = self.get_object(pk, request.user)
        if not address:
            return api_response(
                'error',
                'Address not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = AddressSerializer(
            address,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Address updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        address = self.get_object(pk, request.user)
        if not address:
            return api_response(
                'error',
                'Address not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        address.delete()
        return api_response(
            'success',
            'Address deleted successfully'
        )


class SetDefaultAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        address = Address.objects.filter(
            pk=pk,
            user=request.user
        ).first()
        if not address:
            return api_response(
                'error',
                'Address not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        # Remove default from all
        Address.objects.filter(
            user=request.user
        ).update(is_default=False)
        # Set this as default
        address.is_default = True
        address.save()
        return api_response(
            'success',
            'Default address updated',
            data=AddressSerializer(address).data
        )


class LocationHierarchyView(APIView):
    """
    Get full location hierarchy
    Country → States → Cities → Zones
    """
    permission_classes = []

    def get(self, request):
        country_id = request.query_params.get('country_id')
        state_id = request.query_params.get('state_id')
        city_id = request.query_params.get('city_id')

        if city_id:
            # Return zones for city
            zones = Zone.objects.filter(
                city__id=city_id,
                is_active=True
            )
            return api_response(
                'success',
                'Zones retrieved',
                data=ZoneSerializer(zones, many=True).data
            )

        elif state_id:
            # Return cities for state
            cities = City.objects.filter(
                state__id=state_id,
                is_active=True
            )
            return api_response(
                'success',
                'Cities retrieved',
                data=CitySerializer(cities, many=True).data
            )

        elif country_id:
            # Return states for country
            states = State.objects.filter(
                country__id=country_id,
                is_active=True
            )
            return api_response(
                'success',
                'States retrieved',
                data=StateSerializer(states, many=True).data
            )

        else:
            # Return all countries
            countries = Country.objects.filter(is_active=True)
            return api_response(
                'success',
                'Countries retrieved',
                data=CountrySerializer(countries, many=True).data
            )