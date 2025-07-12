from django.core.management.base import BaseCommand
from ...api_client import get_all_sims_full
from ...save_to_DB import save_sim_to_db
from ...models import CommandRunLog
from django.utils import timezone

class Command(BaseCommand):
    help = "Actualizar SIMs desde la API de 1NCE y guardarlas en la base de datos"
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Descargando SIMs desde API...')
        sims = get_all_sims_full()
        save_sim_to_db(sims)
        self.stdout.write(self.style.SUCCESS('SIMs actualizadas y guardadas en la base de datos.'))

        CommandRunLog.objects.update_or_create(
            command_name = 'update_sims',
            defaults={'last_run': timezone.now()}
        )