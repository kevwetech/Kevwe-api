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
from apps.marketplace.models import Business
from apps.drivers.utils import calculate_distance


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

class NearbyBusinessesView(APIView):
    """
    Discover businesses in a city.
    GPS coordinates auto-detect the city.
    Manual city_id as fallback.
    Filterable by industry and search term.

    GET /api/v1/locations/discover/
        ?lat=5.8904&lng=5.6801      (GPS)
        ?city_id=1                   (manual)
        &industry_id=1               (optional filter)
        &search=pizza                (optional search)
    """
    permission_classes = []

    def get(self, request):
        from apps.marketplace.models import Business, Industry
        from apps.drivers.utils import calculate_distance

        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        city_id = request.query_params.get('city_id')
        industry_id = request.query_params.get('industry_id')
        search = request.query_params.get('search', '').strip()

        detected_city = None
        detected_city_name = None

        # ── GPS: find closest city ──
        if lat and lng:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                cities = City.objects.filter(
                    latitude__isnull=False,
                    longitude__isnull=False,
                )
                closest = None
                closest_dist = float('inf')

                for city in cities:
                    dist = calculate_distance(
                        lat_f, lng_f,
                        float(city.latitude),
                        float(city.longitude),
                    )
                    if dist < closest_dist:
                        closest_dist = dist
                        closest = city

                if closest:
                    detected_city = closest
                    detected_city_name = closest.name

            except Exception as e:
                print(f"GPS city detection error: {e}")

        # ── Manual fallback ──
        if not detected_city and city_id:
            try:
                detected_city = City.objects.get(pk=city_id)
                detected_city_name = detected_city.name
            except City.DoesNotExist:
                return api_response(
                    'error',
                    'City not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

        if not detected_city:
            return api_response(
                'error',
                'Please provide lat/lng or city_id',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # ── Query businesses in detected city ──
        businesses = Business.objects.filter(
            city=detected_city,
            is_active=True,
            is_verified=True,
        )

        if industry_id:
            businesses = businesses.filter(
                industry__id=industry_id
            )

        if search:
            businesses = businesses.filter(
                name__icontains=search
            )

        businesses = businesses.order_by('-rating', 'name')

        # ── Build response ──
        results = []
        for biz in businesses:
            dist_km = None
            if lat and lng:
                try:
                    dist_km = round(calculate_distance(
                        float(lat), float(lng),
                        float(biz.latitude),
                        float(biz.longitude),
                    ), 2) if biz.latitude and biz.longitude else None
                except Exception:
                    pass

            results.append({
                'id': biz.id,
                'name': biz.name,
                'slug': biz.slug,
                'logo': (
                    request.build_absolute_uri(biz.logo.url)
                    if biz.logo else None
                ),
                'cover_image': (
                    request.build_absolute_uri(biz.cover_image.url)
                    if biz.cover_image else None
                ),
                'industry': biz.industry.name,
                'industry_id': biz.industry.id,
                'address': biz.address,
                'city': detected_city_name,
                'rating': str(biz.rating),
                'total_ratings': biz.total_ratings,
                'distance_km': dist_km,
                'is_open': getattr(biz, 'is_open', None),
                'phone': biz.phone,
            })

        # Sort by distance if GPS was provided
        if lat and lng:
            results.sort(
                key=lambda x: x['distance_km']
                if x['distance_km'] is not None
                else float('inf')
            )

        # Get available industries in this city for filter UI
        industries_in_city = Industry.objects.filter(
            businesses__city=detected_city,
            businesses__is_active=True,
        ).distinct().values('id', 'name', 'slug')

        return api_response(
            'success',
            f'Found {len(results)} businesses in '
            f'{detected_city_name}',
            data={
                'detected_city': {
                    'id': detected_city.id,
                    'name': detected_city_name,
                    'state': detected_city.state.name
                    if detected_city.state else None,
                },
                'filters_applied': {
                    'industry_id': industry_id,
                    'search': search or None,
                },
                'available_industries': list(
                    industries_in_city
                ),
                'count': len(results),
                'results': results,
            }
        )