from django.contrib.auth.decorators import login_required
from ..utils import get_assigned_iccids
from ..models import Order, SimCard, CommandRunLog
from ..utils import get_data_monthly_usage, get_top_data_usage_per_month, get_top_sms_usage_per_month
from ..decorators import user_in
from django.shortcuts import render

@login_required 
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def dashboard(request):
    user = request.user

    all_orders = Order.objects.all()
    assigned_sims = get_assigned_iccids(user)
    all_sims = SimCard.objects.filter(iccid__in=assigned_sims)
    activadas = all_sims.filter(status='Enabled').count()
    desactivadas = all_sims.filter(status='Disabled').count()
    data_suficiente = all_sims.filter(quota_status='More than 20% available').count()
    data_bajo = all_sims.filter(quota_status='Less than 20% available').count()
    data_sin_volumen = all_sims.filter(quota_status='No volume available').count()
    sms_suficiente = all_sims.filter(quota_status_SMS='More than 20% available').count()
    sms_bajo = all_sims.filter(quota_status_SMS='Less than 20% available').count()
    sms_sin_volumen = all_sims.filter(quota_status_SMS='No volume available').count()

    labels, data_usage, sms_usage = get_data_monthly_usage(assigned_sims)
    top_data_usage = get_top_data_usage_per_month(assigned_sims)
    top_sms_usage = get_top_sms_usage_per_month(assigned_sims)
    
    all_commands = CommandRunLog.objects.all()
    monthly_usage_command = all_commands.filter(command_name="actual_usage").first()
    update_orders_command = all_commands.filter(command_name="update_orders").first()
    update_sims_command = all_commands.filter(command_name="update_sims").first()

    context = {
        'activadas': activadas,
        'desactivadas': desactivadas,
        'data_suficiente': data_suficiente,
        'data_bajo': data_bajo,
        'data_sin_volumen': data_sin_volumen,
        'sms_suficiente': sms_suficiente,
        'sms_bajo': sms_bajo,
        'sms_sin_volumen': sms_sin_volumen,
        'monthly_usage': {
            'labels': labels,
            'data_usage': data_usage,
            'sms_usage': sms_usage,
            'top_data': top_data_usage,
            'top_sms': top_sms_usage,
        },
        'all_comands': {
            'monthly_usage': monthly_usage_command,
            'update_orders': update_orders_command,
            'update_sims': update_sims_command
        },
        'orders': {
            'all_orders': all_orders
        },
    }

    return render(request, 'dashboard.html', context)
