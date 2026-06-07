from django.urls import path
from .views import (
    CartView,
    CartItemView,
    OrderListCreateView,
    OrderDetailView,
    AdminOrderListView,
    AdminOrderUpdateView,
    OrderTrackingView,
)

urlpatterns = [
    # Cart
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/<int:pk>/', CartItemView.as_view(), name='cart_item'),

    # Orders
    path('', OrderListCreateView.as_view(), name='orders'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/tracking/', OrderTrackingView.as_view(), name='order_tracking'),

    # Admin
    path('admin/', AdminOrderListView.as_view(), name='admin_orders'),
    path('admin/<int:pk>/', AdminOrderUpdateView.as_view(), name='admin_order_update'),
]