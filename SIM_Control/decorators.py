from django.http import HttpResponseForbidden
from functools import wraps

def user_in(*user_types):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Debes iniciar sesión.")
            
            if request.user.user_type == 'MATRIZ':
                return view_func(request, *args, **kwargs)
            
            if request.user.user_type not in user_types:
                return HttpResponseForbidden("Acceso denegado.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def user_is(user_type):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Debes iniciar sesión.")
            if request.user.user_type != user_type:
                return HttpResponseForbidden("No tienes permiso para acceder a esta vista.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
