# Generated by Django 5.2.3 on 2025-07-25 20:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('SIM_Control', '0034_alter_useractionlog_timestamp'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='simassignation',
            name='assigned_to_vehicle',
        ),
    ]
