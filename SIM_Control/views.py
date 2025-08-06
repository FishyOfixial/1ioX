from .my_views import ds_, liv_, lov_, gs_, as_, uss_, od_, sd_, usl_, ss_, ud_, uua_, uu_, rsim_, rm_, ro_, rsta_, rsq_, rdq_, rsms_, gu_, cd_, cr_, cc_
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.management import call_command
import threading

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
            print("🕐 Background: update_status finished")
            print("🕐 Background: starting update_sims")
            call_command('update_sims')
            print("🕐 Background: update_sims finished")
        except Exception:
            print("Background task failed")

    t = threading.Thread(target=worker, daemon=True, name="cron_status_worker")
    t.start()

    return JsonResponse({'status': 'accepted'}, status=202)
