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

def despachos(request):
    """Lista y crea despachos de materiales."""
    if request.method == 'POST':
        try:
            numero_remision = request.POST.get('numero_remision')
            fecha_despacho = request.POST.get('fecha_despacho') or None
            direccion = request.POST.get('direccion_entrega')
            observaciones = request.POST.get('observaciones', '')
            tercero_id = request.POST.get('tercero')

            Despacho.objects.create(
                numero_remision=numero_remision,
                fecha_despacho=fecha_despacho,
                direccion_entrega=direccion,
                observaciones=observaciones,
                tercero_id=tercero_id,
                usuario_creacion=request.user,
            )
            messages.success(request, 'Despacho creado exitosamente.')
            return redirect('gestion:despachos')
        except Exception as e:
            messages.error(request, f'Error al crear el despacho: {str(e)}')

    despachos_list = Despacho.objects.select_related('tercero').all()
    context = {
        'despachos': despachos_list,
        'terceros': Terceros.objects.all(),
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
            cantidad = Decimal(request.POST.get('cantidad'))

            DetalleDespacho.objects.create(
                despacho=despacho,
                producto_id=lote_id,
                bodega_origen_id=bodega_id,
                cantidad=cantidad,
            )
            messages.success(request, 'Detalle agregado exitosamente.')
            return redirect('gestion:detalle_despacho', id=despacho.pk)
        except Exception as e:
            messages.error(request, f'Error al agregar el detalle: {str(e)}')

    detalles = despacho.detalles.select_related('producto', 'bodega_origen').all()
    context = {
        'despacho': despacho,
        'detalles': detalles,
        'lotes': Lotes.objects.filter(activo=True, cantidad_actual__gt=0),
        'bodegas': Bodegas.objects.all(),
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
        messages.success(request, 'Detalle eliminado.')
    return redirect('gestion:detalle_despacho', id=despacho_id)
