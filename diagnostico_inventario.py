#!/usr/bin/env python
"""
Script de diagnóstico para revisar el inventario y detectar duplicaciones
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/Volumes/Indunnova/colorplastic')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
django.setup()

from gestion.models import Lotes, MovimientosInventario, ProduccionLavado
from django.db.models import Sum
from datetime import datetime, timedelta

def diagnosticar_inventario():
    print("=== DIAGNÓSTICO DE INVENTARIO ===\n")
    
    # 1. Revisar lotes activos
    lotes_activos = Lotes.objects.filter(activo=True)
    print(f"Total de lotes activos: {lotes_activos.count()}")
    
    # 2. Revisar total de kilogramos
    total_kg = lotes_activos.aggregate(total=Sum('cantidad_actual'))['total'] or 0
    print(f"Total kilogramos en inventario: {total_kg}")
    
    # 3. Revisar últimos lotes creados (especialmente de lavado)
    print("\n=== ÚLTIMOS 10 LOTES CREADOS ===")
    ultimos_lotes = Lotes.objects.filter(activo=True).order_by('-fecha_creacion')[:10]
    for lote in ultimos_lotes:
        print(f"Lote: {lote.numero_lote} | Material: {lote.id_material.nombre} | "
              f"Cantidad: {lote.cantidad_actual} {lote.unidad_medida} | "
              f"Bodega: {lote.id_bodega_actual.nombre} | "
              f"Fecha: {lote.fecha_creacion}")
    
    # 4. Revisar producciones de lavado recientes
    print("\n=== ÚLTIMAS 5 PRODUCCIONES DE LAVADO ===")
    producciones_lavado = ProduccionLavado.objects.all().order_by('-fecha')[:5]
    for prod in producciones_lavado:
        print(f"OT: {prod.orden_trabajo} | "
              f"Entrada: {prod.cantidad_entrada} kg | "
              f"Salida: {prod.cantidad_salida} kg | "
              f"Lote producido: {prod.id_lote_producido.numero_lote if prod.id_lote_producido else 'N/A'} | "
              f"Fecha: {prod.fecha}")
    
    # 5. Buscar lotes con mismo número (posibles duplicados)
    print("\n=== VERIFICANDO DUPLICADOS POR NÚMERO DE LOTE ===")
    from collections import Counter
    numeros_lote = [lote.numero_lote for lote in lotes_activos]
    duplicados = [numero for numero, count in Counter(numeros_lote).items() if count > 1]
    
    if duplicados:
        print(f"¡ALERTA! Se encontraron {len(duplicados)} números de lote duplicados:")
        for numero in duplicados:
            lotes_dup = Lotes.objects.filter(numero_lote=numero, activo=True)
            print(f"  - {numero}: {lotes_dup.count()} lotes")
            for lote in lotes_dup:
                print(f"    ID: {lote.pk}, Cantidad: {lote.cantidad_actual}, Bodega: {lote.id_bodega_actual.nombre}")
    else:
        print("✓ No se encontraron números de lote duplicados")
    
    # 6. Revisar movimientos recientes de tipo IngresoServicio
    print("\n=== MOVIMIENTOS DE INGRESO POR SERVICIO (ÚLTIMOS 10) ===")
    movimientos_ingreso = MovimientosInventario.objects.filter(
        tipo_movimiento='IngresoServicio'
    ).order_by('-fecha')[:10]
    
    if movimientos_ingreso:
        print("¡ALERTA! Se encontraron movimientos de tipo 'IngresoServicio':")
        for mov in movimientos_ingreso:
            print(f"Fecha: {mov.fecha} | Lote: {mov.id_lote.numero_lote} | "
                  f"Cantidad: {mov.cantidad} | "
                  f"OBS: {mov.observaciones}")
    else:
        print("✓ No se encontraron movimientos de tipo 'IngresoServicio'")
    
    # 7. Verificar si hay lotes con cantidades sospechosamente altas
    print("\n=== LOTES CON CANTIDADES ALTAS (>10 kg) ===")
    lotes_altos = lotes_activos.filter(cantidad_actual__gt=10).order_by('-cantidad_actual')
    if lotes_altos:
        for lote in lotes_altos:
            print(f"Lote: {lote.numero_lote} | "
                  f"Material: {lote.id_material.nombre} | "
                  f"Cantidad: {lote.cantidad_actual} kg | "
                  f"Inicial: {lote.cantidad_inicial} kg")
    else:
        print("✓ No hay lotes con cantidades excesivamente altas")

if __name__ == "__main__":
    diagnosticar_inventario()