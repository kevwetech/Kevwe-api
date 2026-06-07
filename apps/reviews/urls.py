from django.urls import path
from .views import ProductReviewListCreateView, ReviewDetailView

urlpatterns = [
    path(
        'products/<int:product_id>/reviews/',
        ProductReviewListCreateView.as_view(),
        name='product_reviews'
    ),
    path(
        'reviews/<int:pk>/',
        ReviewDetailView.as_view(),
        name='review_detail'
    ),
]