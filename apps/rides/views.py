from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from apps.drivers.models import DriverProfile
from .models import Ride, RideVehicleType, RideTracking
from .serializers import (
    RideSerializer,
    RideVehicleTypeSerializer,
    RequestRideSerializer,
    RateRideSerializer,
    EstimateFareSerializer,
)
from .utils import calculate_ride_fare, find_available_driver
from apps.common.email import send_ride_confirmation_email
from apps.common.ratelimit import AuthRateThrottle


class VehicleTypeListView(APIView):
    """List available vehicle types"""
    permission_classes = []

    def get(self, request):
        vehicle_types = RideVehicleType.objects.filter(
            is_active=True
        )
        serializer = RideVehicleTypeSerializer(
            vehicle_types,
            many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Vehicle types retrieved successfully',
            data={
                'count': vehicle_types.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Admin create vehicle type"""
        serializer = RideVehicleTypeSerializer(data=request.data)
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


class EstimateFareView(APIView):
    """Estimate ride fare before requesting"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = EstimateFareSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            vehicle_types = RideVehicleType.objects.filter(
                is_active=True
            )

            estimates = []
            for vtype in vehicle_types:
                fare_data = calculate_ride_fare(
                    data['pickup_lat'],
                    data['pickup_lng'],
                    data['destination_lat'],
                    data['destination_lng'],
                    vehicle_type=vtype
                )
                estimates.append({
                    'vehicle_type_id': vtype.id,
                    'vehicle_type_name': vtype.name,
                    'distance_km': fare_data['distance_km'],
                    'duration_minutes': fare_data['duration_minutes'],
                    'estimated_fare': fare_data['estimated_fare'],
                    'max_passengers': vtype.max_passengers,
                })

            return api_response(
                'success',
                'Fare estimates retrieved successfully',
                data={
                    'estimates': estimates
                }
            )

        return api_response(
            'error',
            'Estimation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class RequestRideView(APIView):
    """Request a new ride"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    def post(self, request):
        serializer = RequestRideSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Get vehicle type
            vehicle_type = None
            if data.get('vehicle_type_id'):
                try:
                    vehicle_type = RideVehicleType.objects.get(
                        pk=data['vehicle_type_id'],
                        is_active=True
                    )
                except RideVehicleType.DoesNotExist:
                    return api_response(
                        'error',
                        'Vehicle type not found',
                        http_status=status.HTTP_404_NOT_FOUND
                    )

            # Calculate fare
            fare_data = calculate_ride_fare(
                data['pickup_lat'],
                data['pickup_lng'],
                data['destination_lat'],
                data['destination_lng'],
                vehicle_type=vehicle_type
            )

            # Find nearest driver
            driver = find_available_driver(
                data['pickup_lat'],
                data['pickup_lng'],
                vehicle_type=vehicle_type
            )

            # Create ride
            ride = Ride.objects.create(
                rider=request.user,
                driver=driver,
                vehicle_type=vehicle_type,
                reference=generate_reference('RID'),
                pickup_address=data['pickup_address'],
                pickup_lat=data['pickup_lat'],
                pickup_lng=data['pickup_lng'],
                destination_address=data['destination_address'],
                destination_lat=data['destination_lat'],
                destination_lng=data['destination_lng'],
                estimated_fare=fare_data['estimated_fare'],
                distance_km=fare_data['distance_km'],
                duration_minutes=fare_data['duration_minutes'],
                payment_method=data.get('payment_method', 'cash'),
                status='accepted' if driver else 'searching',
            )

            if driver:
                ride.accepted_at = timezone.now()
                ride.save()

                # Create tracking entry
                RideTracking.objects.create(
                    ride=ride,
                    driver_lat=driver.current_lat or 0,
                    driver_lng=driver.current_lng or 0,
                    status='accepted',
                    description=f'Driver {driver.user.full_name} accepted your ride'
                )

                # Notify driver via WebSocket
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync

                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'driver_rides_{driver.id}',
                        {
                            'type': 'ride_request',
                            'ride_id': ride.id,
                            'reference': ride.reference,
                            'pickup_address': ride.pickup_address,
                            'pickup_lat': str(ride.pickup_lat),
                            'pickup_lng': str(ride.pickup_lng),
                            'destination_address': ride.destination_address,
                            'estimated_fare': str(ride.estimated_fare),
                            'rider_name': request.user.full_name,
                        }
                    )

                except Exception:
                    pass

                send_ride_confirmation_email(ride)
                

            return api_response(
                'success',
                'Ride requested successfully' if driver else 'Searching for driver...',
                data=RideSerializer(ride).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Ride request failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class RideDetailView(APIView):
    """Get ride details"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        try:
            return Ride.objects.get(pk=pk, rider=user)
        except Ride.DoesNotExist:
            return None

    def get(self, request, pk):
        ride = self.get_object(pk, request.user)
        if not ride:
            return api_response(
                'error',
                'Ride not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = RideSerializer(ride)
        return api_response(
            'success',
            'Ride retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        """Cancel a ride"""
        ride = self.get_object(pk, request.user)
        if not ride:
            return api_response(
                'error',
                'Ride not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if ride.status not in ['requested', 'searching', 'accepted']:
            return api_response(
                'error',
                'This ride cannot be cancelled',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        ride.status = 'cancelled'
        ride.save()

        return api_response(
            'success',
            'Ride cancelled successfully',
            data=RideSerializer(ride).data
        )


class RideListView(APIView):
    """List rider's rides"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rides = Ride.objects.filter(rider=request.user)

        ride_status = request.query_params.get('status')
        if ride_status:
            rides = rides.filter(status=ride_status)

        serializer = RideSerializer(rides, many=True)
        return api_response(
            'success',
            'Rides retrieved successfully',
            data={
                'count': rides.count(),
                'results': serializer.data
            }
        )


class RateRideView(APIView):
    """Rate a completed ride"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            ride = Ride.objects.get(pk=pk, rider=request.user)
        except Ride.DoesNotExist:
            return api_response(
                'error',
                'Ride not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if ride.status != 'completed':
            return api_response(
                'error',
                'Only completed rides can be rated',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if ride.rider_rating:
            return api_response(
                'error',
                'You have already rated this ride',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RateRideSerializer(data=request.data)
        if serializer.is_valid():
            ride.rider_rating = serializer.validated_data['rating']
            ride.rider_review = serializer.validated_data.get('review', '')
            ride.save()

            # Update driver rating
            if ride.driver:
                driver = ride.driver
                total = driver.total_ratings
                current_rating = float(driver.rating)
                new_rating = (
                    (current_rating * total) +
                    serializer.validated_data['rating']
                ) / (total + 1)
                driver.rating = round(new_rating, 2)
                driver.total_ratings += 1
                driver.save()

            return api_response(
                'success',
                'Ride rated successfully',
                data=RideSerializer(ride).data
            )

        return api_response(
            'error',
            'Rating failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class DriverRideView(APIView):
    """Driver ride management"""
    permission_classes = [IsAuthenticated]

    def get_driver(self, user):
        try:
            return user.driver_profile
        except Exception:
            return None

    def get(self, request):
        """Get driver's rides"""
        driver = self.get_driver(request.user)
        if not driver:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        rides = Ride.objects.filter(driver=driver)
        ride_status = request.query_params.get('status')
        if ride_status:
            rides = rides.filter(status=ride_status)

        serializer = RideSerializer(rides, many=True)
        return api_response(
            'success',
            'Rides retrieved successfully',
            data={
                'count': rides.count(),
                'results': serializer.data
            }
        )

    def patch(self, request, pk):
        """Update ride status as driver"""
        driver = self.get_driver(request.user)
        if not driver:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        try:
            ride = Ride.objects.get(pk=pk, driver=driver)
        except Ride.DoesNotExist:
            return api_response(
                'error',
                'Ride not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        driver_lat = request.data.get('driver_lat')
        driver_lng = request.data.get('driver_lng')

        valid_transitions = {
            'accepted': 'driver_arriving',
            'driver_arriving': 'in_progress',
            'in_progress': 'completed',
        }

        if new_status not in valid_transitions.values():
            return api_response(
                'error',
                'Invalid status transition',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        ride.status = new_status

        if new_status == 'in_progress':
            ride.started_at = timezone.now()
        elif new_status == 'completed':
            ride.completed_at = timezone.now()
            ride.actual_fare = ride.estimated_fare
            ride.payment_status = 'paid' if ride.payment_method != 'cash' else 'unpaid'

            # Update driver stats
            driver.total_rides += 1
            driver.save()

        if driver_lat and driver_lng:
            ride.driver_current_lat = driver_lat
            ride.driver_current_lng = driver_lng

        ride.save()

        # Create tracking entry
        if driver_lat and driver_lng:
            RideTracking.objects.create(
                ride=ride,
                driver_lat=driver_lat,
                driver_lng=driver_lng,
                status=new_status,
                description=f'Status updated to {new_status}'
            )

        # Broadcast to rider via WebSocket
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'ride_{ride.id}',
                {
                    'type': 'ride_update',
                    'status': new_status,
                    'driver_lat': str(driver_lat) if driver_lat else None,
                    'driver_lng': str(driver_lng) if driver_lng else None,
                    'message': f'Ride status updated to {new_status}',
                    'timestamp': str(timezone.now()),
                }
            )
        except Exception:
            pass

        return api_response(
            'success',
            'Ride updated successfully',
            data=RideSerializer(ride).data
        )


class AdminRideListView(APIView):
    """Admin - list all rides"""
    permission_classes = [IsAdmin]

    def get(self, request):
        rides = Ride.objects.all()

        ride_status = request.query_params.get('status')
        if ride_status:
            rides = rides.filter(status=ride_status)

        serializer = RideSerializer(rides, many=True)
        return api_response(
            'success',
            'All rides retrieved',
            data={
                'count': rides.count(),
                'results': serializer.data
            }
        )