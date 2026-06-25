import random
import string
from django.utils import timezone
from datetime import timedelta
from .models import DeliveryRequest, DeliveryTracking
from apps.common.utils import generate_reference
from apps.drivers.utils import find_nearby_drivers, calculate_distance
from apps.notifications.utils import send_notification
from apps.common.termii import send_sms, send_whatsapp
from apps.common.utils import generate_otp
from apps.common.email import send_otp_email



def generate_tracking_number():
    """Generate unique delivery tracking number"""
    chars = string.ascii_uppercase + string.digits
    return 'DLV' + ''.join(random.choices(chars, k=10))


def calculate_delivery_price(
    pickup_state,
    dropoff_state,
    pickup_city,
    dropoff_city,
    package_size,
    weight
):
    """Calculate delivery price"""
    BASE_PRICE = 800

    # Size pricing
    size_price = {
        'small': 0,
        'medium': 500,
        'large': 1000,
    }.get(package_size, 0)

    # Weight pricing
    weight_price = float(weight) * 50

    # Distance pricing
    if pickup_state == dropoff_state:
        if pickup_city == dropoff_city:
            distance_price = 500   # same city
        else:
            distance_price = 1000  # same state different city
    else:
        distance_price = 2500      # different state

    total = BASE_PRICE + size_price + weight_price + distance_price
    return round(total, 2)


DELIVERY_STEPS = [
    {
        'status': 'pending',
        'label': 'Delivery Requested',
        'description': 'Your delivery request has been received',
        'icon': '📦'
    },
    {
        'status': 'assigned',
        'label': 'Dispatcher Assigned',
        'description': 'A dispatcher has been assigned',
        'icon': '🏍️'
    },
    {
        'status': 'picked_up',
        'label': 'Package Picked Up',
        'description': 'Package has been picked up',
        'icon': '✅'
    },
    {
        'status': 'in_transit',
        'label': 'In Transit',
        'description': 'Package is on the way',
        'icon': '🚀'
    },
    {
        'status': 'delivered',
        'label': 'Delivered',
        'description': 'Package has been delivered',
        'icon': '🎉'
    },
]

def create_delivery_for_order(order):
    """
    Auto create a DeliveryRequest when a delivery-type
    order is placed. Pickup = business address,
    dropoff = order's delivery address.
    Returns the created DeliveryRequest or None.
    """
    if order.order_type != 'delivery':
        return None

    if hasattr(order, 'delivery') and order.delivery:
        return order.delivery

    business = order.business

    # Resolve pickup details from business
    pickup_name = business.name if business else 'Vendor'
    pickup_phone = (
        business.phone if business and business.phone
        else (business.owner.phone if business else '')
    )
    pickup_address = business.address if business else ''
    pickup_city_ref = getattr(business, 'city', None)
    pickup_state_ref = getattr(business, 'state', None)
    pickup_lat = getattr(business, 'latitude', None)
    pickup_lng = getattr(business, 'longitude', None)

    delivery = DeliveryRequest.objects.create(
        customer=order.user,
        order=order,
        reference=generate_reference('DLV'),
        tracking_number=generate_tracking_number(),
        package_name=f"Order {order.order_number}",
        package_description=(
            f"{order.items.count()} item(s) from "
            f"{business.name if business else 'vendor'}"
        ),
        package_size='small',
        weight=1.0,

        # Pickup - from business
        pickup_name=pickup_name,
        pickup_phone=pickup_phone or '',
        pickup_address=pickup_address,
        pickup_city=pickup_city_ref.name if pickup_city_ref else order.delivery_city,
        pickup_state=pickup_state_ref.name if pickup_state_ref else order.delivery_state,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        pickup_city_ref=pickup_city_ref,
        pickup_state_ref=pickup_state_ref,

        # Dropoff - from order's delivery address
        dropoff_address_ref=order.delivery_address_ref,
        dropoff_name=order.delivery_name,
        dropoff_phone=order.delivery_phone,
        dropoff_address=order.delivery_address,
        dropoff_city=order.delivery_city,
        dropoff_state=order.delivery_state,
        dropoff_lat=order.delivery_lat,
        dropoff_lng=order.delivery_lng,
        dropoff_city_ref=order.delivery_city_ref,
        dropoff_zone=order.delivery_zone,

        # Price already covered by the order's delivery_fee
        price=order.delivery_fee,
        payment_status='paid' if order.payment_status == 'paid' else 'unpaid',
        notes=f"Auto-created for order {order.order_number}",
    )

    # Auto assign nearest dispatcher
    if pickup_lat and pickup_lng:
        nearby = find_nearby_drivers(pickup_lat, pickup_lng, radius_km=10)
        if nearby:
            delivery.driver = nearby[0]['driver']
            delivery.status = 'assigned'
            delivery.save()

            DeliveryTracking.objects.create(
                delivery=delivery,
                status='assigned',
                description=(
                    f'Driver {delivery.driver.user.full_name} '
                    f'assigned'
                ),
                updated_by=order.user
            )

            # Sync driver back onto the order for visibility
            order.driver = delivery.driver
            order.save()

    DeliveryTracking.objects.create(
        delivery=delivery,
        status='pending',
        description=f'Delivery auto-created from order {order.order_number}',
        updated_by=order.user
    )

    return delivery

PICKUP_PROXIMITY_KM = 0.2  # 200 meters


def check_pickup_arrival(driver):
    """
    Called whenever a driver's location updates.
    Checks all of this driver's active assigned deliveries —
    if driver is now within PICKUP_PROXIMITY_KM of any
    pickup point that hasn't been alerted yet, fires the
    'arrived at pickup' notification to customer + vendor.
    """


    if driver.current_lat is None or driver.current_lng is None:
        return

    active_deliveries = DeliveryRequest.objects.filter(
        driver=driver,
        status__in=['assigned', 'accepted'],
        arrived_at_pickup_at__isnull=True,
    )

    for delivery in active_deliveries:
        distance = calculate_distance(
            driver.current_lat,
            driver.current_lng,
            delivery.pickup_lat,
            delivery.pickup_lng,
        )

        if distance is None or distance > PICKUP_PROXIMITY_KM:
            continue

        delivery.arrived_at_pickup_at = timezone.now()
        delivery.status = 'at_pickup'
        delivery.save()

        DeliveryTracking.objects.create(
            delivery=delivery,
            status='at_pickup',
            description=(
                f'Driver {driver.user.full_name} has arrived '
                f'at the pickup location'
            ),
            latitude=driver.current_lat,
            longitude=driver.current_lng,
        )

        # Notify customer
        send_notification(
            user=delivery.customer,
            title='Driver Arrived 🛵',
            message=(
                f'Your driver has arrived at {delivery.pickup_name} '
                f'to pick up your order.'
            ),
            notification_type='delivery',
            data={'delivery_id': delivery.id}
        )

        # Notify vendor (via the order's business owner)
        if delivery.order and delivery.order.business:
            send_notification(
                user=delivery.order.business.owner,
                title='Driver at Your Location 🛵',
                message=(
                    f'Driver {driver.user.full_name} has arrived '
                    f'to collect order {delivery.order.order_number}.'
                ),
                notification_type='delivery',
                data={
                    'delivery_id': delivery.id,
                    'order_id': delivery.order.id
                }
            )


ARRIVING_SOON_KM = 1.0
DROPOFF_PROXIMITY_KM = 0.2  # 200 meters


def check_dropoff_proximity(driver):
    """
    Called whenever a driver's location updates.
    Checks all of this driver's active deliveries that are
    en route — fires an 'arriving soon' alert at 1km out,
    then an 'arrived' alert at 200m, each only once.
    """
    active_deliveries = DeliveryRequest.objects.filter(
        driver=driver,
        status__in=['picked_up', 'in_transit'],
    )

    for delivery in active_deliveries:
        if delivery.dropoff_lat is None or delivery.dropoff_lng is None:
            continue

        distance = calculate_distance(
            driver.current_lat,
            driver.current_lng,
            delivery.dropoff_lat,
            delivery.dropoff_lng,
        )

        # Arriving soon alert (1km out)
        if (
            distance <= ARRIVING_SOON_KM
            and delivery.arriving_soon_alerted_at is None
        ):
            delivery.arriving_soon_alerted_at = timezone.now()
            delivery.save()

            DeliveryTracking.objects.create(
                delivery=delivery,
                status=delivery.status,
                description=(
                    f'Driver {driver.user.full_name} is arriving soon'
                ),
                latitude=driver.current_lat,
                longitude=driver.current_lng,
            )

            send_notification(
                user=delivery.customer,
                title='Driver Arriving Soon 🛵',
                message=(
                    f'Your driver is about {round(distance, 1)}km away. '
                    f'Get ready to receive your order!'
                ),
                notification_type='delivery',
                data={'delivery_id': delivery.id}
            )

        # Arrived at dropoff alert (200m)
        if (
            distance <= DROPOFF_PROXIMITY_KM
            and delivery.arrived_at_dropoff_at is None
        ):
            delivery.arrived_at_dropoff_at = timezone.now()
            delivery.status = 'at_dropoff'
            delivery.save()
            # Send delivery confirmation OTP to customer
            try:
                send_delivery_otp(delivery)
            except Exception as e:
                print(f"OTP send error: {e}")

            DeliveryTracking.objects.create(
                delivery=delivery,
                status='at_dropoff',
                description=(
                    f'Driver {driver.user.full_name} has arrived '
                    f'at the dropoff location'
                ),
                latitude=driver.current_lat,
                longitude=driver.current_lng,
            )

            send_notification(
                user=delivery.customer,
                title='Driver Has Arrived 🛵',
                message=(
                    f'Your driver has arrived with your order. '
                    f'Please go meet them.'
                ),
                notification_type='delivery',
                data={'delivery_id': delivery.id}
            )

            if delivery.order and delivery.order.business:
                send_notification(
                    user=delivery.order.business.owner,
                    title='Order Reached Customer 📍',
                    message=(
                        f'Driver {driver.user.full_name} has arrived '
                        f'at the dropoff location for order '
                        f'{delivery.order.order_number}.'
                    ),
                    notification_type='delivery',
                    data={
                        'delivery_id': delivery.id,
                        'order_id': delivery.order.id
                    }
                )


def send_delivery_otp(delivery):
    """
    Generate OTP, save to delivery, and send via
    email + SMS + WhatsApp to the customer.
    """
    otp = generate_otp(length=6)
    delivery.delivery_otp = otp
    delivery.delivery_otp_expires_at = (
        timezone.now() + timedelta(minutes=15)
    )
    delivery.delivery_otp_verified = False
    delivery.save()

    customer = delivery.customer
    name = customer.full_name or customer.email
    phone = customer.phone or ''

    message = (
        f"Your delivery confirmation code is: {otp}. "
        f"Give this to your driver. Expires in 15 minutes. "
        f"Do not share with anyone else."
    )

    # Email (live via SendGrid)
    try:
        send_otp_email(
            to_email=customer.email,
            otp=otp,
            otp_type='delivery_confirmation',
            name=name,
        )
    except Exception as e:
        print(f"OTP email error: {e}")

    # SMS (stubbed until TERMII_API_KEY is set)
    if phone:
        try:
            send_sms(phone, message)
        except Exception as e:
            print(f"OTP SMS error: {e}")

        # WhatsApp (stubbed until Termii approves sender)
        try:
            send_whatsapp(phone, message)
        except Exception as e:
            print(f"OTP WhatsApp error: {e}")

    return otp