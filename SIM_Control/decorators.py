from django.http import HttpResponseForbidden
from functools import wraps
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import JsonResponse
from .models import UserActionLog

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

def refresh_command(command_name):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        @user_in("DISTRIBUIDOR", "REVENDEDOR")
        @require_POST
        def _wrapped(request, *args, **kwargs):
            try:
                call_command(command_name)
                UserActionLog.objects.create(
                    user=request.user,
                    action='REFRESH',
                    model_name='CommandRunLog',
                    description=f'{request.user} uso el comando {command_name}'
                )
                return JsonResponse({"ok": True})
            except Exception as e:
                return JsonResponse({"ok": False, "error": str(e)}, status=500)
        return _wrapped
    return decorator
