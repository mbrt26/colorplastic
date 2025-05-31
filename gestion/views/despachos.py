from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from decimal import Decimal
from ..models import (
    Bodegas, Lotes, MovimientosInventario, 
    Materiales, Maquinas, Operarios, Terceros,
    ProduccionMolido, ProduccionLavado, ProduccionPeletizado, ProduccionInyeccion,
    ResiduosProduccion, ProduccionConsumo, MotivoParo, ParosProduccion,
    Despacho, DetalleDespacho
)
from ..inventario_utils import procesar_movimiento_inventario
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import uuid
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@login_required
def despachos(request):
    """Lista y crea despachos de materiales."""
    if request.method == 'POST':
        try:
            numero_remision = request.POST.get('numero_remision')
            fecha_despacho = request.POST.get('fecha_despacho') or None
            direccion = request.POST.get('direccion_entrega')
            observaciones = request.POST.get('observaciones', '')
            tercero_id = request.POST.get('tercero')

            # Validaciones mejoradas
            if not numero_remision or not direccion or not tercero_id:
                raise ValidationError("Todos los campos obligatorios deben estar completos")

            # Verificar que no exista ya un despacho con ese número de remisión
            if Despacho.objects.filter(numero_remision=numero_remision).exists():
                raise ValidationError(f"Ya existe un despacho con el número de remisión {numero_remision}")

            with transaction.atomic():
                despacho = Despacho.objects.create(
                    numero_remision=numero_remision,
                    fecha_despacho=fecha_despacho,
                    direccion_entrega=direccion,
                    observaciones=observaciones,
                    tercero_id=tercero_id,
                    usuario_creacion=request.user,
                )

                # Procesar productos si se enviaron desde el modal
                productos_agregados = 0
                i = 0
                while f'productos[{i}][lote_id]' in request.POST:
                    lote_id = request.POST.get(f'productos[{i}][lote_id]')
                    bodega_id = request.POST.get(f'productos[{i}][bodega_id]')
                    cantidad_str = request.POST.get(f'productos[{i}][cantidad]')
                    
                    if lote_id and bodega_id and cantidad_str:
                        try:
                            cantidad = Decimal(cantidad_str)
                            lote = get_object_or_404(Lotes, pk=lote_id)
                            bodega = get_object_or_404(Bodegas, pk=bodega_id)

                            # Validaciones del producto
                            if lote.cantidad_actual < cantidad:
                                raise ValidationError(f"Stock insuficiente para {lote.numero_lote}. Disponible: {lote.cantidad_actual}, solicitado: {cantidad}")

                            if lote.id_bodega_actual != bodega:
                                raise ValidationError(f"El lote {lote.numero_lote} no está en la bodega {bodega.nombre}")

                            # Crear detalle del despacho
                            DetalleDespacho.objects.create(
                                despacho=despacho,
                                producto=lote,
                                bodega_origen=bodega,
                                cantidad=cantidad,
                            )
                            productos_agregados += 1

                        except (ValueError, Decimal.InvalidOperation):
                            raise ValidationError(f"Cantidad inválida para el producto {i+1}")
                    
                    i += 1

                # Mensaje de éxito
                if productos_agregados > 0:
                    messages.success(request, 
                        f'Despacho {numero_remision} creado exitosamente con {productos_agregados} producto(s).')
                else:
                    messages.success(request, 
                        f'Despacho {numero_remision} creado exitosamente. Puede agregar productos desde la vista de detalles.')
                
                return redirect('gestion:detalle_despacho', id=despacho.pk)

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al crear el despacho: {str(e)}')

    despachos_list = Despacho.objects.select_related('tercero', 'usuario_creacion').all().order_by('-fecha_creacion')
    context = {
        'despachos': despachos_list,
        'terceros': Terceros.objects.filter(activo=True).order_by('nombre'),
        'lotes': Lotes.objects.filter(activo=True, cantidad_actual__gt=0).select_related('id_material', 'id_bodega_actual'),
        'bodegas': Bodegas.objects.all().order_by('nombre'),
    }
    return render(request, 'gestion/despachos.html', context)


@login_required
def detalle_despacho(request, id):
    """Gestiona los detalles de un despacho."""
    despacho = get_object_or_404(Despacho, pk=id)
    
    if request.method == 'POST':
        try:
            lote_id = request.POST.get('producto')
            bodega_id = request.POST.get('bodega_origen')
            cantidad = Decimal(request.POST.get('cantidad', '0'))

            # Validaciones mejoradas
            if not lote_id or not bodega_id or cantidad <= 0:
                raise ValidationError("Todos los campos son obligatorios y la cantidad debe ser mayor a cero")

            lote = get_object_or_404(Lotes, pk=lote_id)
            bodega = get_object_or_404(Bodegas, pk=bodega_id)

            # Verificar que el lote esté en la bodega seleccionada
            if lote.id_bodega_actual != bodega:
                raise ValidationError(f"El lote {lote.numero_lote} no está en la bodega {bodega.nombre}")

            # Verificar stock disponible
            if lote.cantidad_actual < cantidad:
                raise ValidationError(f"Stock insuficiente. Disponible: {lote.cantidad_actual}, solicitado: {cantidad}")

            with transaction.atomic():
                DetalleDespacho.objects.create(
                    despacho=despacho,
                    producto=lote,
                    bodega_origen=bodega,
                    cantidad=cantidad,
                )
                messages.success(request, f'Detalle agregado: {lote.numero_lote} - {cantidad} kg')
                return redirect('gestion:detalle_despacho', id=despacho.pk)

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al agregar el detalle: {str(e)}')

    detalles = despacho.detalles.select_related('producto__id_material', 'bodega_origen').all()
    context = {
        'despacho': despacho,
        'detalles': detalles,
        'lotes': Lotes.objects.filter(activo=True, cantidad_actual__gt=0).select_related('id_material'),
        'bodegas': Bodegas.objects.all().order_by('nombre'),
        'terceros': Terceros.objects.filter(activo=True).order_by('nombre'),
    }
    return render(request, 'gestion/despacho_detalle.html', context)


@login_required
@transaction.atomic
def eliminar_detalle_despacho(request, id):
    """Elimina un detalle de despacho."""
    detalle = get_object_or_404(DetalleDespacho, pk=id)
    despacho_id = detalle.despacho_id
    if request.method == 'POST':
        detalle.delete()
        messages.success(request, 'Detalle eliminado correctamente.')
    return redirect('gestion:detalle_despacho', id=despacho_id)


@login_required
@transaction.atomic
def editar_despacho(request, id):
    """Permite editar la información del despacho (cliente, dirección, etc.)."""
    despacho = get_object_or_404(Despacho, pk=id)
    estado_anterior = despacho.estado
    
    if request.method == 'POST':
        try:
            numero_remision = request.POST.get('numero_remision')
            fecha_despacho = request.POST.get('fecha_despacho') or None
            direccion = request.POST.get('direccion_entrega')
            observaciones = request.POST.get('observaciones', '')
            tercero_id = request.POST.get('tercero')
            estado_nuevo = request.POST.get('estado')

            # Validaciones
            if not numero_remision or not direccion or not tercero_id:
                raise ValidationError("Todos los campos obligatorios deben estar completos")

            # Verificar que no exista otro despacho con ese número de remisión
            if (Despacho.objects.filter(numero_remision=numero_remision)
                .exclude(pk=despacho.pk).exists()):
                raise ValidationError(f"Ya existe otro despacho con el número de remisión {numero_remision}")

            # Lógica especial para cambios de estado
            if estado_nuevo and estado_nuevo != estado_anterior:
                # Si cambia de 'pendiente' a 'despachado', establecer fecha de despacho automáticamente
                if estado_anterior == 'pendiente' and estado_nuevo == 'despachado':
                    if not fecha_despacho:
                        from django.utils import timezone
                        fecha_despacho = timezone.now().date()
                    
                    # Verificar que tenga detalles antes de marcar como despachado
                    if not despacho.detalles.exists():
                        raise ValidationError("No se puede marcar como despachado un despacho sin productos")
                
                # Si cambia de 'despachado' a 'cancelado', podríamos revertir movimientos (opcional)
                elif estado_anterior == 'despachado' and estado_nuevo == 'cancelado':
                    # Aquí podrías implementar lógica para revertir el inventario si es necesario
                    messages.warning(request, 
                        'Despacho cancelado. Nota: Los movimientos de inventario ya realizados no se revierten automáticamente.')

            despacho.numero_remision = numero_remision
            despacho.fecha_despacho = fecha_despacho
            despacho.direccion_entrega = direccion
            despacho.observaciones = observaciones
            despacho.tercero_id = tercero_id
            if estado_nuevo:
                despacho.estado = estado_nuevo
            
            despacho.save()
            
            # Mensaje específico según el cambio
            if estado_nuevo and estado_nuevo != estado_anterior:
                if estado_nuevo == 'despachado':
                    messages.success(request, 
                        f'Despacho {numero_remision} marcado como DESPACHADO exitosamente. Fecha: {fecha_despacho}')
                elif estado_nuevo == 'cancelado':
                    messages.warning(request, f'Despacho {numero_remision} CANCELADO.')
                else:
                    messages.success(request, 
                        f'Estado del despacho {numero_remision} cambiado a {despacho.get_estado_display()}.')
            else:
                messages.success(request, f'Despacho {numero_remision} actualizado exitosamente.')
                
            return redirect('gestion:detalle_despacho', id=despacho.pk)
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al actualizar el despacho: {str(e)}')

    context = {
        'despacho': despacho,
        'terceros': Terceros.objects.filter(activo=True).order_by('nombre'),
        'estados': Despacho.ESTADO_CHOICES,
    }
    return render(request, 'gestion/editar_despacho.html', context)


@login_required
@transaction.atomic
def cambiar_estado_despacho(request, id):
    """Vista para cambios rápidos de estado con confirmación y manejo de inventario."""
    if request.method != 'POST':
        return redirect('gestion:detalle_despacho', id=id)
        
    despacho = get_object_or_404(Despacho, pk=id)
    nuevo_estado = request.POST.get('nuevo_estado')
    
    if nuevo_estado not in dict(Despacho.ESTADO_CHOICES):
        messages.error(request, 'Estado inválido.')
        return redirect('gestion:detalle_despacho', id=id)
    
    estado_anterior = despacho.estado
    
    try:
        with transaction.atomic():
            if nuevo_estado == 'despachado' and estado_anterior != 'despachado':
                # Verificar que tenga productos
                if not despacho.detalles.exists():
                    raise ValidationError("No se puede marcar como despachado un despacho sin productos")
                
                # Establecer fecha de despacho si no tiene
                if not despacho.fecha_despacho:
                    from django.utils import timezone
                    despacho.fecha_despacho = timezone.now().date()
                
                despacho.estado = nuevo_estado
                despacho.save()
                
                # Contar productos despachados
                total_productos = despacho.detalles.count()
                total_cantidad = despacho.detalles.aggregate(
                    total=Sum('cantidad'))['total'] or 0
                
                messages.success(request, 
                    f'✅ Despacho {despacho.numero_remision} marcado como DESPACHADO. '
                    f'Fecha: {despacho.fecha_despacho.strftime("%d/%m/%Y")} | '
                    f'Productos: {total_productos} | Total: {total_cantidad} kg')
                    
            elif nuevo_estado == 'cancelado':
                # Verificar si hay movimientos que se van a revertir
                movimientos_activos = MovimientosInventario.objects.filter(
                    consecutivo_soporte=despacho.numero_remision,
                    tipo_movimiento='Venta'
                ).count()
                
                despacho.estado = nuevo_estado
                despacho.save()
                
                if movimientos_activos > 0:
                    messages.warning(request, 
                        f'🚫 Despacho {despacho.numero_remision} CANCELADO. '
                        f'Se han revertido {movimientos_activos} movimientos de inventario automáticamente.')
                else:
                    messages.warning(request, 
                        f'🚫 Despacho {despacho.numero_remision} CANCELADO.')
                    
            elif nuevo_estado == 'pendiente' and estado_anterior == 'despachado':
                # Contar movimientos que se van a revertir
                movimientos_a_revertir = MovimientosInventario.objects.filter(
                    consecutivo_soporte=despacho.numero_remision,
                    tipo_movimiento='Venta'
                )
                
                total_cantidad_revertida = movimientos_a_revertir.aggregate(
                    total=Sum('cantidad'))['total'] or 0
                    
                despacho.estado = nuevo_estado
                despacho.save()
                
                messages.info(request, 
                    f'⏳ Despacho {despacho.numero_remision} regresado a PENDIENTE. '
                    f'✅ Inventario revertido automáticamente: {total_cantidad_revertida} kg '
                    f'regresaron al stock disponible.')
                    
            elif nuevo_estado == 'pendiente':
                despacho.estado = nuevo_estado
                despacho.save()
                messages.info(request, 
                    f'⏳ Despacho {despacho.numero_remision} marcado como PENDIENTE.')
                    
            else:
                despacho.estado = nuevo_estado
                despacho.save()
                messages.success(request, 
                    f'Estado cambiado a {despacho.get_estado_display()}.')
                    
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Error al cambiar estado: {str(e)}')
    
    return redirect('gestion:detalle_despacho', id=id)
