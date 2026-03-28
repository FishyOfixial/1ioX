from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .utils import log_security_event, log_user_action


def user_in(*user_types):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                log_security_event(
                    "Anonymous access denied",
                    metadata={"path": request.path, "required_user_types": user_types},
                )
                return HttpResponseForbidden("Debes iniciar sesion.")

            if request.user.user_type == "CLIENTE":
                log_security_event(
                    "Customer redirected from control panel route",
                    user=request.user,
                    metadata={"path": request.path, "required_user_types": user_types},
                )
                return redirect("customer_portal:dashboard")

            if request.user.user_type == "MATRIZ":
                return view_func(request, *args, **kwargs)

            if request.user.user_type not in user_types:
                log_security_event(
                    "Access denied by role restriction",
                    user=request.user,
                    metadata={"path": request.path, "required_user_types": user_types},
                )
                return HttpResponseForbidden("Acceso denegado.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def user_is(user_type):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                log_security_event(
                    "Anonymous access denied",
                    metadata={"path": request.path, "required_user_type": user_type},
                )
                return HttpResponseForbidden("Debes iniciar sesion.")
            if request.user.user_type == "CLIENTE":
                log_security_event(
                    "Customer redirected from restricted route",
                    user=request.user,
                    metadata={"path": request.path, "required_user_type": user_type},
                )
                return redirect("customer_portal:dashboard")
            if request.user.user_type != user_type:
                log_security_event(
                    "Access denied by exact role restriction",
                    user=request.user,
                    metadata={"path": request.path, "required_user_type": user_type},
                )
                return HttpResponseForbidden("No tienes permiso para acceder a esta vista.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def matriz_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.user_type == "CLIENTE":
            log_security_event(
                "Customer redirected from matriz route",
                user=request.user,
                metadata={"path": request.path},
            )
            return redirect("customer_portal:dashboard")
        if request.user.user_type != "MATRIZ":
            log_security_event(
                "Access denied by matriz restriction",
                user=request.user,
                metadata={"path": request.path},
            )
            return HttpResponseForbidden("No tienes permiso para acceder a esta vista.")
        return view_func(request, *args, **kwargs)

    return wrapper


def refresh_command(command_name):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        @user_in("DISTRIBUIDOR", "REVENDEDOR")
        @require_POST
        def _wrapped(request, *args, **kwargs):
            try:
                call_command(command_name)
                log_user_action(
                    request.user,
                    "CommandRunLog",
                    "REFRESH",
                    object_id=None,
                    description=f"{request.user} uso el comando {command_name}",
                )
                return JsonResponse({"ok": True})
            except Exception as e:
                return JsonResponse({"ok": False, "error": str(e)}, status=500)

        return _wrapped

    return decorator
