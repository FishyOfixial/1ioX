from django.core.management.base import BaseCommand
from ...api_client import get_sim_sms_all
from ...save_to_DB import save_sms_log
from ...models import CommandRunLog
from django.utils import timezone

class Command(BaseCommand):
    help = "Guarda los SMS en la DB para un ICCID específico"
    
    def add_arguments(self, parser):
        parser.add_argument('iccid', type=str)

    def handle(self, *args, **kwargs):
        iccid = kwargs['iccid']
        sms = get_sim_sms_all(iccid)
        save_sms_log(sms, iccid)
        self.stdout.write(self.style.SUCCESS(f"Guardados {len(sms)} SMS para {iccid}"))

        CommandRunLog.objects.update_or_create(
            command_name = 'save_sms',
            defaults={'last_run': timezone.now()}
        )