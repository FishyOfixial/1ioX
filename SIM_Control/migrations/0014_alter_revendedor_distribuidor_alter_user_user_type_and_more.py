# Generated by Django 5.2.3 on 2025-07-11 06:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SIM_Control', '0013_vehicle_usuario'),
    ]

    operations = [
        migrations.AlterField(
            model_name='revendedor',
            name='distribuidor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='revendedor', to='SIM_Control.distribuidor'),
        ),
        migrations.AlterField(
            model_name='user',
            name='user_type',
            field=models.CharField(choices=[('MATRIZ', 'Matriz'), ('DISTRIBUIDOR', 'Distribuidor'), ('REVENDEDOR', 'Revendedor'), ('FINAL', 'Usuario Final')], default='DISTRIBUIDOR', max_length=20),
        ),
        migrations.AlterField(
            model_name='usuariofinal',
            name='revendedor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='usuarios_finales', to='SIM_Control.revendedor'),
        ),
    ]
