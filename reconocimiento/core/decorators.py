# core/decorators.py
from django.core.exceptions import PermissionDenied

def admin_zona_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'admin_zona':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view

def admin_global_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'admin_global':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view

def profesor_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'profesor':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view
