from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import DriverProfile, Vehicle, DriverDocument, DriverEarnings,VehicleType
from .serializers import (
    DriverProfileSerializer,
    CreateDriverProfileSerializer,
    VehicleSerializer,
    DriverDocumentSerializer,
    DriverEarningsSerializer,
    UpdateLocationSerializer,
    NearbyDriversSerializer,
    VehicleTypeSerializer,
)
from .utils import find_nearby_drivers, calculate_distance
from apps.common.ratelimit import AuthRateThrottle




class RegisterDriverView(APIView):
    """Register as a driver"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if already a driver
        if hasattr(request.user, 'driver_profile'):
            return api_response(
                'error',
                'You are already registered as a driver',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CreateDriverProfileSerializer(data=request.data)
        if serializer.is_valid():
            driver = serializer.save(user=request.user)
            return api_response(
                'success',
                'Driver registration successful. Pending verification.',
                data=DriverProfileSerializer(driver).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Registration failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )



class VehicleTypeListCreateView(APIView):
    """
    GET  - List all vehicle types (public)
    POST - Create vehicle type (admin only)
    """
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        vehicle_types = VehicleType.objects.filter(is_active=True)
        serializer = VehicleTypeSerializer(vehicle_types, many=True)
        return api_response(
            'success',
            'Vehicle types retrieved successfully',
            data={
                'count': vehicle_types.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = VehicleTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Vehicle type created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VehicleTypeDetailView(APIView):
    """
    GET    - Get single vehicle type
    PATCH  - Update vehicle type (admin)
    DELETE - Delete vehicle type (admin)
    """
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return VehicleType.objects.get(pk=pk)
        except VehicleType.DoesNotExist:
            return None

    def get(self, request, pk):
        vehicle_type = self.get_object(pk)
        if not vehicle_type:
            return api_response(
                'error',
                'Vehicle type not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = VehicleTypeSerializer(vehicle_type)
        return api_response(
            'success',
            'Vehicle type retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        vehicle_type = self.get_object(pk)
        if not vehicle_type:
            return api_response(
                'error',
                'Vehicle type not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = VehicleTypeSerializer(
            vehicle_type,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Vehicle type updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        vehicle_type = self.get_object(pk)
        if not vehicle_type:
            return api_response(
                'error',
                'Vehicle type not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        vehicle_type.is_active = False
        vehicle_type.save()
        return api_response(
            'success',
            'Vehicle type deleted successfully'
        )


class DriverProfileView(APIView):
    """Get and update driver profile"""
    permission_classes = [IsAuthenticated]

    def get_driver(self, user):
        try:
            return user.driver_profile
        except DriverProfile.DoesNotExist:
            return None

    def get(self, request):
        driver = self.get_driver(request.user)
        if not driver:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = DriverProfileSerializer(driver)
        return api_response(
            'success',
            'Driver profile retrieved successfully',
            data=serializer.data
        )

    def patch(self, request):
        driver = self.get_driver(request.user)
        if not driver:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = DriverProfileSerializer(
            driver,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Driver profile updated successfully',
                data=serializer.data
            )

        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class DriverAvailabilityView(APIView):
    """Toggle driver availability"""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if not driver.is_verified:
            return api_response(
                'error',
                'Your profile is not verified yet',
                http_status=status.HTTP_403_FORBIDDEN
            )

        is_available = request.data.get('is_available')
        is_online = request.data.get('is_online')

        if is_available is not None:
            driver.is_available = is_available
        if is_online is not None:
            driver.is_online = is_online

        driver.save()

        return api_response(
            'success',
            'Availability updated successfully',
            data={
                'is_available': driver.is_available,
                'is_online': driver.is_online,
            }
        )


class UpdateLocationView(APIView):
    """Update driver current location"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateLocationSerializer(data=request.data)
        if serializer.is_valid():
            driver.current_lat = serializer.validated_data['latitude']
            driver.current_lng = serializer.validated_data['longitude']
            driver.last_location_update = timezone.now()
            driver.save()

            # Check if driver has arrived at any pickup point
            try:
                from apps.deliveries.utils import check_pickup_arrival
                check_pickup_arrival(driver)
            except Exception as e:
                print(f"Pickup arrival check error: {e}")

            # Check if driver is approaching/arrived at dropoff
            try:
                from apps.deliveries.utils import check_dropoff_proximity
                check_dropoff_proximity(driver)
            except Exception as e:
                print(f"Dropoff proximity check error: {e}")

            return api_response(
                'success',
                'Location updated successfully',
                data={
                    'latitude': str(driver.current_lat),
                    'longitude': str(driver.current_lng),
                    'updated_at': driver.last_location_update,
                }
            )

        return api_response(
            'error',
            'Location update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VehicleListCreateView(APIView):
    """Manage driver vehicles"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        vehicles = Vehicle.objects.filter(
            driver=request.user,
            is_active=True
        )
        serializer = VehicleSerializer(vehicles, many=True)
        return api_response(
            'success',
            'Vehicles retrieved successfully',
            data={
                'count': vehicles.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = VehicleSerializer(data=request.data)
        if serializer.is_valid():
            vehicle = serializer.save(driver=request.user)

            # Set as active vehicle if no active vehicle
            if not driver.active_vehicle:
                driver.active_vehicle = vehicle
                driver.save()

            return api_response(
                'success',
                'Vehicle added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Failed to add vehicle',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class VehicleDetailView(APIView):
    """Get, update and delete a vehicle"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Vehicle.objects.get(pk=pk, driver=user)
        except Vehicle.DoesNotExist:
            return None

    def get(self, request, pk):
        vehicle = self.get_object(pk, request.user)
        if not vehicle:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = VehicleSerializer(vehicle)
        return api_response(
            'success',
            'Vehicle retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        vehicle = self.get_object(pk, request.user)
        if not vehicle:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = VehicleSerializer(
            vehicle,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Vehicle updated successfully',
                data=serializer.data
            )

        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        vehicle = self.get_object(pk, request.user)
        if not vehicle:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        vehicle.is_active = False
        vehicle.save()
        return api_response(
            'success',
            'Vehicle removed successfully'
        )


class SetActiveVehicleView(APIView):
    """Set active vehicle for driver"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        try:
            vehicle = Vehicle.objects.get(
                pk=pk,
                driver=request.user,
                is_active=True
            )
        except Vehicle.DoesNotExist:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        driver.active_vehicle = vehicle
        driver.save()

        return api_response(
            'success',
            'Active vehicle updated successfully',
            data=VehicleSerializer(vehicle).data
        )


class DriverDocumentView(APIView):
    """Upload and manage driver documents"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        documents = DriverDocument.objects.filter(driver=driver)
        serializer = DriverDocumentSerializer(documents, many=True)
        return api_response(
            'success',
            'Documents retrieved successfully',
            data={
                'count': documents.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = DriverDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(driver=driver)
            return api_response(
                'success',
                'Document uploaded successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Upload failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class DriverEarningsView(APIView):
    """Get driver earnings"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            driver = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        earnings = DriverEarnings.objects.filter(driver=driver)

        total_earned = sum(
            e.amount for e in earnings
            if e.earning_type != 'penalty'
        )
        total_penalties = sum(
            e.amount for e in earnings
            if e.earning_type == 'penalty'
        )
        total_paid = sum(
            e.amount for e in earnings
            if e.is_paid and e.earning_type != 'penalty'
        )
        total_pending = total_earned - total_paid

        serializer = DriverEarningsSerializer(earnings, many=True)
        return api_response(
            'success',
            'Earnings retrieved successfully',
            data={
                'summary': {
                    'total_earned': str(total_earned),
                    'total_paid': str(total_paid),
                    'total_pending': str(total_pending),
                    'total_penalties': str(total_penalties),
                },
                'count': earnings.count(),
                'results': serializer.data
            }
        )


class NearbyDriversView(APIView):
    """Find nearby available drivers"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    
    def post(self, request):
        serializer = NearbyDriversSerializer(data=request.data)
        if serializer.is_valid():
            lat = serializer.validated_data['latitude']
            lng = serializer.validated_data['longitude']
            radius = serializer.validated_data['radius_km']
            vehicle_type = request.data.get('vehicle_type')

            nearby = find_nearby_drivers(
                lat, lng,
                radius_km=float(radius),
                vehicle_type=vehicle_type
            )

            results = [
                {
                    'driver_id': item['driver'].id,
                    'full_name': item['driver'].user.full_name,
                    'rating': str(item['driver'].rating),
                    'vehicle': VehicleSerializer(
                        item['driver'].active_vehicle
                    ).data if item['driver'].active_vehicle else None,
                    'distance_km': item['distance_km'],
                    'eta_minutes': item['eta_minutes'],
                    'current_lat': str(item['driver'].current_lat),
                    'current_lng': str(item['driver'].current_lng),
                }
                for item in nearby
            ]

            return api_response(
                'success',
                f'Found {len(results)} nearby drivers',
                data={
                    'count': len(results),
                    'results': results
                }
            )

        return api_response(
            'error',
            'Search failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AdminDriverListView(APIView):
    """Admin - list all drivers"""
    permission_classes = [IsAdmin]

    def get(self, request):
        drivers = DriverProfile.objects.all()

        # Filter by status
        driver_status = request.query_params.get('status')
        if driver_status:
            drivers = drivers.filter(status=driver_status)

        # Filter by availability
        is_available = request.query_params.get('is_available')
        if is_available:
            drivers = drivers.filter(
                is_available=is_available == 'true'
            )

        serializer = DriverProfileSerializer(drivers, many=True)
        return api_response(
            'success',
            'Drivers retrieved successfully',
            data={
                'count': drivers.count(),
                'results': serializer.data
            }
        )


class AdminDriverVerifyView(APIView):
    """Admin - verify or reject driver"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            driver = DriverProfile.objects.get(pk=pk)
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if new_status not in ['verified', 'rejected', 'suspended']:
            return api_response(
                'error',
                'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        driver.status = new_status
        driver.save()

        return api_response(
            'success',
            f'Driver {new_status} successfully',
            data=DriverProfileSerializer(driver).data
        )