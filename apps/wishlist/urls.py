from django.urls import path
from .views import (
    WishlistView,
    WishlistItemView,
    ClearWishlistView,
    CheckWishlistView,
    WishlistCollectionListCreateView,
    WishlistCollectionDetailView,
)

urlpatterns = [
    # Collections (before <int:pk> item route to avoid capture)
    path('collections/', WishlistCollectionListCreateView.as_view(), name='wishlist_collections'),
    path('collections/<int:pk>/', WishlistCollectionDetailView.as_view(), name='wishlist_collection_detail'),

    # Items
    path('', WishlistView.as_view(), name='wishlist'),
    path('clear/', ClearWishlistView.as_view(), name='wishlist_clear'),
    path('check/<int:item_id>/', CheckWishlistView.as_view(), name='wishlist_check'),
    path('<int:pk>/', WishlistItemView.as_view(), name='wishlist_item'),
]