from django.db.models.signals import post_save, post_delete
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

    produccion_padre = instance.get_produccion_padre()
    if not produccion_padre:
        return

    movimientos = MovimientosInventario.objects.filter(
        produccion_referencia=str(produccion_padre.id_produccion),
        id_lote=instance.id_lote_consumido,
        tipo_movimiento="ConsumoProduccion",
    )
    for mov in movimientos:
        revert_movimiento_inventario(mov)
