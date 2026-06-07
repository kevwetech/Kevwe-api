from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.common.views import api_response
from apps.common.permissions import IsOwnerOrAdmin
from .models import Review
from .serializers import ReviewSerializer, CreateReviewSerializer


class ProductReviewListCreateView(APIView):
    permission_classes = [] 

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, product_id):
        product_type = request.query_params.get(
            'product_type', 'product'
        )
        reviews = Review.objects.filter(
            product_id=product_id,
            product_type=product_type
        )

        # Filter by rating
        rating = request.query_params.get('rating')
        if rating:
            reviews = reviews.filter(rating=rating)

        serializer = ReviewSerializer(
            reviews,
            many=True,
            context={'request': request}
        )

        # Calculate average rating
        avg_rating = 0
        if reviews.exists():
            avg_rating = sum(
                r.rating for r in reviews
            ) / reviews.count()

        return api_response(
            'success',
            'Reviews retrieved successfully',
            data={
                'count': reviews.count(),
                'average_rating': round(avg_rating, 1),
                'average_display': '★' * round(avg_rating),
                'results': serializer.data
            }
        )

    def post(self, request, product_id):
        product_type = request.query_params.get(
            'product_type', 'product'
        )

        # Check if user already reviewed
        existing = Review.objects.filter(
            user=request.user,
            product_id=product_id,
            product_type=product_type
        ).first()

        if existing:
            return api_response(
                'error',
                'You have already reviewed this item',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CreateReviewSerializer(data=request.data)
        if serializer.is_valid():
            review = serializer.save(
                user=request.user,
                product_id=product_id,
                product_type=product_type
            )
            return api_response(
                'success',
                'Review added successfully',
                data=ReviewSerializer(
                    review,
                    context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Review failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Review.objects.get(pk=pk, user=user)
        except Review.DoesNotExist:
            return None

    def patch(self, request, pk):
        review = self.get_object(pk, request.user)
        if not review:
            return api_response(
                'error',
                'Review not found or not yours',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = CreateReviewSerializer(
            review,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Review updated successfully',
                data=ReviewSerializer(
                    review,
                    context={'request': request}
                ).data
            )

        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        review = self.get_object(pk, request.user)
        if not review:
            return api_response(
                'error',
                'Review not found or not yours',
                http_status=status.HTTP_404_NOT_FOUND
            )
        review.delete()
        return api_response(
            'success',
            'Review deleted successfully'
        )