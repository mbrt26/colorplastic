#!/usr/bin/env python
"""
Script de prueba específico para validar la corrección del problema de duplicación de inventarios
"""

import os
import sys
import django
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
sys.path.append('/Volumes/Indunnova/colorplastic')

# Forzar flush de stdout
import functools
print = functools.partial(print, flush=True)

django.setup()

from gestion.models import Bodegas, Lotes, MovimientosInventario, Materiales
from gestion.inventario_utils import procesar_movimiento_inventario
from django.utils import timezone

def test_correccion_duplicacion():
    """Prueba específica para verificar que se corrigió el problema de duplicación."""
    print("🧪 PRUEBA ESPECÍFICA: CORRECCIÓN DE DUPLICACIÓN DE INVENTARIOS")
    print("=" * 65)
    
    try:
        # Limpiar datos de prueba específicos
        MovimientosInventario.objects.filter(observaciones__contains="CORRECCION").delete()
        Lotes.objects.filter(numero_lote__contains="CORRECCION").delete()
        
        # Crear datos básicos
        bodega_pt, _ = Bodegas.objects.get_or_create(
            nombre="Bodega PT CORRECCION",
            defaults={'descripcion': 'Bodega de prueba corrección'}
        )
        
        material_salida, _ = Materiales.objects.get_or_create(
            nombre="Material CORRECCION",
            defaults={'tipo': 'ProductoTerminado', 'descripcion': 'Material de prueba corrección'}
        )
        
        # PASO 1: Crear lote como en producción
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]
        cantidad_producida = Decimal('100')
        
        lote_producido = Lotes.objects.create(
            numero_lote=f"CORRECCION-{timestamp}",
            id_material=material_salida,
            cantidad_inicial=cantidad_producida,
            cantidad_actual=cantidad_producida,
            id_bodega_actual=bodega_pt,
            activo=True
        )
        
        print(f"✅ PASO 1: Lote creado")
        print(f"  - Número: {lote_producido.numero_lote}")
        print(f"  - Cantidad inicial: {lote_producido.cantidad_inicial} kg")
        print(f"  - Cantidad actual: {lote_producido.cantidad_actual} kg")
        print(f"  - Bodega: {lote_producido.id_bodega_actual.nombre}")
        
        # PASO 2: Registrar movimiento IngresoServicio (como en views.py corregido)
        print(f"\n🔄 PASO 2: Registrando movimiento IngresoServicio...")
        print(f"  - Cantidad antes: {lote_producido.cantidad_actual} kg")
        
        movimiento = procesar_movimiento_inventario(
            tipo_movimiento='IngresoServicio',
            lote=lote_producido,
            cantidad=cantidad_producida,
            bodega_destino=bodega_pt,
            observaciones="CORRECCION - Entrada producción"
        )
        
        # PASO 3: Verificar resultado
        lote_producido.refresh_from_db()
        print(f"  - Cantidad después: {lote_producido.cantidad_actual} kg")
        print(f"  - Movimiento ID: {movimiento.pk}")
        
        # VALIDACIÓN
        print(f"\n📊 VALIDACIÓN:")
        print(f"  - Cantidad esperada: {cantidad_producida} kg")
        print(f"  - Cantidad real: {lote_producido.cantidad_actual} kg")
        
        if lote_producido.cantidad_actual == cantidad_producida:
            print(f"  ✅ CORRECCIÓN EXITOSA: No hay duplicación")
            print(f"  ✅ El lote mantiene su cantidad original: {cantidad_producida} kg")
            resultado = True
        else:
            print(f"  ❌ PROBLEMA PERSISTE: Cantidad incorrecta")
            print(f"     Esperado: {cantidad_producida} kg")
            print(f"     Actual: {lote_producido.cantidad_actual} kg")
            resultado = False
        
        # Verificar que el movimiento se registró
        mov_count = MovimientosInventario.objects.filter(
            observaciones__contains="CORRECCION"
        ).count()
        print(f"  - Movimientos registrados: {mov_count}")
        
        if mov_count == 1:
            print(f"  ✅ Movimiento registrado correctamente para trazabilidad")
        else:
            print(f"  ❌ Problema con registro de movimientos")
            resultado = False
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    resultado = test_correccion_duplicacion()
    print(f"\n" + "=" * 65)
    if resultado:
        print("🎉 CORRECCIÓN VERIFICADA: El problema de duplicación está solucionado")
        print("✅ Los inventarios ahora se calculan correctamente")
    else:
        print("⚠️ LA CORRECCIÓN NO FUNCIONÓ: El problema persiste")
        print("❌ Se requiere revisión adicional")