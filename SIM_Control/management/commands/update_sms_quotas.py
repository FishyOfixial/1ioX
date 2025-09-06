from django.core.management.base import BaseCommand
from ...save_to_DB import save_sim_quota
from ...models import CommandRunLog
from django.utils import timezone

class Command(BaseCommand):
    help = "Guarda el el volumen de cada SIM desde la API"

    def handle(self, *args, **kwargs):
        save_sim_quota('SMS')

        CommandRunLog.objects.update_or_create(
            command_name = 'update_sms_quotas',
            defaults={'last_run': timezone.now()}
        )