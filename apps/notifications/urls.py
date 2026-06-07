from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    MarkAllReadView,
    ClearAllNotificationsView,
    AdminSendNotificationView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification_detail'),
    path('mark-all-read/', MarkAllReadView.as_view(), name='mark_all_read'),
    path('clear/', ClearAllNotificationsView.as_view(), name='clear_notifications'),
    path('admin/send/', AdminSendNotificationView.as_view(), name='admin_send_notification'),
]