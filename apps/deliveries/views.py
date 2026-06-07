from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.logistics_pricing import calculate_logistics_price
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from apps.common.views import api_response
from apps.drivers.models import DriverEarnings, DriverProfile
from apps.drivers.utils import calculate_distance, find_nearby_drivers
from apps.locations.models import Address, City, State, Zone
from apps.notifications.utils import send_notification
from apps.payments.models import PaymentModel
from apps.wallet.utils import get_or_create_wallet

from .models import CompanyEarnings, DeliveryRequest, DeliveryTracking, DeliveryZone
from .serializers import (
    CreateDeliverySerializer,
    DeliveryRequestSerializer,
    DeliveryZoneSerializer,
    RateDeliverySerializer,
)
from .utils import DELIVERY_STEPS, calculate_delivery_price, generate_tracking_number


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _broadcast_delivery_update(delivery, new_status, location, latitude, longitude, description):
    """Push real-time update over Django Channels."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'delivery_{delivery.tracking_number}',
            {
                'type':        'delivery_update',
                'status':      new_status,
                'location':    location,
                'latitude':    str(latitude)  if latitude  else None,
                'longitude':   str(longitude) if longitude else None,
                'description': description,
                'timestamp':   str(timezone.now()),
            }
        )
    except Exception:
        pass


def _resolve_pickup(data, user):
    result = {
        'pickup_address_ref': None,
        'pickup_name':        data.get('pickup_name', ''),
        'pickup_phone':       data.get('pickup_phone', ''),
        'pickup_address':     data.get('pickup_address', ''),
        'pickup_city':        data.get('pickup_city', ''),
        'pickup_state':       data.get('pickup_state', ''),
        'pickup_lat':         data.get('pickup_lat'),
        'pickup_lng':         data.get('pickup_lng'),
        'pickup_city_ref':    None,
        'pickup_state_ref':   None,
        'pickup_zone':        None,
    }

    if data.get('pickup_address_id'):
        addr = Address.objects.filter(
            pk=data['pickup_address_id'],
            user=user
        ).first()
        if addr:
            result.update({
                'pickup_address_ref': addr,
                'pickup_name':        addr.user.full_name,
                'pickup_phone':       addr.user.phone,
                'pickup_address':     addr.street_address,
                'pickup_city_ref':    addr.city,
                'pickup_state_ref':   addr.state,
                'pickup_zone':        addr.zone,
                'pickup_city':        addr.city.name  if addr.city  else '',
                'pickup_state':       addr.state.name if addr.state else '',
                'pickup_lat':         addr.latitude,
                'pickup_lng':         addr.longitude,
            })
    else:
        if data.get('pickup_city_id'):
            city = City.objects.filter(pk=data['pickup_city_id']).first()
            if city:
                result['pickup_city_ref'] = city
                result['pickup_city']     = city.name

        if data.get('pickup_state_id'):
            state = State.objects.filter(pk=data['pickup_state_id']).first()
            if state:
                result['pickup_state_ref'] = state
                result['pickup_state']     = state.name

        if data.get('pickup_zone_id'):
            result['pickup_zone'] = Zone.objects.filter(
                pk=data['pickup_zone_id']
            ).first()

    return result


def _resolve_dropoff(data):
    result = {
        'dropoff_address_ref': None,
        'dropoff_name':        data.get('dropoff_name', ''),
        'dropoff_phone':       data.get('dropoff_phone', ''),
        'dropoff_address':     data.get('dropoff_address', ''),
        'dropoff_city':        data.get('dropoff_city', ''),
        'dropoff_state':       data.get('dropoff_state', ''),
        'dropoff_lat':         data.get('dropoff_lat'),
        'dropoff_lng':         data.get('dropoff_lng'),
        'dropoff_city_ref':    None,
        'dropoff_state_ref':   None,
        'dropoff_zone':        None,
    }

    if data.get('dropoff_address_id'):
        addr = Address.objects.filter(pk=data['dropoff_address_id']).first()
        if addr:
            result.update({
                'dropoff_address_ref': addr,
                'dropoff_name':        addr.user.full_name,
                'dropoff_phone':       addr.user.phone,
                'dropoff_address':     addr.street_address,
                'dropoff_city_ref':    addr.city,
                'dropoff_state_ref':   addr.state,
                'dropoff_zone':        addr.zone,
                'dropoff_city':        addr.city.name  if addr.city  else '',
                'dropoff_state':       addr.state.name if addr.state else '',
                'dropoff_lat':         addr.latitude,
                'dropoff_lng':         addr.longitude,
            })
    else:
        if data.get('dropoff_city_id'):
            city = City.objects.filter(pk=data['dropoff_city_id']).first()
            if city:
                result['dropoff_city_ref'] = city
                result['dropoff_city']     = city.name

        if data.get('dropoff_state_id'):
            state = State.objects.filter(pk=data['dropoff_state_id']).first()
            if state:
                result['dropoff_state_ref'] = state
                result['dropoff_state']     = state.name

        if data.get('dropoff_zone_id'):
            result['dropoff_zone'] = Zone.objects.filter(
                pk=data['dropoff_zone_id']
            ).first()

    return result


def _handle_wallet_payment(user, price):
    wallet  = get_or_create_wallet(user)
    shortage = price - wallet.balance

    if wallet.balance < price:
        return 'unpaid', {
            'wallet_balance': str(wallet.balance),
            'required':       str(price),
            'shortage':       str(shortage),
            'alternatives': [
                {'method': 'paystack',    'message': 'Pay with Paystack'},
                {'method': 'flutterwave', 'message': 'Pay with Flutterwave'},
                {'method': 'topup',       'message': f'Top up ₦{shortage} and try again'},
            ],
        }

    ref     = generate_reference('DLV')
    success = wallet.debit(
        amount=price,
        description='Delivery payment',
        reference=ref,
    )
    return ('paid' if success else 'unpaid'), None


def _record_driver_earnings(delivery, driver):
    """
    Split earnings based on the delivery's payment model.
      • marketplace → 80% driver / 20% platform
      • logistics   → 100% platform
    """
    if not delivery.payment_model:
        return

    model_name = delivery.payment_model.name

    if model_name == 'marketplace':
        driver_cut   = delivery.price * Decimal('0.80')
        platform_cut = delivery.price * Decimal('0.20')

        DriverEarnings.objects.create(
            driver=driver,
            earning_type='delivery',
            amount=driver_cut,
            reference=delivery.reference,
            description=f'Delivery earnings for {delivery.tracking_number}',
        )
        CompanyEarnings.objects.create(
            earning_type='marketplace_commission',
            amount=platform_cut,
            reference=delivery.reference,
            description=f'Commission for {delivery.tracking_number}',
        )

    elif model_name == 'logistics':
        CompanyEarnings.objects.create(
            earning_type='logistics_delivery',
            amount=delivery.price,
            reference=delivery.reference,
            description=f'Logistics delivery for {delivery.tracking_number}',
        )


# ─────────────────────────────────────────────────────────────
# DELIVERY ZONES
# ─────────────────────────────────────────────────────────────

class DeliveryZoneListView(APIView):
    permission_classes = []

    def get(self, request):
        zones = DeliveryZone.objects.filter(is_active=True)
        if state := request.query_params.get('state'):
            zones = zones.filter(state__icontains=state)
        serializer = DeliveryZoneSerializer(zones, many=True)
        return api_response(
            'success', 'Delivery zones retrieved successfully',
            data={'count': zones.count(), 'results': serializer.data},
        )

    def post(self, request):
        serializer = DeliveryZoneSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success', 'Delivery zone created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED,
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ─────────────────────────────────────────────────────────────
# CUSTOMER — LIST & CREATE
# ─────────────────────────────────────────────────────────────

class DeliveryRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        deliveries = DeliveryRequest.objects.filter(customer=request.user)
        if delivery_status := request.query_params.get('status'):
            deliveries = deliveries.filter(status=delivery_status)
        serializer = DeliveryRequestSerializer(deliveries, many=True)
        return api_response(
            'success', 'Deliveries retrieved successfully',
            data={'count': deliveries.count(), 'results': serializer.data},
        )

    def post(self, request):
        serializer = CreateDeliverySerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                'error', 'Failed to create delivery request',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # 1. Resolve addresses
        pickup  = _resolve_pickup(data, request.user)
        dropoff = _resolve_dropoff(data)

        # 2. Distance
        distance_km = 0
        if pickup['pickup_lat'] and dropoff['dropoff_lat']:
            distance_km = calculate_distance(
                pickup['pickup_lat'],  pickup['pickup_lng'],
                dropoff['dropoff_lat'], dropoff['dropoff_lng'],
            )

        # 3. Price
        pickup_zone_obj  = pickup['pickup_zone']
        dropoff_zone_obj = dropoff['dropoff_zone']

        price_data = calculate_logistics_price(
            distance_km=distance_km,
            weight_kg=data['weight'],
            package_size=data['package_size'],
            vehicle_type_id=data.get('vehicle_type_id'),
            service_type=data.get('service_type', 'standard'),
            pickup_city=pickup['pickup_city'],
            pickup_state=pickup['pickup_state'],
            dropoff_city=dropoff['dropoff_city'],
            dropoff_state=dropoff['dropoff_state'],
            pickup_zone_id=pickup_zone_obj.id  if pickup_zone_obj  else None,
            dropoff_zone_id=dropoff_zone_obj.id if dropoff_zone_obj else None,
        )
        price = price_data['total']

        # 4. Payment model FK
        payment_model_name = data.get('payment_model', 'marketplace')
        payment_model_obj  = PaymentModel.objects.filter(
            name=payment_model_name,
            is_active=True,
        ).first()

        # 5. Handle payment
        payment_method = data.get('payment_method', 'wallet')
        payment_status = 'unpaid'

        if payment_method == 'wallet':
            payment_status, wallet_error = _handle_wallet_payment(request.user, price)
            if wallet_error:
                return api_response(
                    'error',
                    f'Insufficient wallet balance. You need ₦{wallet_error["shortage"]} more.',
                    data={**wallet_error, 'price_breakdown': price_data['breakdown']},
                    http_status=status.HTTP_402_PAYMENT_REQUIRED,
                )

        # 6. Create delivery
        delivery = DeliveryRequest.objects.create(
            customer=request.user,
            reference=generate_reference('DLV'),
            tracking_number=generate_tracking_number(),
            payment_model=payment_model_obj,
            package_name=data['package_name'],
            package_description=data.get('package_description', ''),
            package_size=data['package_size'],
            fragile=data.get('fragile', False),
            weight=data['weight'],
            **pickup,
            **dropoff,
            notes=data.get('notes', ''),
            price=price,
            payment_status=payment_status,
        )

        # 7. Auto-assign nearest driver
        if pickup['pickup_lat'] and pickup['pickup_lng']:
            nearby = find_nearby_drivers(
                pickup['pickup_lat'],
                pickup['pickup_lng'],
                radius_km=10,
            )
            if nearby:
                delivery.driver = nearby[0]['driver']
                delivery.status = 'assigned'
                delivery.save()

                DeliveryTracking.objects.create(
                    delivery=delivery,
                    status='assigned',
                    description=f'Driver {delivery.driver.user.full_name} assigned',
                    updated_by=request.user,
                )

        # 8. Initial tracking entry
        DeliveryTracking.objects.create(
            delivery=delivery,
            status='pending',
            description='Delivery request created successfully',
            updated_by=request.user,
        )

        # 9. Notify customer
        send_notification(
            user=request.user,
            title='Delivery Request Created',
            message=(
                f'Your delivery {delivery.tracking_number} has been created. '
                f'Price: ₦{price}'
            ),
            notification_type='system',
            data={
                'delivery_id':     delivery.id,
                'tracking_number': delivery.tracking_number,
            },
        )

        return api_response(
            'success', 'Delivery request created successfully',
            data={
                **DeliveryRequestSerializer(delivery).data,
                'price_breakdown': price_data['breakdown'],
            },
            http_status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────────────────────
# CUSTOMER — DETAIL & CANCEL
# ─────────────────────────────────────────────────────────────

class DeliveryRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_delivery(self, pk, user):
        return DeliveryRequest.objects.filter(pk=pk, customer=user).first()

    def get(self, request, pk):
        delivery = self._get_delivery(pk, request.user)
        if not delivery:
            return api_response(
                'error', 'Delivery not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )
        return api_response(
            'success', 'Delivery retrieved successfully',
            data=DeliveryRequestSerializer(delivery).data,
        )

    def patch(self, request, pk):
        delivery = self._get_delivery(pk, request.user)
        if not delivery:
            return api_response(
                'error', 'Delivery not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if delivery.status not in ['pending', 'assigned']:
            return api_response(
                'error', 'Cannot cancel a delivery that is already in progress',
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.status = 'cancelled'
        delivery.save()

        DeliveryTracking.objects.create(
            delivery=delivery,
            status='cancelled',
            description='Delivery cancelled by customer',
            updated_by=request.user,
        )

        return api_response(
            'success', 'Delivery cancelled successfully',
            data=DeliveryRequestSerializer(delivery).data,
        )


# ─────────────────────────────────────────────────────────────
# PUBLIC — TRACK BY TRACKING NUMBER
# ─────────────────────────────────────────────────────────────

class TrackDeliveryView(APIView):
    permission_classes = []

    def get(self, request, tracking_number):
        try:
            delivery = DeliveryRequest.objects.get(tracking_number=tracking_number)
        except DeliveryRequest.DoesNotExist:
            return api_response(
                'error', 'Delivery not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        tracking_entries = DeliveryTracking.objects.filter(delivery=delivery)
        tracking_dict    = {e.status: e for e in tracking_entries}

        current_index = next(
            (i for i, s in enumerate(DELIVERY_STEPS)
             if s['status'] == delivery.status),
            0,
        )

        steps = []
        for i, step in enumerate(DELIVERY_STEPS):
            entry = tracking_dict.get(step['status'])
            steps.append({
                'status':      step['status'],
                'label':       step['label'],
                'description': entry.description if entry else step['description'],
                'icon':        step['icon'],
                'location':    entry.location   if entry else None,
                'latitude':    str(entry.latitude)  if entry and entry.latitude  else None,
                'longitude':   str(entry.longitude) if entry and entry.longitude else None,
                'timestamp':   entry.created_at if entry else None,
                'completed':   i <= current_index,
                'current':     step['status'] == delivery.status,
            })

        driver = delivery.driver
        return api_response(
            'success', 'Delivery tracking retrieved successfully',
            data={
                'tracking_number':  delivery.tracking_number,
                'reference':        delivery.reference,
                'current_status':   delivery.status,
                'package_name':     delivery.package_name,
                'pickup_address':   delivery.pickup_address,
                'dropoff_address':  delivery.dropoff_address,
                'dropoff_city':     delivery.dropoff_city,
                'driver_name':      driver.user.full_name if driver else None,
                'driver_lat':       str(driver.current_lat)  if driver and driver.current_lat  else None,
                'driver_lng':       str(driver.current_lng)  if driver and driver.current_lng  else None,
                'current_lat':      str(delivery.current_lat)  if delivery.current_lat  else None,
                'current_lng':      str(delivery.current_lng)  if delivery.current_lng  else None,
                'current_location': delivery.current_location,
                'picked_up_at':     delivery.picked_up_at,
                'delivered_at':     delivery.delivered_at,
                'tracking_steps':   steps,
            },
        )


# ─────────────────────────────────────────────────────────────
# CUSTOMER — RATE DELIVERY
# ─────────────────────────────────────────────────────────────

class RateDeliveryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            delivery = DeliveryRequest.objects.get(pk=pk, customer=request.user)
        except DeliveryRequest.DoesNotExist:
            return api_response(
                'error', 'Delivery not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if delivery.status != 'delivered':
            return api_response(
                'error', 'Only delivered packages can be rated',
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        if delivery.rating:
            return api_response(
                'error', 'You have already rated this delivery',
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RateDeliverySerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                'error', 'Rating failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.rating = serializer.validated_data['rating']
        delivery.review = serializer.validated_data.get('review', '')
        delivery.save()

        # Update driver's average rating
        driver = delivery.driver
        if driver:
            new_rating = (
                (float(driver.rating) * driver.total_ratings)
                + serializer.validated_data['rating']
            ) / (driver.total_ratings + 1)
            driver.rating        = round(new_rating, 2)
            driver.total_ratings += 1
            driver.save()

        return api_response(
            'success', 'Delivery rated successfully',
            data=DeliveryRequestSerializer(delivery).data,
        )


# ─────────────────────────────────────────────────────────────
# DRIVER — LIST & UPDATE OWN DELIVERIES
# ─────────────────────────────────────────────────────────────

class DriverDeliveryView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_driver(self, user):
        try:
            return user.driver_profile
        except Exception:
            return None

    def get(self, request):
        driver = self._get_driver(request.user)
        if not driver:
            return api_response(
                'error', 'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        deliveries = DeliveryRequest.objects.filter(driver=driver)
        if delivery_status := request.query_params.get('status'):
            deliveries = deliveries.filter(status=delivery_status)

        serializer = DeliveryRequestSerializer(deliveries, many=True)
        return api_response(
            'success', 'Deliveries retrieved successfully',
            data={'count': deliveries.count(), 'results': serializer.data},
        )

    def patch(self, request, pk):
        driver = self._get_driver(request.user)
        if not driver:
            return api_response(
                'error', 'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        try:
            delivery = DeliveryRequest.objects.get(pk=pk, driver=driver)
        except DeliveryRequest.DoesNotExist:
            return api_response(
                'error', 'Delivery not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        new_status  = request.data.get('status')
        location    = request.data.get('location', '')
        latitude    = request.data.get('latitude')
        longitude   = request.data.get('longitude')
        description = request.data.get('description', '')

        valid_statuses = ['picked_up', 'in_transit', 'delivered', 'failed']
        if new_status not in valid_statuses:
            return api_response(
                'error',
                f'Invalid status. Choose from: {valid_statuses}',
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.status = new_status
        if latitude:  delivery.current_lat      = latitude
        if longitude: delivery.current_lng      = longitude
        if location:  delivery.current_location = location

        if new_status == 'picked_up':
            delivery.picked_up_at = timezone.now()

        elif new_status == 'delivered':
            delivery.delivered_at     = timezone.now()
            driver.total_deliveries  += 1
            driver.save()
            _record_driver_earnings(delivery, driver)

        delivery.save()

        DeliveryTracking.objects.create(
            delivery=delivery,
            status=new_status,
            description=description or f'Status updated to {new_status}',
            location=location,
            latitude=latitude,
            longitude=longitude,
            updated_by=request.user,
        )

        _broadcast_delivery_update(
            delivery, new_status, location, latitude, longitude, description
        )

        send_notification(
            user=delivery.customer,
            title='Delivery Update',
            message=f'Your delivery {delivery.tracking_number} is now {new_status}',
            notification_type='system',
            data={
                'delivery_id':     delivery.id,
                'tracking_number': delivery.tracking_number,
                'status':          new_status,
            },
        )

        return api_response(
            'success', 'Delivery updated successfully',
            data=DeliveryRequestSerializer(delivery).data,
        )


# ─────────────────────────────────────────────────────────────
# DRIVER — UPLOAD PROOF
# ─────────────────────────────────────────────────────────────

class UploadDeliveryProofView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            driver = request.user.driver_profile
        except Exception:
            return api_response(
                'error', 'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        try:
            delivery = DeliveryRequest.objects.get(pk=pk, driver=driver)
        except DeliveryRequest.DoesNotExist:
            return api_response(
                'error', 'Delivery not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        proof = request.FILES.get('delivery_proof')
        if not proof:
            return api_response(
                'error', 'No image provided',
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.delivery_proof = proof
        delivery.save()

        return api_response(
            'success', 'Delivery proof uploaded successfully',
            data={'delivery_proof': delivery.delivery_proof.url},
        )


# ─────────────────────────────────────────────────────────────
# ADMIN — LIST ALL DELIVERIES
# ─────────────────────────────────────────────────────────────

class AdminDeliveryListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        deliveries = DeliveryRequest.objects.all()
        if delivery_status := request.query_params.get('status'):
            deliveries = deliveries.filter(status=delivery_status)
        serializer = DeliveryRequestSerializer(deliveries, many=True)
        return api_response(
            'success', 'All deliveries retrieved',
            data={'count': deliveries.count(), 'results': serializer.data},
        )


# ─────────────────────────────────────────────────────────────
# ADMIN — UPDATE DELIVERY
# ─────────────────────────────────────────────────────────────

class AdminDeliveryUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            delivery = DeliveryRequest.objects.get(pk=pk)
        except DeliveryRequest.DoesNotExist:
            return api_response(
                'error', 'Delivery not found',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        new_status     = request.data.get('status')
        driver_id      = request.data.get('driver_id')
        location       = request.data.get('location', '')
        latitude       = request.data.get('latitude')
        longitude      = request.data.get('longitude')
        description    = request.data.get('description', '')
        payment_status = request.data.get('payment_status')

        if driver_id:
            try:
                driver = DriverProfile.objects.get(pk=driver_id, status='verified')
                delivery.driver = driver
            except DriverProfile.DoesNotExist:
                return api_response(
                    'error', 'Driver not found or not verified',
                    http_status=status.HTTP_404_NOT_FOUND,
                )

        if new_status:
            delivery.status = new_status
            if latitude:  delivery.current_lat      = latitude
            if longitude: delivery.current_lng      = longitude
            if location:  delivery.current_location = location

            DeliveryTracking.objects.create(
                delivery=delivery,
                status=new_status,
                description=description or f'Status updated to {new_status}',
                location=location,
                latitude=latitude,
                longitude=longitude,
                updated_by=request.user,
            )

            _broadcast_delivery_update(
                delivery, new_status, location, latitude, longitude, description
            )

        if payment_status:
            delivery.payment_status = payment_status

        delivery.save()

        return api_response(
            'success', 'Delivery updated successfully',
            data=DeliveryRequestSerializer(delivery).data,
        )