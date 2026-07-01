from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from .models import (
    BookableItem,
    BookableItemAvailability,
    BookingPolicy,
    Booking,
    BookingTracking,
    BookingAddOn,
    BookingPayment,
    BookingGuest,
    BookingCoupon,
    CouponUsage,
    BookingInvoice,
    BookingReminder,
)
from .serializers import (
    BookableItemSerializer,
    BookableItemAvailabilitySerializer,
    BookingPolicySerializer,
    BookingSerializer,
    CreateBookingSerializer,
    CheckAvailabilitySerializer,
    BookingAddOnSerializer,
    BookingReminderSerializer,
    BookingInvoiceSerializer,
    CouponUsageSerializer,
    BookingCouponSerializer,
    BookingGuestSerializer,
    BookingPaymentSerializer,
)


def generate_booking_number():
    import random
    import string
    return 'BKG-' + ''.join(
        random.choices(string.digits, k=8)
    )


# ─── Bookable Item Views ──────────────────────────

class BookableItemListCreateView(APIView):
    """List and create bookable items"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []

    def get(self, request):
        items = BookableItem.objects.filter(
            is_active=True,
            status='active'
        )

        business_id = request.query_params.get('business')
        item_type   = request.query_params.get('type')
        search      = request.query_params.get('search')
        featured    = request.query_params.get('featured')

        if business_id:
            items = items.filter(business__id=business_id)
        if item_type:
            items = items.filter(item_type=item_type)
        if search:
            items = items.filter(name__icontains=search)
        if featured:
            items = items.filter(is_featured=True)

        serializer = BookableItemSerializer(
            items, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Bookable items retrieved successfully',
            data={
                'count': items.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        item_type   = request.data.get('item_type')
        business_id = request.data.get('business')

        # Exclusive items require active subscription
        if item_type in ['room', 'vehicle', 'event', 'table']:
            if not business_id:
                return api_response(
                    'error',
                    'business is required',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            try:
                from apps.marketplace.models import Business
                from apps.subscriptions.models import (
                    BusinessSubscription
                )
                business = Business.objects.get(pk=business_id)
                sub = business.subscription

                can_list, reason = sub.can_accept_bookings(
                    'exclusive'
                )
                if not can_list:
                    return api_response(
                        'error', reason,
                        http_status=status.HTTP_403_FORBIDDEN
                    )

            except BusinessSubscription.DoesNotExist:
                return api_response(
                    'error',
                    'An active subscription with exclusive '
                    'booking support is required to list '
                    'hotel rooms, cars, and event centers.',
                    data={
                        'plans_url': (
                            '/api/v1/subscriptions/business/plans/'
                        ),
                    },
                    http_status=status.HTTP_403_FORBIDDEN
                )

            except Exception:
                return api_response(
                    'error',
                    'Subscription verification failed. '
                    'Please subscribe to a plan.',
                    http_status=status.HTTP_403_FORBIDDEN
                )

        serializer = BookableItemSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            item = serializer.save()
            return api_response(
                'success',
                'Bookable item created successfully',
                data=BookableItemSerializer(
                    item,
                    context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

class BookableItemDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAuthenticated()]
        return []

    def get_object(self, pk):
        try:
            return BookableItem.objects.get(pk=pk)
        except BookableItem.DoesNotExist:
            return None

    def get(self, request, pk):
        item = self.get_object(pk)
        if not item:
            return api_response(
                'error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookableItemSerializer(
            item, context={'request': request}
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
                'error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookableItemSerializer(
            item, data=request.data,
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
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        item = self.get_object(pk)
        if not item:
            return api_response(
                'error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        item.is_active = False
        item.save()
        return api_response(
            'success', 'Item deleted successfully'
        )


class BookingPolicyView(APIView):
    """Set booking policy for an item"""
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        try:
            item = BookableItem.objects.get(pk=item_id)
            policy = item.policy
        except (BookableItem.DoesNotExist,
                BookingPolicy.DoesNotExist):
            return api_response(
                'error', 'Policy not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookingPolicySerializer(policy)
        return api_response(
            'success',
            'Policy retrieved successfully',
            data=serializer.data
        )

    def post(self, request, item_id):
        """Create or update booking policy"""
        try:
            item = BookableItem.objects.get(pk=item_id)
        except BookableItem.DoesNotExist:
            return api_response(
                'error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if (item.business and
                item.business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Permission denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        data['item'] = item.id

        try:
            policy = item.policy
            serializer = BookingPolicySerializer(
                policy, data=data, partial=True
            )
        except BookingPolicy.DoesNotExist:
            serializer = BookingPolicySerializer(data=data)

        if serializer.is_valid():
            serializer.save(item=item)
            return api_response(
                'success',
                'Policy saved successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Failed to save policy',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CheckAvailabilityView(APIView):
    """Check if item is available for dates"""
    permission_classes = []

    def post(self, request):
        serializer = CheckAvailabilitySerializer(
            data=request.data
        )
        if serializer.is_valid():
            data = serializer.validated_data

            try:
                item = BookableItem.objects.get(
                    pk=data['item_id'],
                    is_active=True
                )
            except BookableItem.DoesNotExist:
                return api_response(
                    'error', 'Item not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            check_in = data['check_in']
            check_out = data['check_out']
            guests = data.get('guests', 1)

            # Check capacity
            if guests > item.capacity:
                return api_response(
                    'success',
                    'Availability checked',
                    data={
                        'is_available': False,
                        'reason': f'Capacity exceeded. Max {item.capacity} guests.',
                        'item': item.name,
                        'check_in': str(check_in),
                        'check_out': str(check_out),
                    }
                )

            # Check custom availability overrides
            blocked_dates = BookableItemAvailability.objects.filter(
                item=item,
                date__range=[check_in, check_out],
                is_available=False
            )
            if blocked_dates.exists():
                return api_response(
                    'success',
                    'Availability checked',
                    data={
                        'is_available': False,
                        'reason': f'Item not available on {blocked_dates.first().date}',
                        'blocked_dates': list(
                            blocked_dates.values_list(
                                'date', flat=True
                            )
                        ),
                    }
                )

            # Check policy
            try:
                policy = item.policy
                is_available, reason = policy.check_availability(
                    check_in, check_out
                )
            except BookingPolicy.DoesNotExist:
                # Default exclusive check
                overlapping = Booking.objects.filter(
                    item=item,
                    status__in=[
                        'pending', 'confirmed', 'checked_in'
                    ],
                    check_in__lt=check_out,
                    check_out__gt=check_in,
                ).exists()
                is_available = not overlapping
                reason = (
                    'Available' if is_available
                    else 'Already booked for these dates'
                )

            # Get available slots if slot-based
            available_slots = []
            try:
                if item.policy.booking_mode == 'slot_based':
                    available_slots = item.policy.get_available_slots(
                        check_in
                    )
            except BookingPolicy.DoesNotExist:
                pass

            # Calculate price
            from decimal import Decimal
            duration = (check_out - check_in).days or 1

            # Check custom pricing for dates
            custom_price = BookableItemAvailability.objects.filter(
                item=item,
                date=check_in,
                is_available=True,
                custom_price__isnull=False
            ).first()

            price_per_unit = (
                custom_price.custom_price
                if custom_price
                else item.price_per_unit
            )
            total_price = price_per_unit * duration

            return api_response(
                'success',
                'Availability checked',
                data={
                    'is_available': is_available,
                    'reason': reason,
                    'item': {
                        'id': item.id,
                        'name': item.name,
                        'item_type': item.item_type,
                        'booking_mode': (
                            item.policy.booking_mode
                            if hasattr(item, 'policy')
                            else 'exclusive'
                        ),
                    },
                    'check_in': str(check_in),
                    'check_out': str(check_out),
                    'duration': duration,
                    'price_per_unit': str(price_per_unit),
                    'total_price': str(total_price),
                    'available_slots': available_slots,
                }
            )

        return api_response(
            'error', 'Invalid data',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class GetAvailableSlotsView(APIView):
    """Get available time slots for a date"""
    permission_classes = []

    def get(self, request, item_id):
        try:
            item = BookableItem.objects.get(
                pk=item_id, is_active=True
            )
        except BookableItem.DoesNotExist:
            return api_response(
                'error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        date_str = request.query_params.get('date')
        if not date_str:
            return api_response(
                'error', 'date parameter required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        from datetime import date
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return api_response(
                'error', 'Invalid date format. Use YYYY-MM-DD',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            policy = item.policy
            if policy.booking_mode != 'slot_based':
                return api_response(
                    'error',
                    'This item does not use slot-based booking',
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            slots = policy.get_available_slots(target_date)
        except BookingPolicy.DoesNotExist:
            return api_response(
                'error', 'No booking policy configured',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        available = [s for s in slots if s['is_available']]

        return api_response(
            'success',
            f'{len(available)} slots available on {date_str}',
            data={
                'date': date_str,
                'item': item.name,
                'total_slots': len(slots),
                'available_slots': len(available),
                'slots': slots,
            }
        )


# ─── Booking Views ────────────────────────────────

class BookingListCreateView(APIView):
    """List and create bookings"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user)

        booking_status = request.query_params.get('status')
        business_id    = request.query_params.get('business')

        if booking_status:
            bookings = bookings.filter(status=booking_status)
        if business_id:
            bookings = bookings.filter(
                business__id=business_id
            )

        serializer = BookingSerializer(
            bookings, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Bookings retrieved successfully',
            data={
                'count': bookings.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Create a booking with availability check"""
        serializer = CreateBookingSerializer(
            data=request.data
        )
        if serializer.is_valid():
            data = serializer.validated_data

            # Get item
            try:
                item = BookableItem.objects.get(
                    pk=data['item_id'],
                    is_active=True
                )
            except BookableItem.DoesNotExist:
                return api_response(
                    'error', 'Item not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            check_in  = data['check_in']
            check_out = data['check_out']
            guests    = data.get('guests', 1)

            # Check capacity
            if guests > item.capacity:
                return api_response(
                    'error',
                    f'Exceeds capacity. Max {item.capacity} guests allowed.',
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            
            # ── Subscription check ──
            try:
                sub = (
                    item.business.subscription
                    if item.business else None
                )
                if sub:
                    policy_mode = 'exclusive'
                    try:
                        policy_mode = item.policy.booking_mode
                    except Exception:
                        pass
                    can_book, reason = sub.can_accept_bookings(
                        policy_mode
                    )
                    if not can_book:
                        return api_response(
                            'error',
                            reason,
                            http_status=status.HTTP_403_FORBIDDEN
                        )
            except Exception as e:
                print(f"Subscription check error: {e}")

            # ── KYC check ──
            if getattr(item, 'requires_kyc', False):
                try:
                    from apps.kyc.utils import check_kyc_required
                    is_required, is_verified, kyc_profile = (
                        check_kyc_required(item, request.user)
                    )
                    if is_required and not is_verified:
                        return api_response(
                            'error',
                            'Identity verification (KYC) is required '
                            'to book this item. Please complete KYC '
                            'at /api/v1/kyc/initiate/',
                            data={
                                'kyc_required': True,
                                'kyc_status': (
                                    kyc_profile.status
                                    if kyc_profile
                                    else 'not_started'
                                ),
                                'kyc_url': '/api/v1/kyc/initiate/',
                            },
                            http_status=status.HTTP_403_FORBIDDEN
                        )
                except Exception as e:
                    print(f"KYC check error: {e}")

            # ── Availability check ──
            is_available = True
            reason = 'Available'

            try:
                policy = item.policy
                is_available, reason = policy.check_availability(
                    check_in, check_out
                )
            except BookingPolicy.DoesNotExist:
                # Default: exclusive overlap check
                overlapping = Booking.objects.filter(
                    item=item,
                    status__in=[
                        'pending', 'confirmed', 'checked_in'
                    ],
                    check_in__lt=check_out,
                    check_out__gt=check_in,
                ).exists()
                is_available = not overlapping
                reason = (
                    'Already booked for these dates'
                    if not is_available else 'Available'
                )

            if not is_available:
                return api_response(
                    'error',
                    f'Not available: {reason}',
                    http_status=status.HTTP_409_CONFLICT
                )

            # ── Calculate price ──
            duration = (check_out - check_in).days or 1

            # Custom pricing
            custom_price = BookableItemAvailability.objects.filter(
                item=item,
                date=check_in,
                is_available=True,
                custom_price__isnull=False
            ).first()
            price_per_unit = (
                custom_price.custom_price
                if custom_price
                else item.price_per_unit
            )

            from decimal import Decimal
            subtotal = price_per_unit * duration
            total = subtotal

            # Addon pricing
            addon_total = Decimal('0')
            addons_data = data.get('addons', [])
            for addon in addons_data:
                addon_price = Decimal(str(addon.get('price', 0)))
                addon_qty = int(addon.get('quantity', 1))
                addon_total += addon_price * addon_qty
            total += addon_total

            # Commission splits
            commission_rate = Decimal(
                str(item.effective_commission_rate)
            ) / 100
            vendor_rate = Decimal('0.70')
            if item.business:
                vendor_rate = Decimal(
                    str(
                        item.business.industry.vendor_commission
                    )
                ) / 100

            platform_commission = subtotal * commission_rate
            business_earnings = subtotal * vendor_rate

            # ── Create booking ──
            booking = Booking.objects.create(
                user=request.user,
                business=item.business,
                item=item,
                reference=generate_reference('BKG'),
                booking_number=generate_booking_number(),
                check_in=check_in,
                check_out=check_out,
                check_in_time=data.get('check_in_time'),
                duration=duration,
                guests=guests,
                guest_name=data['guest_name'],
                guest_email=data['guest_email'],
                guest_phone=data['guest_phone'],
                guest_id_type=data.get('guest_id_type', ''),
                guest_id_number=data.get('guest_id_number', ''),
                payment_method=data.get('payment_method', 'wallet'),
                price_per_unit=price_per_unit,
                subtotal=subtotal,
                total=total,
                platform_commission=platform_commission,
                business_earnings=business_earnings,
                special_requests=data.get('special_requests', ''),
                status=(
                    'confirmed' if item.auto_confirm
                    else 'pending'
                ),
            )

            # Create addons
            for addon in addons_data:
                BookingAddOn.objects.create(
                    booking=booking,
                    name=addon.get('name', ''),
                    price=Decimal(str(addon.get('price', 0))),
                    quantity=int(addon.get('quantity', 1)),
                    notes=addon.get('notes', ''),
                )

            # ── Handle payment ──
            payment_method = data.get('payment_method', 'wallet')
            if payment_method == 'wallet':
                from apps.wallet.utils import get_or_create_wallet
                wallet = get_or_create_wallet(request.user)

                if wallet.balance >= total:
                    ref = generate_reference('PAY')
                    success = wallet.debit(
                        amount=total,
                        description=f'Booking {booking.booking_number}',
                        reference=ref
                    )
                    
                    if success:
                        booking.payment_status = 'paid'

                        # Generate check-in code
                        import random
                        booking.checkin_code = ''.join(
                            random.choices('0123456789', k=6)
                        )

                        booking.save()

                        # Send check-in code + directions to customer
                        try:
                            from apps.bookings.utils import (
                                send_booking_checkin_notification
                            )
                            send_booking_checkin_notification(booking)
                        except Exception as e:
                            print(f"Booking notification error: {e}")

                        # Credit vendor earnings (goes to pending)
                        try:
                            from apps.wallet.earnings import (
                                credit_booking_earnings
                            )
                            credit_booking_earnings(booking)
                        except Exception as e:
                            print(f"Booking earnings credit error: {e}")

                        
                        # Credit business wallet
                        if item.business:
                            biz_wallet = get_or_create_wallet(
                                item.business.owner
                            )
                            biz_wallet.credit(
                                amount=business_earnings,
                                description=f'Booking earnings {booking.booking_number}',
                                reference=f'BIZ-{ref}'
                            )
                else:
                    shortage = total - wallet.balance
                    booking.delete()
                    return api_response(
                        'error',
                        f'Insufficient balance. Need ₦{shortage} more.',
                        data={
                            'wallet_balance': str(wallet.balance),
                            'required': str(total),
                            'shortage': str(shortage),
                        },
                        http_status=status.HTTP_402_PAYMENT_REQUIRED
                    )

            # Create tracking
            BookingTracking.objects.create(
                booking=booking,
                status=booking.status,
                description=(
                    'Booking confirmed automatically'
                    if item.auto_confirm
                    else 'Booking pending confirmation'
                ),
                updated_by=request.user
            )

            # Update item stats
            item.total_bookings += 1
            item.total_revenue += subtotal
            item.save()

            # Notify business
            if item.business:
                from apps.notifications.utils import send_notification
                send_notification(
                    user=item.business.owner,
                    title='New Booking! 🎉',
                    message=f'New booking {booking.booking_number} for {item.name}',
                    notification_type='system',
                    data={
                        'booking_id': booking.id,
                        'booking_number': booking.booking_number,
                    }
                )

            return api_response(
                'success',
                'Booking created successfully!',
                data=BookingSerializer(
                    booking,
                    context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error', 'Booking failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookingSerializer(
            booking, context={'request': request}
        )
        return api_response(
            'success',
            'Booking retrieved successfully',
            data=serializer.data
        )


class CancelBookingView(APIView):
    """Cancel a booking with refund logic"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if booking.status in ['checked_in', 'completed']:
            return api_response(
                'error',
                f'Cannot cancel a {booking.status} booking',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if booking.status == 'cancelled':
            return api_response(
                'error',
                'Booking already cancelled',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')

        # Calculate refund
        refund_amount = booking.total
        cancellation_fee = Decimal('0')

        try:
            policy = booking.item.policy
            free_cancel_hours = policy.free_cancellation_hours
            from datetime import datetime, timedelta
            hours_until_checkin = (
                datetime.combine(
                    booking.check_in,
                    datetime.min.time()
                ) - datetime.now()
            ).total_seconds() / 3600

            if hours_until_checkin < free_cancel_hours:
                # Charge cancellation fee
                fee_rate = (
                    policy.cancellation_fee_percentage / 100
                )
                cancellation_fee = booking.total * Decimal(
                    str(fee_rate)
                )
                refund_amount = booking.total - cancellation_fee

        except BookingPolicy.DoesNotExist:
            pass

        from decimal import Decimal

        # Update booking
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = reason
        booking.cancelled_by = request.user
        booking.save()

        # Refund wallet
        if (booking.payment_status == 'paid' and
                booking.payment_method == 'wallet' and
                refund_amount > 0):
            from apps.wallet.utils import get_or_create_wallet
            wallet = get_or_create_wallet(request.user)
            wallet.credit(
                amount=refund_amount,
                description=f'Refund for cancelled booking {booking.booking_number}',
                reference=f'REF-{booking.reference}'
            )
            booking.payment_status = 'refunded'
            booking.save()

            # Deduct from business
            if booking.business:
                biz_wallet = get_or_create_wallet(
                    booking.business.owner
                )
                biz_wallet.debit(
                    amount=booking.business_earnings,
                    description=f'Refund deduction for {booking.booking_number}',
                    reference=f'BREF-{booking.reference}'
                )

        # Create tracking
        BookingTracking.objects.create(
            booking=booking,
            status='cancelled',
            description=f'Booking cancelled. Reason: {reason}. Refund: ₦{refund_amount}',
            updated_by=request.user
        )

        # Notify business
        if booking.business:
            from apps.notifications.utils import send_notification
            send_notification(
                user=booking.business.owner,
                title='Booking Cancelled',
                message=f'Booking {booking.booking_number} for {booking.item.name} has been cancelled.',
                notification_type='system'
            )

        return api_response(
            'success',
            'Booking cancelled successfully',
            data={
                **BookingSerializer(
                    booking,
                    context={'request': request}
                ).data,
                'refund_amount': str(refund_amount),
                'cancellation_fee': str(cancellation_fee),
            }
        )


class VendorBookingListView(APIView):
    """Vendor views their bookings"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error', 'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        bookings = Booking.objects.filter(business=business)

        booking_status = request.query_params.get('status')
        item_id        = request.query_params.get('item')

        if booking_status:
            bookings = bookings.filter(status=booking_status)
        if item_id:
            bookings = bookings.filter(item__id=item_id)

        serializer = BookingSerializer(
            bookings, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Bookings retrieved successfully',
            data={
                'count': bookings.count(),
                'pending': bookings.filter(
                    status='pending'
                ).count(),
                'confirmed': bookings.filter(
                    status='confirmed'
                ).count(),
                'checked_in': bookings.filter(
                    status='checked_in'
                ).count(),
                'results': serializer.data
            }
        )


class VendorUpdateBookingView(APIView):
    """Vendor updates booking status"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, business_id, pk):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(pk=business_id)
            booking = Booking.objects.get(
                pk=pk, business=business
            )
        except (Business.DoesNotExist,
                Booking.DoesNotExist):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Permission denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        new_status  = request.data.get('status')
        description = request.data.get('description', '')

        valid_statuses = [
            'confirmed', 'checked_in',
            'checked_out', 'completed',
            'cancelled', 'no_show'
        ]

        if new_status not in valid_statuses:
            return api_response(
                'error', 'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = new_status
        now = timezone.now()

        if new_status == 'checked_in':
            booking.actual_check_in = now
        elif new_status in ['checked_out', 'completed']:
            booking.actual_check_out = now

        booking.save()

        status_messages = {
            'confirmed':   'Booking confirmed',
            'checked_in':  'Guest checked in successfully',
            'checked_out': 'Guest checked out successfully',
            'completed':   'Booking completed',
            'cancelled':   'Booking cancelled by vendor',
            'no_show':     'Guest did not show up',
        }

        BookingTracking.objects.create(
            booking=booking,
            status=new_status,
            description=description or status_messages.get(
                new_status, f'Status updated to {new_status}'
            ),
            updated_by=request.user
        )

        # Notify customer
        from apps.notifications.utils import send_notification
        send_notification(
            user=booking.user,
            title=f'Booking Update 📋',
            message=status_messages.get(
                new_status,
                f'Your booking {booking.booking_number} is now {new_status}'
            ),
            notification_type='system',
            data={
                'booking_id': booking.id,
                'booking_number': booking.booking_number,
                'status': new_status,
            }
        )

        return api_response(
            'success',
            f'Booking updated to {new_status}',
            data=BookingSerializer(
                booking,
                context={'request': request}
            ).data
        )


class ItemCalendarView(APIView):
    """
    Get availability calendar for an item
    Shows which dates are booked
    """
    permission_classes = []

    def get(self, request, item_id):
        try:
            item = BookableItem.objects.get(
                pk=item_id, is_active=True
            )
        except BookableItem.DoesNotExist:
            return api_response(
                'error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Get month from query params
        year  = int(request.query_params.get(
            'year',
            timezone.now().year
        ))
        month = int(request.query_params.get(
            'month',
            timezone.now().month
        ))

        from datetime import date
        from calendar import monthrange

        _, days_in_month = monthrange(year, month)
        month_start = date(year, month, 1)
        month_end   = date(year, month, days_in_month)

        # Get bookings for this month
        bookings = Booking.objects.filter(
            item=item,
            status__in=['pending', 'confirmed', 'checked_in'],
            check_in__lte=month_end,
            check_out__gte=month_start,
        )

        # Get custom availability overrides
        overrides = BookableItemAvailability.objects.filter(
            item=item,
            date__range=[month_start, month_end]
        )
        override_map = {
            str(o.date): {
                'is_available': o.is_available,
                'custom_price': str(o.custom_price) if o.custom_price else None,
                'notes': o.notes,
            }
            for o in overrides
        }

        # Build calendar
        calendar = []
        current = month_start
        while current <= month_end:
            # Check if date is booked
            day_bookings = [
                b for b in bookings
                if b.check_in <= current < b.check_out
            ]

            override = override_map.get(str(current), {})
            is_blocked = override.get(
                'is_available', True
            ) is False

            # Determine availability
            try:
                policy = item.policy
                if policy.booking_mode == 'exclusive':
                    is_available = (
                        len(day_bookings) == 0 and
                        not is_blocked
                    )
                elif policy.booking_mode == 'slot_based':
                    is_available = (
                        len(day_bookings) < policy.slots_per_day
                        and not is_blocked
                    )
                elif policy.booking_mode == 'seat_based':
                    booked_seats = sum(
                        b.guests for b in day_bookings
                    )
                    is_available = (
                        booked_seats < policy.total_seats
                        and not is_blocked
                    )
                else:
                    is_available = (
                        len(day_bookings) == 0 and
                        not is_blocked
                    )
            except BookingPolicy.DoesNotExist:
                is_available = (
                    len(day_bookings) == 0 and
                    not is_blocked
                )

            calendar.append({
                'date': str(current),
                'is_available': is_available,
                'is_blocked': is_blocked,
                'bookings_count': len(day_bookings),
                'custom_price': override.get('custom_price'),
                'price': override.get(
                    'custom_price',
                    str(item.price_per_unit)
                ),
            })

            from datetime import timedelta
            current += timedelta(days=1)

        return api_response(
            'success',
            'Calendar retrieved successfully',
            data={
                'item': {
                    'id': item.id,
                    'name': item.name,
                    'item_type': item.item_type,
                    'booking_mode': (
                        item.policy.booking_mode
                        if hasattr(item, 'policy')
                        else 'exclusive'
                    ),
                    'price_per_unit': str(item.price_per_unit),
                    'unit_label': item.unit_label,
                },
                'year': year,
                'month': month,
                'calendar': calendar,
            }
        )


class SetAvailabilityView(APIView):
    """Block or unblock specific dates"""
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        try:
            item = BookableItem.objects.get(pk=item_id)
        except BookableItem.DoesNotExist:
            return api_response(
                'error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (item.business and
                item.business.owner != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Permission denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        dates_data = request.data.get('dates', [])
        updated = []

        for entry in dates_data:
            from datetime import date
            date_obj = date.fromisoformat(entry['date'])
            avail, _ = BookableItemAvailability.objects.update_or_create(
                item=item,
                date=date_obj,
                defaults={
                    'is_available': entry.get(
                        'is_available', True
                    ),
                    'custom_price': entry.get('custom_price'),
                    'notes': entry.get('notes', ''),
                }
            )
            updated.append(
                BookableItemAvailabilitySerializer(avail).data
            )

        return api_response(
            'success',
            f'{len(updated)} dates updated successfully',
            data=updated
        )

class BookingPaymentView(APIView):
    """Manage booking payments"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        payments = booking.payments.all()
        total_paid = sum(
            p.amount for p in payments
            if p.status == 'success'
        )
        total_refunded = sum(
            p.refunded_amount for p in payments
        )

        serializer = BookingPaymentSerializer(
            payments, many=True
        )
        return api_response(
            'success',
            'Booking payments retrieved successfully',
            data={
                'total_paid': str(total_paid),
                'total_refunded': str(total_refunded),
                'balance_due': str(
                    booking.total - total_paid
                ),
                'count': payments.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        """Record a payment for a booking"""
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        amount = request.data.get('amount')
        gateway = request.data.get('gateway', 'wallet')
        payment_type = request.data.get(
            'payment_type', 'full'
        )

        if not amount:
            return api_response(
                'error', 'Amount is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        payment = BookingPayment.objects.create(
            booking=booking,
            payment_type=payment_type,
            gateway=gateway,
            amount=amount,
            reference=generate_reference('BPAY'),
            paid_by=request.user,
            status='success',
            paid_at=timezone.now(),
        )

        # Update booking payment status
        total_paid = sum(
            p.amount for p in
            booking.payments.filter(status='success')
        )
        if total_paid >= booking.total:
            booking.payment_status = 'paid'
        elif total_paid > 0:
            booking.payment_status = 'partially_paid'
        booking.save()

        serializer = BookingPaymentSerializer(payment)
        return api_response(
            'success',
            'Payment recorded successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class BookingGuestView(APIView):
    """Manage additional guests"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        guests = booking.guest_list.all()
        serializer = BookingGuestSerializer(
            guests, many=True
        )
        return api_response(
            'success',
            'Guests retrieved successfully',
            data={
                'count': guests.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        """Add guest to booking"""
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check capacity
        current_guests = (
            booking.guest_list.count() + 1
        )  # +1 for primary guest
        if current_guests >= booking.item.capacity:
            return api_response(
                'error',
                f'Maximum capacity ({booking.item.capacity}) reached',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BookingGuestSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(booking=booking)
            return api_response(
                'success',
                'Guest added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Failed to add guest',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, guest_id):
        """Remove a guest"""
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
            guest = BookingGuest.objects.get(
                pk=guest_id, booking=booking
            )
            guest.delete()
            return api_response(
                'success', 'Guest removed successfully'
            )
        except (Booking.DoesNotExist,
                BookingGuest.DoesNotExist):
            return api_response(
                'error', 'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )


class ValidateCouponView(APIView):
    """Validate and preview coupon discount"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').upper()
        item_id = request.data.get('item_id')
        booking_amount = request.data.get('amount', 0)
        nights = request.data.get('nights', 1)

        if not code:
            return api_response(
                'error', 'Coupon code is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            coupon = BookingCoupon.objects.get(code=code)
        except BookingCoupon.DoesNotExist:
            return api_response(
                'error', 'Invalid coupon code',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if not coupon.is_valid:
            return api_response(
                'error', 'Coupon is no longer valid',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check per user limit
        user_uses = CouponUsage.objects.filter(
            coupon=coupon,
            user=request.user
        ).count()

        if user_uses >= coupon.per_user_limit:
            return api_response(
                'error',
                f'You have already used this coupon {coupon.per_user_limit} time(s)',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        discount = coupon.calculate_discount(
            booking_amount, nights
        )

        return api_response(
            'success',
            f'Coupon valid! You save ₦{discount}',
            data={
                'coupon': BookingCouponSerializer(coupon).data,
                'discount_amount': str(discount),
                'original_amount': str(booking_amount),
                'final_amount': str(
                    float(booking_amount) - float(discount)
                ),
            }
        )


class BookingCouponListCreateView(APIView):
    """Manage coupons"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == 'admin':
            coupons = BookingCoupon.objects.all()
        else:
            coupons = BookingCoupon.objects.filter(
                business__owner=request.user
            )

        serializer = BookingCouponSerializer(
            coupons, many=True
        )
        return api_response(
            'success',
            'Coupons retrieved successfully',
            data={
                'count': coupons.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = BookingCouponSerializer(
            data=request.data
        )
        if serializer.is_valid():
            coupon = serializer.save(
                created_by=request.user
            )
            return api_response(
                'success',
                'Coupon created successfully',
                data=BookingCouponSerializer(coupon).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BookingInvoiceView(APIView):
    """Get or generate booking invoice"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        is_owner = booking.user == request.user
        is_vendor = (
            booking.business and
            booking.business.owner == request.user
        )
        if not is_owner and not is_vendor and request.user.role != 'admin':
            return api_response(
                'error', 'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        # Generate if not exists
        invoice = BookingInvoice.generate_for_booking(booking)

        serializer = BookingInvoiceSerializer(invoice)
        return api_response(
            'success',
            'Invoice retrieved successfully',
            data=serializer.data
        )


class BookingReminderView(APIView):
    """Manage booking reminders"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        reminders = booking.reminders.all()
        serializer = BookingReminderSerializer(
            reminders, many=True
        )
        return api_response(
            'success',
            'Reminders retrieved successfully',
            data={
                'count': reminders.count(),
                'pending': reminders.filter(
                    status='pending'
                ).count(),
                'sent': reminders.filter(
                    status='sent'
                ).count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        """Create custom reminder"""
        try:
            booking = Booking.objects.get(
                pk=pk, user=request.user
            )
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = BookingReminderSerializer(
            data=request.data
        )
        if serializer.is_valid():
            reminder = serializer.save(
                booking=booking,
                recipient=request.user,
                reminder_type='custom',
            )
            return api_response(
                'success',
                'Reminder created successfully',
                data=BookingReminderSerializer(
                    reminder
                ).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

class BookingCheckInView(APIView):
    """
    Vendor/staff marks a booking as checked in using the check-in code.
    POST /api/v1/bookings/<pk>/check-in/
    Body: { "checkin_code": "654321" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from django.utils import timezone
        from apps.notifications.utils import send_notification
        from apps.wallet.earnings import settle_booking_earnings

        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Only business owner/staff can check in
        if (
            not booking.business or
            booking.business.owner != request.user
        ):
            return api_response(
                'error',
                'Only the business owner can check in guests',
                http_status=status.HTTP_403_FORBIDDEN
            )

        if booking.status == 'checked_in':
            return api_response(
                'error', 'Guest already checked in',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if booking.status not in ['pending', 'confirmed']:
            return api_response(
                'error',
                f'Cannot check in a booking with '
                f'status: {booking.status}',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Verify check-in code
        checkin_code = request.data.get(
            'checkin_code', ''
        ).strip()

        if not checkin_code:
            return api_response(
                'error', 'Check-in code is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if checkin_code != booking.checkin_code:
            return api_response(
                'error', 'Invalid check-in code',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Mark as checked in
        now = timezone.now()
        booking.status = 'checked_in'
        booking.actual_check_in = now
        booking.save()

        # Create tracking entry
        BookingTracking.objects.create(
            booking=booking,
            status='checked_in',
            description=(
                f'Guest {booking.guest_name} checked in '
                f'via code {booking.checkin_code}'
            ),
            updated_by=request.user,
        )

        # Settle vendor earnings (pending → available)
        try:
            settle_booking_earnings(booking)
        except Exception as e:
            print(f"Booking settlement error: {e}")

        # Notify customer
        send_notification(
            user=booking.user,
            title='Checked In ✅',
            message=(
                f'You have been checked in at '
                f'{booking.item.name}. Enjoy your stay!'
            ),
            notification_type='booking',
            data={'booking_id': booking.id}
        )

        return api_response(
            'success',
            f'Guest {booking.guest_name} checked in successfully!',
            data=BookingSerializer(
                booking, context={'request': request}
            ).data
        )


class BookingCheckOutView(APIView):
    """
    Vendor/staff marks a booking as checked out.
    POST /api/v1/bookings/<pk>/check-out/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from django.utils import timezone
        from apps.notifications.utils import send_notification

        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return api_response(
                'error', 'Booking not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (
            not booking.business or
            booking.business.owner != request.user
        ):
            return api_response(
                'error',
                'Only the business owner can check out guests',
                http_status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != 'checked_in':
            return api_response(
                'error',
                'Guest must be checked in before checking out',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()
        booking.status = 'checked_out'
        booking.actual_check_out = now
        booking.save()

        BookingTracking.objects.create(
            booking=booking,
            status='checked_out',
            description=f'Guest {booking.guest_name} checked out',
            updated_by=request.user,
        )

        # Notify customer
        send_notification(
            user=booking.user,
            title='Checked Out',
            message=(
                f'You have been checked out from '
                f'{booking.item.name}. Thank you!'
            ),
            notification_type='booking',
            data={'booking_id': booking.id}
        )

        return api_response(
            'success',
            f'Guest {booking.guest_name} checked out successfully!',
            data=BookingSerializer(
                booking, context={'request': request}
            ).data
        )