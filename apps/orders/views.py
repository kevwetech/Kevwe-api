from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.products.models import Product
from apps.common.utils import generate_reference
from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
    CartSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    OrderSerializer,
    CreateOrderSerializer,
)
from apps.notifications.utils import send_order_notification
from .tracking import create_order_tracking, get_order_tracking_data
from apps.common.email import send_order_confirmation_email


# ─── CART VIEWS ────────────────────────────────────────

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get_or_create_cart(self, user):
        cart, created = Cart.objects.get_or_create(user=user)
        return cart

    def get(self, request):
        cart = self.get_or_create_cart(request.user)
        serializer = CartSerializer(cart)
        return api_response(
            'success',
            'Cart retrieved successfully',
            data=serializer.data
        )

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            product = Product.objects.get(pk=product_id)

            # Check stock
            if product.stock < quantity:
                return api_response(
                    'error',
                    f'Only {product.stock} items in stock',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            cart = self.get_or_create_cart(request.user)

            # Check if item already in cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            cart_serializer = CartSerializer(cart)
            return api_response(
                'success',
                'Item added to cart',
                data=cart_serializer.data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Failed to add to cart',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request):
        cart = self.get_or_create_cart(request.user)
        cart.items.all().delete()
        return api_response(
            'success',
            'Cart cleared successfully'
        )


class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return CartItem.objects.get(
                pk=pk,
                cart__user=user
            )
        except CartItem.DoesNotExist:
            return None

    def patch(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return api_response(
                'error',
                'Cart item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateCartItemSerializer(data=request.data)
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']

            # Check stock
            if item.product.stock < quantity:
                return api_response(
                    'error',
                    f'Only {item.product.stock} items in stock',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = quantity
            item.save()

            cart_serializer = CartSerializer(item.cart)
            return api_response(
                'success',
                'Cart updated successfully',
                data=cart_serializer.data
            )

        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return api_response(
                'error',
                'Cart item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        item.delete()
        return api_response(
            'success',
            'Item removed from cart'
        )


# ─── ORDER VIEWS ────────────────────────────────────────

class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user)

        # Filter by status
        order_status = request.query_params.get('status')
        if order_status:
            orders = orders.filter(status=order_status)

        serializer = OrderSerializer(orders, many=True)
        return api_response(
            'success',
            'Orders retrieved successfully',
            data={
                'count': orders.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if serializer.is_valid():
            # Get cart
            try:
                cart = Cart.objects.get(user=request.user)
            except Cart.DoesNotExist:
                return api_response(
                    'error',
                    'Your cart is empty',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            if not cart.items.exists():
                return api_response(
                    'error',
                    'Your cart is empty',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate totals
            subtotal = cart.total
            shipping_fee = 1500  # flat rate
            total = subtotal + shipping_fee

            # Create order
            order = Order.objects.create(
                user=request.user,
                reference=generate_reference('ORD'),
                shipping_address=serializer.validated_data['shipping_address'],
                shipping_city=serializer.validated_data['shipping_city'],
                shipping_state=serializer.validated_data['shipping_state'],
                shipping_country=serializer.validated_data.get(
                    'shipping_country', 'Nigeria'
                ),
                phone=serializer.validated_data['phone'],
                notes=serializer.validated_data.get('notes', ''),
                subtotal=subtotal,
                shipping_fee=shipping_fee,
                total=total
            )

            # Create order items from cart
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    product_price=cart_item.product.price,
                    quantity=cart_item.quantity,
                    subtotal=cart_item.subtotal
                )

                # Reduce stock
                cart_item.product.stock -= cart_item.quantity
                cart_item.product.save()

            # Clear cart after order
            cart.items.all().delete()

            send_order_notification(
                user=request.user,
                order=order,
                notification_type='order_placed'
            )
            create_order_tracking(
                order=order,
                status='pending',
                description='Order placed successfully'
            )
            send_order_confirmation_email(order)

            order_serializer = OrderSerializer(order)
            return api_response(
                'success',
                'Order placed successfully',
                data=order_serializer.data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Order failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class OrderDetailView(APIView):
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
        serializer = OrderSerializer(order)
        return api_response(
            'success',
            'Order retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        order = self.get_object(pk, request.user)
        if not order:
            return api_response(
                'error',
                'Order not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Only allow cancellation by user
        if order.status != 'pending':
            return api_response(
                'error',
                'Only pending orders can be cancelled',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'cancelled'
        order.save()

        return api_response(
            'success',
            'Order cancelled successfully',
            data=OrderSerializer(order).data
        )


class AdminOrderListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        orders = Order.objects.all()

        # Filter by status
        order_status = request.query_params.get('status')
        if order_status:
            orders = orders.filter(status=order_status)

        serializer = OrderSerializer(orders, many=True)
        return api_response(
            'success',
            'All orders retrieved',
            data={
                'count': orders.count(),
                'results': serializer.data
            }
        )


class AdminOrderUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return api_response(
                'error',
                'Order not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        payment_status = request.data.get('payment_status')

        if new_status:
            order.status = new_status
        if payment_status:
            order.payment_status = payment_status

        order.save()

        create_order_tracking(
            order=order,
            status=new_status
        )

        return api_response(
            'success',
            'Order updated successfully',
            data=OrderSerializer(order).data
        )


class OrderTrackingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist:
            return api_response(
                'error',
                'Order not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        tracking_data = get_order_tracking_data(order)
        return api_response(
            'success',
            'Order tracking retrieved successfully',
            data=tracking_data
        )