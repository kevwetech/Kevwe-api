from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from .models import WishlistItem, WishlistCollection
from .serializers import (
    WishlistItemSerializer,
    AddToWishlistSerializer,
    WishlistCollectionSerializer,
)
from .services import get_or_create_default_collection


# ═══════════════════════════════════════════════════
# WISHLIST ITEMS
# ═══════════════════════════════════════════════════
class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist = WishlistItem.objects.filter(user=request.user)
        # Optional filters
        item_type = request.query_params.get('item_type')
        collection = request.query_params.get('collection')
        if item_type:
            wishlist = wishlist.filter(item_type=item_type)
        if collection:
            wishlist = wishlist.filter(collection_id=collection)

        serializer = WishlistItemSerializer(wishlist, many=True)
        return api_response(
            'success', 'Wishlist retrieved successfully',
            data={'count': wishlist.count(), 'results': serializer.data})

    def post(self, request):
        serializer = AddToWishlistSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            item_id = serializer.validated_data['item_id']
            item_type = serializer.validated_data.get('item_type', 'product')

            existing = WishlistItem.objects.filter(
                user=request.user, item_id=item_id, item_type=item_type
            ).first()
            if existing:
                return api_response(
                    'error', 'Item already in wishlist',
                    http_status=status.HTTP_400_BAD_REQUEST)

            item = serializer.save(user=request.user)
            return api_response(
                'success', 'Item added to wishlist',
                data=WishlistItemSerializer(item).data,
                http_status=status.HTTP_201_CREATED)

        return api_response(
            'error', 'Failed to add to wishlist',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


class WishlistItemView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return WishlistItem.objects.get(pk=pk, user=user)
        except WishlistItem.DoesNotExist:
            return None

    def patch(self, request, pk):
        """Move to a collection or edit the note."""
        item = self.get_object(pk, request.user)
        if not item:
            return api_response('error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND)
        # Only note + collection are editable
        note = request.data.get('note')
        collection_id = request.data.get('collection')
        if note is not None:
            item.note = note
        if collection_id is not None:
            if collection_id == '' or collection_id is None:
                item.collection = None
            else:
                try:
                    col = WishlistCollection.objects.get(
                        pk=collection_id, user=request.user)
                    item.collection = col
                except WishlistCollection.DoesNotExist:
                    return api_response('error', 'Collection not found',
                        http_status=status.HTTP_404_NOT_FOUND)
        item.save()
        return api_response('success', 'Wishlist item updated',
            data=WishlistItemSerializer(item).data)

    def delete(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return api_response('error', 'Item not found',
                http_status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return api_response('success', 'Item removed from wishlist')


class ClearWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        WishlistItem.objects.filter(user=request.user).delete()
        return api_response('success', 'Wishlist cleared successfully')


class CheckWishlistView(APIView):
    """GET /check/<item_id>/?item_type=product"""
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        item_type = request.query_params.get('item_type', 'product')
        exists = WishlistItem.objects.filter(
            user=request.user, item_id=item_id, item_type=item_type
        ).exists()
        return api_response('success', 'Check complete',
            data={'in_wishlist': exists})


# ═══════════════════════════════════════════════════
# COLLECTIONS
# ═══════════════════════════════════════════════════
class WishlistCollectionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Ensure the default collection always exists
        get_or_create_default_collection(request.user)
        collections = WishlistCollection.objects.filter(user=request.user)
        serializer = WishlistCollectionSerializer(collections, many=True)
        return api_response('success', 'Collections retrieved',
            data={'count': collections.count(), 'results': serializer.data})

    def post(self, request):
        serializer = WishlistCollectionSerializer(data=request.data)
        if serializer.is_valid():
            # Enforce unique name per user gracefully
            name = serializer.validated_data['name']
            if WishlistCollection.objects.filter(
                    user=request.user, name=name).exists():
                return api_response('error',
                    'You already have a collection with that name',
                    http_status=status.HTTP_400_BAD_REQUEST)
            collection = serializer.save(user=request.user)
            return api_response('success', 'Collection created',
                data=WishlistCollectionSerializer(collection).data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


class WishlistCollectionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return WishlistCollection.objects.get(pk=pk, user=user)
        except WishlistCollection.DoesNotExist:
            return None

    def get(self, request, pk):
        col = self.get_object(pk, request.user)
        if not col:
            return api_response('error', 'Collection not found',
                http_status=status.HTTP_404_NOT_FOUND)
        items = col.items.all()
        return api_response('success', 'Collection retrieved', data={
            'collection': WishlistCollectionSerializer(col).data,
            'items': WishlistItemSerializer(items, many=True).data,
        })

    def patch(self, request, pk):
        col = self.get_object(pk, request.user)
        if not col:
            return api_response('error', 'Collection not found',
                http_status=status.HTTP_404_NOT_FOUND)
        serializer = WishlistCollectionSerializer(
            col, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Collection updated',
                data=serializer.data)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        col = self.get_object(pk, request.user)
        if not col:
            return api_response('error', 'Collection not found',
                http_status=status.HTTP_404_NOT_FOUND)
        if col.is_default:
            return api_response('error',
                'Cannot delete your default collection',
                http_status=status.HTTP_400_BAD_REQUEST)
        # Items fall back to no collection (SET_NULL), not deleted
        col.delete()
        return api_response('success', 'Collection deleted')