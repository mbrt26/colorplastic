#!/usr/bin/env python3
"""
Script para diagnosticar el error 'Stock insuficiente. Disponible: 0.00, requerido: 1'
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
sys.path.append('/Volumes/Indunnova/colorplastic')
django.setup()

from gestion.models import Lotes, MovimientosInventario, ProduccionConsumo, ProduccionLavado
from django.db import transaction
from decimal import Decimal

def diagnosticar_stock_error():
    """Diagnostica posibles causas del error de stock insuficiente."""
    print("=== DIAGNÓSTICO ERROR STOCK INSUFICIENTE ===\n")
    
    # 1. Revisar lotes con cantidad_actual = 0
    lotes_vacios = Lotes.objects.filter(cantidad_actual=0, activo=True)
    print(f"🔍 LOTES CON STOCK 0 PERO MARCADOS COMO ACTIVOS:")
    print(f"Total encontrados: {lotes_vacios.count()}")
    for lote in lotes_vacios[:10]:  # Mostrar solo primeros 10
        print(f"  - {lote.numero_lote} | Material: {lote.id_material.nombre} | Stock: {lote.cantidad_actual}")
    
    if lotes_vacios.count() > 0:
        print("⚠️  PROBLEMA DETECTADO: Hay lotes con stock 0 pero marcados como activos")
        print("   Esto puede causar el error cuando se intenta consumir de estos lotes\n")
    
    # 2. Revisar últimos movimientos fallidos
    print("🔍 ÚLTIMOS MOVIMIENTOS DE CONSUMO:")
    movimientos_consumo = MovimientosInventario.objects.filter(
        tipo_movimiento='ConsumoProduccion'
    ).order_by('-fecha')[:5]
    
    for mov in movimientos_consumo:
        print(f"  - Fecha: {mov.fecha}")
        print(f"    Lote: {mov.id_lote.numero_lote}")
        print(f"    Cantidad consumida: {mov.cantidad}")
        print(f"    Stock actual del lote: {mov.id_lote.cantidad_actual}")
        print()
    
    # 3. Verificar lotes que se están usando en producciones recientes
    print("🔍 ÚLTIMAS PRODUCCIONES Y SUS LOTES:")
    producciones_recientes = ProduccionLavado.objects.order_by('-fecha')[:5]
    
    for prod in producciones_recientes:
        print(f"  - Producción OT: {prod.orden_trabajo}")
        print(f"    Lote producido: {prod.id_lote_producido.numero_lote}")
        print(f"    Stock del lote: {prod.id_lote_producido.cantidad_actual}")
        
        # Verificar si tiene consumos asociados
        consumos = prod.consumos_lavado.all()
        if consumos.exists():
            print("    Consumos asociados:")
            for consumo in consumos:
                print(f"      * {consumo.id_lote_consumido.numero_lote} - {consumo.cantidad_consumida} kg")
                print(f"        Stock actual: {consumo.id_lote_consumido.cantidad_actual} kg")
        else:
            print("    Sin consumos asociados")
        print()
    
    # 4. Buscar inconsistencias en el inventario
    print("🔍 VERIFICANDO INCONSISTENCIAS:")
    lotes_inconsistentes = []
    
    for lote in Lotes.objects.filter(activo=True)[:20]:  # Revisar primeros 20 lotes activos
        # Calcular stock basado en movimientos
        movimientos_entrada = MovimientosInventario.objects.filter(
            id_lote=lote,
            tipo_movimiento__in=['Compra', 'AjustePositivo', 'IngresoServicio']
        ).aggregate(total=django.db.models.Sum('cantidad'))['total'] or Decimal('0')
        
        movimientos_salida = MovimientosInventario.objects.filter(
            id_lote=lote,
            tipo_movimiento__in=['Venta', 'ConsumoProduccion', 'AjusteNegativo', 'SalidaServicio']
        ).aggregate(total=django.db.models.Sum('cantidad'))['total'] or Decimal('0')
        
        stock_calculado = lote.cantidad_inicial + movimientos_entrada - movimientos_salida
        
        if abs(stock_calculado - lote.cantidad_actual) > Decimal('0.01'):
            lotes_inconsistentes.append({
                'lote': lote,
                'stock_actual': lote.cantidad_actual,
                'stock_calculado': stock_calculado,
                'diferencia': lote.cantidad_actual - stock_calculado
            })
    
    if lotes_inconsistentes:
        print(f"⚠️  INCONSISTENCIAS DETECTADAS: {len(lotes_inconsistentes)} lotes")
        for item in lotes_inconsistentes[:5]:  # Mostrar primeros 5
            print(f"  - {item['lote'].numero_lote}")
            print(f"    Stock actual: {item['stock_actual']}")
            print(f"    Stock calculado: {item['stock_calculado']}")
            print(f"    Diferencia: {item['diferencia']}")
            print()
    else:
        print("✅ No se detectaron inconsistencias en los stocks")
    
    print("\n=== RECOMENDACIONES ===")
    if lotes_vacios.count() > 0:
        print("1. Ejecutar corrección de lotes activos con stock 0")
    if lotes_inconsistentes:
        print("2. Recalcular stocks basado en movimientos")
    print("3. Verificar que no se esté intentando consumir de lotes sin stock")

def corregir_lotes_activos():
    """Corrige lotes que están marcados como activos pero tienen stock 0."""
    print("\n=== CORRIGIENDO LOTES ACTIVOS CON STOCK 0 ===")
    
    with transaction.atomic():
        lotes_corregidos = Lotes.objects.filter(
            cantidad_actual=0, 
            activo=True
        ).update(activo=False)
        
        print(f"✅ Corregidos {lotes_corregidos} lotes (marcados como inactivos)")

if __name__ == "__main__":
    diagnosticar_stock_error()
    
    # Preguntar si se quiere ejecutar la corrección
    respuesta = input("\n¿Deseas corregir los lotes activos con stock 0? (s/n): ")
    if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        corregir_lotes_activos()
        print("Corrección completada.")