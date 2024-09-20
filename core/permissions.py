from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'

class IsEditor(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['editor', 'admin']

class IsViewer(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['viewer', 'editor', 'admin']
