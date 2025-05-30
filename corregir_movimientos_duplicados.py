#!/usr/bin/env python3
"""
Script para corregir inconsistencias en los movimientos de inventario
de lotes de producción que tienen movimientos duplicados.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
sys.path.append('/Volumes/Indunnova/colorplastic')
django.setup()

from gestion.models import Lotes, MovimientosInventario
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

def corregir_lotes_con_movimientos_duplicados():
    """
    Corrige lotes que tienen movimientos IngresoServicio duplicados
    causados por el bug anterior en los modelos de producción.
    """
    print("=== CORRECCIÓN DE MOVIMIENTOS DUPLICADOS ===\n")
    
    # Buscar lotes con movimientos IngresoServicio
    lotes_con_ingreso_servicio = MovimientosInventario.objects.filter(
        tipo_movimiento='IngresoServicio'
    ).values_list('id_lote', flat=True).distinct()
    
    print(f"🔍 Encontrados {len(lotes_con_ingreso_servicio)} lotes con movimientos IngresoServicio")
    
    lotes_corregidos = 0
    
    with transaction.atomic():
        for lote_id in lotes_con_ingreso_servicio:
            try:
                lote = Lotes.objects.get(id_lote=lote_id)
                
                # Calcular balance teórico basado en movimientos
                entradas = MovimientosInventario.objects.filter(
                    id_lote=lote,
                    tipo_movimiento__in=['Compra', 'AjustePositivo', 'IngresoServicio']
                ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
                
                salidas = MovimientosInventario.objects.filter(
                    id_lote=lote,
                    tipo_movimiento__in=['Venta', 'ConsumoProduccion', 'AjusteNegativo', 'SalidaServicio']
                ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
                
                balance_teorico = lote.cantidad_inicial + entradas - salidas
                diferencia = abs(balance_teorico - lote.cantidad_actual)
                
                # Si hay diferencia significativa (mayor a 0.01), corregir
                if diferencia > Decimal('0.01'):
                    print(f"\n🔧 Corrigiendo lote: {lote.numero_lote}")
                    print(f"  - Cantidad actual: {lote.cantidad_actual} kg")
                    print(f"  - Balance teórico: {balance_teorico} kg")
                    print(f"  - Diferencia: {diferencia} kg")
                    
                    # Verificar si es un lote de producción con movimiento IngresoServicio duplicado
                    movimientos_ingreso = MovimientosInventario.objects.filter(
                        id_lote=lote,
                        tipo_movimiento='IngresoServicio',
                        observaciones__icontains='Producción:'
                    )
                    
                    if movimientos_ingreso.exists() and lote.cantidad_inicial == lote.cantidad_actual:
                        # Este es el caso típico: lote de producción con movimiento duplicado
                        # La cantidad_actual está correcta, pero hay un movimiento extra
                        
                        # Eliminar el movimiento IngresoServicio duplicado
                        movimiento_duplicado = movimientos_ingreso.first()
                        print(f"  ✅ Eliminando movimiento duplicado: {movimiento_duplicado.id_movimiento}")
                        movimiento_duplicado.delete()
                        lotes_corregidos += 1
                        
                    else:
                        # Caso complejo: ajustar la cantidad_actual al balance teórico
                        print(f"  ⚠️  Caso complejo detectado, ajustando cantidad_actual")
                        lote.cantidad_actual = balance_teorico
                        lote.save()
                        lotes_corregidos += 1
                        
            except Exception as e:
                print(f"❌ Error procesando lote {lote_id}: {e}")
                continue
    
    print(f"\n✅ Corrección completada: {lotes_corregidos} lotes corregidos")
    return lotes_corregidos

def verificar_correccion():
    """Verifica que las correcciones se aplicaron correctamente."""
    print("\n=== VERIFICACIÓN POST-CORRECCIÓN ===")
    
    inconsistencias_restantes = 0
    
    # Verificar algunos lotes al azar
    lotes_muestra = Lotes.objects.filter(activo=True)[:20]
    
    for lote in lotes_muestra:
        entradas = MovimientosInventario.objects.filter(
            id_lote=lote,
            tipo_movimiento__in=['Compra', 'AjustePositivo', 'IngresoServicio']
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
        
        salidas = MovimientosInventario.objects.filter(
            id_lote=lote,
            tipo_movimiento__in=['Venta', 'ConsumoProduccion', 'AjusteNegativo', 'SalidaServicio']
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
        
        balance_teorico = lote.cantidad_inicial + entradas - salidas
        diferencia = abs(balance_teorico - lote.cantidad_actual)
        
        if diferencia > Decimal('0.01'):
            print(f"⚠️  Inconsistencia restante en {lote.numero_lote}: {diferencia} kg")
            inconsistencias_restantes += 1
    
    if inconsistencias_restantes == 0:
        print("✅ No se detectaron inconsistencias restantes")
    else:
        print(f"⚠️  Se detectaron {inconsistencias_restantes} inconsistencias restantes")
    
    return inconsistencias_restantes

if __name__ == "__main__":
    print("🔧 INICIANDO CORRECCIÓN DE MOVIMIENTOS DUPLICADOS...")
    
    # Ejecutar corrección
    lotes_corregidos = corregir_lotes_con_movimientos_duplicados()
    
    if lotes_corregidos > 0:
        # Verificar que todo esté correcto
        verificar_correccion()
        print(f"\n🎉 Proceso completado: {lotes_corregidos} lotes corregidos")
    else:
        print("\nℹ️  No se encontraron lotes que requirieran corrección")