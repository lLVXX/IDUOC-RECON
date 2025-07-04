from django.core.exceptions import PermissionDenied

def is_admin_global(user):
    return user.is_authenticated and user.user_type == 'admin_global'

def admin_global_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_admin_global(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
