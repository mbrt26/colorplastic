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
def inventario_bodega(request, bodega_id):
    """Muestra el inventario detallado de una bodega específica."""
    bodega = get_object_or_404(Bodegas, pk=bodega_id)
    lotes = Lotes.objects.filter(id_bodega_actual=bodega, activo=True)
    
    context = {
        'bodega': bodega,
        'lotes': lotes,
    }
    return render(request, 'gestion/inventario_bodega.html', context)

@login_required
def traslado_form(request):
    """Formulario para realizar traslados entre bodegas."""
    # Obtener lote preseleccionado si viene en la URL
    lote_preseleccionado = request.GET.get('lote')
    
    if request.method == 'POST':
        lote_id = request.POST.get('lote_id')
        bodega_destino_id = request.POST.get('bodega_destino')
        cantidad = Decimal(request.POST.get('cantidad', '0'))
        
        try:
            with transaction.atomic():
                lote = Lotes.objects.get(pk=lote_id)
                bodega_origen = lote.id_bodega_actual
                bodega_destino = Bodegas.objects.get(pk=bodega_destino_id)
                
                procesar_movimiento_inventario(
                    tipo_movimiento='Traslado',
                    lote=lote,
                    cantidad=cantidad,
                    bodega_origen=bodega_origen,
                    bodega_destino=bodega_destino,
                    observaciones=f"Traslado desde {bodega_origen.nombre} hacia {bodega_destino.nombre}"
                )
                messages.success(request, 'Traslado realizado exitosamente.')
                return redirect('gestion:inventario_bodega', bodega_id=bodega_origen.pk)
                
        except ValueError as e:
            messages.error(request, 'Error: La cantidad ingresada no es válida.')
        except Exception as e:
            messages.error(request, f'Error al realizar el traslado: {str(e)}')
    
    lotes = Lotes.objects.filter(activo=True)
    bodegas = Bodegas.objects.all()
    
    context = {
        'lotes': lotes,
        'bodegas': bodegas,
        'lote_preseleccionado': lote_preseleccionado
    }
    return render(request, 'gestion/traslado_form.html', context)
@login_required
def inventario_global(request):
    """Vista para mostrar el inventario global con filtros."""
    nombre_material = request.GET.get('nombre_material', '')
    tipo_material = request.GET.get('tipo_material', '')
    
    # Empezamos con todos los lotes activos
    lotes = Lotes.objects.filter(activo=True)
    
    if (nombre_material):
        lotes = lotes.filter(id_material__nombre__icontains=nombre_material)
    if (tipo_material):
        lotes = lotes.filter(id_material__tipo=tipo_material)
    
    # Agregamos joins optimizados
    lotes = lotes.select_related('id_material', 'id_bodega_actual')
    
    # Obtener todas las bodegas y tipos de materiales para los filtros
    bodegas = Bodegas.objects.all()
    tipos_materiales = Materiales.TIPO_MATERIAL_CHOICES
    
    context = {
        'tipos_materiales': tipos_materiales,
        'nombre_material': nombre_material,
        'tipo_material': tipo_material,
        'total_lotes': lotes.count(),
        'total_kg': lotes.filter(unidad_medida='kg').aggregate(total=Sum('cantidad_actual'))['total'] or 0,
    }
    
    # Si hay un tipo de material seleccionado, agrupar por material
    if tipo_material:
        # Agrupar lotes por material
        materiales_dict = {}
        for lote in lotes:
            material = lote.id_material
            if (material) not in materiales_dict:
                materiales_dict[material] = []
            materiales_dict[material].append(lote)
        context['inventario_por_material'] = materiales_dict
    else:
        # Agrupar lotes por bodega (comportamiento original)
        inventario_por_bodega = {}
        for bodega in bodegas:
            inventario_por_bodega[bodega] = lotes.filter(id_bodega_actual=bodega)
        context['inventario_por_bodega'] = inventario_por_bodega
    
    return render(request, 'gestion/inventario_global.html', context)


@login_required
@require_GET
def verificar_stock_api(request, lote_id):
    """API endpoint para verificar el stock actual de un lote en tiempo real."""
    try:
        lote = Lotes.objects.get(pk=lote_id, activo=True)
        return JsonResponse({
            'success': True,
            'stock_actual': float(lote.cantidad_actual),
            'activo': lote.activo,
            'numero_lote': lote.numero_lote
        })
    except Lotes.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Lote no encontrado o inactivo',
            'stock_actual': 0
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'stock_actual': 0
        })

