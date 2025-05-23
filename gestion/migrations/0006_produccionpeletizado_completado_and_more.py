# Generated by Django 5.2 on 2025-05-09 00:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0005_maquinas_activo_alter_lotes_fecha_modificacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='produccionpeletizado',
            name='completado',
            field=models.BooleanField(default=False, verbose_name='Completado'),
        ),
        migrations.AddField(
            model_name='produccionpeletizado',
            name='estado',
            field=models.CharField(choices=[('en_proceso', 'En Proceso'), ('completado', 'Completado')], default='en_proceso', max_length=20, verbose_name='Estado'),
        ),
    ]
