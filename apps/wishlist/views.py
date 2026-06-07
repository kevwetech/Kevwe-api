from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from .models import WishlistItem
from .serializers import WishlistItemSerializer, AddToWishlistSerializer


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist = WishlistItem.objects.filter(user=request.user)
        serializer = WishlistItemSerializer(wishlist, many=True)
        return api_response(
            'success',
            'Wishlist retrieved successfully',
            data={
                'count': wishlist.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = AddToWishlistSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            product_type = serializer.validated_data.get(
                'product_type', 'product'
            )

            # Check if already in wishlist
            existing = WishlistItem.objects.filter(
                user=request.user,
                product_id=product_id,
                product_type=product_type
            ).first()

            if existing:
                return api_response(
                    'error',
                    'Item already in wishlist',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            wishlist_item = serializer.save(user=request.user)
            return api_response(
                'success',
                'Item added to wishlist',
                data=WishlistItemSerializer(wishlist_item).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Failed to add to wishlist',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class WishlistItemView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return WishlistItem.objects.get(pk=pk, user=user)
        except WishlistItem.DoesNotExist:
            return None

    def delete(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return api_response(
                'error',
                'Item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        item.delete()
        return api_response(
            'success',
            'Item removed from wishlist'
        )


class ClearWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        WishlistItem.objects.filter(user=request.user).delete()
        return api_response(
            'success',
            'Wishlist cleared successfully'
        )


class CheckWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        product_type = request.query_params.get(
            'product_type', 'product'
        )
        exists = WishlistItem.objects.filter(
            user=request.user,
            product_id=product_id,
            product_type=product_type
        ).exists()

        return api_response(
            'success',
            'Check complete',
            data={'in_wishlist': exists}
        )