from .my_views import ds_, liv_, lov_, gs_, gsd_, as_, uss_, od_, sd_, usl_, ss_, ud_, uua_, uu_, rsim_, rm_, ro_, rsta_, rsq_, rdq_, rsms_, gu_, cd_, cr_, cc_, co_, gl_, agsl_, adm_
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.management import call_command
import threading
from django.shortcuts import redirect
from datetime import datetime, timedelta
from .models import SIMAssignation

@csrf_exempt
def cron_usage(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    auth = request.headers.get('Authorization', '')
    if auth != f'Bearer {settings.CRON_TOKEN}':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    def worker():
        try:
            print("🕐 Background: starting usage update")
            call_command('actual_usage')
            call_command('update_data_quotas')
            call_command('update_sms_quotas')
            print("🕐 Background: usage update finished")
        except Exception:
            print("Background usage update failed")

    thread = threading.Thread(target=worker, daemon=True, name="cron_usage_worker")
    thread.start()

    return JsonResponse({'status': 'accepted'}, status=202)

@csrf_exempt
def cron_status(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    auth = request.headers.get('Authorization', '')
    if auth != f'Bearer {settings.CRON_TOKEN}':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    def worker():
        try:
            print("🕐 Background: starting update_status")
            call_command('update_status')
            call_command('update_sims')
            print("🕐 Background: update_status finished")
        except Exception:
            print("Background task failed")

    t = threading.Thread(target=worker, daemon=True, name="cron_status_worker")
    t.start()

    return JsonResponse({'status': 'accepted'}, status=202)

@csrf_exempt
def get_expired_sims(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    auth = request.headers.get('Authorization', '')
    if auth != f'Bearer {settings.CRON_TOKEN}':
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    today = datetime.now().date()
    three_days = today + timedelta(days=3)
    expired_sims = SIMAssignation.objects.filter(
        deactivation_date__range=[today, three_days]
    ).select_related('sim', 'content_type')

    if not expired_sims.exists():
        return JsonResponse({'Info': 'No hay SIMs prontas a expirar'}, status=202)
    
    info = []
    for assign in expired_sims:
        if not assign.sim:
            continue
        target = assign.assigned_to
        if target is None:
            continue

        phone = target.get_phone_number() if hasattr(target, 'get_phone_number') else None
        client_name = target.get_full_name() if hasattr(target, 'get_full_name') else str(target)
        time_to_expire = (assign.deactivation_date - today).days
        info.append({
            'iccid': assign.sim.iccid,
            'client': client_name,
            'deactivation_date': assign.deactivation_date,
            'phone_number': phone,
            'time_to_expire': time_to_expire,

        })
    return JsonResponse({'expired_sims': info}, status=202)
    

def set_language(request, lang):
    request.user.preferred_lang = lang
    request.user.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))
