from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from apps.drivers.models import DriverProfile
from .models import Shipment, ShipmentTracking
from apps.common.email import send_shipment_confirmation_email
from apps.common.logistics_pricing import calculate_logistics_price
from apps.drivers.utils import calculate_distance
from apps.wallet.utils import get_or_create_wallet
from apps.common.utils import generate_reference
from decimal import Decimal
from apps.locations.models import City, State, Zone, Address
from apps.common.logistics_pricing import calculate_logistics_price
from apps.drivers.utils import calculate_distance
from apps.common.utils import generate_reference
from apps.wallet.utils import get_or_create_wallet
from apps.common.email import send_shipment_confirmation_email

from .serializers import (
    ShipmentSerializer,
    CreateShipmentSerializer,
    ShipmentTrackingSerializer,
)
from .utils import (
    calculate_shipment_price,
    generate_tracking_number,
    SHIPMENT_STEPS,
)


class ShipmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shipments = Shipment.objects.filter(sender=request.user)

        # Filter by status
        shipment_status = request.query_params.get('status')
        if shipment_status:
            shipments = shipments.filter(status=shipment_status)

        serializer = ShipmentSerializer(shipments, many=True)
        return api_response(
            'success',
            'Shipments retrieved successfully',
            data={
                'count': shipments.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CreateShipmentSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            # ── Resolve pickup details ──────────────
            pickup_address_ref = None
            pickup_name = data.get('pickup_name', '')
            pickup_phone = data.get('pickup_phone', '')
            pickup_address_str = data.get('pickup_address', '')
            pickup_city_str = data.get('pickup_city', '')
            pickup_state_str = data.get('pickup_state', '')
            pickup_lat = data.get('pickup_lat')
            pickup_lng = data.get('pickup_lng')
            pickup_city_ref = None
            pickup_state_ref = None
            pickup_zone_obj = None

            if data.get('pickup_address_id'):
                # Use saved address
                addr = Address.objects.filter(
                    pk=data['pickup_address_id'],
                    user=request.user
                ).first()
                if addr:
                    pickup_address_ref = addr
                    pickup_name = addr.user.full_name
                    pickup_phone = addr.user.phone
                    pickup_address_str = addr.street_address
                    pickup_city_ref = addr.city
                    pickup_state_ref = addr.state
                    pickup_zone_obj = addr.zone
                    pickup_city_str = addr.city.name if addr.city else ''
                    pickup_state_str = addr.state.name if addr.state else ''
                    pickup_lat = addr.latitude
                    pickup_lng = addr.longitude
            else:
                # Manual entry - resolve FKs
                if data.get('pickup_city_id'):
                    pickup_city_ref = City.objects.filter(
                        pk=data['pickup_city_id']
                    ).first()
                    if pickup_city_ref:
                        pickup_city_str = pickup_city_ref.name
                if data.get('pickup_state_id'):
                    pickup_state_ref = State.objects.filter(
                        pk=data['pickup_state_id']
                    ).first()
                    if pickup_state_ref:
                        pickup_state_str = pickup_state_ref.name
                if data.get('pickup_zone_id'):
                    pickup_zone_obj = Zone.objects.filter(
                        pk=data['pickup_zone_id']
                    ).first()

            # ── Resolve delivery details ─────────────
            delivery_address_ref = None
            receiver_name = data.get('receiver_name', '')
            receiver_phone = data.get('receiver_phone', '')
            receiver_email = data.get('receiver_email', '')
            delivery_address_str = data.get('delivery_address', '')
            delivery_city_str = data.get('delivery_city', '')
            delivery_state_str = data.get('delivery_state', '')
            delivery_lat = data.get('delivery_lat')
            delivery_lng = data.get('delivery_lng')
            delivery_city_ref = None
            delivery_state_ref = None
            delivery_zone_obj = None

            if data.get('delivery_address_id'):
                # Use saved address
                addr = Address.objects.filter(
                    pk=data['delivery_address_id']
                ).first()
                if addr:
                    delivery_address_ref = addr
                    receiver_name = addr.user.full_name
                    receiver_phone = addr.user.phone
                    delivery_address_str = addr.street_address
                    delivery_city_ref = addr.city
                    delivery_state_ref = addr.state
                    delivery_zone_obj = addr.zone
                    delivery_city_str = addr.city.name if addr.city else ''
                    delivery_state_str = addr.state.name if addr.state else ''
                    delivery_lat = addr.latitude
                    delivery_lng = addr.longitude
            else:
                # Manual entry - resolve FKs
                if data.get('delivery_city_id'):
                    delivery_city_ref = City.objects.filter(
                        pk=data['delivery_city_id']
                    ).first()
                    if delivery_city_ref:
                        delivery_city_str = delivery_city_ref.name
                if data.get('delivery_state_id'):
                    delivery_state_ref = State.objects.filter(
                        pk=data['delivery_state_id']
                    ).first()
                    if delivery_state_ref:
                        delivery_state_str = delivery_state_ref.name
                if data.get('delivery_zone_id'):
                    delivery_zone_obj = Zone.objects.filter(
                        pk=data['delivery_zone_id']
                    ).first()

            # ── Calculate distance ───────────────────
            distance_km = 0
            if pickup_lat and delivery_lat:
                distance_km = calculate_distance(
                    pickup_lat, pickup_lng,
                    delivery_lat, delivery_lng
                )

            # ── Calculate price ──────────────────────
            price_data = calculate_logistics_price(
                distance_km=distance_km,
                weight_kg=data['weight'],
                package_size=data['package_size'],
                vehicle_type_id=data.get('vehicle_type_id'),
                service_type=data.get('service_type', 'standard'),
                pickup_city=pickup_city_str,
                pickup_state=pickup_state_str,
                dropoff_city=delivery_city_str,
                dropoff_state=delivery_state_str,
                pickup_zone_id=pickup_zone_obj.id if pickup_zone_obj else None,
                dropoff_zone_id=delivery_zone_obj.id if delivery_zone_obj else None,
            )
            price = price_data['total']

            # ── Handle payment ───────────────────────
            payment_method = data.get('payment_method', 'wallet')
            payment_status = 'unpaid'

            if payment_method == 'wallet':
                wallet = get_or_create_wallet(request.user)

                if wallet.balance >= price:
                    ref = generate_reference('SHP')
                    success = wallet.debit(
                        amount=price,
                        description='Shipment payment',
                        reference=ref
                    )
                    if success:
                        payment_status = 'paid'
                else:
                    shortage = price - wallet.balance
                    return api_response(
                        'error',
                        f'Insufficient wallet balance. You need ₦{shortage} more.',
                        data={
                            'wallet_balance': str(wallet.balance),
                            'required': str(price),
                            'shortage': str(shortage),
                            'price_breakdown': price_data['breakdown'],
                            'alternatives': [
                                {
                                    'method': 'paystack',
                                    'message': 'Pay with Paystack'
                                },
                                {
                                    'method': 'flutterwave',
                                    'message': 'Pay with Flutterwave'
                                },
                                {
                                    'method': 'topup',
                                    'message': f'Top up ₦{shortage} and try again'
                                }
                            ]
                        },
                        http_status=status.HTTP_402_PAYMENT_REQUIRED
                    )

            # ── Create shipment ──────────────────────
            shipment = Shipment.objects.create(
                sender=request.user,
                reference=generate_reference('SHP'),
                tracking_number=generate_tracking_number(),
                package_name=data['package_name'],
                package_description=data.get('package_description', ''),
                package_size=data['package_size'],
                weight=data['weight'],
                fragile=data.get('fragile', False),

                # Pickup
                pickup_address_ref=pickup_address_ref,
                pickup_name=pickup_name,
                pickup_phone=pickup_phone,
                pickup_address=pickup_address_str,
                pickup_city=pickup_city_str,
                pickup_state=pickup_state_str,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                pickup_city_ref=pickup_city_ref,
                pickup_state_ref=pickup_state_ref,
                pickup_zone=pickup_zone_obj,

                # Delivery
                delivery_address_ref=delivery_address_ref,
                receiver_name=receiver_name,
                receiver_phone=receiver_phone,
                receiver_email=receiver_email,
                delivery_address=delivery_address_str,
                delivery_city=delivery_city_str,
                delivery_state=delivery_state_str,
                delivery_lat=delivery_lat,
                delivery_lng=delivery_lng,
                delivery_city_ref=delivery_city_ref,
                delivery_state_ref=delivery_state_ref,
                delivery_zone=delivery_zone_obj,

                notes=data.get('notes', ''),
                price=price,
                payment_status=payment_status,
                service_type=data.get('service_type', 'standard'),
            )

            # Create initial tracking
            ShipmentTracking.objects.create(
                shipment=shipment,
                status='pending',
                description='Shipment created successfully',
                updated_by=request.user
            )

            # Send confirmation email
            send_shipment_confirmation_email(shipment)

            return api_response(
                'success',
                'Shipment created successfully',
                data={
                    **ShipmentSerializer(shipment).data,
                    'price_breakdown': price_data['breakdown'],
                },
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Failed to create shipment',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

class EstimateShipmentPriceView(APIView):
    """Get price estimate before creating shipment"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.common.logistics_pricing import get_price_estimate
        from apps.wallet.utils import get_or_create_wallet

        pickup_lat = request.data.get('pickup_lat')
        pickup_lng = request.data.get('pickup_lng')
        delivery_lat = request.data.get('delivery_lat')
        delivery_lng = request.data.get('delivery_lng')
        weight = request.data.get('weight', 1)
        package_size = request.data.get('package_size', 'small')
        pickup_city = request.data.get('pickup_city', '')
        pickup_state = request.data.get('pickup_state', '')
        delivery_city = request.data.get('delivery_city', '')
        delivery_state = request.data.get('delivery_state', '')

        if not all([pickup_lat, pickup_lng, delivery_lat, delivery_lng]):
            return api_response(
                'error',
                'Pickup and delivery coordinates are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        estimates = get_price_estimate(
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=delivery_lat,
            dropoff_lng=delivery_lng,
            weight_kg=weight,
            package_size=package_size,
            pickup_city=pickup_city,
            pickup_state=pickup_state,
            dropoff_city=delivery_city,
            dropoff_state=delivery_state,
        )

        # Add wallet balance
        wallet = get_or_create_wallet(request.user)
        estimates['wallet_balance'] = str(wallet.balance)
        estimates['can_pay_with_wallet'] = {
            option['vehicle_type'] + '_' + option['service_type']:
            wallet.balance >= Decimal(option['price'])
            for option in estimates['estimates']
        }

        return api_response(
            'success',
            'Price estimates retrieved successfully',
            data=estimates
        )


class ShipmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Shipment.objects.get(pk=pk, sender=user)
        except Shipment.DoesNotExist:
            return None

    def get(self, request, pk):
        shipment = self.get_object(pk, request.user)
        if not shipment:
            return api_response(
                'error',
                'Shipment not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ShipmentSerializer(shipment)
        return api_response(
            'success',
            'Shipment retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        shipment = self.get_object(pk, request.user)
        if not shipment:
            return api_response(
                'error',
                'Shipment not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if shipment.status != 'pending':
            return api_response(
                'error',
                'Only pending shipments can be cancelled',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        shipment.status = 'cancelled'
        shipment.save()

        ShipmentTracking.objects.create(
            shipment=shipment,
            status='cancelled',
            description='Shipment cancelled by sender',
            updated_by=request.user
        )

        return api_response(
            'success',
            'Shipment cancelled successfully',
            data=ShipmentSerializer(shipment).data
        )


class TrackShipmentView(APIView):
    """
    Track shipment by tracking number
    Public endpoint - no auth needed
    """
    permission_classes = []

    def get(self, request, tracking_number):
        try:
            shipment = Shipment.objects.get(
                tracking_number=tracking_number
            )
        except Shipment.DoesNotExist:
            return api_response(
                'error',
                'Shipment not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        tracking_entries = ShipmentTracking.objects.filter(
            shipment=shipment
        )
        tracking_dict = {
            entry.status: entry
            for entry in tracking_entries
        }

        current_index = next(
            (i for i, step in enumerate(SHIPMENT_STEPS)
             if step['status'] == shipment.status),
            0
        )

        steps = []
        for i, step in enumerate(SHIPMENT_STEPS):
            entry = tracking_dict.get(step['status'])
            steps.append({
                'status': step['status'],
                'label': step['label'],
                'description': entry.description if entry else step['description'],
                'icon': step['icon'],
                'location': entry.location if entry else None,
                'latitude': str(entry.latitude) if entry and entry.latitude else None,
                'longitude': str(entry.longitude) if entry and entry.longitude else None,
                'timestamp': entry.created_at if entry else None,
                'completed': i <= current_index,
                'current': step['status'] == shipment.status,
            })

        return api_response(
            'success',
            'Shipment tracking retrieved successfully',
            data={
                'tracking_number': shipment.tracking_number,
                'reference': shipment.reference,
                'current_status': shipment.status,
                'package_name': shipment.package_name,
                'receiver_name': shipment.receiver_name,
                'delivery_address': shipment.delivery_address,
                'delivery_city': shipment.delivery_city,
                'estimated_delivery': shipment.estimated_delivery,
                'current_lat': str(shipment.current_lat) if shipment.current_lat else None,
                'current_lng': str(shipment.current_lng) if shipment.current_lng else None,
                'current_location': shipment.current_location,
                'driver_name': shipment.driver.user.full_name if shipment.driver else None,
                'driver_lat': str(shipment.driver.current_lat) if shipment.driver and shipment.driver.current_lat else None,
                'driver_lng': str(shipment.driver.current_lng) if shipment.driver and shipment.driver.current_lng else None,
                'tracking_steps': steps,
            }
        )


class AdminShipmentListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        shipments = Shipment.objects.all()

        shipment_status = request.query_params.get('status')
        if shipment_status:
            shipments = shipments.filter(status=shipment_status)

        serializer = ShipmentSerializer(shipments, many=True)
        return api_response(
            'success',
            'All shipments retrieved',
            data={
                'count': shipments.count(),
                'results': serializer.data
            }
        )


class AdminShipmentUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk)
        except Shipment.DoesNotExist:
            return api_response(
                'error',
                'Shipment not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        driver_id = request.data.get('driver_id')
        location = request.data.get('location', '')
        description = request.data.get('description', '')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        payment_status = request.data.get('payment_status')

        if driver_id:
            try:
                driver = DriverProfile.objects.get(pk=driver_id)
                shipment.driver = driver
            except DriverProfile.DoesNotExist:
                return api_response(
                    'error',
                    'Driver not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

        if new_status:
            shipment.status = new_status

            # Update current location
            if latitude:
                shipment.current_lat = latitude
            if longitude:
                shipment.current_lng = longitude
            if location:
                shipment.current_location = location

            # Create tracking entry
            ShipmentTracking.objects.create(
                shipment=shipment,
                status=new_status,
                description=description or f'Status updated to {new_status}',
                location=location,
                latitude=latitude,
                longitude=longitude,
                updated_by=request.user
            )

        if payment_status:
            shipment.payment_status = payment_status

        shipment.save()

        # Broadcast real-time update
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            import json

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'shipment_{shipment.tracking_number}',
                {
                    'type': 'shipment_update',
                    'status': shipment.status,
                    'location': location,
                    'latitude': str(latitude) if latitude else None,
                    'longitude': str(longitude) if longitude else None,
                    'description': description,
                    'timestamp': str(shipment.updated_at),
                }
            )
        except Exception:
            pass

        return api_response(
            'success',
            'Shipment updated successfully',
            data=ShipmentSerializer(shipment).data
        )


class AssignDriverView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk)
        except Shipment.DoesNotExist:
            return api_response(
                'error',
                'Shipment not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        driver_id = request.data.get('driver_id')
        try:
            driver = DriverProfile.objects.get(
                pk=driver_id,
                status='verified',
                is_available=True
            )
        except DriverProfile.DoesNotExist:
            return api_response(
                'error',
                'Driver not found or not available',
                http_status=status.HTTP_404_NOT_FOUND
            )

        shipment.driver = driver
        shipment.status = 'assigned'
        shipment.save()

        # Create tracking entry
        ShipmentTracking.objects.create(
            shipment=shipment,
            status='assigned',
            description=f'Driver {driver.user.full_name} has been assigned',
            updated_by=request.user
        )

        return api_response(
            'success',
            'Driver assigned successfully',
            data=ShipmentSerializer(shipment).data
        )