from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.models import Subscription


class Command(BaseCommand):
    help = "Expira suscripciones activas vencidas y deshabilita la SIM asociada."

    def handle(self, *args, **options):
        now = timezone.now()
        active_subscriptions = Subscription.objects.filter(status="active")
        expired_subscriptions = active_subscriptions.filter(end_date__lt=now).select_related("sim")

        reviewed_count = active_subscriptions.count()
        expired_count = 0

        self.stdout.write("Revisando suscripciones...")

        for subscription in expired_subscriptions:
            subscription.expire()
            self.stdout.write(
                f"SIM {subscription.sim.iccid} deshabilitada por expiración de plan"
            )
            expired_count += 1

        self.stdout.write(f"{reviewed_count} suscripciones revisadas")
        self.stdout.write(f"{expired_count} suscripciones expiradas")