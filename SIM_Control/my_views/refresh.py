from ..decorators import refresh_command
from django.core.management import call_command
from ..utils import log_user_action
from django.http import JsonResponse

@refresh_command('update_sims')
def refresh_sim(request):
    pass

@refresh_command('actual_usage')
def refresh_monthly(request):
    pass

@refresh_command('update_orders')
def refresh_orders(request):
    pass

@refresh_command('update_status')
def refresh_status(request):
    pass

@refresh_command('update_sms_quotas')
def refresh_sms_quota(request):
    pass

@refresh_command('update_data_quotas')
def refresh_data_quota(request):
    pass

def refresh_sms(request, iccid):
    if request.method == 'POST':
        try:
            call_command('save_sms', iccid)
            log_user_action(request.user, 'CommandRunLog', 'REFRESH', object_id=None, description=f'{request.user} uso el comando save_sms')
            return JsonResponse({"ok": True})
        except Exception as e:
            print(f"Error al ejecutar save_sms para {iccid}: {e}")
            return JsonResponse({"ok": False, "error": str(e)}, status=500)
