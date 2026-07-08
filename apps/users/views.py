from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import (
    UserProfileSerializer,
    UpdateProfileSerializer,
    AvatarSerializer,
    ChangePasswordSerializer,
    SavedAddressSerializer,
    CreateSavedAddressSerializer,
    ValidateAddressSerializer,
)
from .models import SavedAddress,
from apps.common.ratelimit import UploadRateThrottle


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


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return api_response(
            'success',
            'Profile retrieved successfully',
            data=serializer.data
        )


class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Profile updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UploadRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        print("FILES:", request.FILES)  # ← debug
        print("DATA:", request.data)    # ← debug
        
        serializer = AvatarSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            print("Avatar after save:", request.user.avatar)  # ← debug
            return api_response(
                'success',
                'Avatar uploaded successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Upload failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user

            # Check old password
            if not user.check_password(
                serializer.validated_data['old_password']
            ):
                return api_response(
                    'error',
                    'Old password is incorrect',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(
                serializer.validated_data['new_password']
            )
            user.save()

            return api_response(
                'success',
                'Password changed successfully'
            )

        return api_response(
            'error',
            'Password change failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return api_response(
            'success',
            'Account deleted successfully',
            http_status=status.HTTP_204_NO_CONTENT
        )

class SavedAddressListView(APIView):
    """
    GET  /api/v1/users/addresses/       ← list all saved addresses
    POST /api/v1/users/addresses/       ← save new address
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = SavedAddress.objects.filter(
            user=request.user, is_active=True
        )
        data = [{
            'id':         a.id,
            'label':      a.label,
            'name':       a.name,
            'address':    a.address,
            'city':       a.city,
            'state':      a.state,
            'latitude':   float(a.latitude)  if a.latitude  else None,
            'longitude':  float(a.longitude) if a.longitude else None,
            'is_default': a.is_default,
        } for a in addresses]
        return api_response('success', 'Addresses retrieved', data=data)

    def post(self, request):
        d = request.data
        address = SavedAddress.objects.create(
            user       = request.user,
            label      = d.get('label', 'home'),
            name       = d.get('name', ''),
            address    = d.get('address', ''),
            city       = d.get('city', ''),
            state      = d.get('state', ''),
            latitude   = d.get('latitude'),
            longitude  = d.get('longitude'),
            is_default = d.get('is_default', False),
        )
        return api_response('success', 'Address saved', data={
            'id':         address.id,
            'label':      address.label,
            'address':    address.address,
            'is_default': address.is_default,
        }, http_status=status.HTTP_201_CREATED)


class SavedAddressDetailView(APIView):
    """
    PATCH  /api/v1/users/addresses/<pk>/          ← update address
    DELETE /api/v1/users/addresses/<pk>/          ← delete address
    POST   /api/v1/users/addresses/<pk>/default/  ← set as default
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return SavedAddress.objects.get(pk=pk, user=user, is_active=True)
        except SavedAddress.DoesNotExist:
            return None

    def patch(self, request, pk):
        obj = self.get_object(pk, request.user)
        if not obj:
            return api_response('error', 'Address not found',
                http_status=status.HTTP_404_NOT_FOUND)
        for field in ['label','name','address','city','state','latitude','longitude','is_default']:
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()
        return api_response('success', 'Address updated')

    def delete(self, request, pk):
        obj = self.get_object(pk, request.user)
        if not obj:
            return api_response('error', 'Address not found',
                http_status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save()
        return api_response('success', 'Address deleted')


class SetDefaultAddressView(APIView):
    """POST /api/v1/users/addresses/<pk>/default/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            address = SavedAddress.objects.get(
                pk=pk, user=request.user, is_active=True)
        except SavedAddress.DoesNotExist:
            return api_response('error', 'Address not found',
                http_status=status.HTTP_404_NOT_FOUND)
        address.is_default = True
        address.save()
        return api_response('success', 'Default address updated')


class ValidateAddressView(APIView):
    """
    POST /api/v1/users/addresses/validate/
    Checks if customer GPS is far from their saved default address.
    Body: { current_lat, current_lng }
    Returns: { is_far, distance_km, saved_address, suggestion }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import math

        current_lat = request.data.get('current_lat')
        current_lng = request.data.get('current_lng')

        if not current_lat or not current_lng:
            return api_response('error', 'current_lat and current_lng required',
                http_status=status.HTTP_400_BAD_REQUEST)

        # Get default saved address
        default = SavedAddress.objects.filter(
            user=request.user,
            is_active=True,
            is_default=True,
            latitude__isnull=False,
            longitude__isnull=False,
        ).first()

        if not default:
            return api_response('success', 'No saved address to validate',
                data={'is_far': False, 'saved_address': None})

        # Haversine
        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            lat1, lng1, lat2, lng2 = map(
                math.radians,
                [float(lat1), float(lng1), float(lat2), float(lng2)]
            )
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            return R * 2 * math.asin(math.sqrt(a))

        distance = haversine(
            current_lat, current_lng,
            default.latitude, default.longitude
        )
        distance = round(distance, 2)
        is_far   = distance > 2  # Alert if > 2km away

        return api_response('success', 'Address validated', data={
            'is_far':       is_far,
            'distance_km':  distance,
            'saved_address': {
                'id':      default.id,
                'label':   default.label,
                'address': default.address,
                'city':    default.city,
            },
            'suggestion': 'Use current location' if is_far else None,
        })
