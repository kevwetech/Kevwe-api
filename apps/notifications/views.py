from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import Notification
from .serializers import NotificationSerializer
from .utils import send_notification


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user
        )

        # Filter by read status
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            notifications = notifications.filter(
                is_read=is_read == 'true'
            )

        # Filter by type
        notification_type = request.query_params.get('type')
        if notification_type:
            notifications = notifications.filter(
                notification_type=notification_type
            )

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        serializer = NotificationSerializer(
            notifications,
            many=True
        )

        return api_response(
            'success',
            'Notifications retrieved successfully',
            data={
                'unread_count': unread_count,
                'count': notifications.count(),
                'results': serializer.data
            }
        )


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Notification.objects.get(pk=pk, user=user)
        except Notification.DoesNotExist:
            return None

    def patch(self, request, pk):
        notification = self.get_object(pk, request.user)
        if not notification:
            return api_response(
                'error',
                'Notification not found',
                http_status=404
            )

        notification.is_read = True
        notification.save()

        return api_response(
            'success',
            'Notification marked as read',
            data=NotificationSerializer(notification).data
        )

    def delete(self, request, pk):
        notification = self.get_object(pk, request.user)
        if not notification:
            return api_response(
                'error',
                'Notification not found',
                http_status=404
            )

        notification.delete()
        return api_response(
            'success',
            'Notification deleted successfully'
        )


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return api_response(
            'success',
            'All notifications marked as read'
        )


class ClearAllNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        Notification.objects.filter(
            user=request.user
        ).delete()

        return api_response(
            'success',
            'All notifications cleared'
        )


class AdminSendNotificationView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        title = request.data.get('title')
        message = request.data.get('message')
        user_id = request.data.get('user_id')
        send_to_all = request.data.get('send_to_all', False)

        if not title or not message:
            return api_response(
                'error',
                'Title and message are required',
                http_status=400
            )

        if send_to_all:
            # Send to all users
            users = User.objects.filter(is_active=True)
            for user in users:
                send_notification(
                    user=user,
                    title=title,
                    message=message,
                    notification_type='system'
                )
            return api_response(
                'success',
                f'Notification sent to {users.count()} users'
            )

        elif user_id:
            try:
                user = User.objects.get(pk=user_id)
                send_notification(
                    user=user,
                    title=title,
                    message=message,
                    notification_type='system'
                )
                return api_response(
                    'success',
                    'Notification sent successfully'
                )
            except User.DoesNotExist:
                return api_response(
                    'error',
                    'User not found',
                    http_status=404
                )

        return api_response(
            'error',
            'Provide user_id or set send_to_all to true',
            http_status=400
        )