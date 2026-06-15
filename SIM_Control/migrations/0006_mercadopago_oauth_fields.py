from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("SIM_Control", "0005_cleanup_assignation_and_vehicle_imei"),
    ]

    operations = [
        migrations.AddField(
            model_name="distribuidor",
            name="mercado_pago_access_token",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="distribuidor",
            name="mercado_pago_connected_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="distribuidor",
            name="mercado_pago_is_connected",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="distribuidor",
            name="mercado_pago_refresh_token",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="distribuidor",
            name="mercado_pago_token_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="distribuidor",
            name="mercado_pago_user_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="revendedor",
            name="mercado_pago_access_token",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="revendedor",
            name="mercado_pago_connected_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="revendedor",
            name="mercado_pago_is_connected",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="revendedor",
            name="mercado_pago_refresh_token",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="revendedor",
            name="mercado_pago_token_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="revendedor",
            name="mercado_pago_user_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
