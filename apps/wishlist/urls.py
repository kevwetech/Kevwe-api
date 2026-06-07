from django.urls import path
from .views import (
    WishlistView,
    WishlistItemView,
    ClearWishlistView,
    CheckWishlistView,
)

urlpatterns = [
    path('', WishlistView.as_view(), name='wishlist'),
    path('<int:pk>/', WishlistItemView.as_view(), name='wishlist_item'),
    path('clear/', ClearWishlistView.as_view(), name='wishlist_clear'),
    path('check/<int:product_id>/', CheckWishlistView.as_view(), name='wishlist_check'),
]