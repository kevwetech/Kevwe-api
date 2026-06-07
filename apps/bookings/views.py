from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.common.views import api_response
from apps.common.permissions import IsAdmin, IsAdminOrReadOnly
from apps.common.utils import generate_reference
from .models import BookableItem, Booking
from .serializers import (
    BookableItemSerializer,
    BookingSerializer,
    CreateBookingSerializer,
)
from apps.notifications.utils import send_booking_notification
from .tracking import create_booking_tracking, get_booking_tracking_data
from apps.common.email import send_booking_confirmation_email


class BookableItemListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdmin()]

    def get(self, request):
        items = BookableItem.objects.filter(is_active=True)

        # Filter by type
        item_type = request.query_params.get('type')
        if item_type:
            items = items.filter(item_type=item_type)

        # Filter available only
        available = request.query_params.get('available')
        if available == 'true':
            items = items.filter(is_available=True)

        # Search
        search = request.query_params.get('search')
        if search:
            items = items.filter(name__icontains=search)

        serializer = BookableItemSerializer(
            items,
            many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Items retrieved successfully',
            data={
                'count': items.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = BookableItemSerializer(
            data=request.data,
            context={'request': request}
        )
        send_booking_confirmation_email(booking)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Item created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BookableItemDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdmin()]

    def get_object(self, pk):
        try:
            return BookableItem.objects.get(pk=pk, is_active=True)
        except BookableItem.DoesNotExist:
            return None

    def get(self, request, pk):
        item = self.get_object(pk)
        if not item:
            return api_response(
                'error',
                'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookableItemSerializer(
            item,
            context={'request': request}
        )
        return api_response(
            'success',
            'Item retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        item = self.get_object(pk)
        if not item:
            return api_response(
                'error',
                'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookableItemSerializer(
            item,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Item updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        item = self.get_object(pk)
        if not item:
            return api_response(
                'error',
                'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        item.is_active = False
        item.save()
        return api_response(
            'success',
            'Item deleted successfully'
        )


class BookingListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user)

        # Filter by status
        booking_status = request.query_params.get('status')
        if booking_status:
            bookings = bookings.filter(status=booking_status)

        serializer = BookingSerializer(bookings, many=True)
        return api_response(
            'success',
            'Bookings retrieved successfully',
            data={
                'count': bookings.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CreateBookingSerializer(data=request.data)
        if serializer.is_valid():
            item = BookableItem.objects.get(
                pk=serializer.validated_data['item_id']
            )
            check_in = serializer.validated_data['check_in']
            check_out = serializer.validated_data['check_out']

            # Check if item is already booked for these dates
            conflicting = Booking.objects.filter(
                item=item,
                status__in=['pending', 'confirmed', 'checked_in'],
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exists()

            if conflicting:
                return api_response(
                    'error',
                    'Item is not available for selected dates',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate duration and total
            duration = (check_out - check_in).days
            total = item.price_per_unit * duration

            booking = Booking.objects.create(
                user=request.user,
                item=item,
                reference=generate_reference('BKG'),
                check_in=check_in,
                check_out=check_out,
                duration=duration,
                guests=serializer.validated_data['guests'],
                guest_name=serializer.validated_data['guest_name'],
                guest_email=serializer.validated_data['guest_email'],
                guest_phone=serializer.validated_data['guest_phone'],
                special_requests=serializer.validated_data.get(
                    'special_requests', ''
                ),
                price_per_unit=item.price_per_unit,
                total=total
            )

            create_booking_tracking(
                booking=booking,
                status='pending',
                description='Booking request received'
            )

            send_booking_notification(
                user=request.user,
                booking=booking,
                notification_type='booking_confirmed'
            )

            return api_response(
                'success',
                'Booking created successfully',
                data=BookingSerializer(booking).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Booking failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Booking.objects.get(pk=pk, user=user)
        except Booking.DoesNotExist:
            return None

    def get(self, request, pk):
        booking = self.get_object(pk, request.user)
        if not booking:
            return api_response(
                'error',
                'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookingSerializer(booking)
        return api_response(
            'success',
            'Booking retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        booking = self.get_object(pk, request.user)
        if not booking:
            return api_response(
                'error',
                'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if booking.status != 'pending':
            return api_response(
                'error',
                'Only pending bookings can be cancelled',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'cancelled'
        booking.save()

        return api_response(
            'success',
            'Booking cancelled successfully',
            data=BookingSerializer(booking).data
        )


class AdminBookingListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        bookings = Booking.objects.all()

        # Filter by status
        booking_status = request.query_params.get('status')
        if booking_status:
            bookings = bookings.filter(status=booking_status)

        # Filter by item
        item_id = request.query_params.get('item')
        if item_id:
            bookings = bookings.filter(item__id=item_id)

        serializer = BookingSerializer(bookings, many=True)
        return api_response(
            'success',
            'All bookings retrieved',
            data={
                'count': bookings.count(),
                'results': serializer.data
            }
        )


class AdminBookingUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return api_response(
                'error',
                'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        payment_status = request.data.get('payment_status')

        if new_status:
            booking.status = new_status
        if payment_status:
            booking.payment_status = payment_status

        booking.save()

        create_booking_tracking(
            booking=booking,
            status=new_status
        )

        return api_response(
            'success',
            'Booking updated successfully',
            data=BookingSerializer(booking).data
        )


class BookingTrackingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return api_response(
                'error',
                'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        tracking_data = get_booking_tracking_data(booking)
        return api_response(
            'success',
            'Booking tracking retrieved successfully',
            data=tracking_data
        )