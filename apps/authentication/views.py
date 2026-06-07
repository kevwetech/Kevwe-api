from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer,
)
from .models import OTPVerification
from .utils import send_otp_email
from apps.common.ratelimit import AuthRateThrottle
User = get_user_model()


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


@extend_schema(request=RegisterSerializer, responses={201: None})
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate and send OTP
            otp = OTPVerification.generate_otp()
            OTPVerification.objects.create(
                user=user,
                otp=otp,
                otp_type='email_verification'
            )

            try:
                send_otp_email(user.email, otp, 'email_verification')
            except Exception:
                pass

            return api_response(
                'success',
                'Registration successful. Check your email for verification code.',
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Registration failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(request=LoginSerializer, responses={200: None})
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, username=email, password=password)

            if not user:
                return api_response(
                    'error',
                    'Invalid email or password',
                    http_status=status.HTTP_401_UNAUTHORIZED
                )

            if not user.is_verified:
                return api_response(
                    'error',
                    'Please verify your email first',
                    http_status=status.HTTP_403_FORBIDDEN
                )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return api_response(
                'success',
                'Login successful',
                data={
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'full_name': user.full_name,
                        'role': user.role,
                        'is_verified': user.is_verified,
                    },
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                }
            )

        return api_response(
            'error',
            'Login failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return api_response(
                    'error',
                    'Refresh token is required',
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return api_response('success', 'Logout successful')
        except Exception as e:
            return api_response(
                'error',
                f'Logout failed: {str(e)}',
                http_status=status.HTTP_400_BAD_REQUEST
            )

@extend_schema(request=EmailVerificationSerializer, responses={200: None})
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return api_response(
                    'error',
                    'User not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            # Check OTP
            expiry = timezone.now() - timedelta(minutes=10)
            otp_obj = OTPVerification.objects.filter(
                user=user,
                otp=otp,
                otp_type='email_verification',
                is_used=False,
                created_at__gte=expiry
            ).first()

            if not otp_obj:
                return api_response(
                    'error',
                    'Invalid or expired OTP',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            otp_obj.is_used = True
            otp_obj.save()

            user.is_verified = True
            user.save()

            return api_response('success', 'Email verified successfully')

        return api_response(
            'error',
            'Verification failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(request=PasswordResetRequestSerializer, responses={200: None})
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)
                otp = OTPVerification.generate_otp()
                OTPVerification.objects.create(
                    user=user,
                    otp=otp,
                    otp_type='password_reset'
                )
                try:
                    send_otp_email(email, otp, 'password_reset')
                except Exception:
                    pass
            except User.DoesNotExist:
                pass

            return api_response(
                'success',
                'If this email exists you will receive a reset code'
            )

        return api_response(
            'error',
            'Request failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return api_response(
                    'error',
                    'User not found',
                    http_status=status.HTTP_404_NOT_FOUND
                )

            expiry = timezone.now() - timedelta(minutes=10)
            otp_obj = OTPVerification.objects.filter(
                user=user,
                otp=otp,
                otp_type='password_reset',
                is_used=False,
                created_at__gte=expiry
            ).first()

            if not otp_obj:
                return api_response(
                    'error',
                    'Invalid or expired OTP',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            otp_obj.is_used = True
            otp_obj.save()

            user.set_password(new_password)
            user.save()

            return api_response('success', 'Password reset successful')

        return api_response(
            'error',
            'Reset failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )