from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import (
    Materiales, Bodegas, Terceros, Lotes, MovimientosInventario, 
    ProduccionMolido, ProduccionLavado, ProduccionPeletizado, ProduccionInyeccion,
    ProduccionConsumo, ResiduosProduccion, Operarios, Maquinas
)
from .inventario_utils import procesar_movimiento_inventario
from decimal import Decimal

class InventarioCentralizadoTests(TestCase):
    def setUp(self):
        self.material = Materiales.objects.create(nombre="Polietileno", tipo="Molido")
        self.bodega = Bodegas.objects.create(nombre="Principal")
        self.proveedor = Terceros.objects.create(nombre="Proveedor1", tipo="Proveedor")
        self.operario = Operarios.objects.create(codigo="OP1", nombre_completo="Operario Uno")
        
        # Crear una máquina específica para cada proceso
        self.maquina_molido = Maquinas.objects.create(nombre="Molino1", tipo_proceso="Molido")
        self.maquina_lavado = Maquinas.objects.create(nombre="Lavadora1", tipo_proceso="Lavado")
        self.maquina_peletizado = Maquinas.objects.create(nombre="Peletizadora1", tipo_proceso="Peletizado")
        self.maquina_inyeccion = Maquinas.objects.create(nombre="Inyectora1", tipo_proceso="Inyeccion")
        
        self.lote = Lotes.objects.create(
            numero_lote="L001",
            id_material=self.material,
            cantidad_inicial=Decimal('100.00'),
            id_bodega_actual=self.bodega
        )

    def test_entrada_compra(self):
        procesar_movimiento_inventario(
            tipo_movimiento='Compra',
            lote=self.lote,
            cantidad=Decimal('50.00'),
            bodega_destino=self.bodega
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, Decimal('150.00'))

    def test_salida_venta(self):
        procesar_movimiento_inventario(
            tipo_movimiento='Venta',
            lote=self.lote,
            cantidad=Decimal('30.00'),
            bodega_origen=self.bodega
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, Decimal('70.00'))

    def test_error_stock_insuficiente(self):
        with self.assertRaises(ValidationError):
            procesar_movimiento_inventario(
                tipo_movimiento='Venta',
                lote=self.lote,
                cantidad=Decimal('200.00'),
                bodega_origen=self.bodega
            )

    def test_consumo_produccion(self):
        lote_prod = Lotes.objects.create(
            numero_lote="L004",
            id_material=self.material,
            cantidad_inicial=Decimal('0.00'),
            id_bodega_actual=self.bodega
        )
        prod = ProduccionMolido.objects.create(
            id_maquina=self.maquina_molido,
            id_operario=self.operario,
            cantidad_producida=Decimal('10.00'),
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_prod
        )
        ProduccionConsumo.objects.create(
            id_produccion_molido=prod,
            id_lote_consumido=self.lote,
            cantidad_consumida=Decimal('20.00'),
            id_bodega_origen=self.bodega
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, Decimal('80.00'))

    def test_produccion_producto_terminado(self):
        lote_prod = Lotes.objects.create(
            numero_lote="L002",
            id_material=self.material,
            cantidad_inicial=Decimal('0.00'),
            id_bodega_actual=self.bodega
        )
        prod = ProduccionMolido.objects.create(
            id_maquina=self.maquina_molido,
            id_operario=self.operario,
            cantidad_producida=Decimal('25.00'),
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_prod
        )
        lote_prod.refresh_from_db()
        self.assertEqual(lote_prod.cantidad_actual, Decimal('25.00'))

    def test_registro_residuo(self):
        lote_prod = Lotes.objects.create(
            numero_lote="L005",
            id_material=self.material,
            cantidad_inicial=Decimal('50.00'),
            id_bodega_actual=self.bodega
        )
        prod = ProduccionMolido.objects.create(
            id_maquina=self.maquina_molido,
            id_operario=self.operario,
            cantidad_producida=Decimal('10.00'),
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_prod
        )
        # Aquí deberías enlazar el lote afectado y ajustar la lógica de inventario para residuos si aplica
        # Por ahora solo se prueba la creación sin afectar inventario
        residuo = ResiduosProduccion.objects.create(
            id_produccion_molido=prod,
            cantidad=Decimal('5.00'),
            tipo_residuo="Merma",
            unidad_medida="kg"
        )

    def test_simulacion_molido_50_porciento(self):
        """Simula un proceso de molido que consume el 50% de un lote de material comprado."""
        # Crear lote inicial con 100 kg
        lote_material = Lotes.objects.create(
            numero_lote="MATERIA-PRIMA-001",
            id_material=self.material,
            cantidad_inicial=Decimal('100.00'),
            id_bodega_actual=self.bodega
        )

        # Crear lote para el producto molido (inicialmente vacío)
        lote_molido = Lotes.objects.create(
            numero_lote="MOLIDO-001",
            id_material=self.material,
            cantidad_inicial=Decimal('0.00'),
            id_bodega_actual=self.bodega
        )

        # Registrar producción de molido
        produccion = ProduccionMolido.objects.create(
            id_maquina=self.maquina_molido,
            id_operario=self.operario,
            cantidad_producida=Decimal('50.00'),  # Producimos 50 kg de material molido
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_molido,
            orden_trabajo="OT-MOLIDO-001"
        )

        # Registrar consumo del 50% del material
        consumo = ProduccionConsumo.objects.create(
            id_produccion_molido=produccion,
            id_lote_consumido=lote_material,
            cantidad_consumida=Decimal('50.00'),  # Consumimos 50 kg
            id_bodega_origen=self.bodega
        )

        # Verificar que el stock se actualizó correctamente
        lote_material.refresh_from_db()
        lote_molido.refresh_from_db()

        # El lote original debe tener 50 kg restantes (50%)
        self.assertEqual(lote_material.cantidad_actual, Decimal('50.00'))
        # El lote molido debe tener 50 kg producidos
        self.assertEqual(lote_molido.cantidad_actual, Decimal('50.00'))

        # Verificar que el lote original sigue activo (aún tiene stock)
        self.assertTrue(lote_material.activo)
        # Verificar que el lote molido está activo
        self.assertTrue(lote_molido.activo)

    def test_simulacion_proceso_completo(self):
        """
        Simula el proceso completo de transformación:
        Material Original -> Molido -> Lavado -> Peletizado -> Inyección
        """
        # 1. Crear lote inicial de materia prima (1000 kg material original)
        lote_original = Lotes.objects.create(
            numero_lote="ORIGINAL-001",
            id_material=self.material,
            cantidad_inicial=Decimal('1000.00'),
            id_bodega_actual=self.bodega
        )

        # 2. Proceso de Molido
        lote_molido = Lotes.objects.create(
            numero_lote="MOLIDO-001",
            id_material=self.material,
            cantidad_inicial=Decimal('0.00'),
            id_bodega_actual=self.bodega
        )
        
        # Primero crear la producción de molido (genera stock)
        prod_molido = ProduccionMolido.objects.create(
            id_maquina=self.maquina_molido,
            id_operario=self.operario,
            cantidad_producida=Decimal('950.00'),  # 95% eficiencia (50kg de merma)
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_molido,
            orden_trabajo="OT-MOLIDO-001"
        )
        
        # Luego registrar el consumo
        consumo_molido = ProduccionConsumo.objects.create(
            id_produccion_molido=prod_molido,
            id_lote_consumido=lote_original,
            cantidad_consumida=Decimal('1000.00'),
            id_bodega_origen=self.bodega
        )

        # 3. Proceso de Lavado
        lote_lavado = Lotes.objects.create(
            numero_lote="LAVADO-001",
            id_material=self.material,
            cantidad_inicial=Decimal('0.00'),
            id_bodega_actual=self.bodega
        )
        
        # Primero crear la producción de lavado (genera stock)
        prod_lavado = ProduccionLavado.objects.create(
            id_maquina=self.maquina_lavado,
            id_operario=self.operario,
            cantidad_producida=Decimal('900.00'),  # 95% eficiencia del molido (50kg merma)
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_lavado,
            orden_trabajo="OT-LAVADO-001"
        )
        
        lote_molido.refresh_from_db()  # Asegurar que tenemos el stock actualizado
        
        # Luego registrar el consumo
        consumo_lavado = ProduccionConsumo.objects.create(
            id_produccion_lavado=prod_lavado,
            id_lote_consumido=lote_molido,
            cantidad_consumida=Decimal('950.00'),
            id_bodega_origen=self.bodega
        )

        # 4. Proceso de Peletizado
        lote_peletizado = Lotes.objects.create(
            numero_lote="PELET-001",
            id_material=self.material,
            cantidad_inicial=Decimal('0.00'),
            id_bodega_actual=self.bodega
        )
        
        # Primero crear la producción de peletizado (genera stock)
        prod_peletizado = ProduccionPeletizado.objects.create(
            id_maquina=self.maquina_peletizado,
            id_operario=self.operario,
            cantidad_producida=Decimal('880.00'),  # 98% eficiencia del lavado (20kg merma)
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_peletizado,
            orden_trabajo="OT-PELET-001"
        )
        
        lote_lavado.refresh_from_db()  # Asegurar que tenemos el stock actualizado
        
        # Luego registrar el consumo
        consumo_peletizado = ProduccionConsumo.objects.create(
            id_produccion_peletizado=prod_peletizado,
            id_lote_consumido=lote_lavado,
            cantidad_consumida=Decimal('900.00'),
            id_bodega_origen=self.bodega
        )

        # 5. Proceso de Inyección (Producto Final)
        lote_inyeccion = Lotes.objects.create(
            numero_lote="INYEC-001",
            id_material=self.material,
            cantidad_inicial=Decimal('0.00'),
            id_bodega_actual=self.bodega
        )
        
        # Primero crear la producción de inyección (genera stock)
        prod_inyeccion = ProduccionInyeccion.objects.create(
            id_maquina=self.maquina_inyeccion,
            id_operario=self.operario,
            cantidad_producida=Decimal('850.00'),  # 97% eficiencia del peletizado (30kg merma)
            id_bodega_destino=self.bodega,
            id_lote_producido=lote_inyeccion,
            orden_trabajo="OT-INYEC-001"
        )
        
        lote_peletizado.refresh_from_db()  # Asegurar que tenemos el stock actualizado
        
        # Luego registrar el consumo
        consumo_inyeccion = ProduccionConsumo.objects.create(
            id_produccion_inyeccion=prod_inyeccion,
            id_lote_consumido=lote_peletizado,
            cantidad_consumida=Decimal('880.00'),
            id_bodega_origen=self.bodega
        )

        # Verificar cantidades finales
        lote_original.refresh_from_db()
        lote_molido.refresh_from_db()
        lote_lavado.refresh_from_db()
        lote_peletizado.refresh_from_db()
        lote_inyeccion.refresh_from_db()

        # Material original debe estar en 0 (todo consumido)
        self.assertEqual(lote_original.cantidad_actual, Decimal('0.00'))
        # Verificar cantidades producidas en cada etapa
        self.assertEqual(lote_molido.cantidad_actual, Decimal('0.00'))  # Todo consumido en lavado
        self.assertEqual(lote_lavado.cantidad_actual, Decimal('0.00'))  # Todo consumido en peletizado
        self.assertEqual(lote_peletizado.cantidad_actual, Decimal('0.00'))  # Todo consumido en inyección
        self.assertEqual(lote_inyeccion.cantidad_actual, Decimal('850.00'))  # Producto final

        # Verificar eficiencia total del proceso
        eficiencia_total = (lote_inyeccion.cantidad_actual / lote_original.cantidad_inicial) * 100
        self.assertGreater(eficiencia_total, 80)  # La eficiencia total debe ser mayor al 80%

        # Verificar estado activo/inactivo
        self.assertFalse(lote_original.activo)  # Consumido completamente
        self.assertFalse(lote_molido.activo)    # Consumido completamente
        self.assertFalse(lote_lavado.activo)    # Consumido completamente
        self.assertFalse(lote_peletizado.activo) # Consumido completamente
        self.assertTrue(lote_inyeccion.activo)   # Producto final con stock

    def test_traslado_entre_bodegas(self):
        """Prueba que un traslado actualice correctamente el inventario y la bodega del lote."""
        # Crear una segunda bodega para el traslado
        bodega_destino = Bodegas.objects.create(nombre="Bodega Secundaria")
        
        # Asegurarse de que el lote esté en la bodega origen correcta
        self.lote.id_bodega_actual = self.bodega
        self.lote.save()
        
        # Verificar bodega inicial
        self.assertEqual(self.lote.id_bodega_actual, self.bodega)
        self.assertEqual(self.lote.cantidad_actual, Decimal('100.00'))
        
        # Realizar traslado
        procesar_movimiento_inventario(
            tipo_movimiento='Traslado',
            lote=self.lote,
            cantidad=Decimal('100.00'),  # Trasladar todo el stock
            bodega_origen=self.bodega,
            bodega_destino=bodega_destino
        )
        
        # Refrescar el lote desde la base de datos
        self.lote.refresh_from_db()
        
        # Verificar que la bodega se actualizó correctamente
        self.assertEqual(self.lote.id_bodega_actual, bodega_destino)
        # Verificar que la cantidad permanece igual después del traslado
        self.assertEqual(self.lote.cantidad_actual, Decimal('100.00'))
        # Verificar que el lote sigue activo
        self.assertTrue(self.lote.activo)
