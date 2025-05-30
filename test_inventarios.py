#!/usr/bin/env python
"""
Script de prueba para validar el cálculo de inventarios en ColorPlastic
Este script permite probar y depurar los movimientos de inventario de forma aislada.
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

print("🔧 Configurando Django...")
try:
    django.setup()
    print("✅ Django configurado correctamente")
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

try:
    from gestion.models import (
        Bodegas, Lotes, MovimientosInventario, Materiales, 
        Maquinas, Operarios, ProduccionLavado
    )
    from gestion.inventario_utils import procesar_movimiento_inventario
    from django.db import transaction
    from django.utils import timezone
    print("✅ Modelos importados correctamente")
except Exception as e:
    print(f"❌ Error importando modelos: {e}")
    sys.exit(1)

def test_conexion_db():
    """Prueba la conexión a la base de datos."""
    try:
        count = Lotes.objects.count()
        print(f"✅ Conexión DB exitosa - {count} lotes en total")
        return True
    except Exception as e:
        print(f"❌ Error conectando a DB: {e}")
        return False

def limpiar_datos_prueba():
    """Limpia todos los datos de prueba."""
    print("🧹 Limpiando datos de prueba...")
    try:
        # Eliminar en orden correcto para evitar problemas de FK
        # 1. Primero eliminar producciones que referencian lotes
        prod_deleted = ProduccionLavado.objects.filter(orden_trabajo__contains="TEST").delete()
        print(f"  - Producciones eliminadas: {prod_deleted[0]}")
        
        # 2. Luego eliminar movimientos de inventario
        mov_deleted = MovimientosInventario.objects.filter(observaciones__contains="PRUEBA").delete()
        print(f"  - Movimientos eliminados: {mov_deleted[0]}")
        
        # 3. Finalmente eliminar lotes
        lotes_deleted = Lotes.objects.filter(numero_lote__contains="TEST").delete()
        print(f"  - Lotes eliminados: {lotes_deleted[0]}")
        
        print("✅ Datos de prueba limpiados correctamente")
        
    except Exception as e:
        print(f"❌ Error limpiando datos: {e}")
        # Si hay error, intentar eliminar uno por uno
        print("🔧 Intentando limpieza forzada...")
        try:
            # Forzar eliminación de lotes de prueba uno por uno
            lotes_test = Lotes.objects.filter(numero_lote__contains="TEST")
            for lote in lotes_test:
                try:
                    # Eliminar movimientos asociados primero
                    MovimientosInventario.objects.filter(id_lote=lote).delete()
                    # Eliminar producciones asociadas
                    ProduccionLavado.objects.filter(id_lote_producido=lote).delete()
                    # Finalmente eliminar el lote
                    lote.delete()
                    print(f"  - Lote {lote.numero_lote} eliminado forzadamente")
                except Exception as inner_e:
                    print(f"  - No se pudo eliminar lote {lote.numero_lote}: {inner_e}")
        except Exception as force_e:
            print(f"❌ Error en limpieza forzada: {force_e}")

def crear_datos_base():
    """Crea los datos base necesarios para las pruebas."""
    print("📦 Creando datos base...")
    
    try:
        # Crear bodega de prueba
        bodega_mp, created = Bodegas.objects.get_or_create(
            nombre="Bodega Materia Prima TEST",
            defaults={'descripcion': 'Bodega de prueba para materia prima'}
        )
        print(f"  - Bodega MP: {'creada' if created else 'existente'}")
        
        bodega_pt, created = Bodegas.objects.get_or_create(
            nombre="Bodega Producto Terminado TEST",
            defaults={'descripcion': 'Bodega de prueba para producto terminado'}
        )
        print(f"  - Bodega PT: {'creada' if created else 'existente'}")
        
        # Crear materiales de prueba
        material_entrada, created = Materiales.objects.get_or_create(
            nombre="Plástico Sucio TEST",
            defaults={'tipo': 'MateriaPrima', 'descripcion': 'Material de prueba para entrada'}
        )
        print(f"  - Material entrada: {'creado' if created else 'existente'}")
        
        material_salida, created = Materiales.objects.get_or_create(
            nombre="Plástico Lavado TEST",
            defaults={'tipo': 'ProductoTerminado', 'descripcion': 'Material de prueba para salida'}
        )
        print(f"  - Material salida: {'creado' if created else 'existente'}")
        
        # Crear operario y máquina de prueba
        operario, created = Operarios.objects.get_or_create(
            codigo="OP001-TEST",
            defaults={'nombre_completo': 'Operario Prueba', 'activo': True}
        )
        print(f"  - Operario: {'creado' if created else 'existente'}")
        
        maquina, created = Maquinas.objects.get_or_create(
            nombre="Máquina Lavado TEST",
            defaults={'tipo_proceso': 'Lavado', 'descripcion': 'Máquina de prueba', 'activo': True}
        )
        print(f"  - Máquina: {'creada' if created else 'existente'}")
        
        print("✅ Todos los datos base están listos")
        return bodega_mp, bodega_pt, material_entrada, material_salida, operario, maquina
        
    except Exception as e:
        print(f"❌ Error creando datos base: {e}")
        raise

def crear_lote_inicial_simple(bodega_mp, material_entrada, cantidad=100):
    """Crea un lote inicial de forma directa con número único."""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # microsegundos para unicidad
    numero_lote = f"TEST-DIRECTO-{timestamp}"
    
    print(f"📦 Creando lote inicial DIRECTO con {cantidad} kg...")
    print(f"  - Número de lote: {numero_lote}")
    
    try:
        # Verificar que no existe el lote
        if Lotes.objects.filter(numero_lote=numero_lote).exists():
            print(f"⚠️ Lote {numero_lote} ya existe, generando nuevo número...")
            import random
            numero_lote = f"TEST-DIRECTO-{timestamp}-{random.randint(1000, 9999)}"
        
        # Crear lote directamente
        lote_inicial = Lotes.objects.create(
            numero_lote=numero_lote,
            id_material=material_entrada,
            cantidad_inicial=cantidad,
            cantidad_actual=cantidad,
            id_bodega_actual=bodega_mp,
            activo=True
        )
        print(f"✅ Lote creado directamente: {lote_inicial.numero_lote}")
        print(f"  - Cantidad inicial: {lote_inicial.cantidad_inicial}")
        print(f"  - Cantidad actual: {lote_inicial.cantidad_actual}")
        
        return lote_inicial
    except Exception as e:
        print(f"❌ Error creando lote: {e}")
        raise

def probar_movimiento_simple():
    """Prueba básica de un movimiento de inventario."""
    print("\n🔬 PROBANDO MOVIMIENTO SIMPLE...")
    
    try:
        # Crear datos básicos
        bodega_mp, bodega_pt, material_entrada, material_salida, operario, maquina = crear_datos_base()
        
        # Crear lote inicial
        lote = crear_lote_inicial_simple(bodega_mp, material_entrada, 100)
        
        print(f"Estado inicial del lote:")
        print(f"  - Cantidad antes: {lote.cantidad_actual}")
        
        # Probar movimiento de consumo
        print("🔄 Probando movimiento de consumo...")
        movimiento = procesar_movimiento_inventario(
            tipo_movimiento='ConsumoProduccion',
            lote=lote,
            cantidad=Decimal('30'),
            bodega_origen=bodega_mp,
            observaciones="PRUEBA - Consumo simple"
        )
        
        # Refrescar lote
        lote.refresh_from_db()
        print(f"✅ Movimiento procesado:")
        print(f"  - ID Movimiento: {movimiento.pk}")
        print(f"  - Cantidad consumida: {movimiento.cantidad}")
        print(f"  - Cantidad después: {lote.cantidad_actual}")
        print(f"  - Esperado: 70, Actual: {lote.cantidad_actual}")
        
        if lote.cantidad_actual == Decimal('70'):
            print("✅ MOVIMIENTO SIMPLE CORRECTO")
            return True
        else:
            print("❌ MOVIMIENTO SIMPLE INCORRECTO")
            return False
            
    except Exception as e:
        print(f"❌ Error en movimiento simple: {e}")
        import traceback
        traceback.print_exc()
        return False

def probar_proceso_completo():
    """Prueba completa del proceso de producción con inventarios."""
    print("\n🏭 PROBANDO PROCESO COMPLETO DE PRODUCCIÓN...")
    
    try:
        # Crear datos básicos
        bodega_mp, bodega_pt, material_entrada, material_salida, operario, maquina = crear_datos_base()
        
        # Crear lote inicial con suficiente material (usando timestamp único)
        timestamp_base = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]
        lote_entrada = Lotes.objects.create(
            numero_lote=f"TEST-ENTRADA-{timestamp_base}",
            id_material=material_entrada,
            cantidad_inicial=200,
            cantidad_actual=200,
            id_bodega_actual=bodega_mp,
            activo=True
        )
        
        print(f"\n📋 ESTADO INICIAL:")
        print(f"  - Lote entrada: {lote_entrada.numero_lote}")
        print(f"  - Stock inicial: {lote_entrada.cantidad_actual} kg")
        
        cantidad_procesar = Decimal('80')
        
        # PASO 1: Crear lote de salida (simulando producción)
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]
        numero_lote_salida = f"TEST-PRODUCIDO-{timestamp}"
        
        lote_salida = Lotes.objects.create(
            numero_lote=numero_lote_salida,
            id_material=material_salida,
            cantidad_inicial=cantidad_procesar,
            cantidad_actual=cantidad_procesar,
            id_bodega_actual=bodega_pt,
            activo=True
        )
        print(f"\n✅ PASO 1 - Lote de salida creado: {lote_salida.numero_lote}")
        print(f"  - Cantidad producida: {lote_salida.cantidad_actual} kg")
        
        # PASO 2: Registrar entrada del lote producido
        movimiento_entrada = procesar_movimiento_inventario(
            tipo_movimiento='IngresoServicio',
            lote=lote_salida,
            cantidad=cantidad_procesar,
            bodega_destino=bodega_pt,
            observaciones="PRUEBA - Entrada producción"
        )
        print(f"✅ PASO 2 - Movimiento de entrada registrado: {movimiento_entrada.pk}")
        
        # Verificar el lote de salida después del movimiento de entrada
        lote_salida.refresh_from_db()
        print(f"  - Stock lote salida después entrada: {lote_salida.cantidad_actual} kg")
        
        # AQUÍ ESTÁ EL PROBLEMA CLAVE: ¿Qué está pasando con el stock?
        print(f"  - ⚠️ ANÁLISIS: El stock debería ser {cantidad_procesar} + {cantidad_procesar} = {cantidad_procesar * 2}")
        print(f"  - 🔍 REAL: El stock es {lote_salida.cantidad_actual}")
        
        # PASO 3: Registrar consumo del lote de entrada
        print(f"\n🔄 PASO 3 - Procesando consumo...")
        print(f"  - Stock antes consumo: {lote_entrada.cantidad_actual} kg")
        
        movimiento_consumo = procesar_movimiento_inventario(
            tipo_movimiento='ConsumoProduccion',
            lote=lote_entrada,
            cantidad=cantidad_procesar,
            bodega_origen=bodega_mp,
            observaciones="PRUEBA - Consumo producción"
        )
        print(f"✅ PASO 3 - Movimiento de consumo registrado: {movimiento_consumo.pk}")
        
        # Verificar el lote de entrada después del consumo
        lote_entrada.refresh_from_db()
        print(f"  - Stock después consumo: {lote_entrada.cantidad_actual} kg")
        
        # ANÁLISIS DETALLADO DEL PROBLEMA
        print(f"\n🔍 ANÁLISIS DETALLADO:")
        print(f"  - Lote entrada inicial: 200 kg")
        print(f"  - Consumo registrado: {cantidad_procesar} kg")
        print(f"  - Stock entrada esperado: {200 - cantidad_procesar} = {Decimal('200') - cantidad_procesar} kg")
        print(f"  - Stock entrada real: {lote_entrada.cantidad_actual} kg")
        
        print(f"  - Lote salida inicial: {cantidad_procesar} kg")
        print(f"  - Entrada registrada: {cantidad_procesar} kg")
        print(f"  - Stock salida esperado: {cantidad_procesar} kg (sin duplicar)")
        print(f"  - Stock salida real: {lote_salida.cantidad_actual} kg")
        
        # El problema está aquí: ¿Por qué el lote de salida duplica su stock?
        if lote_salida.cantidad_actual == cantidad_procesar * 2:
            print(f"  ❌ PROBLEMA IDENTIFICADO: El lote de salida está duplicando el stock!")
            print(f"     - Se crea con {cantidad_procesar} kg")
            print(f"     - Al registrar IngresoServicio se SUMA otros {cantidad_procesar} kg")
            print(f"     - Resultado: {cantidad_procesar * 2} kg (INCORRECTO)")
            return False
        
        # Verificar movimientos registrados
        movimientos_prueba = MovimientosInventario.objects.filter(observaciones__contains="PRUEBA").order_by('fecha')
        print(f"\n📈 MOVIMIENTOS REGISTRADOS ({movimientos_prueba.count()}):")
        
        total_entradas = Decimal('0')
        total_salidas = Decimal('0')
        
        for mov in movimientos_prueba:
            if mov.tipo_movimiento in ['IngresoServicio']:
                total_entradas += mov.cantidad
                print(f"  📥 {mov.tipo_movimiento}: +{mov.cantidad} kg (Lote: {mov.id_lote.numero_lote})")
            elif mov.tipo_movimiento in ['ConsumoProduccion']:
                total_salidas += mov.cantidad
                print(f"  📤 {mov.tipo_movimiento}: -{mov.cantidad} kg (Lote: {mov.id_lote.numero_lote})")
        
        print(f"\n📊 BALANCE DE MOVIMIENTOS:")
        print(f"  - Total entradas: {total_entradas} kg")
        print(f"  - Total salidas: {total_salidas} kg")
        print(f"  - Balance neto: {total_entradas - total_salidas} kg")
        
        return True
            
    except Exception as e:
        print(f"❌ Error en proceso completo: {e}")
        import traceback
        traceback.print_exc()
        return False

def ejecutar_prueba_basica():
    """Ejecuta una prueba básica del sistema."""
    print("🚀 INICIANDO PRUEBA BÁSICA DE INVENTARIOS")
    print("=" * 50)
    
    # Verificar conexión
    if not test_conexion_db():
        return
    
    # Limpiar datos
    limpiar_datos_prueba()
    
    # Probar movimiento simple
    resultado = probar_movimiento_simple()
    
    print("\n" + "=" * 50)
    if resultado:
        print("🎉 PRUEBA BÁSICA EXITOSA")
    else:
        print("⚠️ PRUEBA BÁSICA FALLIDA")

def ejecutar_prueba_completa():
    """Ejecuta una prueba completa del sistema."""
    print("🚀 INICIANDO PRUEBA COMPLETA DE INVENTARIOS")
    print("=" * 60)
    
    # Verificar conexión
    if not test_conexion_db():
        return
    
    # Probar movimiento simple
    print("\n🔧 PARTE 1: MOVIMIENTO SIMPLE")
    resultado_simple = probar_movimiento_simple()
    
    # Probar proceso completo
    print("\n🏭 PARTE 2: PROCESO COMPLETO")
    resultado_completo = probar_proceso_completo()
    
    print("\n" + "=" * 60)
    if resultado_simple and resultado_completo:
        print("🎉 TODAS LAS PRUEBAS EXITOSAS")
        print("✅ El sistema de inventarios funciona correctamente")
    else:
        print("⚠️ ALGUNAS PRUEBAS FALLARON")
        if not resultado_simple:
            print("  ❌ Fallo en movimiento simple")
        if not resultado_completo:
            print("  ❌ Fallo en proceso completo")

if __name__ == "__main__":
    ejecutar_prueba_completa()