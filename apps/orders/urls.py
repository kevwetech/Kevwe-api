from django.urls import path
from .views import (
    CartView,
    AddToCartView,
    UpdateCartItemView,
    OrderListCreateView,
    OrderDetailView,
    CancelOrderView,
    RateOrderView,
    VendorOrderListView,
    VendorUpdateOrderView,
    AdminOrderListView,
)

urlpatterns = [
    # Cart
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='add_to_cart'),
    path('cart/items/<int:item_id>/', UpdateCartItemView.as_view(), name='update_cart_item'),

    # Customer orders
    path('', OrderListCreateView.as_view(), name='orders'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel_order'),
    path('<int:pk>/rate/', RateOrderView.as_view(), name='rate_order'),

    # Vendor orders
    path('business/<int:business_id>/', VendorOrderListView.as_view(), name='vendor_orders'),
    path('business/<int:business_id>/<int:pk>/', VendorUpdateOrderView.as_view(), name='vendor_update_order'),

    # Admin
    path('admin/', AdminOrderListView.as_view(), name='admin_orders'),
]