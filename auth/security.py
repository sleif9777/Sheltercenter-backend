from rest_framework.permissions import BasePermission

from users.enums import SecurityLevel


class IsStaffUser(BasePermission):
    """Requires SecurityLevel >= GREETER (1)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.security_level >= SecurityLevel.GREETER
        )


class IsAdminUser(BasePermission):
    """Requires SecurityLevel >= ADMIN (2)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.security_level >= SecurityLevel.ADMIN
        )
