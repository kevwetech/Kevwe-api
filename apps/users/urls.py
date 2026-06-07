from django.urls import path
from .views import (
    ProfileView,
    UpdateProfileView,
    AvatarUploadView,
    ChangePasswordView,
    DeleteAccountView,
)

urlpatterns = [
    path('me/', ProfileView.as_view(), name='profile'),
    path('me/update/', UpdateProfileView.as_view(), name='update_profile'),
    path('me/avatar/', AvatarUploadView.as_view(), name='avatar_upload'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('me/delete/', DeleteAccountView.as_view(), name='delete_account'),
]