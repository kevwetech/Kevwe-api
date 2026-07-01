from rest_framework.permissions import BasePermission
from .utils import check_permission


class HasBusinessPermission(BasePermission):
    """
    DRF permission class for staff permission checks.
    Usage: set required_permission on the view.

    class MyView(APIView):
        permission_classes = [HasBusinessPermission]
        required_permission = 'view_bookings'
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        permission_code = getattr(
            view, 'required_permission', None
        )
        if not permission_code:
            return True

        business_id = (
            view.kwargs.get('business_id')
            or request.data.get('business_id')
            or request.query_params.get('business_id')
        )
        if not business_id:
            return False

        try:
            from apps.marketplace.models import Business
            business = Business.objects.get(pk=business_id)
            return check_permission(
                request.user, business, permission_code
            )
        except Exception:
            return False