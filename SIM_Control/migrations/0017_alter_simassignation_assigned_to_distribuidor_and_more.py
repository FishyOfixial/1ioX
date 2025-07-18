# Generated by Django 5.2.3 on 2025-07-11 23:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SIM_Control', '0016_alter_simassignation_assigned_to_vehicle'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simassignation',
            name='assigned_to_distribuidor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='distribuidor', to='SIM_Control.distribuidor'),
        ),
        migrations.AlterField(
            model_name='simassignation',
            name='assigned_to_revendedor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='revendedor', to='SIM_Control.revendedor'),
        ),
        migrations.AlterField(
            model_name='simassignation',
            name='assigned_to_usuario_final',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='usuario_final', to='SIM_Control.usuariofinal'),
        ),
        migrations.AlterField(
            model_name='simassignation',
            name='assigned_to_vehicle',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vehiculo', to='SIM_Control.vehicle'),
        ),
    ]
