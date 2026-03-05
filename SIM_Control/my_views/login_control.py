from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from auditlogs.utils import create_log

from ..forms import CustomLoginForm
from ..utils import log_user_action


def login_view(request):
    if request.method == "GET":
        return render(request, "login.html", {"form": CustomLoginForm()})

    username = (request.POST.get("username") or "").strip()
    user = authenticate(
        request,
        username=username,
        password=(request.POST.get("password") or "").strip(),
    )

    if user is None:
        create_log(
            log_type="USER",
            severity="WARNING",
            message="Failed login attempt",
            metadata={"username": username},
        )
        return render(
            request,
            "login.html",
            {"error": "Correo o contrasena invalido", "form": CustomLoginForm()},
        )

    login(request, user)
    create_log(
        log_type="USER",
        user=user,
        message="User login successful",
        reference_id=str(user.id),
    )
    log_user_action(user, "User", "LOGIN", description=f"{user} inicio sesion")
    return redirect("customer_portal:dashboard" if user.user_type == "CLIENTE" else "dashboard")


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

