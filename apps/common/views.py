from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser


def api_response(status_str, message, data=None, errors=None, http_status=200):
    response = {
        'status': status_str,
        'message': message,
    }
    if data is not None:
        response['data'] = data
    if errors is not None:
        response['errors'] = errors
    return Response(response, status=http_status)


class BaseListCreateView(APIView):
    """
    Base view for listing and creating items
    Override serializer_class and queryset in child class
    """
    serializer_class = None
    permission_classes = [IsAuthenticated]
    search_fields = ['name']

    def get_queryset(self):
        return self.queryset.filter(is_active=True)

    def get(self, request):
        queryset = self.get_queryset()

        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        serializer = self.serializer_class(
            queryset,
            many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Data retrieved successfully',
            data={
                'count': queryset.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BaseRetrieveUpdateDeleteView(APIView):
    """
    Base view for retrieving, updating and deleting a single item
    Override serializer_class and queryset in child class
    """
    serializer_class = None
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return self.queryset.get(pk=pk)
        except Exception:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return api_response(
                'error',
                'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.serializer_class(
            obj,
            context={'request': request}
        )
        return api_response(
            'success',
            'Data retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return api_response(
                'error',
                'Not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return api_response(
                'error',
                'Not found',
                http_status=status.HTTP_404_NOT_FOUND
        )
        obj.delete()
        return Response(
            {
                'status': 'success',
                'message': 'Deleted successfully'
            },
            status=status.HTTP_200_OK  # ← change 204 to 200
    )