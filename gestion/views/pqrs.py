from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ..models import (
    PQRS, SeguimientoPQRS, Cliente, Contacto, Oportunidad, 
    Pedido, User
)


@login_required
def pqrs_dashboard(request):
    """Dashboard principal de PQRS con KPIs y métricas."""
    
    # KPIs principales
    total_pqrs = PQRS.objects.count()
    pqrs_abiertas = PQRS.objects.exclude(estado__in=['solucionada', 'cerrada']).count()
    pqrs_vencidas = PQRS.objects.filter(
        fecha_vencimiento__lt=timezone.now(),
        estado__in=['recibida', 'en_proceso', 'escalada']
    ).count()
    
    # PQRS por tipo
    pqrs_por_tipo = PQRS.objects.values('tipo').annotate(
        count=Count('id_pqrs')
    ).order_by('tipo')
    
    # PQRS por estado
    pqrs_por_estado = PQRS.objects.values('estado').annotate(
        count=Count('id_pqrs')
    ).order_by('estado')
    
    # PQRS por prioridad
    pqrs_por_prioridad = PQRS.objects.values('prioridad').annotate(
        count=Count('id_pqrs')
    ).order_by('prioridad')
    
    # Métricas de tiempo
    pqrs_resueltas = PQRS.objects.filter(estado='solucionada')
    if pqrs_resueltas.exists():
        tiempo_promedio_respuesta = pqrs_resueltas.aggregate(
            promedio=Avg('tiempo_respuesta')
        )['promedio']
        tiempo_promedio_solucion = pqrs_resueltas.aggregate(
            promedio=Avg('tiempo_solucion')
        )['promedio']
    else:
        tiempo_promedio_respuesta = None
        tiempo_promedio_solucion = None
    
    # PQRS urgentes (críticas o próximas a vencer)
    pqrs_urgentes = PQRS.objects.filter(
        Q(prioridad='critica') | 
        Q(fecha_vencimiento__lte=timezone.now() + timedelta(hours=24)),
        estado__in=['recibida', 'en_proceso']
    ).select_related('cliente__tercero', 'usuario_asignado').order_by('fecha_vencimiento')[:10]
    
    # PQRS recientes
    pqrs_recientes = PQRS.objects.select_related(
        'cliente__tercero', 'usuario_asignado'
    ).order_by('-fecha_creacion')[:10]
    
    # Satisfacción del cliente
    satisfaccion_promedio = PQRS.objects.filter(
        satisfaccion_cliente__isnull=False
    ).aggregate(promedio=Avg('satisfaccion_cliente'))['promedio']
    
    # Usuarios con más PQRS asignadas
    usuarios_pqrs = User.objects.annotate(
        pqrs_activas=Count('pqrs_asignadas', filter=Q(pqrs_asignadas__estado__in=['recibida', 'en_proceso']))
    ).filter(pqrs_activas__gt=0).order_by('-pqrs_activas')[:5]
    
    # Cumplimiento de SLA
    total_con_sla = PQRS.objects.filter(estado__in=['solucionada', 'cerrada']).count()
    cumplimiento_sla = 0
    if total_con_sla > 0:
        pqrs_cumplidas = sum(1 for pqrs in PQRS.objects.filter(estado__in=['solucionada', 'cerrada']) if pqrs.cumple_sla)
        cumplimiento_sla = (pqrs_cumplidas / total_con_sla) * 100
    
    context = {
        'total_pqrs': total_pqrs,
        'pqrs_abiertas': pqrs_abiertas,
        'pqrs_vencidas': pqrs_vencidas,
        'pqrs_por_tipo': pqrs_por_tipo,
        'pqrs_por_estado': pqrs_por_estado,
        'pqrs_por_prioridad': pqrs_por_prioridad,
        'tiempo_promedio_respuesta': tiempo_promedio_respuesta,
        'tiempo_promedio_solucion': tiempo_promedio_solucion,
        'pqrs_urgentes': pqrs_urgentes,
        'pqrs_recientes': pqrs_recientes,
        'satisfaccion_promedio': satisfaccion_promedio,
        'usuarios_pqrs': usuarios_pqrs,
        'cumplimiento_sla': cumplimiento_sla,
    }
    
    return render(request, 'pqrs/dashboard.html', context)


@login_required
def pqrs_list(request):
    """Lista de PQRS con filtros y búsqueda."""
    
    # Obtener parámetros de filtro
    busqueda = request.GET.get('busqueda', '')
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    usuario_asignado = request.GET.get('usuario_asignado', '')
    canal = request.GET.get('canal', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    solo_vencidas = request.GET.get('solo_vencidas', '')
    
    # Construir query base
    pqrs = PQRS.objects.select_related(
        'cliente__tercero', 'usuario_asignado', 'usuario_creacion'
    ).all()
    
    # Aplicar filtros
    if busqueda:
        pqrs = pqrs.filter(
            Q(numero_pqrs__icontains=busqueda) |
            Q(asunto__icontains=busqueda) |
            Q(nombre_contacto__icontains=busqueda) |
            Q(email_contacto__icontains=busqueda) |
            Q(descripcion__icontains=busqueda)
        )
    
    if tipo:
        pqrs = pqrs.filter(tipo=tipo)
    
    if estado:
        pqrs = pqrs.filter(estado=estado)
    
    if prioridad:
        pqrs = pqrs.filter(prioridad=prioridad)
    
    if usuario_asignado:
        pqrs = pqrs.filter(usuario_asignado_id=usuario_asignado)
    
    if canal:
        pqrs = pqrs.filter(canal_recepcion=canal)
    
    if fecha_desde:
        pqrs = pqrs.filter(fecha_creacion__date__gte=fecha_desde)
    
    if fecha_hasta:
        pqrs = pqrs.filter(fecha_creacion__date__lte=fecha_hasta)
    
    if solo_vencidas:
        pqrs = pqrs.filter(
            fecha_vencimiento__lt=timezone.now(),
            estado__in=['recibida', 'en_proceso', 'escalada']
        )
    
    # Ordenar
    pqrs = pqrs.order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(pqrs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener opciones para filtros
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'page_obj': page_obj,
        'busqueda': busqueda,
        'tipo': tipo,
        'estado': estado,
        'prioridad': prioridad,
        'usuario_asignado': usuario_asignado,
        'canal': canal,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'solo_vencidas': solo_vencidas,
        'usuarios': usuarios,
        'tipo_choices': PQRS.TIPO_CHOICES,
        'estado_choices': PQRS.ESTADO_CHOICES,
        'prioridad_choices': PQRS.PRIORIDAD_CHOICES,
        'canal_choices': PQRS.CANAL_CHOICES,
    }
    
    return render(request, 'pqrs/pqrs_list.html', context)


@login_required
def pqrs_detail(request, pqrs_id):
    """Vista detallada de una PQRS específica."""
    
    pqrs = get_object_or_404(PQRS.objects.select_related(
        'cliente__tercero', 'usuario_asignado', 'usuario_creacion',
        'pedido_relacionado', 'oportunidad_relacionada'
    ), id_pqrs=pqrs_id)
    
    # Obtener seguimientos
    seguimientos = pqrs.seguimientos.select_related('usuario').order_by('-fecha')
    
    # Verificar permisos
    puede_editar = (
        request.user == pqrs.usuario_asignado or
        request.user == pqrs.usuario_creacion or
        request.user.is_superuser
    )
    
    context = {
        'pqrs': pqrs,
        'seguimientos': seguimientos,
        'puede_editar': puede_editar,
    }
    
    return render(request, 'pqrs/pqrs_detail.html', context)


@login_required
def pqrs_create(request):
    """Vista para crear una nueva PQRS."""
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                tipo = request.POST.get('tipo')
                nombre_contacto = request.POST.get('nombre_contacto')
                email_contacto = request.POST.get('email_contacto')
                telefono_contacto = request.POST.get('telefono_contacto', '')
                asunto = request.POST.get('asunto')
                descripcion = request.POST.get('descripcion')
                canal_recepcion = request.POST.get('canal_recepcion')
                prioridad = request.POST.get('prioridad', 'media')
                usuario_asignado_id = request.POST.get('usuario_asignado')
                cliente_id = request.POST.get('cliente_id')
                pedido_id = request.POST.get('pedido_relacionado')
                oportunidad_id = request.POST.get('oportunidad_relacionada')
                
                # Validar campos requeridos
                if not all([tipo, nombre_contacto, email_contacto, asunto, descripcion, canal_recepcion]):
                    messages.error(request, 'Todos los campos obligatorios deben ser completados.')
                    return redirect('gestion:pqrs_create')
                
                # Obtener objetos relacionados
                usuario_asignado = get_object_or_404(User, id=usuario_asignado_id)
                cliente = None
                if cliente_id:
                    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
                
                pedido = None
                if pedido_id:
                    pedido = get_object_or_404(Pedido, id_pedido=pedido_id)
                
                oportunidad = None
                if oportunidad_id:
                    oportunidad = get_object_or_404(Oportunidad, id_oportunidad=oportunidad_id)
                
                # Crear la PQRS
                pqrs = PQRS.objects.create(
                    tipo=tipo,
                    nombre_contacto=nombre_contacto,
                    email_contacto=email_contacto,
                    telefono_contacto=telefono_contacto,
                    asunto=asunto,
                    descripcion=descripcion,
                    canal_recepcion=canal_recepcion,
                    prioridad=prioridad,
                    usuario_creacion=request.user,
                    usuario_asignado=usuario_asignado,
                    cliente=cliente,
                    pedido_relacionado=pedido,
                    oportunidad_relacionada=oportunidad,
                    fecha_asignacion=timezone.now()
                )
                
                # Crear seguimiento inicial
                SeguimientoPQRS.objects.create(
                    pqrs=pqrs,
                    tipo_seguimiento='cambio_estado',
                    descripcion=f"PQRS {pqrs.numero_pqrs} creada y asignada a {usuario_asignado.get_full_name()}",
                    usuario=request.user,
                    visible_cliente=False,
                    notificar_cliente=False,
                    estado_nuevo='recibida'
                )
                
                messages.success(request, f'PQRS {pqrs.numero_pqrs} creada exitosamente.')
                return redirect('gestion:pqrs_detail', pqrs_id=pqrs.id_pqrs)
                
        except Exception as e:
            messages.error(request, f'Error al crear la PQRS: {str(e)}')
    
    # Obtener datos para el formulario
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    clientes = Cliente.objects.select_related('tercero').filter(estado='activo').order_by('tercero__nombre')
    
    # Precargar datos desde parámetros GET
    cliente_id = request.GET.get('cliente_id')
    pedido_id = request.GET.get('pedido_id')
    oportunidad_id = request.GET.get('oportunidad_id')
    
    context = {
        'usuarios': usuarios,
        'clientes': clientes,
        'tipo_choices': PQRS.TIPO_CHOICES,
        'prioridad_choices': PQRS.PRIORIDAD_CHOICES,
        'canal_choices': PQRS.CANAL_CHOICES,
        'cliente_id': cliente_id,
        'pedido_id': pedido_id,
        'oportunidad_id': oportunidad_id,
    }
    
    return render(request, 'pqrs/pqrs_form.html', context)


@login_required
def pqrs_edit(request, pqrs_id):
    """Vista para editar una PQRS existente."""
    
    pqrs = get_object_or_404(PQRS, id_pqrs=pqrs_id)
    
    # Verificar permisos
    if not (request.user == pqrs.usuario_asignado or request.user == pqrs.usuario_creacion or request.user.is_superuser):
        messages.error(request, 'No tienes permisos para editar esta PQRS.')
        return redirect('gestion:pqrs_detail', pqrs_id=pqrs_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Guardar estado anterior
                estado_anterior = pqrs.estado
                
                # Actualizar campos
                pqrs.tipo = request.POST.get('tipo')
                pqrs.nombre_contacto = request.POST.get('nombre_contacto')
                pqrs.email_contacto = request.POST.get('email_contacto')
                pqrs.telefono_contacto = request.POST.get('telefono_contacto', '')
                pqrs.asunto = request.POST.get('asunto')
                pqrs.descripcion = request.POST.get('descripcion')
                pqrs.canal_recepcion = request.POST.get('canal_recepcion')
                pqrs.prioridad = request.POST.get('prioridad')
                pqrs.estado = request.POST.get('estado')
                pqrs.solucion = request.POST.get('solucion', '')
                
                # Actualizar usuario asignado
                usuario_asignado_id = request.POST.get('usuario_asignado')
                if usuario_asignado_id:
                    pqrs.usuario_asignado = get_object_or_404(User, id=usuario_asignado_id)
                
                # Actualizar entidades relacionadas
                cliente_id = request.POST.get('cliente_id')
                pqrs.cliente = get_object_or_404(Cliente, id_cliente=cliente_id) if cliente_id else None
                
                pedido_id = request.POST.get('pedido_relacionado')
                pqrs.pedido_relacionado = get_object_or_404(Pedido, id_pedido=pedido_id) if pedido_id else None
                
                oportunidad_id = request.POST.get('oportunidad_relacionada')
                pqrs.oportunidad_relacionada = get_object_or_404(Oportunidad, id_oportunidad=oportunidad_id) if oportunidad_id else None
                
                pqrs.save()
                
                # Crear seguimiento si cambió el estado
                if estado_anterior != pqrs.estado:
                    SeguimientoPQRS.objects.create(
                        pqrs=pqrs,
                        tipo_seguimiento='cambio_estado',
                        descripcion=f"Estado cambiado de {estado_anterior} a {pqrs.estado}",
                        usuario=request.user,
                        visible_cliente=True,
                        notificar_cliente=True,
                        estado_anterior=estado_anterior,
                        estado_nuevo=pqrs.estado
                    )
                
                messages.success(request, 'PQRS actualizada exitosamente.')
                return redirect('gestion:pqrs_detail', pqrs_id=pqrs.id_pqrs)
                
        except Exception as e:
            messages.error(request, f'Error al actualizar la PQRS: {str(e)}')
    
    # Obtener datos para el formulario
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    clientes = Cliente.objects.select_related('tercero').filter(estado='activo').order_by('tercero__nombre')
    pedidos = Pedido.objects.select_related('cliente__tercero').filter(estado='confirmado').order_by('-fecha_creacion')
    oportunidades = Oportunidad.objects.select_related('cliente__tercero').exclude(etapa__in=['ganada', 'perdida']).order_by('-fecha_creacion')
    
    context = {
        'pqrs': pqrs,
        'usuarios': usuarios,
        'clientes': clientes,
        'pedidos': pedidos,
        'oportunidades': oportunidades,
        'tipo_choices': PQRS.TIPO_CHOICES,
        'estado_choices': PQRS.ESTADO_CHOICES,
        'prioridad_choices': PQRS.PRIORIDAD_CHOICES,
        'canal_choices': PQRS.CANAL_CHOICES,
    }
    
    return render(request, 'pqrs/pqrs_form.html', context)


@login_required
def agregar_seguimiento(request, pqrs_id):
    """Vista para agregar un seguimiento a una PQRS."""
    
    if request.method == 'POST':
        pqrs = get_object_or_404(PQRS, id_pqrs=pqrs_id)
        
        # Verificar permisos
        if not (request.user == pqrs.usuario_asignado or request.user == pqrs.usuario_creacion or request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para agregar seguimientos.'})
        
        try:
            tipo_seguimiento = request.POST.get('tipo_seguimiento')
            descripcion = request.POST.get('descripcion')
            visible_cliente = request.POST.get('visible_cliente') == 'true'
            notificar_cliente = request.POST.get('notificar_cliente') == 'true'
            
            if not descripcion:
                return JsonResponse({'success': False, 'error': 'La descripción es requerida.'})
            
            SeguimientoPQRS.objects.create(
                pqrs=pqrs,
                tipo_seguimiento=tipo_seguimiento,
                descripcion=descripcion,
                usuario=request.user,
                visible_cliente=visible_cliente,
                notificar_cliente=notificar_cliente
            )
            
            return JsonResponse({'success': True, 'message': 'Seguimiento agregado exitosamente.'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido.'})


@login_required
def cambiar_estado_pqrs(request, pqrs_id):
    """Vista para cambiar el estado de una PQRS."""
    
    if request.method == 'POST':
        pqrs = get_object_or_404(PQRS, id_pqrs=pqrs_id)
        
        # Verificar permisos
        if not (request.user == pqrs.usuario_asignado or request.user == pqrs.usuario_creacion or request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para cambiar el estado.'})
        
        try:
            estado_anterior = pqrs.estado
            nuevo_estado = request.POST.get('estado')
            
            if nuevo_estado not in [choice[0] for choice in PQRS.ESTADO_CHOICES]:
                return JsonResponse({'success': False, 'error': 'Estado inválido.'})
            
            pqrs.estado = nuevo_estado
            pqrs.save()
            
            # Crear seguimiento
            SeguimientoPQRS.objects.create(
                pqrs=pqrs,
                tipo_seguimiento='cambio_estado',
                descripcion=f"Estado cambiado de {estado_anterior} a {nuevo_estado}",
                usuario=request.user,
                visible_cliente=True,
                notificar_cliente=True,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado
            )
            
            return JsonResponse({'success': True, 'message': 'Estado actualizado exitosamente.'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido.'})


@login_required
def mis_pqrs(request):
    """Vista para mostrar las PQRS asignadas al usuario actual."""
    
    # Obtener PQRS asignadas al usuario
    pqrs_asignadas = PQRS.objects.filter(
        usuario_asignado=request.user
    ).select_related('cliente__tercero').order_by('-fecha_creacion')
    
    # Aplicar filtros básicos
    estado = request.GET.get('estado', '')
    if estado:
        pqrs_asignadas = pqrs_asignadas.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(pqrs_asignadas, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas del usuario
    total_asignadas = pqrs_asignadas.count()
    pendientes = pqrs_asignadas.filter(estado='recibida').count()
    en_proceso = pqrs_asignadas.filter(estado='en_proceso').count()
    solucionadas = pqrs_asignadas.filter(estado='solucionada').count()
    vencidas = pqrs_asignadas.filter(
        fecha_vencimiento__lt=timezone.now(),
        estado__in=['recibida', 'en_proceso']
    ).count()
    
    context = {
        'page_obj': page_obj,
        'estado': estado,
        'estado_choices': PQRS.ESTADO_CHOICES,
        'total_asignadas': total_asignadas,
        'pendientes': pendientes,
        'en_proceso': en_proceso,
        'solucionadas': solucionadas,
        'vencidas': vencidas,
    }
    
    return render(request, 'pqrs/mis_pqrs.html', context)