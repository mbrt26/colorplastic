#!/usr/bin/env python3
"""
Script para limpiar movimientos de inventario duplicados
y corregir las cantidades de los lotes afectados.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
sys.path.append('/Volumes/Indunnova/colorplastic')
django.setup()

from gestion.models import MovimientosInventario, Lotes
from django.db import transaction

def limpiar_duplicados():
    """Elimina movimientos de IngresoServicio duplicados y corrige inventarios."""
    print("=== INICIANDO LIMPIEZA DE DUPLICADOS ===\n")
    
    with transaction.atomic():
        # Encontrar todos los movimientos de IngresoServicio
        movimientos_duplicados = MovimientosInventario.objects.filter(
            tipo_movimiento='IngresoServicio'
        ).order_by('fecha')
        
        print(f"Encontrados {movimientos_duplicados.count()} movimientos de IngresoServicio para eliminar:")
        
        lotes_afectados = {}
        
        for mov in movimientos_duplicados:
            print(f"- Movimiento ID {mov.id_movimiento}: {mov.id_lote.numero_lote} - {mov.cantidad} kg")
            
            # Guardar información del lote afectado
            lote = mov.id_lote
            if lote.numero_lote not in lotes_afectados:
                lotes_afectados[lote.numero_lote] = {
                    'lote': lote,
                    'cantidad_a_restar': 0
                }
            lotes_afectados[lote.numero_lote]['cantidad_a_restar'] += mov.cantidad
        
        # Eliminar los movimientos duplicados
        print(f"\nEliminando {movimientos_duplicados.count()} movimientos duplicados...")
        movimientos_duplicados.delete()
        
        # Corregir las cantidades de los lotes afectados
        print("\nCorrigiendo cantidades en lotes afectados:")
        for numero_lote, info in lotes_afectados.items():
            lote = info['lote']
            cantidad_a_restar = info['cantidad_a_restar']
            cantidad_anterior = lote.cantidad_actual
            
            # La cantidad actual debería ser igual a la cantidad inicial para lotes de producción
            # ya que no deberían tener el movimiento de IngresoServicio
            nueva_cantidad = lote.cantidad_inicial
            
            lote.cantidad_actual = nueva_cantidad
            lote.save()
            
            print(f"  {numero_lote}: {cantidad_anterior} kg -> {nueva_cantidad} kg "
                  f"(restando {cantidad_a_restar} kg duplicados)")
    
    print("\n=== LIMPIEZA COMPLETADA ===")

if __name__ == "__main__":
    limpiar_duplicados()