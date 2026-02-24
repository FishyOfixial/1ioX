from .my_views import ds_, liv_, lov_, gs_, gsd_, as_, uss_, od_, sd_, usl_, ss_, ud_, uua_, uu_, rsim_, rm_, ro_, rsta_, rsq_, rdq_, rsms_, gu_, cd_, cr_, cc_, co_, gl_, agsl_, adm_
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.management import call_command
import threading
from django.shortcuts import redirect
from datetime import datetime, timedelta
from .models import SIMAssignation
from django.contrib.auth.decorators import login_required

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
def cron_check_subscriptions(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    auth = request.headers.get('Authorization', '')
    if auth != f'Bearer {settings.CRON_TOKEN}':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    def worker():
        try:
            print("Background: starting check_subscriptions")
            call_command('check_subscriptions')
            print("Background: check_subscriptions finished")
        except Exception:
            print("Background check_subscriptions failed")

    thread = threading.Thread(target=worker, daemon=True, name="cron_check_subscriptions_worker")
    thread.start()

    return JsonResponse({'status': 'accepted'}, status=202)    

def set_language(request, lang):
    request.user.preferred_lang = lang
    request.user.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))


def role_based_404_redirect(request, exception):
    if request.user.is_authenticated:
        if request.user.user_type == 'CLIENTE':
            return redirect('customer_portal:dashboard')
        return redirect('dashboard')
    return redirect('login')


@login_required
def root_entrypoint(request):
    if request.user.user_type == 'CLIENTE':
        return redirect('customer_portal:dashboard')
    return ds_(request)
