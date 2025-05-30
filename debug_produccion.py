#!/usr/bin/env python3
"""
Script de depuración para diagnosticar el problema de validación de stock
en el proceso de producción de molido.
"""

import os
import sys
import django
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
django.setup()

from django.db import transaction
from django.core.exceptions import ValidationError
from gestion.models import Lotes, Operarios, Maquinas, Materiales, Bodegas
from gestion.inventario_utils import procesar_movimiento_inventario

def simular_flujo_completo():
    """Simula exactamente el flujo que sigue la vista web."""
    print("=== DIAGNÓSTICO COMPLETO DEL FLUJO DE PRODUCCIÓN ===")
    
    # 1. Obtener el lote problemático
    lote = Lotes.objects.filter(numero_lote__contains='1-Lavado-20250529203220').first()
    if not lote:
        print("❌ Error: Lote no encontrado")
        return
    
    print(f"✓ Lote encontrado: {lote.numero_lote}")
    print(f"  - ID: {lote.id_lote}")
    print(f"  - Stock actual: {lote.cantidad_actual}")
    print(f"  - Activo: {lote.activo}")
    print(f"  - Material: {lote.id_material.nombre}")
    print(f"  - Bodega: {lote.id_bodega_actual.nombre}")
    print()
    
    # 2. Obtener datos necesarios para el proceso
    operario = Operarios.objects.filter(activo=True).first()
    maquina = Maquinas.objects.filter(tipo_proceso='Molido', activo=True).first()
    material_salida = Materiales.objects.first()
    bodega_destino = Bodegas.objects.first()
    
    if not all([operario, maquina, material_salida, bodega_destino]):
        print("❌ Error: Faltan datos maestros (operario, máquina, material o bodega)")
        return
    
    print(f"✓ Datos maestros obtenidos:")
    print(f"  - Operario: {operario.nombre_completo}")
    print(f"  - Máquina: {maquina.nombre}")
    print(f"  - Material salida: {material_salida.nombre}")
    print(f"  - Bodega destino: {bodega_destino.nombre}")
    print()
    
    # 3. Simular datos del formulario
    datos_formulario = {
        'operario': operario.id_operario,
        'maquina': maquina.id_maquina,
        'orden_trabajo': 'TEST-DEBUG-001',
        'turno': 'Mañana',
        'bodega_destino': bodega_destino.id_bodega,
        'material_salida': material_salida.id_material,
        'lotes_entrada': [str(lote.id_lote)],
        'cantidades_entrada': ['1.0'],
        'observaciones': 'Prueba de depuración completa'
    }
    
    print(f"✓ Datos del formulario simulados:")
    for key, value in datos_formulario.items():
        print(f"  - {key}: {value}")
    print()
    
    # 4. Simular el procesamiento en la vista (SIN transacción atómica)
    print("=== SIMULANDO FLUJO DE LA VISTA (SIN TRANSACCIÓN) ===")
    
    try:
        # Paso 1: Obtener lotes y cantidades (como en la vista)
        lotes_entrada = datos_formulario['lotes_entrada']
        cantidades_entrada = datos_formulario['cantidades_entrada']
        
        print(f"Paso 1: Lotes de entrada: {lotes_entrada}")
        print(f"Paso 1: Cantidades de entrada: {cantidades_entrada}")
        
        # Paso 2: Validar que hay al menos un lote
        if not lotes_entrada:
            raise ValidationError('Debe seleccionar al menos un lote de entrada')
        print("✓ Paso 2: Validación de lotes OK")
        
        # Paso 3: Calcular cantidad total de entrada
        cantidad_total_entrada = Decimal('0')
        for cantidad in cantidades_entrada:
            cantidad_total_entrada += Decimal(cantidad)
        print(f"✓ Paso 3: Cantidad total entrada: {cantidad_total_entrada}")
        
        # Paso 4: Crear el lote de producción
        timestamp = "20250529999999"  # Timestamp fijo para prueba
        numero_lote_unico = f"{datos_formulario['orden_trabajo']}-Molido-{timestamp}"
        
        print(f"✓ Paso 4: Creando lote de producción: {numero_lote_unico}")
        
        # Paso 5: Procesar cada lote de entrada (AQUÍ DEBE ESTAR EL PROBLEMA)
        print("=== PROCESANDO LOTES DE ENTRADA ===")
        
        for i, (lote_id, cantidad_str) in enumerate(zip(lotes_entrada, cantidades_entrada)):
            print(f"\n--- Procesando lote {i+1}/{len(lotes_entrada)} ---")
            
            # Obtener el lote sin select_for_update (como en la vista actual)
            lote_entrada = Lotes.objects.get(pk=lote_id)
            cantidad = Decimal(cantidad_str)
            
            print(f"Lote obtenido: {lote_entrada.numero_lote}")
            print(f"Stock antes del procesamiento: {lote_entrada.cantidad_actual}")
            print(f"Cantidad a procesar: {cantidad}")
            print(f"Lote activo: {lote_entrada.activo}")
            
            # Validaciones básicas (como en la vista actual)
            if not lote_entrada.activo:
                raise ValidationError(f'El lote {lote_entrada.numero_lote} no está activo.')
            
            if cantidad <= 0:
                raise ValidationError(f'La cantidad debe ser mayor que cero para el lote {lote_entrada.numero_lote}.')
            
            print("✓ Validaciones básicas OK")
            
            # AQUÍ ES DONDE DEBE FALLAR - Procesar movimiento
            print("Llamando a procesar_movimiento_inventario...")
            try:
                movimiento = procesar_movimiento_inventario(
                    tipo_movimiento='ConsumoProduccion',
                    lote=lote_entrada,
                    cantidad=cantidad,
                    bodega_origen=lote_entrada.id_bodega_actual,
                    bodega_destino=None,
                    produccion_referencia=datos_formulario['orden_trabajo'],
                    observaciones=f"Consumo para Molido - OT: {datos_formulario['orden_trabajo']}"
                )
                print(f"✓ Movimiento procesado exitosamente: {movimiento.id_movimiento}")
                
                # Verificar estado del lote después
                lote_entrada.refresh_from_db()
                print(f"Stock después del procesamiento: {lote_entrada.cantidad_actual}")
                print(f"Lote activo después: {lote_entrada.activo}")
                
            except Exception as e:
                print(f"❌ ERROR al procesar movimiento: {str(e)}")
                print(f"   Tipo de error: {type(e).__name__}")
                
                # Información adicional de depuración
                print(f"\n=== INFORMACIÓN DE DEPURACIÓN ===")
                print(f"Lote ID: {lote_entrada.id_lote}")
                print(f"Lote número: {lote_entrada.numero_lote}")
                print(f"Stock reportado: {lote_entrada.cantidad_actual}")
                print(f"Activo: {lote_entrada.activo}")
                print(f"Bodega origen: {lote_entrada.id_bodega_actual}")
                print(f"Cantidad solicitada: {cantidad}")
                
                # Verificar si el lote cambió entre consultas
                lote_recheck = Lotes.objects.get(pk=lote_id)
                print(f"Re-verificación - Stock: {lote_recheck.cantidad_actual}")
                print(f"Re-verificación - Activo: {lote_recheck.activo}")
                
                return False
        
        print("\n✅ TODOS LOS LOTES PROCESADOS EXITOSAMENTE")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR GENERAL EN EL FLUJO: {str(e)}")
        print(f"   Tipo de error: {type(e).__name__}")
        return False

def verificar_estado_final():
    """Verifica el estado final del lote después de la prueba."""
    print("\n=== VERIFICACIÓN ESTADO FINAL ===")
    lote = Lotes.objects.filter(numero_lote__contains='1-Lavado-20250529203220').first()
    if lote:
        print(f"Estado final del lote {lote.numero_lote}:")
        print(f"  - Stock actual: {lote.cantidad_actual}")
        print(f"  - Activo: {lote.activo}")
    else:
        print("❌ Lote no encontrado en verificación final")

if __name__ == "__main__":
    print("Iniciando diagnóstico completo...\n")
    
    # Ejecutar la simulación
    resultado = simular_flujo_completo()
    
    # Verificar estado final
    verificar_estado_final()
    
    print(f"\n=== RESULTADO FINAL ===")
    if resultado:
        print("✅ La simulación se completó exitosamente")
        print("   El problema NO está en la lógica de procesamiento")
        print("   Revisar otros aspectos: formulario, validaciones adicionales, etc.")
    else:
        print("❌ La simulación falló")
        print("   El problema está en la lógica de procesamiento")
        print("   Revisar la función procesar_movimiento_inventario y validaciones")