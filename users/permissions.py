from rest_framework.permissions import BasePermission

from users.enums import SecurityLevel


def MinSecurityLevel(level: SecurityLevel) -> type[BasePermission]:
    """Factory returning a DRF permission class that requires at least `level`."""

    class _Permission(BasePermission):
        def has_permission(self, request: object, _view: object) -> bool:
            return (
                hasattr(request, "user")
                and hasattr(request.user, "security_level")
                and request.user.security_level >= level
            )

    _Permission.__name__ = f"MinSecurityLevel_{level.name}"
    return _Permission


def AnySecurityLevel(*levels: SecurityLevel) -> type[BasePermission]:
    """Factory returning a DRF permission class that requires one of exactly `levels`.

    Use when a higher number is a different role rather than more access (e.g. DASHBOARD).
    """

    class _Permission(BasePermission):
        def has_permission(self, request: object, _view: object) -> bool:
            return (
                hasattr(request, "user")
                and hasattr(request.user, "security_level")
                and request.user.security_level in levels
            )

    _Permission.__name__ = f"AnySecurityLevel_{'_'.join(level.name for level in levels)}"
    return _Permission
