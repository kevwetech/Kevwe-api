from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import Review, ReviewHelpfulness, ReviewReport
from .serializers import (
    ReviewSerializer,
    CreateReviewSerializer,
    ReplyReviewSerializer,
    ReviewHelpfulnessSerializer,
    ReviewReportSerializer,
)


def update_object_rating(objects_type, objects_id):
    """
    Auto update rating on the reviewed object
    """
    reviews = Review.objects.filter(
        objects_type=objects_type,
        objects_id=objects_id,
        status='approved'
    )
    if not reviews.exists():
        return

    avg = sum(r.rating for r in reviews) / reviews.count()
    avg = round(avg, 2)
    count = reviews.count()

    try:
        if objects_type == 'business':
            from apps.marketplace.models import Business
            obj = Business.objects.filter(pk=objects_id).first()
            if obj:
                obj.rating = avg
                obj.total_ratings = count
                obj.save()

        elif objects_type == 'product':
            from apps.catalog.models import Product
            obj = Product.objects.filter(pk=objects_id).first()
            if obj:
                obj.rating = avg
                obj.total_ratings = count
                obj.save()

        elif objects_type == 'driver':
            from apps.drivers.models import DriverProfile
            obj = DriverProfile.objects.filter(
                pk=objects_id
            ).first()
            if obj:
                obj.rating = avg
                obj.total_ratings = count
                obj.save()

    except Exception as e:
        print(f"Rating update error: {e}")


class ReviewListCreateView(APIView):
    """List and create reviews"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []

    def get(self, request):
        reviews = Review.objects.filter(status='approved')

        objects_type = request.query_params.get('type')
        objects_id = request.query_params.get('id')
        rating = request.query_params.get('rating')
        is_featured = request.query_params.get('featured')

        if objects_type:
            reviews = reviews.filter(objects_type=objects_type)
        if objects_id:
            reviews = reviews.filter(objects_id=objects_id)
        if rating:
            reviews = reviews.filter(rating=rating)
        if is_featured:
            reviews = reviews.filter(is_featured=True)

        # Rating summary
        if objects_type and objects_id:
            total = reviews.count()
            avg = (
                sum(r.rating for r in reviews) / total
                if total > 0 else 0
            )
            distribution = {
                str(i): reviews.filter(rating=i).count()
                for i in range(1, 6)
            }
        else:
            total = reviews.count()
            avg = 0
            distribution = {}

        serializer = ReviewSerializer(
            reviews, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Reviews retrieved successfully',
            data={
                'summary': {
                    'total': total,
                    'average': round(avg, 2),
                    'distribution': distribution,
                },
                'count': total,
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CreateReviewSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Check already reviewed
            if Review.objects.filter(
                user=request.user,
                objects_id=data['objects_id'],
                objects_type=data['objects_type']
            ).exists():
                return api_response(
                    'error',
                    'You have already reviewed this item',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Verify order if provided
            is_verified = False
            order = None
            if data.get('order_id'):
                from apps.orders.models import Order
                order = Order.objects.filter(
                    pk=data['order_id'],
                    user=request.user,
                    status='delivered'
                ).first()
                if order:
                    is_verified = True

            # Auto verify if reviewing
            # from a completed order
            if data['objects_type'] == 'business':
                from apps.orders.models import Order
                has_order = Order.objects.filter(
                    user=request.user,
                    business__id=data['objects_id'],
                    status='delivered'
                ).exists()
                if has_order:
                    is_verified = True

            elif data['objects_type'] == 'product':
                from apps.orders.models import OrderItem
                has_purchase = OrderItem.objects.filter(
                    order__user=request.user,
                    product__id=data['objects_id'],
                    order__status='delivered'
                ).exists()
                if has_purchase:
                    is_verified = True

            review = Review.objects.create(
                user=request.user,
                objects_id=data['objects_id'],
                objects_type=data['objects_type'],
                rating=data['rating'],
                title=data.get('title', ''),
                comment=data.get('comment', ''),
                food_rating=data.get('food_rating'),
                delivery_rating=data.get('delivery_rating'),
                service_rating=data.get('service_rating'),
                value_rating=data.get('value_rating'),
                order=order,
                is_verified=is_verified,
                status='approved',
            )

            # Update object rating
            update_object_rating(
                data['objects_type'],
                data['objects_id']
            )

            return api_response(
                'success',
                'Review submitted successfully',
                data=ReviewSerializer(
                    review,
                    context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Review submission failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ReviewDetailView(APIView):
    """Get update delete review"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAuthenticated()]
        return []

    def get_object(self, pk):
        try:
            return Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return None

    def get(self, request, pk):
        review = self.get_object(pk)
        if not review:
            return api_response(
                'error', 'Review not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ReviewSerializer(
            review, context={'request': request}
        )
        return api_response(
            'success',
            'Review retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        review = self.get_object(pk)
        if not review:
            return api_response(
                'error', 'Review not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Only owner or admin can update
        if (review.user != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Permission denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        serializer = ReviewSerializer(
            review, data=request.data,
            partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            update_object_rating(
                review.objects_type,
                review.objects_id
            )
            return api_response(
                'success',
                'Review updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        review = self.get_object(pk)
        if not review:
            return api_response(
                'error', 'Review not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if (review.user != request.user and
                request.user.role != 'admin'):
            return api_response(
                'error', 'Permission denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        objects_type = review.objects_type
        objects_id = review.objects_id
        review.delete()

        update_object_rating(objects_type, objects_id)

        return api_response(
            'success', 'Review deleted successfully'
        )


class ReplyReviewView(APIView):
    """Business owner replies to review"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return api_response(
                'error', 'Review not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check if user owns the business being reviewed
        if review.objects_type == 'business':
            from apps.marketplace.models import Business
            business = Business.objects.filter(
                pk=review.objects_id,
                owner=request.user
            ).first()
            if not business and request.user.role != 'admin':
                return api_response(
                    'error',
                    'Only the business owner can reply',
                    http_status=status.HTTP_403_FORBIDDEN
                )

        serializer = ReplyReviewSerializer(data=request.data)
        if serializer.is_valid():
            review.reply = serializer.validated_data['reply']
            review.replied_by = request.user
            review.replied_at = timezone.now()
            review.save()

            # Notify reviewer
            from apps.notifications.utils import send_notification
            send_notification(
                user=review.user,
                title='New Reply to Your Review',
                message=f'Someone replied to your review',
                notification_type='system'
            )

            return api_response(
                'success',
                'Reply added successfully',
                data=ReviewSerializer(
                    review,
                    context={'request': request}
                ).data
            )

        return api_response(
            'error', 'Reply failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ReviewHelpfulnessView(APIView):
    """Vote on review helpfulness"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return api_response(
                'error', 'Review not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Can't vote on own review
        if review.user == request.user:
            return api_response(
                'error',
                'Cannot vote on your own review',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        is_helpful = request.data.get('is_helpful', True)

        vote, created = ReviewHelpfulness.objects.update_or_create(
            review=review,
            user=request.user,
            defaults={'is_helpful': is_helpful}
        )

        # Update counts
        review.helpful_count = review.helpfulness_votes.filter(
            is_helpful=True
        ).count()
        review.not_helpful_count = review.helpfulness_votes.filter(
            is_helpful=False
        ).count()
        review.save()

        return api_response(
            'success',
            'Vote recorded successfully',
            data={
                'helpful_count': review.helpful_count,
                'not_helpful_count': review.not_helpful_count,
                'your_vote': 'helpful' if is_helpful else 'not helpful'
            }
        )


class ReviewReportView(APIView):
    """Report a review"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return api_response(
                'error', 'Review not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if ReviewReport.objects.filter(
            review=review,
            reported_by=request.user
        ).exists():
            return api_response(
                'error',
                'You have already reported this review',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReviewReportSerializer(data=request.data)
        if serializer.is_valid():
            report = serializer.save(
                review=review,
                reported_by=request.user
            )

            # Flag review if too many reports
            report_count = ReviewReport.objects.filter(
                review=review
            ).count()
            if report_count >= 3:
                review.status = 'flagged'
                review.save()

            return api_response(
                'success',
                'Review reported successfully',
                data=ReviewReportSerializer(report).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error', 'Report failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class MyReviewsView(APIView):
    """Get all reviews by current user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reviews = Review.objects.filter(user=request.user)
        objects_type = request.query_params.get('type')
        if objects_type:
            reviews = reviews.filter(objects_type=objects_type)

        serializer = ReviewSerializer(
            reviews, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Your reviews retrieved successfully',
            data={
                'count': reviews.count(),
                'results': serializer.data
            }
        )


class AdminReviewListView(APIView):
    """Admin manage all reviews"""
    permission_classes = [IsAdmin]

    def get(self, request):
        reviews = Review.objects.all()

        review_status = request.query_params.get('status')
        objects_type = request.query_params.get('type')

        if review_status:
            reviews = reviews.filter(status=review_status)
        if objects_type:
            reviews = reviews.filter(objects_type=objects_type)

        serializer = ReviewSerializer(
            reviews, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'All reviews retrieved',
            data={
                'count': reviews.count(),
                'pending': reviews.filter(
                    status='pending'
                ).count(),
                'flagged': reviews.filter(
                    status='flagged'
                ).count(),
                'results': serializer.data
            }
        )

    def patch(self, request, pk):
        """Admin approve/reject/feature review"""
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return api_response(
                'error', 'Review not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        is_featured = request.data.get('is_featured')

        if new_status:
            review.status = new_status
        if is_featured is not None:
            review.is_featured = is_featured

        review.save()

        update_object_rating(
            review.objects_type,
            review.objects_id
        )

        return api_response(
            'success',
            'Review updated successfully',
            data=ReviewSerializer(
                review, context={'request': request}
            ).data
        )