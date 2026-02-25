from django.db import migrations


def seed_test_plan(apps, schema_editor):
    MembershipPlan = apps.get_model("billing", "MembershipPlan")

    plan, created = MembershipPlan.objects.get_or_create(
        name="Prueba 1 dia",
        duration_days=1,
        defaults={
            "price": 0,
            "is_active": True,
            "period_unit": "day",
            "period_count": 1,
        },
    )

    if not created:
        updates = []
        if not plan.is_active:
            plan.is_active = True
            updates.append("is_active")
        if not plan.period_unit:
            plan.period_unit = "day"
            updates.append("period_unit")
        if not plan.period_count:
            plan.period_count = 1
            updates.append("period_count")
        if updates:
            plan.save(update_fields=updates)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0006_subscription_auto_renew_fields"),
    ]

    operations = [
        migrations.RunPython(seed_test_plan, noop_reverse),
    ]
