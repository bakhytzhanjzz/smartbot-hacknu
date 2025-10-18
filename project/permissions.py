# project/permissions.py
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow read-only for everyone, write only for owner (has .owner or .user relation).
    """

    def has_object_permission(self, request, view, obj):
        # Allow safe methods for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # try common owner attributes
        owner_attrs = ['owner', 'employer', 'user']
        for attr in owner_attrs:
            if hasattr(obj, attr):
                owner = getattr(obj, attr)
                # if owner is a FK to Employer with .user
                if getattr(owner, 'user', None):
                    return owner.user == request.user
                # if owner is a user directly
                if owner == request.user:
                    return True
        return False

class IsEmployer(permissions.BasePermission):
    """
    Allow only authenticated users that have Employer profile to POST/PUT for employer-scoped endpoints.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'employer')
