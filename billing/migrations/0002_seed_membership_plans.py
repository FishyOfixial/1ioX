from django.db import migrations


def seed_membership_plans(apps, schema_editor):
    MembershipPlan = apps.get_model("billing", "MembershipPlan")

    plans = [
        {"name": "Mensual", "duration_days": 30, "price": "0.00"},
        {"name": "Trimestral", "duration_days": 90, "price": "0.00"},
        {"name": "Semestral", "duration_days": 180, "price": "0.00"},
        {"name": "Anual", "duration_days": 365, "price": "0.00"},
    ]

    for plan in plans:
        MembershipPlan.objects.get_or_create(
            name=plan["name"],
            duration_days=plan["duration_days"],
            defaults={"price": plan["price"], "is_active": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_membership_plans, migrations.RunPython.noop),
    ]
