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
)
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
