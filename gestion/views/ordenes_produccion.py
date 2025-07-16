from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count, F, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import uuid

from ..models import (
    OrdenProduccion, DetalleOrdenProduccion, PlanificacionProcesos,
    Pedido, Maquinas, User, ProduccionMolido, ProduccionLavado,
    ProduccionPeletizado, ProduccionInyeccion, ProduccionHomogeneizacion,
    Tarea
)


@login_required
def ordenes_dashboard(request):
    """Dashboard principal de órdenes de producción."""
    
    # Estadísticas generales
    ordenes_total = OrdenProduccion.objects.count()
    ordenes_activas = OrdenProduccion.objects.filter(
        estado__in=['programada', 'en_proceso']
    ).count()
    
    ordenes_completadas_mes = OrdenProduccion.objects.filter(
        fecha_real_fin__gte=timezone.now().replace(day=1),
        estado='completada'
    ).count()
    
    # Eficiencia promedio (órdenes completadas)
    eficiencia = OrdenProduccion.objects.filter(
        estado='completada',
        fecha_real_fin__isnull=False,
        fecha_programada_fin__isnull=False
    ).aggregate(
        eficiencia=Avg('porcentaje_avance')
    )['eficiencia'] or 0
    
    # Órdenes por estado
    ordenes_por_estado = list(OrdenProduccion.objects.values('estado').annotate(
        count=Count('id_orden')
    ).order_by('estado'))
    
    # Órdenes urgentes (alta prioridad o próximas a vencer)
    ordenes_urgentes = OrdenProduccion.objects.filter(
        Q(prioridad='urgente') | Q(prioridad='alta') |
        Q(fecha_programada_fin__lte=timezone.now() + timedelta(days=2)),
        estado__in=['programada', 'en_proceso']
    ).select_related('pedido__cliente__tercero').order_by('fecha_programada_fin')[:10]
    
    # Carga de trabajo por proceso
    carga_por_proceso = PlanificacionProcesos.objects.filter(
        estado__in=['programado', 'en_proceso']
    ).values('tipo_proceso').annotate(
        cantidad=Count('id_planificacion'),
        horas_estimadas=Sum('duracion_estimada')
    )
    
    # Últimas órdenes
    ultimas_ordenes = OrdenProduccion.objects.select_related(
        'pedido__cliente__tercero', 'supervisor_asignado'
    ).order_by('-fecha_creacion')[:10]
    
    context = {
        'ordenes_total': ordenes_total,
        'ordenes_activas': ordenes_activas,
        'ordenes_completadas_mes': ordenes_completadas_mes,
        'eficiencia': eficiencia,
        'ordenes_por_estado': ordenes_por_estado,
        'ordenes_urgentes': ordenes_urgentes,
        'carga_por_proceso': carga_por_proceso,
        'ultimas_ordenes': ultimas_ordenes,
    }
    
    return render(request, 'ordenes/dashboard.html', context)


@login_required
def ordenes_list(request):
    """Lista de órdenes de producción con filtros."""
    
    # Filtros
    busqueda = request.GET.get('busqueda', '')
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    supervisor = request.GET.get('supervisor', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Query base
    ordenes = OrdenProduccion.objects.select_related(
        'pedido__cliente__tercero', 'supervisor_asignado', 'usuario_creacion'
    )
    
    # Aplicar filtros
    if busqueda:
        ordenes = ordenes.filter(
            Q(numero_orden__icontains=busqueda) |
            Q(pedido__numero_pedido__icontains=busqueda) |
            Q(pedido__cliente__tercero__nombre__icontains=busqueda)
        )
    
    if estado:
        ordenes = ordenes.filter(estado=estado)
    
    if prioridad:
        ordenes = ordenes.filter(prioridad=prioridad)
    
    if supervisor:
        ordenes = ordenes.filter(supervisor_asignado_id=supervisor)
    
    if fecha_desde:
        ordenes = ordenes.filter(fecha_programada_inicio__gte=fecha_desde)
    
    if fecha_hasta:
        ordenes = ordenes.filter(fecha_programada_inicio__lte=fecha_hasta)
    
    # Ordenar y paginar
    ordenes = ordenes.order_by('-fecha_creacion')
    paginator = Paginator(ordenes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    supervisores = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'page_obj': page_obj,
        'supervisores': supervisores,
        'estado_choices': OrdenProduccion.ESTADO_CHOICES,
        'prioridad_choices': OrdenProduccion.PRIORIDAD_CHOICES,
        'busqueda': busqueda,
        'estado': estado,
        'prioridad': prioridad,
        'supervisor': supervisor,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    
    return render(request, 'ordenes/ordenes_list.html', context)


@login_required
def orden_detail(request, id_orden):
    """Detalle de una orden de producción."""
    
    orden = get_object_or_404(OrdenProduccion, pk=id_orden)
    
    # Obtener detalles con información adicional
    detalles = orden.detalles.select_related(
        'material', 'detalle_pedido'
    ).prefetch_related('planificaciones__maquina', 'planificaciones__operario')
    
    # Obtener tareas relacionadas con la orden
    tareas = orden.tareas.select_related(
        'asignado_a', 'creado_por'
    ).prefetch_related('subtareas', 'comentarios').order_by('-prioridad', 'fecha_vencimiento')
    
    # Calcular estadísticas
    total_planificado = detalles.aggregate(
        total=Sum('cantidad_producir')
    )['total'] or 0
    
    total_producido = detalles.aggregate(
        total=Sum('cantidad_producida')
    )['total'] or 0
    
    # Planificaciones agrupadas por proceso
    planificaciones_por_proceso = {}
    for detalle in detalles:
        for planificacion in detalle.planificaciones.all():
            tipo = planificacion.get_tipo_proceso_display()
            if tipo not in planificaciones_por_proceso:
                planificaciones_por_proceso[tipo] = []
            planificaciones_por_proceso[tipo].append(planificacion)
    
    context = {
        'orden': orden,
        'detalles': detalles,
        'tareas': tareas,
        'total_planificado': total_planificado,
        'total_producido': total_producido,
        'planificaciones_por_proceso': planificaciones_por_proceso,
    }
    
    return render(request, 'ordenes/orden_detail.html', context)


@login_required
@transaction.atomic
def planificar_procesos(request, id_orden):
    """Planificar los procesos de producción para una orden."""
    
    orden = get_object_or_404(OrdenProduccion, pk=id_orden)
    
    # Verificar que la orden esté en estado programada
    if orden.estado != 'programada':
        messages.error(request, 'Solo se pueden planificar órdenes en estado programada.')
        return redirect('gestion:orden_detail', id_orden=orden.id_orden)
    
    if request.method == 'POST':
        try:
            # Procesar la planificación
            planificaciones_data = json.loads(request.POST.get('planificaciones', '[]'))
            
            for plan_data in planificaciones_data:
                detalle = DetalleOrdenProduccion.objects.get(
                    id_detalle=plan_data['detalle_id'],
                    orden=orden
                )
                
                # Crear planificaciones para cada proceso en la secuencia
                for i, proceso in enumerate(detalle.secuencia_procesos):
                    # Generar orden de trabajo única
                    orden_trabajo = f"OT-{orden.numero_orden}-{proceso.upper()[:3]}-{str(i+1).zfill(2)}"
                    
                    # Obtener datos del proceso
                    proceso_data = plan_data['procesos'].get(proceso, {})
                    
                    if not proceso_data.get('maquina_id') or not proceso_data.get('operario_id'):
                        continue
                    
                    # Calcular fecha programada
                    fecha_programada = datetime.strptime(
                        proceso_data['fecha_programada'], 
                        '%Y-%m-%dT%H:%M'
                    )
                    
                    PlanificacionProcesos.objects.create(
                        detalle_orden=detalle,
                        tipo_proceso=proceso,
                        secuencia=i + 1,
                        maquina_id=proceso_data['maquina_id'],
                        operario_id=proceso_data['operario_id'],
                        fecha_programada=fecha_programada,
                        duracion_estimada=proceso_data.get('duracion_estimada', 120),
                        orden_trabajo=orden_trabajo,
                        estado='programado'
                    )
            
            # Actualizar estado de la orden
            orden.estado = 'en_proceso'
            orden.fecha_real_inicio = timezone.now()
            orden.save()
            
            messages.success(request, 'Procesos planificados exitosamente.')
            return redirect('gestion:orden_detail', id_orden=orden.id_orden)
            
        except Exception as e:
            messages.error(request, f'Error al planificar procesos: {str(e)}')
    
    # Obtener recursos disponibles
    maquinas_por_tipo = {}
    for tipo, _ in PlanificacionProcesos.TIPO_PROCESO_CHOICES:
        maquinas_por_tipo[tipo] = Maquinas.objects.filter(
            tipo_proceso=tipo,
            estado='Operativa'
        )
    
    operarios = User.objects.filter(
        is_active=True,
        groups__name='Operarios'
    ).order_by('first_name', 'last_name')
    
    # Preparar datos de detalles con secuencias
    detalles_data = []
    for detalle in orden.detalles.all():
        detalle_info = {
            'id': str(detalle.id_detalle),
            'material': detalle.material.nombre,
            'cantidad': float(detalle.cantidad_producir),
            'secuencia_procesos': detalle.secuencia_procesos,
            'tiempo_estimado': detalle.tiempo_estimado_total
        }
        detalles_data.append(detalle_info)
    
    context = {
        'orden': orden,
        'maquinas_por_tipo': maquinas_por_tipo,
        'operarios': operarios,
        'detalles_data': json.dumps(detalles_data),
        'tipos_proceso': dict(PlanificacionProcesos.TIPO_PROCESO_CHOICES),
    }
    
    return render(request, 'ordenes/planificar_procesos.html', context)


@login_required
@transaction.atomic
def actualizar_progreso_proceso(request, id_planificacion):
    """Actualizar el progreso de un proceso específico."""
    
    planificacion = get_object_or_404(PlanificacionProcesos, pk=id_planificacion)
    
    if request.method == 'POST':
        try:
            accion = request.POST.get('accion')
            
            if accion == 'iniciar':
                planificacion.estado = 'en_proceso'
                planificacion.fecha_inicio_real = timezone.now()
                planificacion.save()
                
                # Actualizar estado del detalle si es el primer proceso
                if planificacion.secuencia == 1:
                    planificacion.detalle_orden.estado = 'en_proceso'
                    planificacion.detalle_orden.fecha_inicio = timezone.now()
                    planificacion.detalle_orden.save()
                
                messages.success(request, f'Proceso {planificacion.get_tipo_proceso_display()} iniciado.')
                
            elif accion == 'completar':
                cantidad_procesada = Decimal(request.POST.get('cantidad_procesada', 0))
                
                planificacion.estado = 'completado'
                planificacion.fecha_fin_real = timezone.now()
                planificacion.cantidad_procesada = cantidad_procesada
                planificacion.save()
                
                # Crear registro en el módulo de producción correspondiente
                crear_registro_produccion(planificacion, cantidad_procesada)
                
                # Verificar si es el último proceso del detalle
                ultimo_proceso = planificacion.detalle_orden.planificaciones.order_by('-secuencia').first()
                if planificacion == ultimo_proceso:
                    planificacion.detalle_orden.estado = 'completado'
                    planificacion.detalle_orden.fecha_fin = timezone.now()
                    planificacion.detalle_orden.cantidad_producida = cantidad_procesada
                    planificacion.detalle_orden.save()
                    
                    # Actualizar avance de la orden
                    planificacion.detalle_orden.orden.actualizar_avance()
                
                messages.success(request, f'Proceso {planificacion.get_tipo_proceso_display()} completado.')
                
            elif accion == 'pausar':
                planificacion.estado = 'pausado'
                planificacion.save()
                messages.info(request, f'Proceso {planificacion.get_tipo_proceso_display()} pausado.')
                
            return redirect('gestion:orden_detail', id_orden=planificacion.detalle_orden.orden.id_orden)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar proceso: {str(e)}')
    
    return redirect('gestion:orden_detail', id_orden=planificacion.detalle_orden.orden.id_orden)


def crear_registro_produccion(planificacion, cantidad_procesada):
    """Crear registro en el módulo de producción correspondiente."""
    
    # Mapeo de tipo de proceso a modelo de producción
    modelos_produccion = {
        'molido': ProduccionMolido,
        'lavado': ProduccionLavado,
        'peletizado': ProduccionPeletizado,
        'inyeccion': ProduccionInyeccion,
        'homogeneizacion': ProduccionHomogeneizacion,
    }
    
    modelo = modelos_produccion.get(planificacion.tipo_proceso)
    if not modelo:
        return
    
    # Crear registro con datos básicos
    datos_base = {
        'orden_trabajo': planificacion.orden_trabajo,
        'fecha': timezone.now().date(),
        'turno': 'Mañana' if timezone.now().hour < 14 else 'Tarde',
        'maquina': planificacion.maquina,
        'operario': planificacion.operario,
        'material_entrada': planificacion.detalle_orden.material,
        'cantidad_entrada': cantidad_procesada,
        'cantidad_salida': cantidad_procesada * Decimal('0.95'),  # 5% de merma estimada
        'observaciones': f'Generado desde OP: {planificacion.detalle_orden.orden.numero_orden}',
    }
    
    # Ajustar campos según el tipo de proceso
    if planificacion.tipo_proceso == 'molido':
        datos_base['tipo_molido'] = 'Grueso'
    elif planificacion.tipo_proceso == 'lavado':
        datos_base['temperatura_agua'] = 60
        datos_base['tiempo_lavado'] = 30
        datos_base['detergente_usado'] = 5
    elif planificacion.tipo_proceso == 'peletizado':
        datos_base['temperatura_fusion'] = 180
        datos_base['velocidad_extrusion'] = 50
    elif planificacion.tipo_proceso == 'inyeccion':
        datos_base['producto_fabricado'] = 'Producto estándar'
        datos_base['molde_usado'] = 'Molde genérico'
        datos_base['ciclos_realizados'] = 100
        datos_base['piezas_buenas'] = 95
        datos_base['piezas_malas'] = 5
    
    # Crear el registro
    registro = modelo.objects.create(**datos_base)
    
    # Guardar referencia en la planificación
    planificacion.produccion_id = str(registro.id_produccion)
    planificacion.save()


@login_required
def calendario_produccion(request):
    """Vista de calendario de producción."""
    
    # Obtener mes actual o el solicitado
    mes = request.GET.get('mes')
    if mes:
        fecha_inicio = datetime.strptime(mes, '%Y-%m').date()
    else:
        fecha_inicio = timezone.now().date().replace(day=1)
    
    # Calcular fecha fin del mes
    if fecha_inicio.month == 12:
        fecha_fin = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1)
    else:
        fecha_fin = fecha_inicio.replace(month=fecha_inicio.month + 1)
    
    # Obtener planificaciones del mes
    planificaciones = PlanificacionProcesos.objects.filter(
        fecha_programada__gte=fecha_inicio,
        fecha_programada__lt=fecha_fin
    ).select_related(
        'detalle_orden__orden__pedido__cliente__tercero',
        'maquina',
        'operario'
    ).order_by('fecha_programada')
    
    # Agrupar por día y máquina
    calendario = {}
    for plan in planificaciones:
        fecha = plan.fecha_programada.date()
        if fecha not in calendario:
            calendario[fecha] = {}
        
        maquina = plan.maquina.nombre
        if maquina not in calendario[fecha]:
            calendario[fecha][maquina] = []
        
        calendario[fecha][maquina].append(plan)
    
    context = {
        'fecha_inicio': fecha_inicio,
        'calendario': calendario,
        'mes_anterior': (fecha_inicio - timedelta(days=1)).strftime('%Y-%m'),
        'mes_siguiente': fecha_fin.strftime('%Y-%m'),
    }
    
    return render(request, 'ordenes/calendario_produccion.html', context)


@login_required
def cambiar_estado_orden(request, id_orden):
    """Cambiar estado de la orden de producción."""
    
    orden = get_object_or_404(OrdenProduccion, pk=id_orden)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        
        # Validar transición de estado
        transiciones_validas = {
            'programada': ['en_proceso', 'cancelada'],
            'en_proceso': ['pausada', 'completada', 'cancelada'],
            'pausada': ['en_proceso', 'cancelada'],
        }
        
        if orden.estado in transiciones_validas:
            if nuevo_estado in transiciones_validas[orden.estado]:
                orden.estado = nuevo_estado
                
                # Actualizar fechas según el estado
                if nuevo_estado == 'en_proceso' and not orden.fecha_real_inicio:
                    orden.fecha_real_inicio = timezone.now()
                elif nuevo_estado == 'completada':
                    orden.fecha_real_fin = timezone.now()
                    orden.porcentaje_avance = 100
                    
                    # Actualizar estado del pedido
                    pedido = orden.pedido
                    # Verificar si todas las órdenes del pedido están completadas
                    ordenes_pendientes = pedido.ordenes_produccion.exclude(
                        estado='completada'
                    ).exclude(pk=orden.pk).exists()
                    
                    if not ordenes_pendientes:
                        pedido.estado = 'completado'
                        pedido.fecha_entrega = timezone.now().date()
                        pedido.save()
                
                orden.save()
                
                messages.success(request, f'Estado de la orden actualizado a {orden.get_estado_display()}.')
            else:
                messages.error(request, 'Transición de estado no válida.')
        else:
            messages.error(request, 'La orden no puede cambiar de estado en su condición actual.')
    
    return redirect('gestion:orden_detail', id_orden=orden.id_orden)