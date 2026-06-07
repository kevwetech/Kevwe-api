from django.urls import path
from .user_views import(UserDashboardView,)
from .views import (
    DashboardView,
    AdminUserListView,
    AdminUserDetailView,
    
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('users/', AdminUserListView.as_view(), name='admin_users'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    # User dashboard
    path('user/', UserDashboardView.as_view(), name='user_dashboard'),
]