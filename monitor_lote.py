#!/usr/bin/env python3
"""
Script para monitorear el estado del lote en tiempo real durante el proceso
"""

import os
import sys
import django
import time
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
django.setup()

from gestion.models import Lotes

def monitorear_lote(numero_lote):
    """Monitorea el estado de un lote en tiempo real"""
    print(f"=== MONITOREANDO LOTE: {numero_lote} ===")
    print("Presiona Ctrl+C para detener el monitoreo")
    print()
    
    try:
        while True:
            try:
                lote = Lotes.objects.get(numero_lote=numero_lote)
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] Stock: {lote.cantidad_actual} | Activo: {lote.activo} | ID: {lote.id_lote}")
                time.sleep(2)  # Verificar cada 2 segundos
                
            except Lotes.DoesNotExist:
                print(f"❌ Lote {numero_lote} no encontrado")
                break
            except Exception as e:
                print(f"❌ Error al consultar lote: {e}")
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("\n✓ Monitoreo detenido")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        numero_lote = sys.argv[1]
    else:
        numero_lote = "1-Lavado-20250529201736"  # Lote por defecto
    
    monitorear_lote(numero_lote)