from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def config(request):
    return redirect("admin")


@login_required
def update_limits(request):
    return redirect("admin")
