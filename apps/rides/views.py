from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from apps.drivers.models import DriverProfile
from .utils import calculate_ride_fare, find_available_driver
from apps.common.email import send_ride_confirmation_email
from apps.common.ratelimit import AuthRateThrottle
from .models import (
    Ride, RideVehicleType, RideTracking,
    TransportVehicle, TransportRoute, TransportStop,
    TransportSchedule, ScheduleFare, TransportSeat,
    TransportBooking, TransportPassenger,
    TransportBoardingLog, TransportScheduleTracking,
    TransportCancellationPolicy, TransportBaggage,
    TransportRating,
)
from .serializers import (
    RideSerializer,
    RideVehicleTypeSerializer,
    RequestRideSerializer,
    RateRideSerializer,
    EstimateFareSerializer,
    TransportVehicleSerializer, TransportRouteSerializer,
    TransportScheduleSerializer, TransportBookingSerializer,
    TransportPassengerSerializer, TransportBoardingLogSerializer,
    TransportScheduleTrackingSerializer,
    TransportCancellationPolicySerializer,
    TransportBaggageSerializer, TransportRatingSerializer,
    BookTransportSerializer, SearchRouteSerializer,
    ScheduleFareSerializer, TransportSeatSerializer,
)
import uuid
from django.db import transaction
from django.utils import timezone



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
            
            # ── Send confirmation with start code + tracking link ──
            try:
                from apps.notifications.utils import send_notification
                tracking_url = f'/HOME/HTML/track.html?type=ride&id={ride.id}'
                send_notification(
                    user=request.user,
                    title='Ride Requested 🚗',
                    message=(
                        f'Your ride {ride.reference} has been requested. '
                        f'Give your driver this start code: {ride.start_code}. '
                        f'Track your ride: {tracking_url}'
                    ),
                    notification_type='system',
                    data={
                        'ride_id': ride.id,
                        'reference': ride.reference,
                        'start_code': ride.start_code,
                        'tracking_url': tracking_url,
                    },
                )
            except Exception:
                pass

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

        elif new_status == 'completed':
            ride.completed_at = timezone.now()
            ride.actual_fare = ride.estimated_fare
            ride.payment_status = 'paid' if ride.payment_method != 'cash' else 'unpaid'

            # ── Release escrow (non-cash rides) ──
            if ride.payment_method != 'cash':
                from apps.payments.escrow import release_escrow, EscrowTriggers
                release_escrow(
                    'ride', ride.id,
                    trigger=EscrowTriggers.RIDE_COMPLETED,
                    notes=f'Trip completed by driver {driver.user.email}',
                )

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



# ── Route search ──────────────────────────────────
class TransportRouteSearchView(APIView):
    """
    Search available routes and schedules.
    GET /api/v1/transport/routes/search/?origin=Lagos&destination=Abuja&date=2026-07-10&passengers=2
    """
    permission_classes = []

    def get(self, request):
        origin      = request.query_params.get('origin', '')
        destination = request.query_params.get('destination', '')
        date        = request.query_params.get('date')
        passengers  = int(request.query_params.get('passengers', 1))

        if not origin or not destination or not date:
            return api_response(
                'error', 'origin, destination and date are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        schedules = TransportSchedule.objects.filter(
            route__origin__icontains=origin,
            route__destination__icontains=destination,
            departure_date=date,
            status='scheduled',
            is_active=True,
        ).select_related('route', 'route__business', 'vehicle')

        # Filter by available seats
        available = [s for s in schedules if s.available_seats >= passengers]

        return api_response(
            'success', f'{len(available)} schedules found',
            data=TransportScheduleSerializer(available, many=True).data
        )


# ── Route list (for a business) ───────────────────
class TransportRouteListView(APIView):
    """
    GET  /api/v1/transport/routes/          ← all active routes
    POST /api/v1/transport/routes/          ← create route (business owner)
    """
    permission_classes = []

    def get(self, request):
        business_id = request.query_params.get('business_id')
        qs = TransportRoute.objects.filter(is_active=True)
        if business_id:
            qs = qs.filter(business_id=business_id)
        return api_response(
            'success', 'Routes retrieved',
            data=TransportRouteSerializer(qs, many=True).data
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        serializer = TransportRouteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Route created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


# ── Schedule list / create ────────────────────────
class TransportScheduleListView(APIView):
    """
    GET  /api/v1/transport/schedules/?route_id=1&date=2026-07-10
    POST /api/v1/transport/schedules/
    """
    permission_classes = []

    def get(self, request):
        qs = TransportSchedule.objects.filter(is_active=True)
        route_id = request.query_params.get('route_id')
        date     = request.query_params.get('date')
        if route_id: qs = qs.filter(route_id=route_id)
        if date:     qs = qs.filter(departure_date=date)
        return api_response('success', 'Schedules retrieved',
            data=TransportScheduleSerializer(qs, many=True).data)

    def post(self, request):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        serializer = TransportScheduleSerializer(data=request.data)
        if serializer.is_valid():
            schedule = serializer.save()
            # Auto-generate seats if total_seats provided
            if schedule.total_seats:
                TransportSeat.objects.bulk_create([
                    TransportSeat(
                        schedule=schedule,
                        seat_number=str(i + 1),
                        seat_class='economy',
                        status='available',
                    )
                    for i in range(schedule.total_seats)
                ])
            return api_response('success', 'Schedule created',
                data=TransportScheduleSerializer(schedule).data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


# ── Schedule detail ───────────────────────────────
class TransportScheduleDetailView(APIView):
    """
    GET   /api/v1/transport/schedules/<pk>/
    PATCH /api/v1/transport/schedules/<pk>/  ← update status
    """
    permission_classes = []

    def get(self, request, pk):
        try:
            schedule = TransportSchedule.objects.get(pk=pk)
        except TransportSchedule.DoesNotExist:
            return api_response('error', 'Schedule not found',
                http_status=status.HTTP_404_NOT_FOUND)
        return api_response('success', 'Schedule retrieved',
            data=TransportScheduleSerializer(schedule).data)

    def patch(self, request, pk):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        try:
            schedule = TransportSchedule.objects.get(pk=pk)
        except TransportSchedule.DoesNotExist:
            return api_response('error', 'Schedule not found',
                http_status=status.HTTP_404_NOT_FOUND)
        serializer = TransportScheduleSerializer(
            schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Schedule updated',
                data=serializer.data)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


# ── Book transport ────────────────────────────────
class BookTransportView(APIView):
    """
    POST /api/v1/transport/book/
    Body: { schedule_id, passengers: [{name, phone, seat_class, seat_id}], payment_method }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = BookTransportSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response('error', 'Validation failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get schedule
        try:
            schedule = TransportSchedule.objects.select_for_update().get(
                pk=data['schedule_id'])
        except TransportSchedule.DoesNotExist:
            return api_response('error', 'Schedule not found',
                http_status=status.HTTP_404_NOT_FOUND)

        # Check availability
        num_passengers = len(data['passengers'])
        if schedule.available_seats < num_passengers:
            return api_response('error',
                f'Only {schedule.available_seats} seats available',
                http_status=status.HTTP_400_BAD_REQUEST)

        # Calculate total
        total = 0
        for p in data['passengers']:
            seat_class = p.get('seat_class', 'economy')
            fare = schedule.fares.filter(
                seat_class=seat_class, is_active=True).first()
            p['amount'] = float(fare.price) if fare else 0
            total += p['amount']

        # Create booking
        booking = TransportBooking.objects.create(
            schedule=schedule,
            customer=request.user,
            reference=f"TRN-{uuid.uuid4().hex[:8].upper()}",
            total_amount=total,
            payment_method=data['payment_method'],
        )

        # Create passengers
        for p in data['passengers']:
            seat = None
            if p.get('seat_id'):
                try:
                    seat = TransportSeat.objects.select_for_update().get(
                        pk=p['seat_id'],
                        schedule=schedule,
                        status='available',
                    )
                    seat.status = 'booked'
                    seat.save()
                except TransportSeat.DoesNotExist:
                    pass

            passenger = TransportPassenger.objects.create(
                booking=booking,
                seat=seat,
                name=p['name'],
                phone=p.get('phone', ''),
                email=p.get('email', ''),
                seat_class=p.get('seat_class', 'economy'),
                amount=p['amount'],
            )
            passenger.generate_ticket_code()
        # ── Send ticket notification ──
        try:
            from apps.notifications.utils import send_notification
            tracking_url = f'/HOME/HTML/track.html?type=transport&ref={booking.reference}'
            ticket_codes = ', '.join(
                p.ticket_code for p in booking.passengers.all()
            )
            send_notification(
                user=request.user,
                title='Ticket Booked 🎫',
                message=(
                    f'Your transport booking {booking.reference} is confirmed. '
                    f'Ticket code(s): {ticket_codes}. '
                    f'Show at boarding. Track: {tracking_url}'
                ),
                notification_type='system',
                data={
                    'booking_id': booking.id,
                    'reference': booking.reference,
                    'ticket_codes': ticket_codes,
                    'tracking_url': tracking_url,
                },
            )
        except Exception:
            pass
        

        return api_response(
            'success', 'Booking created successfully',
            data=TransportBookingSerializer(booking).data,
            http_status=status.HTTP_201_CREATED
        )


# ── Customer booking list ─────────────────────────
class MyTransportBookingsView(APIView):
    """
    GET /api/v1/transport/my-bookings/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = TransportBooking.objects.filter(
            customer=request.user
        ).select_related('schedule', 'schedule__route')
        return api_response('success', 'Bookings retrieved',
            data=TransportBookingSerializer(bookings, many=True).data)


# ── Booking detail ────────────────────────────────
class TransportBookingDetailView(APIView):
    """
    GET    /api/v1/transport/bookings/<pk>/
    DELETE /api/v1/transport/bookings/<pk>/  ← cancel
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = TransportBooking.objects.get(
                pk=pk, customer=request.user)
        except TransportBooking.DoesNotExist:
            return api_response('error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND)
        return api_response('success', 'Booking retrieved',
            data=TransportBookingSerializer(booking).data)

    def delete(self, request, pk):
        try:
            booking = TransportBooking.objects.get(
                pk=pk, customer=request.user)
        except TransportBooking.DoesNotExist:
            return api_response('error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND)

        if booking.status not in ['pending', 'confirmed']:
            return api_response('error', 'Booking cannot be cancelled',
                http_status=status.HTTP_400_BAD_REQUEST)

        # Apply cancellation policy
        policy = TransportCancellationPolicy.objects.filter(
            business=booking.schedule.route.business
        ).order_by('-hours_before').first()

        refund_percent = 0
        if policy:
            hours_until = (
                timezone.datetime.combine(
                    booking.schedule.departure_date,
                    booking.schedule.departure_time
                ) - timezone.now()
            ).total_seconds() / 3600
            applicable = TransportCancellationPolicy.objects.filter(
                business=booking.schedule.route.business,
                hours_before__lte=hours_until
            ).order_by('-hours_before').first()
            if applicable:
                refund_percent = applicable.refund_percentage

        refund_amount = float(booking.total_amount) * float(refund_percent) / 100

        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = request.data.get('reason', '')
        booking.refund_amount = refund_amount
        booking.save()

        # Free up seats
        for passenger in booking.passengers.all():
            if passenger.seat:
                passenger.seat.status = 'available'
                passenger.seat.save()

        return api_response('success',
            f'Booking cancelled. Refund: ₦{refund_amount:.2f}',
            data={'refund_amount': refund_amount, 'refund_percent': refund_percent})


# ── Boarding scan ─────────────────────────────────
class TransportBoardingView(APIView):
    """
    POST /api/v1/transport/board/
    Body: { ticket_code, action: check_in|board }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ticket_code = request.data.get('ticket_code')
        action      = request.data.get('action', 'board')

        try:
            passenger = TransportPassenger.objects.get(
                ticket_code=ticket_code)
        except TransportPassenger.DoesNotExist:
            return api_response('error', 'Invalid ticket code',
                http_status=status.HTTP_404_NOT_FOUND)

        if passenger.booking.status != 'confirmed':
            return api_response('error', 'Booking not confirmed',
                http_status=status.HTTP_400_BAD_REQUEST)

        # Update boarding status
        status_map = {
            'check_in': 'checked_in',
            'board':    'boarded',
        }
        new_status = status_map.get(action, 'boarded')
        passenger.boarding_status = new_status
        if new_status == 'boarded':
            passenger.boarded_at = timezone.now()
        passenger.save()


        # Log
        TransportBoardingLog.objects.create(
            passenger=passenger,
            scanned_by=request.user,
            action=action,
        )
        # ── Release escrow on boarding ──
        from apps.payments.escrow import release_escrow, EscrowTriggers
        release_escrow(
            'transport', passenger.booking.id,
            trigger=EscrowTriggers.PASSENGER_BOARDED,
            notes=f'Passenger {passenger.full_name} boarded — ticket {passenger.ticket_code}',
        )

        return api_response('success',
            f'Passenger {new_status}',
            data=TransportPassengerSerializer(passenger).data)


# ── Schedule tracking ─────────────────────────────
class TransportTrackingView(APIView):
    """
    GET  /api/v1/transport/schedules/<pk>/tracking/
    POST /api/v1/transport/schedules/<pk>/tracking/
    """
    permission_classes = []

    def get(self, request, pk):
        tracking = TransportScheduleTracking.objects.filter(schedule_id=pk)
        return api_response('success', 'Tracking retrieved',
            data=TransportScheduleTrackingSerializer(tracking, many=True).data)

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        try:
            schedule = TransportSchedule.objects.get(pk=pk)
        except TransportSchedule.DoesNotExist:
            return api_response('error', 'Schedule not found',
                http_status=status.HTTP_404_NOT_FOUND)
        log = TransportScheduleTracking.objects.create(
            schedule=schedule,
            status=request.data.get('status', ''),
            description=request.data.get('description', ''),
            city=request.data.get('city', ''),
            reported_by=request.user,
        )
        return api_response('success', 'Tracking updated',
            data=TransportScheduleTrackingSerializer(log).data,
            http_status=status.HTTP_201_CREATED)


# ── Rate transport ────────────────────────────────
class TransportRatingView(APIView):
    """
    POST /api/v1/transport/bookings/<pk>/rate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = TransportBooking.objects.get(
                pk=pk, customer=request.user, status='completed')
        except TransportBooking.DoesNotExist:
            return api_response('error', 'Booking not found or not completed',
                http_status=status.HTTP_404_NOT_FOUND)

        if hasattr(booking, 'rating'):
            return api_response('error', 'Already rated',
                http_status=status.HTTP_400_BAD_REQUEST)

        rating = TransportRating.objects.create(
            booking=booking,
            overall_rating=request.data.get('overall_rating', 5),
            driver_rating=request.data.get('driver_rating'),
            vehicle_rating=request.data.get('vehicle_rating'),
            review=request.data.get('review', ''),
        )
        return api_response('success', 'Rating submitted',
            data=TransportRatingSerializer(rating).data,
            http_status=status.HTTP_201_CREATED)


# ── Business: manage vehicles ─────────────────────
class TransportVehicleView(APIView):
    """
    GET  /api/v1/transport/vehicles/?business_id=1
    POST /api/v1/transport/vehicles/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business_id = request.query_params.get('business_id')
        qs = TransportVehicle.objects.filter(is_active=True)
        if business_id:
            qs = qs.filter(business_id=business_id)
        return api_response('success', 'Vehicles retrieved',
            data=TransportVehicleSerializer(qs, many=True).data)

    def post(self, request):
        serializer = TransportVehicleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Vehicle added',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


# ── Cancellation policy ───────────────────────────
class TransportCancellationPolicyView(APIView):
    """
    GET  /api/v1/transport/cancellation-policy/?business_id=1
    POST /api/v1/transport/cancellation-policy/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business_id = request.query_params.get('business_id')
        qs = TransportCancellationPolicy.objects.all()
        if business_id:
            qs = qs.filter(business_id=business_id)
        return api_response('success', 'Policies retrieved',
            data=TransportCancellationPolicySerializer(qs, many=True).data)

    def post(self, request):
        serializer = TransportCancellationPolicySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Policy created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)

class VerifyRideStartView(APIView):
    """
    POST /api/v1/rides/<pk>/verify-start/
    Driver enters the customer's start code before beginning trip.
    Body: { "start_code": "A3F7" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from django.utils import timezone

        try:
            ride = Ride.objects.get(pk=pk)
        except Ride.DoesNotExist:
            return api_response('error', 'Ride not found',
                http_status=status.HTTP_404_NOT_FOUND)

        # Only the assigned driver can verify
        if not ride.driver or ride.driver.user != request.user:
            return api_response('error', 'Only the assigned driver can verify this ride',
                http_status=status.HTTP_403_FORBIDDEN)

        if ride.start_code_verified:
            return api_response('error', 'Ride already verified',
                http_status=status.HTTP_400_BAD_REQUEST)

        code = str(request.data.get('start_code', '')).strip().upper()
        if code != ride.start_code:
            return api_response('error', 'Invalid start code',
                http_status=status.HTTP_400_BAD_REQUEST)

        ride.start_code_verified = True
        ride.start_code_verified_at = timezone.now()
        ride.status = 'in_progress'
        ride.started_at = timezone.now()
        ride.save()

        RideTracking.objects.create(
            ride=ride,
            driver_lat=ride.driver_current_lat or 0,
            driver_lng=ride.driver_current_lng or 0,
            status='in_progress',
            description='Start code verified — trip started',
        )

        # Notify customer via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'ride_{ride.id}',
            {
                'type': 'ride_update',
                'status': 'in_progress',
                'driver_lat': str(ride.driver_current_lat) if ride.driver_current_lat else None,
                'driver_lng': str(ride.driver_current_lng) if ride.driver_current_lng else None,
                'message': 'Trip started — code verified',
            }
        )

        return api_response('success', 'Trip started', data={
            'ride_id': ride.id,
            'reference': ride.reference,
            'status': ride.status,
        })