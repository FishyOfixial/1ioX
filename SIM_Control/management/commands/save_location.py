from django.core.management.base import BaseCommand
from ...api_client import get_sim_location_api
from ...save_to_DB import save_sim_location
from ...models import CommandRunLog
from django.utils import timezone

class Command(BaseCommand):
    help = "Guarda los SMS en la DB para un ICCID específico"
    
    def add_arguments(self, parser):
        parser.add_argument('iccid', type=str)

    def handle(self, *args, **kwargs):
        iccid = kwargs['iccid']
        location = get_sim_location_api(iccid)
        save_sim_location(location, iccid)
        self.stdout.write(self.style.SUCCESS(f"Guardada localizacion para {iccid}"))

        CommandRunLog.objects.update_or_create(
            command_name = 'save_location',
            defaults={'last_run': timezone.now()}
        )