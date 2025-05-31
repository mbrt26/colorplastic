from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from .models import Lotes, MovimientosInventario

def procesar_movimiento_inventario(tipo_movimiento, lote, cantidad, bodega_origen=None, bodega_destino=None, usuario=None, **kwargs):
    """
    Procesa un movimiento de inventario de forma centralizada y atómica.
    Valida stock, actualiza cantidades y registra el movimiento.
    """
    with transaction.atomic():
        try:
            # Asegurar que cantidad sea Decimal
            if not isinstance(cantidad, Decimal):
                cantidad = Decimal(str(cantidad))
        except (InvalidOperation, TypeError) as e:
            raise ValidationError(f"Cantidad inválida: {cantidad}")

        if cantidad <= Decimal('0'):
            raise ValidationError("La cantidad debe ser mayor que cero.")
            
        lote_original = Lotes.objects.select_for_update().get(pk=lote.pk)
        
        # Validar traslado primero (caso especial que requiere ambas bodegas)
        if tipo_movimiento == 'Traslado':
            if not bodega_origen or not bodega_destino:
                raise ValidationError("El traslado requiere bodega origen y destino.")
            if bodega_origen == bodega_destino:
                raise ValidationError("La bodega origen y destino no pueden ser iguales en un traslado.")
            if lote_original.id_bodega_actual != bodega_origen:
                raise ValidationError(f"El lote {lote_original.numero_lote} no está en la bodega origen.")
            if lote_original.cantidad_actual < cantidad:
                raise ValidationError(f"Stock insuficiente. Disponible: {lote_original.cantidad_actual}, requerido: {cantidad}")

            # Traslado parcial: crear nuevo lote
            if cantidad < lote_original.cantidad_actual:
                nuevo_lote = Lotes.objects.create(
                    numero_lote=f"{lote_original.numero_lote}-T",
                    id_material=lote_original.id_material,
                    cantidad_inicial=cantidad,
                    cantidad_actual=cantidad,
                    id_bodega_actual=bodega_destino,
                    activo=True
                )
                lote_original.cantidad_actual -= cantidad
            else:
                # Traslado completo: solo cambiar bodega
                lote_original.id_bodega_actual = bodega_destino
                
        # Validar otros movimientos
        elif tipo_movimiento in ['Venta', 'SalidaServicio', 'ConsumoProduccion', 'AjusteNegativo']:
            if not bodega_origen:
                raise ValidationError(f"Movimiento de salida ({tipo_movimiento}) requiere bodega origen.")
            if lote_original.id_bodega_actual != bodega_origen:
                raise ValidationError(f"El lote {lote_original.numero_lote} no está en la bodega origen.")
            if lote_original.cantidad_actual < cantidad:
                raise ValidationError(f"Stock insuficiente. Disponible: {lote_original.cantidad_actual}, requerido: {cantidad}")
            lote_original.cantidad_actual -= cantidad
                
        elif tipo_movimiento in ['Compra', 'IngresoServicio', 'AjustePositivo']:
            if not bodega_destino:
                raise ValidationError(f"Movimiento de entrada ({tipo_movimiento}) requiere bodega destino.")
            
            # Para IngresoServicio de producción, verificar si es un lote recién creado
            if tipo_movimiento == 'IngresoServicio':
                # Si el lote ya tiene la cantidad y está en la bodega destino,
                # solo registramos el movimiento sin modificar la cantidad
                # (esto evita duplicar el stock en lotes de producción)
                if (lote_original.id_bodega_actual == bodega_destino and 
                    lote_original.cantidad_actual >= cantidad):
                    # Lote ya creado con la cantidad correcta, solo registrar movimiento
                    pass  # No modificar cantidad_actual
                else:
                    # Movimiento de ingreso normal (compras, ajustes, etc.)
                    lote_original.cantidad_actual += cantidad
            else:
                # Para Compra y AjustePositivo siempre sumar
                lote_original.cantidad_actual += cantidad
        else:
            raise ValidationError(f"Tipo de movimiento no soportado: {tipo_movimiento}")
            
        # Actualizar estado activo
        lote_original.activo = lote_original.cantidad_actual > Decimal('0')
        lote_original.save()
        
        # Crear el registro del movimiento
        movimiento = MovimientosInventario.objects.create(
            tipo_movimiento=tipo_movimiento,
            id_lote=lote_original,
            cantidad=cantidad,
            id_origen_bodega=bodega_origen,
            id_destino_bodega=bodega_destino,
            **kwargs
        )

        return movimiento


def revert_movimiento_inventario(movimiento: MovimientosInventario):
    """Revierte un movimiento de inventario de manera atómica."""
    with transaction.atomic():
        lote = Lotes.objects.select_for_update().get(pk=movimiento.id_lote.pk)

        if movimiento.tipo_movimiento in ["IngresoServicio", "Compra", "AjustePositivo"]:
            # Revertir entradas restando stock
            if lote.cantidad_actual < movimiento.cantidad:
                raise ValidationError(
                    f"Stock insuficiente para revertir movimiento en {lote.numero_lote}"
                )
            lote.cantidad_actual -= movimiento.cantidad

        elif movimiento.tipo_movimiento in [
            "ConsumoProduccion",
            "Venta",
            "AjusteNegativo",
            "SalidaServicio",
        ]:
            # Revertir salidas sumando stock
            lote.cantidad_actual += movimiento.cantidad

        elif movimiento.tipo_movimiento == "Traslado":
            # Para efectos de estas pruebas no se usa, pero se deja soporte básico
            if movimiento.id_destino_bodega:
                if lote.cantidad_actual < movimiento.cantidad:
                    raise ValidationError(
                        f"Stock insuficiente para revertir traslado en {lote.numero_lote}"
                    )
                lote.cantidad_actual -= movimiento.cantidad
            if movimiento.id_origen_bodega:
                lote.id_bodega_actual = movimiento.id_origen_bodega

        else:
            raise ValidationError(
                f"Tipo de movimiento no soportado para reversión: {movimiento.tipo_movimiento}"
            )

        lote.activo = lote.cantidad_actual > Decimal("0")
        lote.save()
        movimiento.delete()
