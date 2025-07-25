# Generated by Django 5.2.3 on 2025-07-07 18:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SIM_Control', '0007_alter_simquota_threshold_percentage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simquota',
            name='last_status_change_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='simquota',
            name='threshold_percentage',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
