from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count, F
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from ..models import (
    Pedido, DetallePedido, Cliente, Contacto, Materiales,
    OrdenProduccion, DetalleOrdenProduccion, PlanificacionProcesos,
    Maquinas, User, Tarea
)


@login_required
def pedidos_dashboard(request):
    """Dashboard principal de pedidos."""
    
    # Estadísticas generales
    pedidos_total = Pedido.objects.count()
    pedidos_mes = Pedido.objects.filter(
        fecha_pedido__gte=timezone.now().replace(day=1)
    ).count()
    
    pedidos_pendientes = Pedido.objects.filter(
        estado__in=['borrador', 'confirmado']
    ).count()
    
    pedidos_en_produccion = Pedido.objects.filter(
        estado='en_produccion'
    ).count()
    
    # Valor total de pedidos del mes
    valor_mes = Pedido.objects.filter(
        fecha_pedido__gte=timezone.now().replace(day=1)
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Pedidos por estado
    pedidos_por_estado = Pedido.objects.values('estado').annotate(
        count=Count('id_pedido'),
        valor=Sum('total')
    ).order_by('estado')
    
    # Pedidos urgentes (fecha requerida en los próximos 7 días)
    pedidos_urgentes = Pedido.objects.filter(
        fecha_requerida__lte=timezone.now().date() + timedelta(days=7),
        estado__in=['confirmado', 'en_produccion']
    ).select_related('cliente__tercero').order_by('fecha_requerida')[:10]
    
    # Últimos pedidos
    ultimos_pedidos = Pedido.objects.select_related(
        'cliente__tercero', 'usuario_creacion'
    ).order_by('-fecha_pedido')[:10]
    
    context = {
        'pedidos_total': pedidos_total,
        'pedidos_mes': pedidos_mes,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_en_produccion': pedidos_en_produccion,
        'valor_mes': valor_mes,
        'pedidos_por_estado': pedidos_por_estado,
        'pedidos_urgentes': pedidos_urgentes,
        'ultimos_pedidos': ultimos_pedidos,
    }
    
    return render(request, 'pedidos/dashboard.html', context)


@login_required
def pedidos_list(request):
    """Lista de pedidos con filtros."""
    
    # Filtros
    busqueda = request.GET.get('busqueda', '')
    estado = request.GET.get('estado', '')
    cliente_id = request.GET.get('cliente', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Query base
    pedidos = Pedido.objects.select_related(
        'cliente__tercero', 'contacto', 'usuario_creacion'
    )
    
    # Aplicar filtros
    if busqueda:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=busqueda) |
            Q(cliente__tercero__nombre__icontains=busqueda) |
            Q(orden_compra_cliente__icontains=busqueda)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    if cliente_id:
        pedidos = pedidos.filter(cliente_id=cliente_id)
    
    if fecha_desde:
        pedidos = pedidos.filter(fecha_pedido__gte=fecha_desde)
    
    if fecha_hasta:
        pedidos = pedidos.filter(fecha_pedido__lte=fecha_hasta)
    
    # Ordenar y paginar
    pedidos = pedidos.order_by('-fecha_pedido')
    paginator = Paginator(pedidos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    clientes = Cliente.objects.select_related('tercero').filter(
        estado='activo'
    ).order_by('tercero__nombre')
    
    context = {
        'page_obj': page_obj,
        'clientes': clientes,
        'estado_choices': Pedido.ESTADO_CHOICES,
        'busqueda': busqueda,
        'estado': estado,
        'cliente_id': cliente_id,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'today': timezone.now().date(),
    }
    
    return render(request, 'pedidos/pedidos_list.html', context)


@login_required
def pedido_detail(request, id_pedido):
    """Detalle de un pedido específico."""
    
    pedido = get_object_or_404(Pedido, pk=id_pedido)
    
    # Obtener detalles del pedido
    detalles = pedido.detalles.select_related('material').all()
    
    # Órdenes de producción relacionadas
    ordenes_produccion = pedido.ordenes_produccion.all()
    
    # Obtener tareas relacionadas con el pedido
    tareas = pedido.tareas.select_related('asignado_a', 'creado_por').order_by('-fecha_creacion')
    
    # Calcular progreso
    if detalles:
        total_items = detalles.count()
        items_entregados = detalles.filter(
            cantidad_entregada__gte=F('cantidad')
        ).count()
        progreso = (items_entregados / total_items) * 100
    else:
        progreso = 0
    
    context = {
        'pedido': pedido,
        'detalles': detalles,
        'ordenes_produccion': ordenes_produccion,
        'tareas': tareas,
        'progreso': progreso,
    }
    
    return render(request, 'pedidos/pedido_detail.html', context)


@login_required
@transaction.atomic
def pedido_create(request):
    """Crear nuevo pedido."""
    
    if request.method == 'POST':
        try:
            # Generar número de pedido
            ultimo_pedido = Pedido.objects.order_by('-numero_pedido').first()
            if ultimo_pedido:
                ultimo_numero = int(ultimo_pedido.numero_pedido.split('-')[1])
                nuevo_numero = f"PED-{str(ultimo_numero + 1).zfill(6)}"
            else:
                nuevo_numero = "PED-000001"
            
            # Crear pedido
            pedido = Pedido.objects.create(
                numero_pedido=nuevo_numero,
                cliente_id=request.POST.get('cliente'),
                contacto_id=request.POST.get('contacto'),
                fecha_requerida=request.POST.get('fecha_requerida'),
                estado='borrador',
                prioridad=request.POST.get('prioridad', 'normal'),
                orden_compra_cliente=request.POST.get('orden_compra_cliente') or None,
                condiciones_pago=request.POST.get('condiciones_pago'),
                direccion_entrega=request.POST.get('direccion_entrega'),
                descuento_porcentaje=Decimal(request.POST.get('descuento_porcentaje', 0)),
                observaciones=request.POST.get('observaciones') or None,
                usuario_creacion=request.user
            )
            
            # Procesar detalles del pedido
            detalles_json = request.POST.get('detalles', '[]')
            detalles = json.loads(detalles_json)
            
            for detalle in detalles:
                DetallePedido.objects.create(
                    pedido=pedido,
                    material_id=detalle['material_id'],
                    descripcion_adicional=detalle.get('descripcion_adicional'),
                    cantidad=Decimal(detalle['cantidad']),
                    unidad_medida=detalle['unidad_medida'],
                    precio_unitario=Decimal(detalle['precio_unitario']),
                    descuento_porcentaje=Decimal(detalle.get('descuento_porcentaje', 0)),
                    especificaciones=detalle.get('especificaciones'),
                    requiere_proceso_especial=detalle.get('requiere_proceso_especial', False),
                    proceso_especial=detalle.get('proceso_especial')
                )
            
            # Recalcular totales
            pedido.calcular_totales()
            
            messages.success(request, f'Pedido {nuevo_numero} creado exitosamente.')
            return redirect('gestion:pedido_detail', id_pedido=pedido.id_pedido)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
    
    # Datos para el formulario
    clientes = Cliente.objects.select_related('tercero').filter(
        estado='activo'
    ).order_by('tercero__nombre')
    
    materiales = Materiales.objects.all().order_by('nombre')
    
    context = {
        'clientes': clientes,
        'materiales': materiales,
        'prioridad_choices': [
            ('baja', 'Baja'),
            ('normal', 'Normal'),
            ('alta', 'Alta'),
            ('urgente', 'Urgente'),
        ],
    }
    
    return render(request, 'pedidos/pedido_form.html', context)


@login_required
@transaction.atomic
def pedido_edit(request, id_pedido):
    """Editar pedido existente."""
    
    pedido = get_object_or_404(Pedido, pk=id_pedido)
    
    # Solo se pueden editar pedidos en borrador o confirmados
    if pedido.estado not in ['borrador', 'confirmado']:
        messages.error(request, 'Este pedido no puede ser editado en su estado actual.')
        return redirect('gestion:pedido_detail', id_pedido=pedido.id_pedido)
    
    if request.method == 'POST':
        try:
            # Actualizar pedido
            pedido.contacto_id = request.POST.get('contacto')
            pedido.fecha_requerida = request.POST.get('fecha_requerida')
            pedido.prioridad = request.POST.get('prioridad')
            pedido.orden_compra_cliente = request.POST.get('orden_compra_cliente') or None
            pedido.condiciones_pago = request.POST.get('condiciones_pago')
            pedido.direccion_entrega = request.POST.get('direccion_entrega')
            pedido.descuento_porcentaje = Decimal(request.POST.get('descuento_porcentaje', 0))
            pedido.observaciones = request.POST.get('observaciones') or None
            pedido.save()
            
            # Actualizar detalles
            # Primero eliminar los detalles existentes
            pedido.detalles.all().delete()
            
            # Crear nuevos detalles
            detalles_json = request.POST.get('detalles', '[]')
            detalles = json.loads(detalles_json)
            
            for detalle in detalles:
                DetallePedido.objects.create(
                    pedido=pedido,
                    material_id=detalle['material_id'],
                    descripcion_adicional=detalle.get('descripcion_adicional'),
                    cantidad=Decimal(detalle['cantidad']),
                    unidad_medida=detalle['unidad_medida'],
                    precio_unitario=Decimal(detalle['precio_unitario']),
                    descuento_porcentaje=Decimal(detalle.get('descuento_porcentaje', 0)),
                    especificaciones=detalle.get('especificaciones'),
                    requiere_proceso_especial=detalle.get('requiere_proceso_especial', False),
                    proceso_especial=detalle.get('proceso_especial')
                )
            
            # Recalcular totales
            pedido.calcular_totales()
            
            messages.success(request, 'Pedido actualizado exitosamente.')
            return redirect('gestion:pedido_detail', id_pedido=pedido.id_pedido)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el pedido: {str(e)}')
    
    # Datos para el formulario
    contactos = pedido.cliente.contactos.filter(activo=True).order_by('nombre')
    materiales = Materiales.objects.all().order_by('nombre')
    
    # Preparar detalles existentes para el formulario
    detalles_json = []
    for detalle in pedido.detalles.all():
        detalles_json.append({
            'material_id': str(detalle.material.id_material),
            'material_nombre': detalle.material.nombre,
            'descripcion_adicional': detalle.descripcion_adicional or '',
            'cantidad': str(detalle.cantidad),
            'unidad_medida': detalle.unidad_medida,
            'precio_unitario': str(detalle.precio_unitario),
            'descuento_porcentaje': str(detalle.descuento_porcentaje),
            'subtotal': str(detalle.subtotal),
            'especificaciones': detalle.especificaciones or {},
            'requiere_proceso_especial': detalle.requiere_proceso_especial,
            'proceso_especial': detalle.proceso_especial or ''
        })
    
    context = {
        'pedido': pedido,
        'contactos': contactos,
        'materiales': materiales,
        'prioridad_choices': [
            ('baja', 'Baja'),
            ('normal', 'Normal'),
            ('alta', 'Alta'),
            ('urgente', 'Urgente'),
        ],
        'detalles_json': json.dumps(detalles_json),
    }
    
    return render(request, 'pedidos/pedido_form.html', context)


@login_required
@transaction.atomic
def pedido_cambiar_estado(request, id_pedido):
    """Cambiar estado del pedido."""
    
    pedido = get_object_or_404(Pedido, pk=id_pedido)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        
        # Validar transición de estado
        transiciones_validas = {
            'borrador': ['confirmado', 'cancelado'],
            'confirmado': ['en_produccion', 'cancelado'],
            'en_produccion': ['parcial', 'completado', 'cancelado'],
            'parcial': ['completado', 'cancelado'],
        }
        
        if pedido.estado in transiciones_validas:
            if nuevo_estado in transiciones_validas[pedido.estado]:
                pedido.estado = nuevo_estado
                
                # Si se confirma el pedido, actualizar fecha
                if nuevo_estado == 'confirmado':
                    pedido.fecha_confirmacion = timezone.now()
                
                # Si se completa, actualizar fecha de entrega
                if nuevo_estado == 'completado':
                    pedido.fecha_entrega = timezone.now().date()
                
                pedido.save()
                
                messages.success(request, f'Estado del pedido actualizado a {pedido.get_estado_display()}.')
            else:
                messages.error(request, 'Transición de estado no válida.')
        else:
            messages.error(request, 'El pedido no puede cambiar de estado en su condición actual.')
    
    return redirect('gestion:pedido_detail', id_pedido=pedido.id_pedido)


@login_required
@transaction.atomic
def generar_orden_produccion(request, id_pedido):
    """Generar orden de producción desde un pedido."""
    
    pedido = get_object_or_404(Pedido, pk=id_pedido)
    
    # Validar que el pedido esté confirmado
    if pedido.estado != 'confirmado':
        messages.error(request, 'Solo se pueden generar órdenes de producción para pedidos confirmados.')
        return redirect('gestion:pedido_detail', id_pedido=pedido.id_pedido)
    
    if request.method == 'POST':
        try:
            # Generar número de orden
            ultima_orden = OrdenProduccion.objects.order_by('-numero_orden').first()
            if ultima_orden:
                ultimo_numero = int(ultima_orden.numero_orden.split('-')[1])
                nuevo_numero = f"OP-{str(ultimo_numero + 1).zfill(6)}"
            else:
                nuevo_numero = "OP-000001"
            
            # Crear orden de producción
            orden = OrdenProduccion.objects.create(
                numero_orden=nuevo_numero,
                pedido=pedido,
                fecha_programada_inicio=request.POST.get('fecha_inicio'),
                fecha_programada_fin=request.POST.get('fecha_fin'),
                estado='programada',
                prioridad=pedido.prioridad,
                observaciones=request.POST.get('observaciones') or None,
                instrucciones_especiales=request.POST.get('instrucciones') or None,
                usuario_creacion=request.user,
                supervisor_asignado_id=request.POST.get('supervisor') or None
            )
            
            # Crear detalles de la orden basados en los detalles del pedido
            for detalle_pedido in pedido.detalles.all():
                # Determinar secuencia de procesos según el material
                tipo_material = detalle_pedido.material.tipo
                secuencia_procesos = []
                
                if tipo_material == 'Reciclado':
                    secuencia_procesos = ['molido', 'lavado', 'peletizado']
                elif tipo_material == 'Virgen':
                    secuencia_procesos = ['peletizado']
                elif tipo_material == 'Molido':
                    secuencia_procesos = ['lavado', 'peletizado']
                
                # Si requiere proceso especial, agregar inyección
                if detalle_pedido.requiere_proceso_especial:
                    secuencia_procesos.append('inyeccion')
                
                DetalleOrdenProduccion.objects.create(
                    orden=orden,
                    detalle_pedido=detalle_pedido,
                    material=detalle_pedido.material,
                    cantidad_producir=detalle_pedido.cantidad,
                    unidad_medida=detalle_pedido.unidad_medida,
                    secuencia_procesos=secuencia_procesos,
                    tiempo_estimado_total=len(secuencia_procesos) * 120,  # 2 horas por proceso
                    estado='pendiente'
                )
            
            # Cambiar estado del pedido a en_produccion
            pedido.estado = 'en_produccion'
            pedido.save()
            
            messages.success(request, f'Orden de producción {nuevo_numero} generada exitosamente.')
            return redirect('gestion:orden_detail', id_orden=orden.id_orden)
            
        except Exception as e:
            messages.error(request, f'Error al generar la orden de producción: {str(e)}')
    
    # Datos para el formulario
    supervisores = User.objects.filter(
        is_active=True,
        groups__name__in=['Supervisores', 'Administradores']
    ).order_by('first_name', 'last_name')
    
    # Fecha sugerida de inicio (mañana)
    fecha_inicio_sugerida = (timezone.now() + timedelta(days=1)).date()
    
    # Calcular tiempo estimado basado en los detalles
    tiempo_estimado_dias = 0
    for detalle in pedido.detalles.all():
        # Estimar 1 día por cada 1000 kg
        dias = int(detalle.cantidad / 1000) + 1
        tiempo_estimado_dias = max(tiempo_estimado_dias, dias)
    
    fecha_fin_sugerida = fecha_inicio_sugerida + timedelta(days=tiempo_estimado_dias)
    
    context = {
        'pedido': pedido,
        'supervisores': supervisores,
        'fecha_inicio_sugerida': fecha_inicio_sugerida,
        'fecha_fin_sugerida': fecha_fin_sugerida,
    }
    
    return render(request, 'pedidos/generar_orden_produccion.html', context)


@login_required
def get_materiales_info(request):
    """API endpoint para obtener información de materiales."""
    
    material_ids = request.GET.getlist('ids[]')
    
    if not material_ids:
        return JsonResponse({'materiales': []})
    
    materiales = Materiales.objects.filter(
        id_material__in=material_ids
    ).values('id_material', 'nombre', 'tipo', 'descripcion')
    
    materiales_list = []
    for material in materiales:
        # Precio sugerido según tipo
        if material['tipo'] == 'Virgen':
            precio_sugerido = 5000
        elif material['tipo'] == 'Reciclado':
            precio_sugerido = 3000
        else:
            precio_sugerido = 2000
        
        materiales_list.append({
            'id': str(material['id_material']),
            'nombre': material['nombre'],
            'tipo': material['tipo'],
            'descripcion': material['descripcion'] or '',
            'precio_sugerido': precio_sugerido,
            'unidad_medida': 'KG'
        })
    
    return JsonResponse({'materiales': materiales_list})