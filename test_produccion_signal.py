#!/usr/bin/env python
"""Prueba que los consumos de producci\u00f3n descuentan inventario solo una vez."""

import os
import sys
import django
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
# Compatibilidad con rutas antiguas
sys.path.append('/Volumes/Indunnova/colorplastic')

# Inicializar Django
django.setup()
from django.core.management import call_command

# Asegurar que las tablas existan y limpiar datos previos
call_command('migrate', run_syncdb=True, verbosity=0)
call_command('flush', verbosity=0, interactive=False)

from gestion.models import (
    Bodegas, Lotes, Materiales, Maquinas, Operarios,
    ProduccionMolido, ProduccionConsumo, MovimientosInventario
)


def test_consumo_post_save():
    """Crea un proceso de producci\u00f3n y verifica que el stock se descuente una sola vez."""

    # Limpiar posibles residuos de pruebas anteriores
    MovimientosInventario.objects.filter(observaciones__contains="SIGNAL").delete()
    ProduccionConsumo.objects.filter(id_lote_consumido__numero_lote__contains="SIGNAL").delete()
    ProduccionMolido.objects.filter(id_lote_producido__numero_lote__contains="SIGNAL").delete()
    Lotes.objects.filter(numero_lote__contains="SIGNAL").delete()
    Bodegas.objects.filter(nombre__contains="SIGNAL").delete()
    Materiales.objects.filter(nombre__contains="MAT SIGNAL").delete()
    Maquinas.objects.filter(nombre__contains="MAQ SIGNAL").delete()
    Operarios.objects.filter(nombre_completo__contains="Operario Signal").delete()

    bodega = Bodegas.objects.create(nombre="BODEGA SIGNAL")
    material = Materiales.objects.create(nombre="MAT SIGNAL", tipo="Molido")
    maquina = Maquinas.objects.create(nombre="MAQ SIGNAL", tipo_proceso="Molido")
    operario = Operarios.objects.create(codigo="SIG", nombre_completo="Operario Signal")

    lote = Lotes.objects.create(
        numero_lote="SIGNAL-001",
        id_material=material,
        cantidad_inicial=Decimal("100.00"),
        id_bodega_actual=bodega
    )

    lote_prod = Lotes.objects.create(
        numero_lote="SIGNAL-PROD",
        id_material=material,
        cantidad_inicial=Decimal("0.00"),
        id_bodega_actual=bodega
    )

    prod = ProduccionMolido.objects.create(
        id_maquina=maquina,
        id_operario=operario,
        cantidad_salida=Decimal("10.00"),
        id_bodega_destino=bodega,
        id_lote_producido=lote_prod
    )

    ProduccionConsumo.objects.create(
        id_produccion_molido=prod,
        id_lote_consumido=lote,
        cantidad_consumida=Decimal("20.00"),
        id_bodega_origen=bodega
    )

    lote.refresh_from_db()
    mov_count = MovimientosInventario.objects.filter(
        id_lote=lote, tipo_movimiento="ConsumoProduccion"
    ).count()

    if lote.cantidad_actual == Decimal("80.00") and mov_count == 1:
        print("✅ Consumo aplicado exactamente una vez")
        return True
    else:
        print(f"❌ Resultado inesperado - Stock: {lote.cantidad_actual}, Movimientos: {mov_count}")
        return False


if __name__ == "__main__":
    test_consumo_post_save()
