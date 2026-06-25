from ..decorators import refresh_command
import logging
from django.core.management import call_command
from ..utils import bump_all_sim_list_cache_versions, bump_dashboard_cache_version, log_user_action
from django.http import JsonResponse

logger = logging.getLogger(__name__)

@refresh_command('update_sims')
def refresh_sim(request):
    bump_dashboard_cache_version()
    bump_all_sim_list_cache_versions()

@refresh_command('actual_usage')
def refresh_monthly(request):
    bump_dashboard_cache_version()

@refresh_command('update_orders')
def refresh_orders(request):
    bump_dashboard_cache_version()

@refresh_command('update_status')
def refresh_status(request):
    bump_dashboard_cache_version()
    bump_all_sim_list_cache_versions()

@refresh_command('update_sms_quotas')
def refresh_sms_quota(request):
    bump_dashboard_cache_version()
    bump_all_sim_list_cache_versions()

@refresh_command('update_data_quotas')
def refresh_data_quota(request):
    bump_dashboard_cache_version()
    bump_all_sim_list_cache_versions()

def refresh_sms(request, iccid):
    if request.method == 'POST':
        try:
            call_command('save_sms', iccid)
            log_user_action(request.user, 'CommandRunLog', 'REFRESH', object_id=None, description=f'{request.user} uso el comando save_sms')
            return JsonResponse({"ok": True})
        except Exception as e:
            logger.exception("Error al ejecutar save_sms para %s", iccid)
            return JsonResponse({"ok": False, "error": str(e)}, status=500)
