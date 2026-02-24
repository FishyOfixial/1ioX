from django.core.management.base import BaseCommand

from billing.models import MembershipPlan


class Command(BaseCommand):
    help = "Rellena period_unit y period_count en planes existentes sin duplicar ni borrar datos."

    PERIOD_MAPPING = {
        30: ("month", 1),
        90: ("month", 3),
        180: ("month", 6),
        365: ("year", 1),
        1825: ("year", 5),
    }

    def handle(self, *args, **options):
        updated = 0
        reviewed = 0

        plans = MembershipPlan.objects.all().order_by("id")

        self.stdout.write("Migrando periodos de planes...")

        for plan in plans:
            reviewed += 1
            if plan.period_unit and plan.period_count:
                continue

            mapping = self.PERIOD_MAPPING.get(plan.duration_days)
            if not mapping:
                continue

            plan.period_unit, plan.period_count = mapping
            plan.save(update_fields=["period_unit", "period_count"])
            updated += 1

            self.stdout.write(
                f"Plan actualizado: {plan.name} -> {plan.period_count} {plan.period_unit}"
            )

        self.stdout.write(f"{reviewed} planes revisados")
        self.stdout.write(f"{updated} planes actualizados")