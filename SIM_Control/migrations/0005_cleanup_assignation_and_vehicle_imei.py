from django.db import migrations, models
import django.db.models.deletion


def dedupe_vehicle_sim_relations(apps, schema_editor):
    Vehicle = apps.get_model("SIM_Control", "Vehicle")
    seen_sim_ids = set()
    for vehicle in Vehicle.objects.exclude(sim_id__isnull=True).order_by("-id"):
        if vehicle.sim_id in seen_sim_ids:
            vehicle.sim_id = None
            vehicle.save(update_fields=["sim"])
            continue
        seen_sim_ids.add(vehicle.sim_id)


class Migration(migrations.Migration):
    dependencies = [
        ("SIM_Control", "0004_rename_sim_control_logger__e4f261_idx_sim_control_logger__31705d_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(dedupe_vehicle_sim_relations, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="simassignation",
            name="deactivation_date",
        ),
        migrations.RemoveField(
            model_name="simassignation",
            name="last_topup_date",
        ),
        migrations.RemoveField(
            model_name="simassignation",
            name="topup_duration",
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="sim",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vehicle",
                to="SIM_Control.simcard",
            ),
        ),
    ]

