from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def customer_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != "CLIENTE":
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped_view