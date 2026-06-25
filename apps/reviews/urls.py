from django.urls import path
from .views import (
    ReviewListCreateView,
    ReviewDetailView,
    ReplyReviewView,
    ReviewHelpfulnessView,
    ReviewReportView,
    MyReviewsView,
    AdminReviewListView,
)

urlpatterns = [
    # Reviews
    path('', ReviewListCreateView.as_view(), name='reviews'),
    path('<int:pk>/', ReviewDetailView.as_view(), name='review_detail'),
    path('<int:pk>/reply/', ReplyReviewView.as_view(), name='reply_review'),
    path('<int:pk>/helpful/', ReviewHelpfulnessView.as_view(), name='review_helpful'),
    path('<int:pk>/report/', ReviewReportView.as_view(), name='report_review'),

    # My reviews
    path('my/', MyReviewsView.as_view(), name='my_reviews'),

    # Admin
    path('admin/', AdminReviewListView.as_view(), name='admin_reviews'),
    path('admin/<int:pk>/', AdminReviewListView.as_view(), name='admin_review_update'),
]