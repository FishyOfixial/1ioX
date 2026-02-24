from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from SIM_Control.models import SimCard
from billing.models import Subscription
from billing.services.subscription_dates import normalize_to_midday


class Command(BaseCommand):
    help = (
        "Actualiza el start_date de la suscripción actual de cada SIM "
        "para que coincida con activation_date de SimCard (si existe)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cambios sin escribir en base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        sims = (
            SimCard.objects.filter(activation_date__isnull=False)
            .only("id", "iccid", "activation_date")
        )

        scanned = 0
        updated = 0
        skipped = 0

        self.stdout.write("Revisando suscripciones actuales...")

        for sim in sims.iterator():
            scanned += 1
            subscription = sim.current_subscription
            if not subscription:
                skipped += 1
                continue

            # Solo aplica para la suscripción actual (activa/pending/suspended).
            if subscription.status not in {"active", "pending", "suspended"}:
                skipped += 1
                continue

            new_start = normalize_to_midday(sim.activation_date)
            if not new_start:
                skipped += 1
                continue

            new_end = normalize_to_midday(new_start + relativedelta(years=5))

            if subscription.start_date == new_start and subscription.end_date == new_end:
                skipped += 1
                continue

            self.stdout.write(
                (
                    f"SIM {sim.iccid}: "
                    f"start {subscription.start_date} -> {new_start} | "
                    f"end {subscription.end_date} -> {new_end}"
                )
            )

            if not dry_run:
                Subscription.objects.filter(pk=subscription.pk).update(
                    start_date=new_start,
                    end_date=new_end,
                )
            updated += 1

        mode = "DRY-RUN" if dry_run else "EJECUCIÓN"
        self.stdout.write(self.style.SUCCESS(f"{mode} finalizada"))
        self.stdout.write(f"SIMs revisadas: {scanned}")
        self.stdout.write(f"Suscripciones actualizadas: {updated}")
        self.stdout.write(f"Suscripciones omitidas: {skipped}")
        self.stdout.write(f"Timestamp: {now.isoformat()}")
