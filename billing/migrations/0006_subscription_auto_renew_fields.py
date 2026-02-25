from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0005_subscriptionpurchase"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="mp_last_event_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="mp_preapproval_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="mp_preapproval_status",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
