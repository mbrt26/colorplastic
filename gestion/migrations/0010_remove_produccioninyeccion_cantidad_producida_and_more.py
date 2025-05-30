# Generated by Django 4.2.9 on 2025-05-22 22:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0009_despacho_produccioninyeccion_archivo_adjunto_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='produccioninyeccion',
            name='cantidad_producida',
        ),
        migrations.RemoveField(
            model_name='produccionlavado',
            name='cantidad_producida',
        ),
        migrations.RemoveField(
            model_name='produccionmolido',
            name='cantidad_producida',
        ),
        migrations.RemoveField(
            model_name='produccionpeletizado',
            name='cantidad_producida',
        ),
        migrations.AddField(
            model_name='produccioninyeccion',
            name='cantidad_entrada',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Entrada'),
        ),
        migrations.AddField(
            model_name='produccioninyeccion',
            name='cantidad_salida',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Salida'),
        ),
        migrations.AddField(
            model_name='produccioninyeccion',
            name='merma',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Merma (Pérdida)'),
        ),
        migrations.AddField(
            model_name='produccionlavado',
            name='cantidad_entrada',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Entrada'),
        ),
        migrations.AddField(
            model_name='produccionlavado',
            name='cantidad_salida',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Salida'),
        ),
        migrations.AddField(
            model_name='produccionlavado',
            name='merma',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Merma (Pérdida)'),
        ),
        migrations.AddField(
            model_name='produccionmolido',
            name='cantidad_entrada',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Entrada'),
        ),
        migrations.AddField(
            model_name='produccionmolido',
            name='cantidad_salida',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Salida'),
        ),
        migrations.AddField(
            model_name='produccionmolido',
            name='merma',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Merma (Pérdida)'),
        ),
        migrations.AddField(
            model_name='produccionpeletizado',
            name='cantidad_entrada',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Entrada'),
        ),
        migrations.AddField(
            model_name='produccionpeletizado',
            name='cantidad_salida',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Cantidad de Salida'),
        ),
        migrations.AddField(
            model_name='produccionpeletizado',
            name='merma',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Merma (Pérdida)'),
        ),
    ]
