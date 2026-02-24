from datetime import timedelta

from django.shortcuts import render
from django.db.models import Case, When
from django.core.paginator import Paginator
from django.utils import timezone
from ..decorators import matriz_required
from .translations import get_translation
from ..models import IntegrationLog, UserActionLog, User

@matriz_required
def administration(request):
    user = request.user

    lang, base = get_translation(user, "dashboard")
    cutoff = timezone.now() - timedelta(days=90)

    # Data retention: old admin/integration logs are not needed after 3 months.
    UserActionLog.objects.filter(timestamp__lt=cutoff).delete()
    IntegrationLog.objects.filter(created_at__lt=cutoff).delete()

    action = (request.GET.get("action") or "").upper()
    user_id = request.GET.get("user_id")
    int_source = request.GET.get("int_source") or ""
    int_level = (request.GET.get("int_level") or "").upper()

    logs_qs = UserActionLog.objects.filter(timestamp__gte=cutoff).select_related("user").order_by("-timestamp")
    if user.username != "Ivan":
        logs_qs = logs_qs.exclude(action__in=["LOGIN", "LOGOUT", "REFRESH"])
    if action:
        logs_qs = logs_qs.filter(action=action)
    if user_id:
        logs_qs = logs_qs.filter(user_id=user_id)

    integration_qs = IntegrationLog.objects.filter(created_at__gte=cutoff).order_by("-created_at")
    if int_source:
        integration_qs = integration_qs.filter(logger_name=int_source)
    if int_level:
        integration_qs = integration_qs.filter(level=int_level)

    user_logs_page = Paginator(logs_qs, 50).get_page(request.GET.get("user_logs_page"))
    integration_logs_page = Paginator(integration_qs, 50).get_page(request.GET.get("integration_logs_page"))

    orden = ['MATRIZ', 'DISTRIBUIDOR', 'REVENDEDOR']
    cases = [When(user_type=value, then=pos) for pos, value in enumerate(orden)]
    users = User.objects.filter(user_type__in=orden).only("id", "first_name", "last_name", "user_type").order_by(Case(*cases))
    
    context = {
        'base': base,
        'lang': lang,
        'filters': {
            'logs': user_logs_page,
            'users': users
        },
        'integration_logs': integration_logs_page,
        'selected_action': action,
        'selected_user_id': str(user_id or ""),
        'selected_int_source': int_source,
        'selected_int_level': int_level,
        
    }
    return render(request, 'admin.html', context)
