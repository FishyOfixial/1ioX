from django.core.management.base import BaseCommand
from ...api_client import get_all_orders_full
from ...save_to_DB import save_order_to_db
from ...models import CommandRunLog
from django.utils import timezone

class Command(BaseCommand):
    help = "Actualizar SIMs desde la API de 1NCE y guardarlas en la base de datos"
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Descargando Orders desde API...')
        orders = get_all_orders_full()
        save_order_to_db(orders)
        self.stdout.write(self.style.SUCCESS('Orders actualizadas y guardadas en la base de datos.'))

        CommandRunLog.objects.update_or_create(
            command_name = 'update_orders',
            defaults={'last_run': timezone.now()}
        )