from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin, IsVendor
from apps.common.utils import generate_reference, generate_order_number
from .models import Cart, CartItem, Order, OrderItem, OrderTracking
from apps.wallet.views import get_or_create_vendor_wallet
from apps.commissions.utils import get_commission_rule
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    OrderSerializer,
    CreateOrderSerializer,
    RateOrderSerializer,
)


# ─── Cart Views ───────────────────────────────────

class CartView(APIView):
    """Get or clear cart"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(
            user=request.user
        )
        serializer = CartSerializer(
            cart, context={'request': request}
        )
        return api_response(
            'success',
            'Cart retrieved successfully',
            data=serializer.data
        )

    def delete(self, request):
        """Clear cart"""
        try:
            cart = Cart.objects.get(user=request.user)
            cart.clear()
            cart.business = None
            cart.save()
        except Cart.DoesNotExist:
            pass
        return api_response(
            'success',
            'Cart cleared successfully'
        )


class AddToCartView(APIView):
    """Add item to cart"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Get business
            from apps.marketplace.models import Business
            try:
                business = Business.objects.get(
                    pk=data['business_id'],
                    status='active',
                    is_active=True
                )
            except Business.DoesNotExist:
                return api_response(
                    'error',
                    'Business not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            # Check business accepts orders
            if not business.accepts_orders:
                return api_response(
                    'error',
                    f'{business.name} is not accepting orders right now',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Get product
            from apps.catalog.models import Product, ProductVariant
            try:
                product = Product.objects.get(
                    pk=data['product_id'],
                    business=business,
                    status='active',
                    is_active=True
                )
            except Product.DoesNotExist:
                return api_response(
                    'error',
                    'Product not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            # Check product available
            if not product.is_available:
                return api_response(
                    'error',
                    f'{product.name} is not available',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Get variant
            variant = None
            if data.get('variant_id'):
                variant = ProductVariant.objects.filter(
                    pk=data['variant_id'],
                    product=product,
                    is_active=True
                ).first()
                if not variant:
                    return api_response(
                        'error',
                        'Variant not found',
                        http_status=status.HTTP_404_NOT_FOUND
                    )

            # Get or create cart
            cart, _ = Cart.objects.get_or_create(
                user=request.user
            )

            # Check cart business consistency
            if cart.business and cart.business != business:
                return api_response(
                    'error',
                    f'Your cart has items from {cart.business.name}. Clear cart to order from {business.name}.',
                    data={
                        'current_business': cart.business.name,
                        'current_business_id': cart.business.id,
                    },
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Set cart business
            cart.business = business
            cart.save()

            # Calculate addon price
            selected_addons = data.get('selected_addons', [])
            addon_price = sum(
                float(item.get('price', 0))
                for group in selected_addons
                for item in group.get('items', [])
            )

            # Get unit price
            unit_price = variant.price if variant else product.price

            # Add to cart or update quantity
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=variant,
                defaults={
                    'quantity': data['quantity'],
                    'unit_price': unit_price,
                    'addon_price': addon_price,
                    'selected_addons': selected_addons,
                    'special_instructions': data.get(
                        'special_instructions', ''
                    ),
                }
            )

            if not created:
                cart_item.quantity += data['quantity']
                cart_item.selected_addons = selected_addons
                cart_item.addon_price = addon_price
                cart_item.special_instructions = data.get(
                    'special_instructions', ''
                )
                cart_item.save()

            # Return updated cart
            cart_serializer = CartSerializer(
                cart, context={'request': request}
            )
            return api_response(
                'success',
                f'{product.name} added to cart',
                data=cart_serializer.data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Failed to add to cart',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class UpdateCartItemView(APIView):
    """Update or remove cart item"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        try:
            cart = Cart.objects.get(user=request.user)
            item = CartItem.objects.get(
                pk=item_id, cart=cart
            )
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return api_response(
                'error',
                'Cart item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        quantity = request.data.get('quantity')
        special_instructions = request.data.get(
            'special_instructions'
        )

        if quantity is not None:
            if int(quantity) <= 0:
                item.delete()
                return api_response(
                    'success',
                    'Item removed from cart'
                )
            item.quantity = int(quantity)

        if special_instructions is not None:
            item.special_instructions = special_instructions

        item.save()

        cart_serializer = CartSerializer(
            cart, context={'request': request}
        )
        return api_response(
            'success',
            'Cart updated successfully',
            data=cart_serializer.data
        )

    def delete(self, request, item_id):
        try:
            cart = Cart.objects.get(user=request.user)
            item = CartItem.objects.get(
                pk=item_id, cart=cart
            )
            item.delete()
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return api_response(
                'error',
                'Cart item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        cart_serializer = CartSerializer(
            cart, context={'request': request}
        )
        return api_response(
            'success',
            'Item removed from cart',
            data=cart_serializer.data
        )


# ─── Order Views ──────────────────────────────────

class OrderListCreateView(APIView):
    """List user orders and create new order"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user)

        order_status = request.query_params.get('status')
        business_id  = request.query_params.get('business')

        if order_status:
            orders = orders.filter(status=order_status)
        if business_id:
            orders = orders.filter(business__id=business_id)

        serializer = OrderSerializer(
            orders, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Orders retrieved successfully',
            data={
                'count': orders.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Create order from cart"""
        serializer = CreateOrderSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Get cart
            try:
                cart = Cart.objects.get(
                    user=request.user
                )
            except Cart.DoesNotExist:
                return api_response(
                    'error',
                    'Cart is empty',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            if not cart.items.exists():
                return api_response(
                    'error',
                    'Cart is empty',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            if not cart.business:
                return api_response(
                    'error',
                    'No business associated with cart',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            business = cart.business

            # Check min order amount
            if cart.total < business.min_order_amount:
                return api_response(
                    'error',
                    f'Minimum order amount is ₦{business.min_order_amount}. Your cart total is ₦{cart.total}',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Resolve delivery address
            delivery_address_ref = None
            delivery_name = data.get('delivery_name', '')
            delivery_phone = data.get('delivery_phone', '')
            delivery_address_str = data.get('delivery_address', '')
            delivery_city_str = data.get('delivery_city', '')
            delivery_state_str = data.get('delivery_state', '')
            delivery_lat = data.get('delivery_lat')
            delivery_lng = data.get('delivery_lng')
            delivery_city_ref = None
            delivery_zone = None

            if data.get('delivery_address_id'):
                from apps.locations.models import Address
                addr = Address.objects.filter(
                    pk=data['delivery_address_id'],
                    user=request.user
                ).first()
                if addr:
                    delivery_address_ref = addr
                    delivery_name = request.user.full_name
                    delivery_phone = request.user.phone
                    delivery_address_str = addr.street_address
                    delivery_city_str = addr.city.name if addr.city else ''
                    delivery_state_str = addr.state.name if addr.state else ''
                    delivery_lat = addr.latitude
                    delivery_lng = addr.longitude
                    delivery_city_ref = addr.city
                    delivery_zone = addr.zone
            else:
                if data.get('city_id'):
                    from apps.locations.models import City
                    delivery_city_ref = City.objects.filter(
                        pk=data['city_id']
                    ).first()
                if data.get('zone_id'):
                    from apps.locations.models import Zone
                    delivery_zone = Zone.objects.filter(
                        pk=data['zone_id']
                    ).first()

            # Calculate delivery fee
            delivery_fee = business.delivery_fee
            if delivery_zone:
                delivery_fee = (
                    delivery_fee *
                    delivery_zone.price_multiplier
                )

            # Create order
            order = Order.objects.create(
                user=request.user,
                business=business,
                reference=generate_reference('ORD'),
                order_number=generate_order_number(),
                order_type=data.get('order_type', 'delivery'),
                payment_method=data.get('payment_method', 'wallet'),
                delivery_address_ref=delivery_address_ref,
                delivery_name=delivery_name,
                delivery_phone=delivery_phone,
                delivery_address=delivery_address_str,
                delivery_city=delivery_city_str,
                delivery_state=delivery_state_str,
                delivery_lat=delivery_lat,
                delivery_lng=delivery_lng,
                delivery_city_ref=delivery_city_ref,
                delivery_zone=delivery_zone,
                delivery_fee=delivery_fee,
                estimated_delivery_time=(
                    business.delivery_time_minutes
                ),
                scheduled_time=data.get('scheduled_time'),
                special_instructions=data.get(
                    'special_instructions', ''
                ),
                notes=data.get('notes', ''),
            )

            # Create order items from cart
            for cart_item in cart.items.all():
                product_image = None
                if cart_item.product and cart_item.product.cover_image:
                    product_image = request.build_absolute_uri(
                        cart_item.product.cover_image.url
                    )

                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    product_name=cart_item.product.name if cart_item.product else '',
                    variant_name=cart_item.variant.name if cart_item.variant else '',
                    product_image=product_image,
                    unit_price=cart_item.unit_price,
                    addon_price=cart_item.addon_price,
                    quantity=cart_item.quantity,
                    selected_addons=cart_item.selected_addons,
                    special_instructions=cart_item.special_instructions or '',
                )

            # Calculate totals and commissions
            order.calculate_totals()

            # Handle payment
            payment_method = data.get('payment_method', 'wallet')

            if payment_method == 'wallet':
                from apps.wallet.utils import get_or_create_wallet
                wallet = get_or_create_wallet(request.user)

                if wallet.balance >= order.total:
                    ref = generate_reference('PAY')
                    success = wallet.debit(
                        amount=order.total,
                        description=f'Order {order.order_number} payment',
                        reference=ref
                    )
                    if success:
                        order.payment_status = 'paid'
                        order.save()

                        # Credit business wallet
                        
                        vendor_wallet = get_or_create_vendor_wallet(business)
                        commission_rule = get_commission_rule(business)
                        settlement_days = (
                            commission_rule.settlement_period_days
                            if commission_rule
                            else vendor_wallet.settlement_period_days
                        )
                        vendor_wallet.credit_earning(
                            amount=order.business_earnings,
                            description=f'Earnings from order {order.order_number}',
                            reference=f'BIZ-{ref}',
                            order=order,
                            settlement_days=settlement_days,
                        )
                else:
                    shortage = order.total - wallet.balance
                    order.delete()
                    return api_response(
                        'error',
                        f'Insufficient wallet balance. You need ₦{shortage} more.',
                        data={
                            'wallet_balance': str(wallet.balance),
                            'required': str(order.total),
                            'shortage': str(shortage),
                            'alternatives': [
                                {
                                    'method': 'paystack',
                                    'message': 'Pay with Paystack'
                                },
                                {
                                    'method': 'flutterwave',
                                    'message': 'Pay with Flutterwave'
                                },
                            ]
                        },
                        http_status=status.HTTP_402_PAYMENT_REQUIRED
                    )

            # Create initial tracking
            OrderTracking.objects.create(
                order=order,
                status='pending',
                description='Order placed successfully',
                updated_by=request.user
            )

            # Update business stats
            business.total_orders += 1
            business.total_revenue += order.subtotal
            business.save()

            # Update product stats
            for item in order.items.all():
                if item.product:
                    item.product.total_sold += item.quantity
                    item.product.total_revenue += item.subtotal
                    item.product.save()

            # Auto create commission record
            try:
                from apps.commissions.utils import create_order_commission
                create_order_commission(order)
            except Exception as e:
                print(f"Commission creation error: {e}")
            
            # Credit vendor + driver earnings (goes to pending)
            try:
                from apps.wallet.earnings import credit_order_earnings
                credit_order_earnings(order)
            except Exception as e:
                print(f"Order earnings credit error: {e}")

            # Fraud check on order placement
            try:
                from apps.fraud.utils import (
                    score_order, evaluate_and_alert
                )
                score, rules = score_order(request.user, order)
                if score > 0:
                    evaluate_and_alert(
                        alert_type='order',
                        user=request.user,
                        score=score,
                        triggered_rules=rules,
                        context={
                            'order_id': order.id,
                            'order_number': order.order_number,
                            'total': str(order.total),
                        }
                    )
            except Exception as e:
                print(f"Fraud check error: {e}")

            # Auto create delivery request for delivery orders
            try:
                from apps.deliveries.utils import create_delivery_for_order
                create_delivery_for_order(order)
            except Exception as e:
                print(f"Delivery creation error: {e}")

            # Clear cart
            cart.clear()
            cart.business = None
            cart.save()

            # Notify business
            from apps.notifications.utils import send_notification
            send_notification(
                user=business.owner,
                title='New Order! 🎉',
                message=f'New order {order.order_number} received for ₦{order.total}',
                notification_type='system',
                data={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'total': str(order.total),
                }
            )

            # Notify customer
            send_notification(
                user=request.user,
                title='Order Placed! 🎉',
                message=f'Your order {order.order_number} has been placed successfully.',
                notification_type='system',
                data={
                    'order_id': order.id,
                    'order_number': order.order_number,
                }
            )

            return api_response(
                'success',
                'Order placed successfully!',
                data=OrderSerializer(
                    order, context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Failed to create order',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class OrderDetailView(APIView):
    """Get single order"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Order.objects.get(pk=pk, user=user)
        except Order.DoesNotExist:
            return None

    def get(self, request, pk):
        order = self.get_object(pk, request.user)
        if not order:
            return api_response(
                'error',
                'Order not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = OrderSerializer(
            order, context={'request': request}
        )
        return api_response(
            'success',
            'Order retrieved successfully',
            data=serializer.data
        )


class CancelOrderView(APIView):
    """Cancel an order"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = Order.objects.get(
                pk=pk, user=request.user
            )
        except Order.DoesNotExist:
            return api_response(
                'error',
                'Order not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Only pending orders can be cancelled
        if order.status not in ['pending', 'confirmed']:
            return api_response(
                'error',
                f'Cannot cancel order in {order.status} status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')

        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.cancelled_by = request.user
        order.cancellation_reason = reason
        order.save()

        # Refund wallet if paid
        if order.payment_status == 'paid':
            if order.payment_method == 'wallet':
                from apps.wallet.utils import get_or_create_wallet
                wallet = get_or_create_wallet(request.user)
                wallet.credit(
                    amount=order.total,
                    description=f'Refund for cancelled order {order.order_number}',
                    reference=f'REF-{order.reference}'
                )
                order.payment_status = 'refunded'
                order.save()

                # Deduct from business wallet
                from apps.wallet.utils import get_or_create_wallet as get_wallet
                business_wallet = get_wallet(order.business.owner)
                business_wallet.debit(
                    amount=order.business_earnings,
                    description=f'Refund deduction for cancelled order {order.order_number}',
                    reference=f'BREF-{order.reference}'
                )

        # Create tracking
        OrderTracking.objects.create(
            order=order,
            status='cancelled',
            description=f'Order cancelled. Reason: {reason}',
            updated_by=request.user
        )

        # Notify business
        from apps.notifications.utils import send_notification
        send_notification(
            user=order.business.owner,
            title='Order Cancelled',
            message=f'Order {order.order_number} has been cancelled by customer.',
            notification_type='system'
        )

        return api_response(
            'success',
            'Order cancelled successfully',
            data=OrderSerializer(
                order, context={'request': request}
            ).data
        )


class RateOrderView(APIView):
    """Rate a completed order"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = Order.objects.get(
                pk=pk, user=request.user
            )
        except Order.DoesNotExist:
            return api_response(
                'error',
                'Order not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if order.status != 'delivered':
            return api_response(
                'error',
                'Only delivered orders can be rated',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        if order.rating:
            return api_response(
                'error',
                'Order already rated',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RateOrderSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            order.rating = data['rating']
            order.review = data.get('review', '')
            order.rated_at = timezone.now()
            order.save()

            # Update business rating
            business = order.business
            if business:
                all_ratings = Order.objects.filter(
                    business=business,
                    rating__isnull=False
                )
                avg = sum(
                    o.rating for o in all_ratings
                ) / all_ratings.count()
                business.rating = round(avg, 2)
                business.total_ratings = all_ratings.count()
                business.save()

            return api_response(
                'success',
                'Order rated successfully',
                data=OrderSerializer(
                    order, context={'request': request}
                ).data
            )

        return api_response(
            'error',
            'Rating failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


# ─── Vendor Order Views ───────────────────────────

class VendorOrderListView(APIView):
    """Vendor views their business orders"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        from apps.marketplace.models import Business
        try:
            business = Business.objects.get(
                pk=business_id
            )
        except Business.DoesNotExist:
            return api_response(
                'error',
                'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        from apps.marketplace.models import BusinessStaff
        is_owner = business.owner == request.user
        has_permission = BusinessStaff.objects.filter(
            business=business,
            user=request.user,
            status='active'
        ).filter(
            role__permissions__codename='can_manage_orders'
        ).exists()

        if not is_owner and not has_permission:
            return api_response(
                'error',
                'You do not have permission to view orders',
                http_status=status.HTTP_403_FORBIDDEN
            )

        orders = Order.objects.filter(business=business)

        order_status = request.query_params.get('status')
        payment_status = request.query_params.get('payment')

        if order_status:
            orders = orders.filter(status=order_status)
        if payment_status:
            orders = orders.filter(payment_status=payment_status)

        serializer = OrderSerializer(
            orders, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Orders retrieved successfully',
            data={
                'count': orders.count(),
                'pending': orders.filter(
                    status='pending'
                ).count(),
                'confirmed': orders.filter(
                    status='confirmed'
                ).count(),
                'preparing': orders.filter(
                    status='preparing'
                ).count(),
                'delivered': orders.filter(
                    status='delivered'
                ).count(),
                'results': serializer.data
            }
        )


class VendorUpdateOrderView(APIView):
    """Vendor updates order status"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, business_id, pk):
        from apps.marketplace.models import Business, BusinessStaff
        try:
            business = Business.objects.get(pk=business_id)
        except Business.DoesNotExist:
            return api_response(
                'error',
                'Business not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        is_owner = business.owner == request.user
        has_permission = BusinessStaff.objects.filter(
            business=business,
            user=request.user,
            status='active'
        ).filter(
            role__permissions__codename='can_manage_orders'
        ).exists()

        if not is_owner and not has_permission:
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            order = Order.objects.get(
                pk=pk, business=business
            )
        except Order.DoesNotExist:
            return api_response(
                'error',
                'Order not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        description = request.data.get('description', '')

        valid_statuses = [
            'confirmed', 'preparing',
            'ready', 'out_for_delivery',
            'delivered', 'cancelled', 'failed'
        ]

        if new_status not in valid_statuses:
            return api_response(
                'error',
                f'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        old_status = order.status
        order.status = new_status

        # Auto set timestamps
        now = timezone.now()
        if new_status == 'confirmed':
            order.confirmed_at = now
        elif new_status == 'preparing':
            order.preparing_at = now
        elif new_status == 'ready':
            order.ready_at = now
        elif new_status == 'delivered':
            order.delivered_at = now
        elif new_status == 'cancelled':
            order.cancelled_at = now
            order.cancellation_reason = request.data.get(
                'reason', ''
            )
            order.cancelled_by = request.user

        order.save()

        # Create tracking entry
        status_messages = {
            'confirmed':       'Order confirmed by restaurant',
            'preparing':       'Your order is being prepared',
            'ready':           'Order is ready for pickup/delivery',
            'out_for_delivery': 'Order is on the way',
            'delivered':       'Order delivered successfully',
            'cancelled':       'Order cancelled by vendor',
        }

        OrderTracking.objects.create(
            order=order,
            status=new_status,
            description=description or status_messages.get(
                new_status, f'Order status updated to {new_status}'
            ),
            updated_by=request.user
        )

        # Notify customer
        from apps.notifications.utils import send_notification
        send_notification(
            user=order.user,
            title=f'Order Update 📦',
            message=status_messages.get(
                new_status,
                f'Your order {order.order_number} is now {new_status}'
            ),
            notification_type='system',
            data={
                'order_id': order.id,
                'order_number': order.order_number,
                'status': new_status,
            }
        )

        return api_response(
            'success',
            f'Order status updated to {new_status}',
            data=OrderSerializer(
                order, context={'request': request}
            ).data
        )


# ─── Admin Order Views ────────────────────────────

class AdminOrderListView(APIView):
    """Admin views all orders"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return api_response(
                'error',
                'Admin access required',
                http_status=status.HTTP_403_FORBIDDEN
            )

        orders = Order.objects.all()

        order_status   = request.query_params.get('status')
        business_id    = request.query_params.get('business')
        payment_status = request.query_params.get('payment')

        if order_status:
            orders = orders.filter(status=order_status)
        if business_id:
            orders = orders.filter(business__id=business_id)
        if payment_status:
            orders = orders.filter(payment_status=payment_status)

        serializer = OrderSerializer(
            orders, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'All orders retrieved',
            data={
                'count':     orders.count(),
                'pending':   orders.filter(status='pending').count(),
                'delivered': orders.filter(status='delivered').count(),
                'cancelled': orders.filter(status='cancelled').count(),
                'results':   serializer.data
            }
        )