from .my_views import ds_, liv_, lov_, gs_, as_, uss_, od_, sd_, usl_, ss_, ud_, uua_, uu_, rsim_, rm_, ro_, rsta_, rsq_, rdq_, rsms_, gu_, cd_, cr_, cc_

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.management import call_command

@csrf_exempt
def cron_task(request):
    token = request.headers.get('Authorization')
    if token != f'Bearer {settings.CRON_TOKEN}':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    print("🕐 Iniciando Cron Job")
    call_command('actual_usage')
    call_command('update_status')
    call_command('update_sims')
    print("🕐 Cron Job terminado")

    return JsonResponse({'status': 'task completed'})