from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, F, Case, When, IntegerField, Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
import json

from ..models import (
    Tarea, Subtarea, ComentarioTarea, PlantillaTarea,
    Cliente, Pedido, OrdenProduccion, Oportunidad, User
)


@login_required
def tareas_dashboard(request):
    """Dashboard principal de tareas."""
    
    # Estadísticas generales
    tareas_total = Tarea.objects.count()
    
    # Mis tareas
    mis_tareas = Tarea.objects.filter(asignado_a=request.user)
    mis_tareas_pendientes = mis_tareas.filter(estado__in=['pendiente', 'en_progreso']).count()
    mis_tareas_vencidas = mis_tareas.filter(estado='vencida').count()
    
    # Tareas por estado
    tareas_por_estado = Tarea.objects.values('estado').annotate(
        cantidad=Count('id_tarea')
    ).order_by('estado')
    
    # Tareas por módulo
    tareas_por_modulo = Tarea.objects.values('modulo_origen').annotate(
        cantidad=Count('id_tarea')
    ).order_by('modulo_origen')
    
    # Tareas urgentes y próximas a vencer
    tareas_urgentes = Tarea.objects.filter(
        Q(prioridad='urgente') | 
        Q(fecha_vencimiento__lte=timezone.now() + timedelta(days=2)),
        estado__in=['pendiente', 'en_progreso']
    ).select_related('asignado_a', 'cliente', 'pedido').order_by('fecha_vencimiento')[:10]
    
    # Tareas completadas hoy
    hoy = timezone.now().date()
    tareas_completadas_hoy = Tarea.objects.filter(
        fecha_completado__date=hoy,
        estado='completada'
    ).count()
    
    # Productividad del equipo (últimos 7 días)
    hace_7_dias = timezone.now() - timedelta(days=7)
    productividad_equipo = User.objects.filter(
        tareas_asignadas__fecha_completado__gte=hace_7_dias,
        tareas_asignadas__estado='completada'
    ).annotate(
        tareas_completadas=Count('tareas_asignadas')
    ).order_by('-tareas_completadas')[:5]
    
    # Mis tareas recientes
    mis_tareas_recientes = mis_tareas.filter(
        estado__in=['pendiente', 'en_progreso']
    ).order_by('-prioridad', 'fecha_vencimiento')[:10]
    
    context = {
        'tareas_total': tareas_total,
        'mis_tareas_pendientes': mis_tareas_pendientes,
        'mis_tareas_vencidas': mis_tareas_vencidas,
        'tareas_completadas_hoy': tareas_completadas_hoy,
        'tareas_por_estado': list(tareas_por_estado),
        'tareas_por_modulo': list(tareas_por_modulo),
        'tareas_urgentes': tareas_urgentes,
        'productividad_equipo': productividad_equipo,
        'mis_tareas_recientes': mis_tareas_recientes,
    }
    
    return render(request, 'tareas/dashboard.html', context)


@login_required
def mis_tareas(request):
    """Lista de tareas asignadas al usuario actual."""
    
    # Filtros
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    modulo = request.GET.get('modulo', '')
    busqueda = request.GET.get('busqueda', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Query base
    tareas = Tarea.objects.filter(
        Q(asignado_a=request.user) | Q(equipo=request.user)
    ).distinct().select_related(
        'asignado_a', 'creado_por', 'cliente', 'pedido', 'orden_produccion', 'oportunidad'
    )
    
    # Aplicar filtros
    if estado:
        tareas = tareas.filter(estado=estado)
    
    if prioridad:
        tareas = tareas.filter(prioridad=prioridad)
    
    if modulo:
        tareas = tareas.filter(modulo_origen=modulo)
    
    if busqueda:
        tareas = tareas.filter(
            Q(codigo__icontains=busqueda) |
            Q(titulo__icontains=busqueda) |
            Q(descripcion__icontains=busqueda)
        )
    
    if fecha_desde:
        tareas = tareas.filter(fecha_vencimiento__gte=fecha_desde)
    
    if fecha_hasta:
        tareas = tareas.filter(fecha_vencimiento__lte=fecha_hasta)
    
    # Ordenar
    tareas = tareas.order_by(
        Case(
            When(estado='vencida', then=0),
            When(prioridad='urgente', then=1),
            When(prioridad='alta', then=2),
            When(prioridad='media', then=3),
            When(prioridad='baja', then=4),
            default=5,
            output_field=IntegerField()
        ),
        'fecha_vencimiento'
    )
    
    # Paginar
    paginator = Paginator(tareas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estado_choices': Tarea.ESTADO_CHOICES,
        'prioridad_choices': Tarea.PRIORIDAD_CHOICES,
        'modulo_choices': Tarea.MODULO_CHOICES,
        'estado': estado,
        'prioridad': prioridad,
        'modulo': modulo,
        'busqueda': busqueda,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    
    return render(request, 'tareas/mis_tareas.html', context)


@login_required
def tareas_equipo(request):
    """Lista de todas las tareas del equipo/empresa."""
    
    # Verificar permisos
    if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
        messages.error(request, 'No tiene permisos para ver todas las tareas.')
        return redirect('gestion:tareas_dashboard')
    
    # Filtros
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    modulo = request.GET.get('modulo', '')
    asignado_a = request.GET.get('asignado_a', '')
    busqueda = request.GET.get('busqueda', '')
    
    # Query base
    tareas = Tarea.objects.select_related(
        'asignado_a', 'creado_por', 'cliente', 'pedido', 'orden_produccion', 'oportunidad'
    )
    
    # Aplicar filtros
    if estado:
        tareas = tareas.filter(estado=estado)
    
    if prioridad:
        tareas = tareas.filter(prioridad=prioridad)
    
    if modulo:
        tareas = tareas.filter(modulo_origen=modulo)
    
    if asignado_a:
        tareas = tareas.filter(asignado_a_id=asignado_a)
    
    if busqueda:
        tareas = tareas.filter(
            Q(codigo__icontains=busqueda) |
            Q(titulo__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(asignado_a__first_name__icontains=busqueda) |
            Q(asignado_a__last_name__icontains=busqueda)
        )
    
    # Ordenar
    tareas = tareas.order_by('-prioridad', 'fecha_vencimiento')
    
    # Paginar
    paginator = Paginator(tareas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'page_obj': page_obj,
        'usuarios': usuarios,
        'estado_choices': Tarea.ESTADO_CHOICES,
        'prioridad_choices': Tarea.PRIORIDAD_CHOICES,
        'modulo_choices': Tarea.MODULO_CHOICES,
        'estado': estado,
        'prioridad': prioridad,
        'modulo': modulo,
        'asignado_a': asignado_a,
        'busqueda': busqueda,
    }
    
    return render(request, 'tareas/tareas_equipo.html', context)


@login_required
def tarea_detail(request, id_tarea):
    """Detalle de una tarea específica."""
    
    tarea = get_object_or_404(Tarea, pk=id_tarea)
    
    # Verificar permisos
    if tarea.asignado_a != request.user and request.user not in tarea.equipo.all():
        if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
            messages.error(request, 'No tiene permisos para ver esta tarea.')
            return redirect('gestion:mis_tareas')
    
    # Obtener subtareas
    subtareas = tarea.subtareas.order_by('orden', 'titulo')
    
    # Obtener comentarios
    comentarios = tarea.comentarios.select_related('usuario').order_by('-fecha')
    if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
        comentarios = comentarios.filter(es_interno=False)
    
    # Obtener entidad relacionada
    entidad_relacionada = tarea.get_entidad_relacionada()
    
    context = {
        'tarea': tarea,
        'subtareas': subtareas,
        'comentarios': comentarios,
        'entidad_relacionada': entidad_relacionada,
        'puede_editar': tarea.asignado_a == request.user or request.user.groups.filter(
            name__in=['Supervisores', 'Administradores']
        ).exists(),
    }
    
    return render(request, 'tareas/tarea_detail.html', context)


@login_required
@transaction.atomic
def tarea_create(request):
    """Crear nueva tarea."""
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            tipo = request.POST.get('tipo')
            prioridad = request.POST.get('prioridad')
            modulo_origen = request.POST.get('modulo_origen')
            asignado_a_id = request.POST.get('asignado_a')
            fecha_vencimiento = request.POST.get('fecha_vencimiento')
            
            # Crear tarea
            tarea = Tarea.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                tipo=tipo,
                prioridad=prioridad,
                modulo_origen=modulo_origen,
                asignado_a_id=asignado_a_id,
                creado_por=request.user,
                fecha_vencimiento=fecha_vencimiento,
                enviar_recordatorio=request.POST.get('enviar_recordatorio') == 'on',
                dias_antes_recordatorio=int(request.POST.get('dias_antes_recordatorio', 1))
            )
            
            # Asignar a entidad relacionada si corresponde
            if modulo_origen == 'crm':
                cliente_id = request.POST.get('cliente_id')
                oportunidad_id = request.POST.get('oportunidad_id')
                if cliente_id:
                    tarea.cliente_id = cliente_id
                if oportunidad_id:
                    tarea.oportunidad_id = oportunidad_id
            elif modulo_origen == 'pedidos':
                pedido_id = request.POST.get('pedido_id')
                if pedido_id:
                    tarea.pedido_id = pedido_id
            elif modulo_origen == 'ordenes':
                orden_id = request.POST.get('orden_produccion_id')
                if orden_id:
                    tarea.orden_produccion_id = orden_id
            
            tarea.save()
            
            # Agregar miembros del equipo
            equipo_ids = request.POST.getlist('equipo')
            if equipo_ids:
                tarea.equipo.set(equipo_ids)
            
            # Crear subtareas
            subtareas_json = request.POST.get('subtareas', '[]')
            subtareas = json.loads(subtareas_json)
            
            for idx, subtarea_titulo in enumerate(subtareas):
                if subtarea_titulo.strip():
                    Subtarea.objects.create(
                        tarea_padre=tarea,
                        titulo=subtarea_titulo,
                        orden=idx + 1
                    )
            
            # Agregar etiquetas
            etiquetas = request.POST.get('etiquetas', '').split(',')
            tarea.etiquetas = [tag.strip() for tag in etiquetas if tag.strip()]
            tarea.save()
            
            messages.success(request, f'Tarea {tarea.codigo} creada exitosamente.')
            return redirect('gestion:tarea_detail', id_tarea=tarea.id_tarea)
            
        except Exception as e:
            messages.error(request, f'Error al crear la tarea: {str(e)}')
    
    # Datos para el formulario
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    # Obtener entidades según el contexto
    clientes = Cliente.objects.filter(estado='activo').select_related('tercero').order_by('tercero__nombre')
    pedidos = Pedido.objects.filter(estado__in=['confirmado', 'en_produccion']).order_by('-numero_pedido')[:50]
    ordenes = OrdenProduccion.objects.filter(estado__in=['programada', 'en_proceso']).order_by('-numero_orden')[:50]
    
    # Si viene de un módulo específico
    modulo_origen = request.GET.get('modulo')
    entidad_id = request.GET.get('entidad_id')
    
    context = {
        'usuarios': usuarios,
        'clientes': clientes,
        'pedidos': pedidos,
        'ordenes': ordenes,
        'tipo_choices': Tarea.TIPO_CHOICES,
        'prioridad_choices': Tarea.PRIORIDAD_CHOICES,
        'modulo_choices': Tarea.MODULO_CHOICES,
        'modulo_origen': modulo_origen,
        'entidad_id': entidad_id,
        'fecha_default': (timezone.now() + timedelta(days=7)).date(),
    }
    
    return render(request, 'tareas/tarea_form.html', context)


@login_required
@transaction.atomic
def tarea_edit(request, id_tarea):
    """Editar tarea existente."""
    
    tarea = get_object_or_404(Tarea, pk=id_tarea)
    
    # Verificar permisos
    if tarea.asignado_a != request.user:
        if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
            messages.error(request, 'No tiene permisos para editar esta tarea.')
            return redirect('gestion:tarea_detail', id_tarea=tarea.id_tarea)
    
    if request.method == 'POST':
        try:
            # Actualizar datos
            tarea.titulo = request.POST.get('titulo')
            tarea.descripcion = request.POST.get('descripcion')
            tarea.tipo = request.POST.get('tipo')
            tarea.prioridad = request.POST.get('prioridad')
            tarea.asignado_a_id = request.POST.get('asignado_a')
            tarea.fecha_vencimiento = request.POST.get('fecha_vencimiento')
            tarea.enviar_recordatorio = request.POST.get('enviar_recordatorio') == 'on'
            tarea.dias_antes_recordatorio = int(request.POST.get('dias_antes_recordatorio', 1))
            
            # Actualizar etiquetas
            etiquetas = request.POST.get('etiquetas', '').split(',')
            tarea.etiquetas = [tag.strip() for tag in etiquetas if tag.strip()]
            
            tarea.save()
            
            # Actualizar equipo
            equipo_ids = request.POST.getlist('equipo')
            tarea.equipo.set(equipo_ids)
            
            # Actualizar subtareas
            # Primero eliminar las existentes
            tarea.subtareas.all().delete()
            
            # Crear nuevas subtareas
            subtareas_json = request.POST.get('subtareas', '[]')
            subtareas = json.loads(subtareas_json)
            
            for idx, subtarea_data in enumerate(subtareas):
                if isinstance(subtarea_data, dict):
                    titulo = subtarea_data.get('titulo', '')
                    completada = subtarea_data.get('completada', False)
                else:
                    titulo = subtarea_data
                    completada = False
                
                if titulo.strip():
                    Subtarea.objects.create(
                        tarea_padre=tarea,
                        titulo=titulo,
                        orden=idx + 1,
                        completada=completada
                    )
            
            messages.success(request, 'Tarea actualizada exitosamente.')
            return redirect('gestion:tarea_detail', id_tarea=tarea.id_tarea)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la tarea: {str(e)}')
    
    # Datos para el formulario
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    # Preparar subtareas para el formulario
    subtareas_json = [
        {
            'titulo': st.titulo,
            'completada': st.completada
        } for st in tarea.subtareas.order_by('orden')
    ]
    
    context = {
        'tarea': tarea,
        'usuarios': usuarios,
        'tipo_choices': Tarea.TIPO_CHOICES,
        'prioridad_choices': Tarea.PRIORIDAD_CHOICES,
        'etiquetas_str': ', '.join(tarea.etiquetas) if tarea.etiquetas else '',
        'subtareas_json': json.dumps(subtareas_json),
        'equipo_ids': list(tarea.equipo.values_list('id', flat=True)),
    }
    
    return render(request, 'tareas/tarea_form.html', context)


@login_required
@require_POST
def cambiar_estado_tarea(request, id_tarea):
    """Cambiar estado de la tarea."""
    
    tarea = get_object_or_404(Tarea, pk=id_tarea)
    
    # Verificar permisos
    if tarea.asignado_a != request.user and request.user not in tarea.equipo.all():
        if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
            return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    nuevo_estado = request.POST.get('estado')
    
    # Validar transición de estado
    transiciones_validas = {
        'pendiente': ['en_progreso', 'cancelada'],
        'en_progreso': ['pausada', 'completada', 'cancelada'],
        'pausada': ['en_progreso', 'cancelada'],
        'vencida': ['en_progreso', 'completada', 'cancelada'],
    }
    
    if tarea.estado in transiciones_validas:
        if nuevo_estado in transiciones_validas[tarea.estado]:
            tarea.estado = nuevo_estado
            
            # Actualizar fechas según el estado
            if nuevo_estado == 'en_progreso' and not tarea.fecha_inicio:
                tarea.fecha_inicio = timezone.now()
            elif nuevo_estado == 'completada':
                tarea.fecha_completado = timezone.now()
                tarea.porcentaje_avance = 100
            
            tarea.save()
            
            # Registrar comentario automático
            ComentarioTarea.objects.create(
                tarea=tarea,
                usuario=request.user,
                comentario=f"Estado cambiado de {tarea.get_estado_display()} a {tarea.get_estado_display()}",
                es_interno=True
            )
            
            return JsonResponse({
                'success': True,
                'nuevo_estado': tarea.estado,
                'estado_display': tarea.get_estado_display()
            })
        else:
            return JsonResponse({'error': 'Transición de estado no válida'}, status=400)
    else:
        return JsonResponse({'error': 'La tarea no puede cambiar de estado'}, status=400)


@login_required
@require_POST
def toggle_subtarea(request, id_subtarea):
    """Marcar/desmarcar subtarea como completada."""
    
    subtarea = get_object_or_404(Subtarea, pk=id_subtarea)
    tarea = subtarea.tarea_padre
    
    # Verificar permisos
    if tarea.asignado_a != request.user and request.user not in tarea.equipo.all():
        if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
            return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    # Toggle estado
    subtarea.completada = not subtarea.completada
    if subtarea.completada:
        subtarea.fecha_completado = timezone.now()
        subtarea.completado_por = request.user
    else:
        subtarea.fecha_completado = None
        subtarea.completado_por = None
    
    subtarea.save()
    
    # Actualizar progreso de la tarea
    tarea.actualizar_progreso()
    
    return JsonResponse({
        'success': True,
        'completada': subtarea.completada,
        'progreso': tarea.porcentaje_avance
    })


@login_required
@require_POST
def agregar_comentario(request, id_tarea):
    """Agregar comentario a la tarea."""
    
    tarea = get_object_or_404(Tarea, pk=id_tarea)
    
    # Verificar permisos
    if tarea.asignado_a != request.user and request.user not in tarea.equipo.all():
        if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
            return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    comentario_texto = request.POST.get('comentario')
    es_interno = request.POST.get('es_interno') == 'true'
    
    if not comentario_texto:
        return JsonResponse({'error': 'El comentario no puede estar vacío'}, status=400)
    
    comentario = ComentarioTarea.objects.create(
        tarea=tarea,
        usuario=request.user,
        comentario=comentario_texto,
        es_interno=es_interno
    )
    
    return JsonResponse({
        'success': True,
        'comentario': {
            'id': str(comentario.id_comentario),
            'usuario': comentario.usuario.get_full_name() or comentario.usuario.username,
            'fecha': comentario.fecha.strftime('%d/%m/%Y %H:%M'),
            'texto': comentario.comentario,
            'es_interno': comentario.es_interno
        }
    })


@login_required
def calendario_tareas(request):
    """Vista de calendario de tareas."""
    
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
    
    # Obtener tareas del mes
    if request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
        tareas = Tarea.objects.filter(
            fecha_vencimiento__gte=fecha_inicio,
            fecha_vencimiento__lt=fecha_fin
        )
    else:
        tareas = Tarea.objects.filter(
            Q(asignado_a=request.user) | Q(equipo=request.user),
            fecha_vencimiento__gte=fecha_inicio,
            fecha_vencimiento__lt=fecha_fin
        ).distinct()
    
    tareas = tareas.select_related('asignado_a').order_by('fecha_vencimiento')
    
    # Agrupar por día
    calendario = {}
    for tarea in tareas:
        fecha = tarea.fecha_vencimiento.date()
        if fecha not in calendario:
            calendario[fecha] = []
        calendario[fecha].append(tarea)
    
    context = {
        'fecha_inicio': fecha_inicio,
        'calendario': calendario,
        'mes_anterior': (fecha_inicio - timedelta(days=1)).strftime('%Y-%m'),
        'mes_siguiente': fecha_fin.strftime('%Y-%m'),
    }
    
    return render(request, 'tareas/calendario.html', context)


@login_required
def plantillas_list(request):
    """Lista de plantillas de tareas."""
    
    # Solo supervisores y administradores
    if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
        messages.error(request, 'No tiene permisos para gestionar plantillas.')
        return redirect('gestion:tareas_dashboard')
    
    plantillas = PlantillaTarea.objects.all().order_by('modulo', 'nombre')
    
    context = {
        'plantillas': plantillas,
    }
    
    return render(request, 'tareas/plantillas_list.html', context)


@login_required
@transaction.atomic
def plantilla_create(request):
    """Crear nueva plantilla de tarea."""
    
    # Solo supervisores y administradores
    if not request.user.groups.filter(name__in=['Supervisores', 'Administradores']).exists():
        messages.error(request, 'No tiene permisos para crear plantillas.')
        return redirect('gestion:tareas_dashboard')
    
    if request.method == 'POST':
        try:
            subtareas = json.loads(request.POST.get('subtareas', '[]'))
            
            plantilla = PlantillaTarea.objects.create(
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion'),
                modulo=request.POST.get('modulo'),
                titulo_template=request.POST.get('titulo_template'),
                descripcion_template=request.POST.get('descripcion_template'),
                tipo=request.POST.get('tipo'),
                prioridad_default=request.POST.get('prioridad_default'),
                dias_para_vencer=int(request.POST.get('dias_para_vencer', 7)),
                subtareas_template=subtareas,
                trigger=request.POST.get('trigger', ''),
                activa=request.POST.get('activa') == 'on'
            )
            
            messages.success(request, 'Plantilla creada exitosamente.')
            return redirect('gestion:plantillas_list')
            
        except Exception as e:
            messages.error(request, f'Error al crear la plantilla: {str(e)}')
    
    context = {
        'tipo_choices': Tarea.TIPO_CHOICES,
        'prioridad_choices': Tarea.PRIORIDAD_CHOICES,
        'modulo_choices': Tarea.MODULO_CHOICES,
        'trigger_choices': PlantillaTarea.TRIGGER_CHOICES,
    }
    
    return render(request, 'tareas/plantilla_form.html', context)