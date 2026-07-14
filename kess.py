# ═══════════════════════════════════════════════════════════
# NEW SERIALIZERS
# ═══════════════════════════════════════════════════════════

# ── ADD to apps/rides/serializers.py ──────────────────────
# (after existing RideVehicleTypeSerializer)

class RideVehicleTypeSerializer(serializers.ModelSerializer):
    """Updated — add business + vehicle_category fields"""
    business_name = serializers.CharField(
        source='business.name', read_only=True)

    class Meta:
        model = RideVehicleType
        fields = (
            'id', 'business', 'business_name', 'vehicle_category',
            'name', 'description', 'base_fare', 'per_km_rate',
            'per_minute_rate', 'minimum_fare', 'max_passengers',
            'icon', 'is_active',
        )
        read_only_fields = ('id',)


class TransportRouteListSerializer(serializers.ModelSerializer):
    """Lightweight route list (no nested stops/schedules)"""
    business_name = serializers.CharField(
        source='business.name', read_only=True)
    stops_count = serializers.SerializerMethodField()

    class Meta:
        model = TransportRoute
        fields = (
            'id', 'business', 'business_name', 'name', 'route_code',
            'transport_type', 'origin', 'destination',
            'distance_km', 'estimated_duration_minutes',
            'amenities', 'is_active', 'is_return_available',
            'stops_count',
        )

    def get_stops_count(self, obj):
        return obj.stops.count()


# ── ADD to apps/shipments/serializers.py ──────────────────

class ShipmentVehicleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentVehicleCategory
        fields = (
            'id', 'transport_mode', 'name', 'slug', 'description',
            'icon', 'max_weight_kg', 'is_active', 'order',
        )


class ShipmentVehicleTypeSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name', read_only=True)
    category_name = serializers.CharField(
        source='category.name', read_only=True)
    transport_mode = serializers.CharField(
        source='category.transport_mode', read_only=True)

    class Meta:
        model = ShipmentVehicleType
        fields = (
            'id', 'business', 'business_name', 'category',
            'category_name', 'transport_mode', 'name', 'description',
            'max_weight_kg', 'base_fare', 'per_km_rate',
            'icon', 'is_active', 'order',
        )
        read_only_fields = ('id',)


class ShipmentServiceCategorySerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source='business.name', read_only=True)

    class Meta:
        model = ShipmentServiceCategory
        fields = (
            'id', 'business', 'business_name', 'name', 'slug',
            'description', 'icon',
            'estimated_days_min', 'estimated_days_max',
            'is_active', 'order',
        )
        read_only_fields = ('id', 'slug')


# ═══════════════════════════════════════════════════════════
# NEW VIEWS
# ═══════════════════════════════════════════════════════════

# ── ADD to apps/rides/views.py ────────────────────────────
# Replace VehicleTypeListView with this (same URL, extended):

class VehicleTypeListView(APIView):
    """
    GET  /api/v1/rides/vehicle-types/
         ?business_id=N → that business's types + platform defaults
         (no business_id) → platform-wide types only
    POST /api/v1/rides/vehicle-types/ (business owner or admin)
         Body: { business, vehicle_category, name, base_fare, ... }
    """
    permission_classes = []

    def get(self, request):
        business_id = request.query_params.get('business_id')
        if business_id:
            # platform defaults + this business's custom types
            from django.db.models import Q
            vehicle_types = RideVehicleType.objects.filter(
                Q(business__isnull=True) | Q(business_id=business_id),
                is_active=True,
            )
        else:
            vehicle_types = RideVehicleType.objects.filter(
                is_active=True, business__isnull=True)

        serializer = RideVehicleTypeSerializer(
            vehicle_types, many=True, context={'request': request})
        return api_response('success', 'Vehicle types retrieved',
            data={'count': vehicle_types.count(), 'results': serializer.data})

    def post(self, request):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)

        business_id = request.data.get('business')
        if business_id:
            from apps.marketplace.models import Business
            try:
                business = Business.objects.get(
                    pk=business_id, owner=request.user)
            except Business.DoesNotExist:
                return api_response('error', 'Business not found or not yours',
                    http_status=status.HTTP_403_FORBIDDEN)

        serializer = RideVehicleTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Vehicle type created',
                data=serializer.data, http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


class VehicleTypeDetailView(APIView):
    """
    GET/PATCH/DELETE /api/v1/rides/vehicle-types/<pk>/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return RideVehicleType.objects.get(pk=pk)
        except RideVehicleType.DoesNotExist:
            return None

    def get(self, request, pk):
        vt = self.get_object(pk)
        if not vt:
            return api_response('error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND)
        return api_response('success', 'Vehicle type retrieved',
            data=RideVehicleTypeSerializer(vt).data)

    def patch(self, request, pk):
        vt = self.get_object(pk)
        if not vt:
            return api_response('error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND)
        if vt.business and vt.business.owner != request.user:
            return api_response('error', 'Not your business',
                http_status=status.HTTP_403_FORBIDDEN)
        serializer = RideVehicleTypeSerializer(
            vt, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Updated',
                data=serializer.data)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        vt = self.get_object(pk)
        if not vt:
            return api_response('error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND)
        if vt.business and vt.business.owner != request.user:
            return api_response('error', 'Not your business',
                http_status=status.HTTP_403_FORBIDDEN)
        if not vt.business:
            return api_response('error',
                'Cannot delete platform-wide vehicle types',
                http_status=status.HTTP_403_FORBIDDEN)
        vt.delete()
        return api_response('success', 'Deleted',
            http_status=status.HTTP_204_NO_CONTENT)


# Transport routes CRUD (business already has business FK)
class TransportRouteCreateView(APIView):
    """
    POST /api/v1/rides/routes/
    Body: { business, name, origin, destination, distance_km,
            estimated_duration_minutes, transport_type, amenities }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.marketplace.models import Business
        business_id = request.data.get('business')
        try:
            business = Business.objects.get(
                pk=business_id, owner=request.user)
        except Business.DoesNotExist:
            return api_response('error', 'Business not found or not yours',
                http_status=status.HTTP_403_FORBIDDEN)

        serializer = TransportRouteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(business=business)
            return api_response('success', 'Route created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


class TransportRouteDetailView(APIView):
    """
    GET/PATCH/DELETE /api/v1/rides/routes/<pk>/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return TransportRoute.objects.get(pk=pk)
        except TransportRoute.DoesNotExist:
            return None

    def get(self, request, pk):
        route = self.get_object(pk)
        if not route:
            return api_response('error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND)
        return api_response('success', 'Route retrieved',
            data=TransportRouteSerializer(route).data)

    def patch(self, request, pk):
        route = self.get_object(pk)
        if not route:
            return api_response('error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND)
        if route.business.owner != request.user:
            return api_response('error', 'Not your business',
                http_status=status.HTTP_403_FORBIDDEN)
        serializer = TransportRouteSerializer(
            route, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Route updated',
                data=serializer.data)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        route = self.get_object(pk)
        if not route:
            return api_response('error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND)
        if route.business.owner != request.user:
            return api_response('error', 'Not your business',
                http_status=status.HTTP_403_FORBIDDEN)
        route.delete()
        return api_response('success', 'Route deleted',
            http_status=status.HTTP_204_NO_CONTENT)


# ── ADD to apps/shipments/views.py ────────────────────────



# ═══════════════════════════════════════════════════════════
# NEW URL PATTERNS
# ═══════════════════════════════════════════════════════════

# ── ADD to apps/rides/urls.py ─────────────────────────────
# (keep existing vehicle-types/ URL, add detail + routes)

path('vehicle-types/<int:pk>/', VehicleTypeDetailView.as_view(), name='vehicle_type_detail'),
path('routes/', TransportRouteCreateView.as_view(), name='transport_route_create'),
path('routes/<int:pk>/', TransportRouteDetailView.as_view(), name='transport_route_detail'),

# ── ADD to apps/shipments/urls.py ─────────────────────────

path('vehicle-categories/', ShipmentVehicleCategoryListView.as_view(), name='shipment_vehicle_categories'),
path('vehicle-types/', ShipmentVehicleTypeListCreateView.as_view(), name='shipment_vehicle_types'),
path('vehicle-types/<int:pk>/', ShipmentVehicleTypeDetailView.as_view(), name='shipment_vehicle_type_detail'),
path('service-categories/', ShipmentServiceCategoryListCreateView.as_view(), name='shipment_service_categories'),
path('service-categories/<int:pk>/', ShipmentServiceCategoryDetailView.as_view(), name='shipment_service_category_detail'),