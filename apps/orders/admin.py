from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, OrderTracking

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__email',)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'created_at')
    search_fields = ('cart__user__email',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'user', 'status',
        'payment_status', 'total', 'created_at'
    )
    list_filter = ('status', 'payment_status')
    search_fields = ('reference', 'user__email')
    ordering = ('-created_at',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'quantity', 'subtotal')
    search_fields = ('order__reference',)

@admin.register(OrderTracking)
class OrderTrackingAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'created_at')
    list_filter = ('status',)
    ordering = ('-created_at',)