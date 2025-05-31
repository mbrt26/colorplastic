from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
import uuid

from ..models import (
    Bodegas, Materiales, Lotes, MovimientosInventario, 
    Terceros
)
from ..inventario_utils import procesar_movimiento_inventario

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
def ingreso_materiales(request):
    """Vista principal para el módulo de ingreso de materiales desde proveedores"""
    # Obtener ingresos recientes (últimos 30 días)
    fecha_limite = timezone.now() - timezone.timedelta(days=30)
    ingresos_recientes = MovimientosInventario.objects.filter(
        tipo_movimiento='Compra',
        fecha__gte=fecha_limite
    ).select_related(
        'id_lote__id_material',
        'id_destino_bodega',
        'id_origen_tercero'
    ).order_by('-fecha')[:20]
    
    # Estadísticas
    total_ingresos_mes = MovimientosInventario.objects.filter(
        tipo_movimiento='Compra',
        fecha__gte=fecha_limite
    ).count()
    
    # Obtener proveedores activos
    proveedores = Terceros.objects.filter(tipo='Proveedor', activo=True).order_by('nombre')
    
    # Obtener materiales y bodegas para los formularios
    materiales = Materiales.objects.all().order_by('nombre')
    bodegas = Bodegas.objects.all().order_by('nombre')
    
    context = {
        'ingresos_recientes': ingresos_recientes,
        'total_ingresos_mes': total_ingresos_mes,
        'proveedores': proveedores,
        'materiales': materiales,
        'bodegas': bodegas,
    }
    
    return render(request, 'gestion/ingreso_materiales.html', context)

@login_required
@require_POST
def procesar_ingreso_material(request):
    """Procesar el ingreso de un nuevo material desde proveedor"""
    try:
        with transaction.atomic():
            # Obtener datos del formulario
            proveedor_id = request.POST.get('proveedor')
            material_id = request.POST.get('material')
            bodega_id = request.POST.get('bodega')
            cantidad = Decimal(request.POST.get('cantidad', '0'))
            numero_lote = request.POST.get('numero_lote')
            factura_remision = request.POST.get('factura_remision')
            fecha_vencimiento = request.POST.get('fecha_vencimiento')
            costo_unitario = request.POST.get('costo_unitario')
            clasificacion = request.POST.get('clasificacion')
            observaciones = request.POST.get('observaciones', '')
            
            # Validaciones básicas
            if not all([proveedor_id, material_id, bodega_id, cantidad, numero_lote]):
                messages.error(request, 'Por favor complete todos los campos obligatorios.')
                return redirect('gestion:ingreso_materiales')
            
            if cantidad <= 0:
                messages.error(request, 'La cantidad debe ser mayor que cero.')
                return redirect('gestion:ingreso_materiales')
            
            # Verificar que el número de lote no exista
            if Lotes.objects.filter(numero_lote=numero_lote).exists():
                messages.error(request, f'Ya existe un lote con el número {numero_lote}.')
                return redirect('gestion:ingreso_materiales')
            
            # Obtener objetos
            proveedor = get_object_or_404(Terceros, id_tercero=proveedor_id, tipo='Proveedor')
            material = get_object_or_404(Materiales, id_material=material_id)
            bodega = get_object_or_404(Bodegas, id_bodega=bodega_id)
            
            # Crear el lote
            lote_data = {
                'numero_lote': numero_lote,
                'id_material': material,
                'cantidad_inicial': cantidad,
                'cantidad_actual': cantidad,
                'id_bodega_actual': bodega,
                'proveedor_origen': proveedor,
                'observaciones': observaciones,
            }
            
            # Agregar campos opcionales si se proporcionan
            if fecha_vencimiento:
                lote_data['fecha_vencimiento'] = fecha_vencimiento
            
            if costo_unitario:
                lote_data['costo_unitario'] = Decimal(costo_unitario)
            
            if clasificacion:
                lote_data['clasificacion'] = clasificacion
            
            lote = Lotes.objects.create(**lote_data)
            
            # Crear el movimiento de inventario
            movimiento = MovimientosInventario.objects.create(
                tipo_movimiento='Compra',
                id_lote=lote,
                cantidad=cantidad,
                id_destino_bodega=bodega,
                id_origen_tercero=proveedor,
                factura_remision=factura_remision,
                observaciones=f'Ingreso de material desde proveedor: {proveedor.nombre}'
            )
            
            messages.success(
                request, 
                f'Material ingresado exitosamente. Lote: {numero_lote} - Cantidad: {cantidad} kg'
            )
            
            return redirect('gestion:detalle_ingreso_material', movimiento_id=movimiento.id_movimiento)
            
    except Exception as e:
        messages.error(request, f'Error al procesar el ingreso: {str(e)}')
        return redirect('gestion:ingreso_materiales')

@login_required
def detalle_ingreso_material(request, movimiento_id):
    """Vista para mostrar el detalle de un ingreso de material específico"""
    movimiento = get_object_or_404(
        MovimientosInventario.objects.select_related(
            'id_lote__id_material',
            'id_destino_bodega',
            'id_origen_tercero'
        ),
        id_movimiento=movimiento_id,
        tipo_movimiento='Compra'
    )
    
    # Obtener otros movimientos del mismo lote para historial
    historial_lote = MovimientosInventario.objects.filter(
        id_lote=movimiento.id_lote
    ).exclude(
        id_movimiento=movimiento_id
    ).select_related(
        'id_origen_bodega',
        'id_destino_bodega',
        'id_origen_tercero',
        'id_destino_tercero'
    ).order_by('-fecha')[:10]
    
    context = {
        'movimiento': movimiento,
        'lote': movimiento.id_lote,
        'historial_lote': historial_lote,
    }
    
    return render(request, 'gestion/detalle_ingreso_material.html', context)

@login_required
def buscar_proveedores(request):
    """API endpoint para buscar proveedores por nombre"""
    term = request.GET.get('term', '')
    proveedores = Terceros.objects.filter(
        tipo='Proveedor',
        activo=True,
        nombre__icontains=term
    ).values('id_tercero', 'nombre', 'identificacion')[:10]
    
    return JsonResponse(list(proveedores), safe=False)

@login_required
def verificar_numero_lote(request):
    """API endpoint para verificar si un número de lote ya existe"""
    numero_lote = request.GET.get('numero_lote', '')
    existe = Lotes.objects.filter(numero_lote=numero_lote).exists()
    
    return JsonResponse({'existe': existe})

