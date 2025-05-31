from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError  # Import ValidationError

from .models import (
    MovimientosInventario,
    Lotes,
    ProduccionConsumo,
    ProduccionMolido,
    ProduccionLavado,
    ProduccionPeletizado,
    ProduccionInyeccion,
    DetalleDespacho,
    Despacho,
)

@receiver(post_save, sender=MovimientosInventario)
def registrar_movimiento(sender, instance: MovimientosInventario, created, **kwargs):
    """
    Registra el movimiento en el log. Las validaciones se hacen en procesar_movimiento_inventario.
    """
    if created:
        print(f"Movimiento {instance.tipo_movimiento} registrado: {instance.id_movimiento}")

@receiver(post_save, sender=ProduccionConsumo)
def crear_movimiento_consumo_produccion(sender, instance: ProduccionConsumo, created, **kwargs):
    """
    Registra el consumo de producción usando la función centralizada procesar_movimiento_inventario.
    """
    if created:
        try:
            from .inventario_utils import procesar_movimiento_inventario
            produccion_padre = instance.get_produccion_padre()
            if not produccion_padre:
                raise ValidationError(f"No se pudo determinar la producción padre para el consumo {instance.id_consumo}.")

            # Crear el movimiento usando la función centralizada
            procesar_movimiento_inventario(
                tipo_movimiento='ConsumoProduccion',
                lote=instance.id_lote_consumido,
                cantidad=instance.cantidad_consumida,
                bodega_origen=instance.id_bodega_origen,
                produccion_referencia=str(produccion_padre.id_produccion),
                consecutivo_soporte=f"CONSUMO-PROD-{produccion_padre.id_produccion}",
                observaciones=f"Consumo automático para producción {produccion_padre._meta.verbose_name} ID: {produccion_padre.id_produccion}"
            )
            print(f"Consumo de producción procesado para {instance.id_consumo}")

        except ValidationError as e:
             raise e
        except Exception as e:
            print(f"ERROR CRÍTICO al procesar consumo de producción {instance.id_consumo}: {e}")
            raise ValidationError(f"Error inesperado al procesar consumo: {e}")

@receiver(post_save, sender=Lotes)
def actualizar_estado_activo_lote(sender, instance: Lotes, **kwargs):
    """
    Actualiza el estado activo del lote basado en su cantidad actual.
    """
    if instance.cantidad_actual == 0 and instance.activo:
        # Usar update() directo para evitar recursión infinita
        Lotes.objects.filter(pk=instance.pk).update(activo=False)
    elif instance.cantidad_actual > 0 and not instance.activo:
        Lotes.objects.filter(pk=instance.pk).update(activo=True)

# ... (resto del archivo si hubiera más señales) ...


def _revert_movimientos_produccion(instance):
    """Revierta todos los movimientos asociados a una producción."""
    from .inventario_utils import revert_movimiento_inventario

    movimientos = MovimientosInventario.objects.filter(
        produccion_referencia=str(instance.id_produccion)
    )
    for mov in movimientos:
        revert_movimiento_inventario(mov)


@receiver(post_delete, sender=ProduccionMolido)
@receiver(post_delete, sender=ProduccionLavado)
@receiver(post_delete, sender=ProduccionPeletizado)
@receiver(post_delete, sender=ProduccionInyeccion)
def revertir_produccion(sender, instance, **kwargs):
    _revert_movimientos_produccion(instance)


@receiver(post_delete, sender=ProduccionConsumo)
def revertir_consumo_produccion(sender, instance, **kwargs):
    from .inventario_utils import revert_movimiento_inventario

    produccion_padre_id = (
        instance.id_produccion_molido_id or
        instance.id_produccion_lavado_id or
        instance.id_produccion_peletizado_id or
        instance.id_produccion_inyeccion_id
    )
    if not produccion_padre_id:
        return

    movimientos = MovimientosInventario.objects.filter(
        produccion_referencia=str(produccion_padre_id),
        id_lote=instance.id_lote_consumido,
        tipo_movimiento="ConsumoProduccion",
    )
    for mov in movimientos:
        revert_movimiento_inventario(mov)


@receiver(post_save, sender=DetalleDespacho)
def crear_movimiento_despacho(sender, instance: DetalleDespacho, created, **kwargs):
    """Genera el movimiento de inventario SOLO si el despacho está en estado 'despachado'."""
    if not created:
        return
    
    # ✅ NUEVA LÓGICA: Solo crear movimiento si el despacho está despachado
    if instance.despacho.estado == 'despachado':
        from .inventario_utils import procesar_movimiento_inventario

        procesar_movimiento_inventario(
            tipo_movimiento="Venta",
            lote=instance.producto,
            cantidad=instance.cantidad,
            bodega_origen=instance.bodega_origen,
            id_destino_tercero=instance.despacho.tercero,
            consecutivo_soporte=instance.despacho.numero_remision,
            observaciones=f"Despacho {instance.despacho.numero_remision}",
        )
        print(f"✅ Movimiento de inventario creado para detalle de despacho despachado: {instance.despacho.numero_remision}")
    else:
        print(f"⏳ Detalle agregado a despacho en estado '{instance.despacho.estado}'. No se descuenta inventario hasta que sea despachado.")

@receiver(post_delete, sender=DetalleDespacho)
def revertir_despacho(sender, instance: DetalleDespacho, **kwargs):
    """Revierte los movimientos generados por un detalle de despacho al eliminarlo."""
    from .inventario_utils import revert_movimiento_inventario

    movimientos = MovimientosInventario.objects.filter(
        consecutivo_soporte=instance.despacho.numero_remision,
        id_lote=instance.producto,
        tipo_movimiento="Venta",
        cantidad=instance.cantidad,
    )
    for mov in movimientos:
        revert_movimiento_inventario(mov)


@receiver(pre_save, sender=Despacho)
def capturar_estado_anterior_despacho(sender, instance: Despacho, **kwargs):
    """Captura el estado anterior del despacho antes de guardarlo."""
    if instance.pk:  # Solo si el despacho ya existe
        try:
            despacho_anterior = Despacho.objects.get(pk=instance.pk)
            instance._estado_anterior = despacho_anterior.estado
        except Despacho.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Despacho)
def manejar_cambio_estado_despacho(sender, instance: Despacho, created, **kwargs):
    """Maneja los movimientos de inventario cuando cambia el estado del despacho."""
    if created:
        return  # No hacer nada en despachos nuevos
    
    estado_anterior = getattr(instance, '_estado_anterior', None)
    estado_actual = instance.estado
    
    # Solo procesar si hubo un cambio de estado
    if estado_anterior and estado_anterior != estado_actual:
        from .inventario_utils import revert_movimiento_inventario, procesar_movimiento_inventario
        
        try:
            # Caso 1: De "despachado" a "pendiente" - REVERTIR movimientos
            if estado_anterior == 'despachado' and estado_actual == 'pendiente':
                print(f"🔄 Revirtiendo despacho {instance.numero_remision} de despachado a pendiente")
                
                # Buscar todos los movimientos de "Venta" asociados a este despacho
                movimientos_despacho = MovimientosInventario.objects.filter(
                    consecutivo_soporte=instance.numero_remision,
                    tipo_movimiento='Venta'
                )
                
                for movimiento in movimientos_despacho:
                    print(f"  ↩️ Revirtiendo movimiento: {movimiento.id_lote.numero_lote} - {movimiento.cantidad} kg")
                    revert_movimiento_inventario(movimiento)
                
                print(f"✅ Despacho {instance.numero_remision} revertido exitosamente")
            
            # Caso 2: De "pendiente" a "despachado" - RECREAR movimientos si no existen
            elif estado_anterior == 'pendiente' and estado_actual == 'despachado':
                print(f"📦 Marcando despacho {instance.numero_remision} como despachado")
                
                # Verificar movimientos existentes
                movimientos_existentes = MovimientosInventario.objects.filter(
                    consecutivo_soporte=instance.numero_remision,
                    tipo_movimiento='Venta'
                ).count()
                
                detalles_count = instance.detalles.count()
                
                # Si no hay movimientos o hay inconsistencia, RECREAR todos los movimientos
                if movimientos_existentes == 0:
                    print(f"🔄 No hay movimientos, recreando {detalles_count} movimientos de inventario")
                    
                    # Recrear movimientos para cada detalle
                    for detalle in instance.detalles.all():
                        print(f"  ➕ Creando movimiento: {detalle.producto.numero_lote} - {detalle.cantidad} kg")
                        
                        procesar_movimiento_inventario(
                            tipo_movimiento="Venta",
                            lote=detalle.producto,
                            cantidad=detalle.cantidad,
                            bodega_origen=detalle.bodega_origen,
                            id_destino_tercero=instance.tercero,
                            consecutivo_soporte=instance.numero_remision,
                            observaciones=f"Despacho {instance.numero_remision} - Recreado por cambio de estado",
                        )
                    
                    print(f"✅ Movimientos recreados para despacho {instance.numero_remision}")
                
                elif movimientos_existentes != detalles_count:
                    print(f"⚠️ Inconsistencia detectada: {movimientos_existentes} movimientos vs {detalles_count} detalles")
                    
                    # Limpiar movimientos existentes y recrear todos
                    MovimientosInventario.objects.filter(
                        consecutivo_soporte=instance.numero_remision,
                        tipo_movimiento='Venta'
                    ).delete()
                    
                    # Recrear movimientos
                    for detalle in instance.detalles.all():
                        procesar_movimiento_inventario(
                            tipo_movimiento="Venta",
                            lote=detalle.producto,
                            cantidad=detalle.cantidad,
                            bodega_origen=detalle.bodega_origen,
                            id_destino_tercero=instance.tercero,
                            consecutivo_soporte=instance.numero_remision,
                            observaciones=f"Despacho {instance.numero_remision} - Corregido por inconsistencia",
                        )
                    
                    print(f"✅ Inconsistencia corregida para despacho {instance.numero_remision}")
                else:
                    print(f"✅ Despacho {instance.numero_remision} ya tiene movimientos correctos")
                
            # Caso 3: De cualquier estado a "cancelado" - REVERTIR si había movimientos
            elif estado_actual == 'cancelado' and estado_anterior in ['despachado', 'en_proceso']:
                print(f"🚫 Cancelando despacho {instance.numero_remision}")
                
                movimientos_despacho = MovimientosInventario.objects.filter(
                    consecutivo_soporte=instance.numero_remision,
                    tipo_movimiento='Venta'
                )
                
                for movimiento in movimientos_despacho:
                    print(f"  ↩️ Revirtiendo por cancelación: {movimiento.id_lote.numero_lote} - {movimiento.cantidad} kg")
                    revert_movimiento_inventario(movimiento)
                
                print(f"✅ Despacho {instance.numero_remision} cancelado y revertido")
            
            # Caso 4: De "cancelado" a "pendiente" - NO hacer nada (ya está sin movimientos)
            elif estado_anterior == 'cancelado' and estado_actual == 'pendiente':
                print(f"📝 Despacho {instance.numero_remision} reactivado como pendiente")
            
            # Caso 5: De "cancelado" a "despachado" - RECREAR movimientos
            elif estado_anterior == 'cancelado' and estado_actual == 'despachado':
                print(f"🔄 Reactivando despacho {instance.numero_remision} como despachado")
                
                # Recrear movimientos para cada detalle
                for detalle in instance.detalles.all():
                    print(f"  ➕ Recreando movimiento: {detalle.producto.numero_lote} - {detalle.cantidad} kg")
                    
                    procesar_movimiento_inventario(
                        tipo_movimiento="Venta",
                        lote=detalle.producto,
                        cantidad=detalle.cantidad,
                        bodega_origen=detalle.bodega_origen,
                        id_destino_tercero=instance.tercero,
                        consecutivo_soporte=instance.numero_remision,
                        observaciones=f"Despacho {instance.numero_remision} - Reactivado desde cancelado",
                    )
                
                print(f"✅ Despacho {instance.numero_remision} reactivado exitosamente")
                
        except Exception as e:
            print(f"❌ Error al manejar cambio de estado del despacho {instance.numero_remision}: {e}")
            raise ValidationError(f"Error al procesar cambio de estado: {e}")
