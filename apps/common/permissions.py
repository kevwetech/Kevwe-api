from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Only admin users can access
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Admins can do everything
    Others can only read
    """
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return (
            request.user.is_authenticated and
            request.user.role == 'admin'
        )

class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated
        )

class IsVendor(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['vendor', 'admin']
        )

class IsDriver(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['driver', 'admin']
        )
        



class IsOwnerOrAdmin(BasePermission):
    """
    Only owner or admin can access
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated and
            (obj == request.user or request.user.role == 'admin')
        )