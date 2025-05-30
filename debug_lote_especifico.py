#!/usr/bin/env python3
"""
Script para diagnosticar el lote específico: 1-Molido-20250529215357
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
sys.path.append('/Volumes/Indunnova/colorplastic')
django.setup()

from gestion.models import Lotes, MovimientosInventario, ProduccionConsumo
from django.db.models import Sum
from decimal import Decimal

def diagnosticar_lote_especifico():
    """Diagnostica el lote específico que está causando problemas."""
    numero_lote = "1-Molido-20250529215357"
    
    print(f"=== DIAGNÓSTICO DETALLADO DEL LOTE: {numero_lote} ===\n")
    
    try:
        lote = Lotes.objects.get(numero_lote=numero_lote)
    except Lotes.DoesNotExist:
        print(f"❌ ERROR: No se encontró el lote {numero_lote}")
        return
    
    print(f"📦 INFORMACIÓN DEL LOTE:")
    print(f"  - ID: {lote.id_lote}")
    print(f"  - Número: {lote.numero_lote}")
    print(f"  - Material: {lote.id_material.nombre}")
    print(f"  - Cantidad inicial: {lote.cantidad_inicial} kg")
    print(f"  - Cantidad actual: {lote.cantidad_actual} kg")
    print(f"  - Bodega actual: {lote.id_bodega_actual.nombre}")
    print(f"  - Activo: {lote.activo}")
    print(f"  - Fecha creación: {lote.fecha_creacion}")
    print()
    
    # Buscar todos los movimientos de este lote
    print("📋 HISTORIAL DE MOVIMIENTOS:")
    movimientos = MovimientosInventario.objects.filter(id_lote=lote).order_by('fecha')
    
    if not movimientos.exists():
        print("  ⚠️  No se encontraron movimientos para este lote")
    else:
        balance = lote.cantidad_inicial
        print(f"  Balance inicial: {balance} kg")
        
        for i, mov in enumerate(movimientos, 1):
            if mov.tipo_movimiento in ['Compra', 'AjustePositivo', 'IngresoServicio']:
                balance += mov.cantidad
                operacion = f"+{mov.cantidad}"
            else:
                balance -= mov.cantidad
                operacion = f"-{mov.cantidad}"
            
            print(f"  {i}. {mov.fecha.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Tipo: {mov.tipo_movimiento}")
            print(f"     Cantidad: {operacion} kg")
            print(f"     Balance después: {balance} kg")
            print(f"     Observaciones: {mov.observaciones or 'N/A'}")
            if mov.produccion_referencia:
                print(f"     Producción ref: {mov.produccion_referencia}")
            print()
    
    # Calcular balance teórico
    entradas = MovimientosInventario.objects.filter(
        id_lote=lote,
        tipo_movimiento__in=['Compra', 'AjustePositivo', 'IngresoServicio']
    ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
    
    salidas = MovimientosInventario.objects.filter(
        id_lote=lote,
        tipo_movimiento__in=['Venta', 'ConsumoProduccion', 'AjusteNegativo', 'SalidaServicio']
    ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
    
    balance_teorico = lote.cantidad_inicial + entradas - salidas
    
    print(f"🧮 CÁLCULO DE BALANCE:")
    print(f"  - Cantidad inicial: {lote.cantidad_inicial} kg")
    print(f"  - Total entradas: +{entradas} kg")
    print(f"  - Total salidas: -{salidas} kg")
    print(f"  - Balance teórico: {balance_teorico} kg")
    print(f"  - Cantidad actual en BD: {lote.cantidad_actual} kg")
    print(f"  - Diferencia: {lote.cantidad_actual - balance_teorico} kg")
    print()
    
    # Buscar consumos que referencien este lote
    print("🔍 CONSUMOS QUE USAN ESTE LOTE:")
    consumos = ProduccionConsumo.objects.filter(id_lote_consumido=lote)
    
    if not consumos.exists():
        print("  ✅ No se encontraron consumos pendientes para este lote")
    else:
        print(f"  Total consumos encontrados: {consumos.count()}")
        for consumo in consumos:
            produccion = consumo.get_produccion_padre()
            print(f"  - Consumo ID: {consumo.id_consumo}")
            print(f"    Cantidad a consumir: {consumo.cantidad_consumida} kg")
            print(f"    Producción padre: {produccion._meta.verbose_name if produccion else 'N/A'}")
            print(f"    Bodega origen: {consumo.id_bodega_origen.nombre}")
            print()
    
    # Verificar si el lote está siendo usado en alguna producción como lote producido
    from gestion.models import ProduccionMolido, ProduccionLavado, ProduccionPeletizado, ProduccionInyeccion
    
    print("🏭 PRODUCCIONES QUE GENERARON ESTE LOTE:")
    producciones = []
    
    try:
        if hasattr(lote, 'produccion_molido_origen'):
            producciones.append(('Molido', lote.produccion_molido_origen))
    except:
        pass
    
    try:
        if hasattr(lote, 'produccion_lavado_origen'):
            producciones.append(('Lavado', lote.produccion_lavado_origen))
    except:
        pass
    
    try:
        if hasattr(lote, 'produccion_peletizado_origen'):
            producciones.append(('Peletizado', lote.produccion_peletizado_origen))
    except:
        pass
    
    try:
        if hasattr(lote, 'produccion_inyeccion_origen'):
            producciones.append(('Inyección', lote.produccion_inyeccion_origen))
    except:
        pass
    
    if producciones:
        for tipo, produccion in producciones:
            print(f"  - Tipo: {tipo}")
            print(f"    OT: {produccion.orden_trabajo}")
            print(f"    Fecha: {produccion.fecha}")
            print(f"    Cantidad entrada: {produccion.cantidad_entrada} kg")
            print(f"    Cantidad salida: {produccion.cantidad_salida} kg")
            print()
    else:
        print("  ⚠️  No se encontró la producción que generó este lote")
    
    print("=== RECOMENDACIONES ===")
    if lote.cantidad_actual <= 0:
        print("❌ PROBLEMA: El lote tiene stock 0 o negativo")
        print("   - No se puede consumir material de este lote")
        print("   - Verificar si el lote debería estar inactivo")
        if lote.activo:
            print("   - ACCIÓN: Marcar el lote como inactivo")
    elif balance_teorico != lote.cantidad_actual:
        print("⚠️  INCONSISTENCIA: Balance teórico no coincide con cantidad actual")
        print("   - Revisar movimientos de inventario")
        print("   - Posible corrección automática necesaria")
    else:
        print("✅ El lote parece estar en estado correcto")

def corregir_lote_especifico():
    """Corrige el lote específico si tiene problemas."""
    numero_lote = "1-Molido-20250529215357"
    
    try:
        lote = Lotes.objects.get(numero_lote=numero_lote)
    except Lotes.DoesNotExist:
        print(f"❌ ERROR: No se encontró el lote {numero_lote}")
        return
    
    print(f"\n=== CORRIGIENDO LOTE: {numero_lote} ===")
    
    if lote.cantidad_actual <= 0 and lote.activo:
        print("🔧 Marcando lote como inactivo...")
        lote.activo = False
        lote.save()
        print("✅ Lote marcado como inactivo")
    else:
        print("ℹ️  No se requiere corrección para este lote")

if __name__ == "__main__":
    diagnosticar_lote_especifico()
    
    respuesta = input("\n¿Deseas corregir este lote si tiene problemas? (s/n): ")
    if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        corregir_lote_especifico()
        print("Proceso completado.")