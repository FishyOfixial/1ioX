from django.core.management.base import BaseCommand
from django.utils import timezone

from auditlogs.utils import create_log
from billing.models import Subscription
from billing.services.subscription_api_sync import ensure_sim_disabled


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
            ensure_sim_disabled(subscription)

            create_log(
                log_type="SUBSCRIPTION",
                severity="WARNING",
                message="Subscription expired by check_subscriptions command",
                reference_id=str(subscription.id),
                metadata={"sim_iccid": subscription.sim.iccid},
            )

            self.stdout.write(
                f"SIM {subscription.sim.iccid} deshabilitada por expiracion de plan"
            )
            expired_count += 1

        self.stdout.write(f"{reviewed_count} suscripciones revisadas")
        self.stdout.write(f"{expired_count} suscripciones expiradas")
