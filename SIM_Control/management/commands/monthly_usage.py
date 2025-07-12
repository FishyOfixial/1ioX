from django.core.management.base import BaseCommand
from ...save_to_DB import save_usage_per_sim_month
from ...models import CommandRunLog
from django.utils import timezone

class Command(BaseCommand):
    help = "Guarda el uso mensual de cada SIM desde la API"

    def handle(self, *args, **kwargs):
        save_usage_per_sim_month()

        CommandRunLog.objects.update_or_create(
            command_name = 'monthly_usage',
            defaults={'last_run': timezone.now()}
        )