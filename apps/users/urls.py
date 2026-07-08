from django.urls import path
from .views import (
    ProfileView,
    UpdateProfileView,
    AvatarUploadView,
    ChangePasswordView,
    DeleteAccountView,
    SavedAddressListView, 
    SavedAddressDetailView,
    SetDefaultAddressView, 
    ValidateAddressView,
)

urlpatterns = [
    path('me/', ProfileView.as_view(), name='profile'),
    path('me/update/', UpdateProfileView.as_view(), name='update_profile'),
    path('me/avatar/', AvatarUploadView.as_view(), name='avatar_upload'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('me/delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('addresses/',                  SavedAddressListView.as_view(),   name='saved_addresses'),
    path('addresses/<int:pk>/',         SavedAddressDetailView.as_view(), name='address_detail'),
    path('addresses/<int:pk>/default/', SetDefaultAddressView.as_view(),  name='set_default_address'),
    path('addresses/validate/',         ValidateAddressView.as_view(),    name='validate_address'),
]