from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db.models import Exists, OuterRef

from SIM_Control.models import SimCard
from billing.models import MembershipPlan, Subscription


class Command(BaseCommand):
    help = "Inicializa suscripciones activas de 5 años para SIMs sin suscripciones."

    def handle(self, *args, **options):

        plan_5_years, _ = MembershipPlan.objects.get_or_create(
            name="5 Años",
            duration_days=1825,
            defaults={"price": 0, "is_active": True},
        )

        subquery = Subscription.objects.filter(sim=OuterRef("pk"))

        sims_without_subscriptions = SimCard.objects.annotate(
            has_subscription=Exists(subquery)
        ).filter(has_subscription=False)

        total_found = sims_without_subscriptions.count()
        initialized_count = 0

        self.stdout.write(f"{total_found} SIMs encontradas sin suscripciones")

        with transaction.atomic():
            for sim in sims_without_subscriptions.iterator():

                if Subscription.objects.filter(sim=sim).exists():
                    continue

                now = timezone.now()

                self.stdout.write(f"Inicializando SIM {sim.iccid}")

                Subscription.objects.create(
                    sim=sim,
                    plan=plan_5_years,
                    start_date=now,
                    status="active",
                    auto_renew=False,
                )

                initialized_count += 1

        self.stdout.write(f"{initialized_count} SIMs inicializadas")
