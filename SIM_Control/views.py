from .my_views import ds_, liv_, lov_, gs_, as_, uss_, od_, sd_, usl_, ss_, ud_, uua_, uu_, rsim_, rm_, ro_, rsta_, rsq_, rdq_, rsms_, gu_, cd_, cr_, cc_

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.management import call_command

@csrf_exempt
def cron_usage(request):
    token = request.headers.get('Authorization')
    if token != f'Bearer {settings.CRON_TOKEN}':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    print("🕐 Iniciando usage update")
    call_command('actual_usage')
    call_command('update_data_quotas')
    call_command('update_sms_quotas')
    print("🕐 usage update terminado")

    return JsonResponse({'status': 'task completed'})

@csrf_exempt
def cron_status(request):
    token = request.headers.get('Authorization')
    if token != f'Bearer {settings.CRON_TOKEN}':
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    print("🕐 Iniciando status update")
    call_command('update_status')
    call_command('update_sims')
    print("🕐 status update terminado")
