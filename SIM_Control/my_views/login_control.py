from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from auditlogs.utils import create_log

from ..forms import CustomLoginForm
from ..utils import log_user_action
from ..security import (
    clear_login_failures,
    get_default_post_login_redirect,
    get_login_lockout_state,
    register_login_failure,
)


def login_view(request):
    if request.method == "GET":
        return render(request, "login.html", {"form": CustomLoginForm()})

    username = (request.POST.get("username") or "").strip()
    lockout_state = get_login_lockout_state(request, username)
    if lockout_state:
        retry_after_minutes = max((lockout_state["retry_after_seconds"] + 59) // 60, 1)
        return render(
            request,
            "login.html",
            {
                "error": f"Demasiados intentos. Intenta de nuevo en {retry_after_minutes} minuto(s).",
                "form": CustomLoginForm(),
            },
            status=429,
        )

    user = authenticate(
        request,
        username=username,
        password=(request.POST.get("password") or "").strip(),
    )

    if user is None:
        lockout_state = register_login_failure(request, username)
        if lockout_state:
            retry_after_minutes = max((lockout_state["retry_after_seconds"] + 59) // 60, 1)
            error_message = f"Demasiados intentos. Intenta de nuevo en {retry_after_minutes} minuto(s)."
            return render(
                request,
                "login.html",
                {"error": error_message, "form": CustomLoginForm()},
                status=429,
            )
        return render(
            request,
            "login.html",
            {"error": "Correo o contrasena invalido", "form": CustomLoginForm()},
        )

    clear_login_failures(request, username)
    login(request, user)
    create_log(
        log_type="USER",
        user=user,
        message="User login successful",
        reference_id=str(user.id),
    )
    log_user_action(user, "User", "LOGIN", description=f"{user} inicio sesion")
    return redirect(get_default_post_login_redirect(user))


def logout_view(request):
    create_log(
        log_type="USER",
        user=request.user if request.user.is_authenticated else None,
        message="User logout",
        reference_id=str(request.user.id) if request.user.is_authenticated else None,
    )
    log_user_action(request.user, "User", "LOGOUT", description=f"{request.user} cerro sesion")
    logout(request)
    return redirect("login")

