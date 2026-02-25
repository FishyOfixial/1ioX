from django.core.management.base import BaseCommand
from django.utils import timezone

from SIM_Control.models import UserActionLog
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

            UserActionLog.objects.create(
                user=None,
                action="UPDATE",
                model_name="Subscription",
                object_id=str(subscription.id),
                description=(
                    f"Subscription expirada para SIM {subscription.sim.iccid} "
                    f"(subscription_id={subscription.id})"
                )[:255],
                timestamp=timezone.now(),
            )

            self.stdout.write(
                f"SIM {subscription.sim.iccid} deshabilitada por expiracion de plan"
            )
            expired_count += 1

        self.stdout.write(f"{reviewed_count} suscripciones revisadas")
        self.stdout.write(f"{expired_count} suscripciones expiradas")
