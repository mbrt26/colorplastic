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
    Cliente, Contacto, Oportunidad, InteraccionCliente, 
    Terceros, User, Tarea
)


@login_required
def crm_dashboard(request):
    """Dashboard principal del CRM con KPIs y métricas comerciales."""
    
    # KPIs principales
    total_clientes = Cliente.objects.count()
    clientes_activos = Cliente.objects.filter(estado='activo').count()
    total_oportunidades = Oportunidad.objects.count()
    oportunidades_abiertas = Oportunidad.objects.exclude(etapa__in=['ganada', 'perdida']).count()
    
    # Pipeline value
    pipeline_total = Oportunidad.objects.exclude(etapa__in=['ganada', 'perdida']).aggregate(
        total=Sum('valor_estimado'))['total'] or 0
    pipeline_ponderado = sum([op.valor_ponderado for op in 
                             Oportunidad.objects.exclude(etapa__in=['ganada', 'perdida'])])
    
    # Oportunidades por etapa
    oportunidades_por_etapa = Oportunidad.objects.exclude(etapa__in=['ganada', 'perdida']).values(
        'etapa').annotate(count=Count('id_oportunidad'), valor=Sum('valor_estimado'))
    
    # Calcular el promedio para cada etapa
    for etapa in oportunidades_por_etapa:
        if etapa['count'] > 0:
            etapa['promedio'] = etapa['valor'] / etapa['count']
        else:
            etapa['promedio'] = 0
    
    # Actividades recientes
    interacciones_recientes = InteraccionCliente.objects.select_related(
        'cliente__tercero', 'contacto', 'usuario'
    ).order_by('-fecha_interaccion')[:10]
    
    # Próximas actividades
    proximas_actividades = InteraccionCliente.objects.filter(
        requiere_seguimiento=True,
        fecha_seguimiento__gte=timezone.now().date()
    ).select_related('cliente__tercero', 'contacto').order_by('fecha_seguimiento')[:10]
    
    # Oportunidades próximas a cerrar
    proximas_a_cerrar = Oportunidad.objects.filter(
        fecha_cierre_estimada__lte=timezone.now().date() + timedelta(days=30),
        etapa__in=['propuesta', 'negociacion', 'cierre']
    ).select_related('cliente__tercero', 'contacto').order_by('fecha_cierre_estimada')[:10]
    
    # Clientes nuevos del mes
    inicio_mes = timezone.now().replace(day=1)
    clientes_nuevos = Cliente.objects.filter(fecha_registro__gte=inicio_mes).count()
    
    # Calcular tasa de conversión
    if total_oportunidades > 0:
        tasa_conversion = (oportunidades_abiertas * 100) / total_oportunidades
    else:
        tasa_conversion = 0
    
    context = {
        'total_clientes': total_clientes,
        'clientes_activos': clientes_activos,
        'total_oportunidades': total_oportunidades,
        'oportunidades_abiertas': oportunidades_abiertas,
        'pipeline_total': pipeline_total,
        'pipeline_ponderado': pipeline_ponderado,
        'oportunidades_por_etapa': oportunidades_por_etapa,
        'interacciones_recientes': interacciones_recientes,
        'proximas_actividades': proximas_actividades,
        'proximas_a_cerrar': proximas_a_cerrar,
        'clientes_nuevos': clientes_nuevos,
        'tasa_conversion': tasa_conversion,
    }
    
    return render(request, 'crm/dashboard.html', context)


@login_required
def clientes_list(request):
    """Lista de clientes con filtros y búsqueda."""
    
    # Obtener parámetros de filtro
    busqueda = request.GET.get('busqueda', '')
    tipo_cliente = request.GET.get('tipo_cliente', '')
    estado = request.GET.get('estado', '')
    usuario_asignado = request.GET.get('usuario_asignado', '')
    
    # Construir query base
    clientes = Cliente.objects.select_related('tercero', 'usuario_asignado')
    
    # Aplicar filtros
    if busqueda:
        clientes = clientes.filter(
            Q(tercero__nombre__icontains=busqueda) |
            Q(tercero__identificacion__icontains=busqueda) |
            Q(industria__icontains=busqueda)
        )
    
    if tipo_cliente:
        clientes = clientes.filter(tipo_cliente=tipo_cliente)
    
    if estado:
        clientes = clientes.filter(estado=estado)
    
    if usuario_asignado:
        clientes = clientes.filter(usuario_asignado_id=usuario_asignado)
    
    # Ordenar y paginar
    clientes = clientes.order_by('-fecha_registro')
    paginator = Paginator(clientes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'page_obj': page_obj,
        'usuarios': usuarios,
        'tipo_cliente_choices': Cliente.TIPO_CLIENTE_CHOICES,
        'estado_choices': Cliente.ESTADO_CHOICES,
        'busqueda': busqueda,
        'tipo_cliente': tipo_cliente,
        'estado': estado,
        'usuario_asignado': usuario_asignado,
    }
    
    return render(request, 'crm/clientes_list.html', context)


@login_required
def cliente_detail(request, id_cliente):
    """Detalle de un cliente específico."""
    
    cliente = get_object_or_404(Cliente, pk=id_cliente)
    
    # Obtener datos relacionados
    contactos = cliente.contactos.filter(activo=True).order_by('nombre')
    oportunidades = cliente.oportunidades.all().order_by('-fecha_creacion')
    interacciones = cliente.interacciones.select_related('contacto', 'usuario').order_by('-fecha_interaccion')
    tareas = cliente.tareas.select_related('asignado_a', 'creado_por').order_by('-fecha_creacion')
    
    # Estadísticas del cliente
    total_oportunidades = oportunidades.count()
    oportunidades_ganadas = oportunidades.filter(etapa='ganada').count()
    valor_total_ganado = oportunidades.filter(etapa='ganada').aggregate(
        total=Sum('valor_estimado'))['total'] or 0
    pipeline_activo = oportunidades.exclude(etapa__in=['ganada', 'perdida']).aggregate(
        total=Sum('valor_estimado'))['total'] or 0
    
    # Estadísticas de tareas
    tareas_pendientes = tareas.filter(estado='pendiente').count()
    tareas_en_progreso = tareas.filter(estado='en_progreso').count()
    tareas_completadas = tareas.filter(estado='completada').count()
    
    context = {
        'cliente': cliente,
        'contactos': contactos,
        'oportunidades': oportunidades,
        'interacciones': interacciones,
        'tareas': tareas,
        'total_oportunidades': total_oportunidades,
        'oportunidades_ganadas': oportunidades_ganadas,
        'valor_total_ganado': valor_total_ganado,
        'pipeline_activo': pipeline_activo,
        'tareas_pendientes': tareas_pendientes,
        'tareas_en_progreso': tareas_en_progreso,
        'tareas_completadas': tareas_completadas,
    }
    
    return render(request, 'crm/cliente_detail.html', context)


@login_required
@transaction.atomic
def cliente_create(request):
    """Crear nuevo cliente."""
    
    if request.method == 'POST':
        try:
            # Crear tercero primero
            tercero = Terceros.objects.create(
                nombre=request.POST.get('nombre'),
                tipo='Cliente',
                identificacion=request.POST.get('identificacion'),
                direccion=request.POST.get('direccion'),
                telefono=request.POST.get('telefono'),
                email=request.POST.get('email'),
                activo=True
            )
            
            # Crear cliente CRM
            cliente = Cliente.objects.create(
                tercero=tercero,
                tipo_cliente=request.POST.get('tipo_cliente'),
                estado='prospecto',
                limite_credito=request.POST.get('limite_credito', 0) or 0,
                dias_credito=request.POST.get('dias_credito', 0) or 0,
                descuento_maximo=request.POST.get('descuento_maximo', 0) or 0,
                sitio_web=request.POST.get('sitio_web') or None,
                industria=request.POST.get('industria') or None,
                numero_empleados=request.POST.get('numero_empleados') or None,
                facturacion_anual=request.POST.get('facturacion_anual') or None,
                observaciones=request.POST.get('observaciones') or None,
                usuario_asignado=request.user
            )
            
            messages.success(request, f'Cliente {tercero.nombre} creado exitosamente.')
            return redirect('gestion:cliente_detail', id_cliente=cliente.id_cliente)
            
        except Exception as e:
            messages.error(request, f'Error al crear el cliente: {str(e)}')
    
    # Datos para el formulario
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'usuarios': usuarios,
        'tipo_cliente_choices': Cliente.TIPO_CLIENTE_CHOICES,
    }
    
    return render(request, 'crm/cliente_form.html', context)


@login_required
@transaction.atomic
def cliente_edit(request, id_cliente):
    """Editar cliente existente."""
    
    cliente = get_object_or_404(Cliente, pk=id_cliente)
    
    if request.method == 'POST':
        try:
            # Actualizar tercero
            tercero = cliente.tercero
            tercero.nombre = request.POST.get('nombre')
            tercero.identificacion = request.POST.get('identificacion')
            tercero.direccion = request.POST.get('direccion')
            tercero.telefono = request.POST.get('telefono')
            tercero.email = request.POST.get('email')
            tercero.save()
            
            # Actualizar cliente CRM
            cliente.tipo_cliente = request.POST.get('tipo_cliente')
            cliente.estado = request.POST.get('estado')
            cliente.limite_credito = request.POST.get('limite_credito', 0) or 0
            cliente.dias_credito = request.POST.get('dias_credito', 0) or 0
            cliente.descuento_maximo = request.POST.get('descuento_maximo', 0) or 0
            cliente.sitio_web = request.POST.get('sitio_web') or None
            cliente.industria = request.POST.get('industria') or None
            cliente.numero_empleados = request.POST.get('numero_empleados') or None
            cliente.facturacion_anual = request.POST.get('facturacion_anual') or None
            cliente.observaciones = request.POST.get('observaciones') or None
            
            usuario_asignado_id = request.POST.get('usuario_asignado')
            if usuario_asignado_id:
                cliente.usuario_asignado = User.objects.get(pk=usuario_asignado_id)
            
            cliente.save()
            
            messages.success(request, f'Cliente {tercero.nombre} actualizado exitosamente.')
            return redirect('gestion:cliente_detail', id_cliente=cliente.id_cliente)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el cliente: {str(e)}')
    
    # Datos para el formulario
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'cliente': cliente,
        'usuarios': usuarios,
        'tipo_cliente_choices': Cliente.TIPO_CLIENTE_CHOICES,
        'estado_choices': Cliente.ESTADO_CHOICES,
    }
    
    return render(request, 'crm/cliente_form.html', context)


@login_required
def oportunidades_list(request):
    """Lista de oportunidades con filtros."""
    
    # Obtener parámetros de filtro
    etapa = request.GET.get('etapa', '')
    prioridad = request.GET.get('prioridad', '')
    usuario_asignado = request.GET.get('usuario_asignado', '')
    cliente_id = request.GET.get('cliente', '')
    
    # Construir query base
    oportunidades = Oportunidad.objects.select_related(
        'cliente__tercero', 'contacto', 'usuario_asignado'
    )
    
    # Aplicar filtros
    if etapa:
        oportunidades = oportunidades.filter(etapa=etapa)
    
    if prioridad:
        oportunidades = oportunidades.filter(prioridad=prioridad)
    
    if usuario_asignado:
        oportunidades = oportunidades.filter(usuario_asignado_id=usuario_asignado)
    
    if cliente_id:
        oportunidades = oportunidades.filter(cliente_id=cliente_id)
    
    # Ordenar y paginar
    oportunidades = oportunidades.order_by('-fecha_creacion')
    paginator = Paginator(oportunidades, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    clientes = Cliente.objects.select_related('tercero').order_by('tercero__nombre')
    
    # Contar oportunidades por etapa
    oportunidades_por_etapa = {}
    for etapa_key, etapa_display in Oportunidad.ETAPA_CHOICES:
        count = Oportunidad.objects.filter(etapa=etapa_key).count()
        oportunidades_por_etapa[etapa_key] = count
    
    context = {
        'page_obj': page_obj,
        'usuarios': usuarios,
        'clientes': clientes,
        'etapa_choices': Oportunidad.ETAPA_CHOICES,
        'prioridad_choices': Oportunidad.PRIORIDAD_CHOICES,
        'etapa': etapa,
        'prioridad': prioridad,
        'usuario_asignado': usuario_asignado,
        'cliente_id': cliente_id,
        'oportunidades_por_etapa': oportunidades_por_etapa,
    }
    
    return render(request, 'crm/oportunidades_list.html', context)


@login_required
@transaction.atomic
def oportunidad_create(request):
    """Crear nueva oportunidad."""
    
    if request.method == 'POST':
        try:
            cliente = Cliente.objects.get(pk=request.POST.get('cliente'))
            contacto = Contacto.objects.get(pk=request.POST.get('contacto'))
            
            oportunidad = Oportunidad.objects.create(
                cliente=cliente,
                contacto=contacto,
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion'),
                etapa=request.POST.get('etapa', 'prospecto'),
                prioridad=request.POST.get('prioridad', 'media'),
                valor_estimado=request.POST.get('valor_estimado'),
                probabilidad=request.POST.get('probabilidad', 50),
                fecha_cierre_estimada=request.POST.get('fecha_cierre_estimada'),
                proximo_paso=request.POST.get('proximo_paso') or None,
                fecha_proximo_paso=request.POST.get('fecha_proximo_paso') or None,
                usuario_asignado=request.user
            )
            
            messages.success(request, f'Oportunidad {oportunidad.nombre} creada exitosamente.')
            return redirect('gestion:oportunidades_list')
            
        except Exception as e:
            messages.error(request, f'Error al crear la oportunidad: {str(e)}')
    
    # Datos para el formulario
    clientes = Cliente.objects.select_related('tercero').filter(estado='activo').order_by('tercero__nombre')
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'clientes': clientes,
        'usuarios': usuarios,
        'etapa_choices': Oportunidad.ETAPA_CHOICES,
        'prioridad_choices': Oportunidad.PRIORIDAD_CHOICES,
    }
    
    return render(request, 'crm/oportunidad_form.html', context)


@login_required
def get_contactos_by_cliente(request):
    """API endpoint para obtener contactos de un cliente."""
    
    cliente_id = request.GET.get('cliente_id')
    if not cliente_id:
        return JsonResponse({'contactos': []})
    
    try:
        contactos = Contacto.objects.filter(
            cliente_id=cliente_id, 
            activo=True
        ).values('id_contacto', 'nombre', 'apellido', 'cargo')
        
        contactos_list = [
            {
                'id': str(contacto['id_contacto']),
                'nombre': f"{contacto['nombre']} {contacto['apellido']}",
                'cargo': contacto['cargo'] or ''
            }
            for contacto in contactos
        ]
        
        return JsonResponse({'contactos': contactos_list})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@transaction.atomic
def contacto_create(request, id_cliente):
    """Crear nuevo contacto para un cliente."""
    
    cliente = get_object_or_404(Cliente, pk=id_cliente)
    
    if request.method == 'POST':
        try:
            contacto = Contacto.objects.create(
                cliente=cliente,
                nombre=request.POST.get('nombre'),
                apellido=request.POST.get('apellido'),
                cargo=request.POST.get('cargo') or None,
                email=request.POST.get('email') or None,
                telefono=request.POST.get('telefono') or None,
                celular=request.POST.get('celular') or None,
                departamento=request.POST.get('departamento') or None,
                es_decision_maker=request.POST.get('es_decision_maker') == 'on',
                activo=True
            )
            
            messages.success(request, f'Contacto {contacto.nombre} {contacto.apellido} creado exitosamente.')
            return redirect('gestion:cliente_detail', id_cliente=cliente.id_cliente)
            
        except Exception as e:
            messages.error(request, f'Error al crear el contacto: {str(e)}')
            return redirect('gestion:cliente_detail', id_cliente=cliente.id_cliente)
    
    context = {
        'cliente': cliente,
    }
    
    return render(request, 'crm/contacto_form.html', context)


@login_required
@transaction.atomic
def interaccion_create(request, id_cliente):
    """Registrar nueva interacción con un cliente."""
    
    cliente = get_object_or_404(Cliente, pk=id_cliente)
    
    if request.method == 'POST':
        try:
            contacto_id = request.POST.get('contacto')
            contacto = None
            if contacto_id:
                contacto = Contacto.objects.get(pk=contacto_id)
            
            oportunidad_id = request.POST.get('oportunidad')
            oportunidad = None
            if oportunidad_id:
                oportunidad = Oportunidad.objects.get(pk=oportunidad_id)
            
            fecha_interaccion = request.POST.get('fecha_interaccion')
            if fecha_interaccion:
                fecha_interaccion = datetime.strptime(fecha_interaccion, '%Y-%m-%dT%H:%M')
            else:
                fecha_interaccion = timezone.now()
            
            interaccion = InteraccionCliente.objects.create(
                cliente=cliente,
                contacto=contacto,
                oportunidad=oportunidad,
                tipo=request.POST.get('tipo'),
                asunto=request.POST.get('asunto'),
                descripcion=request.POST.get('descripcion'),
                fecha_interaccion=fecha_interaccion,
                requiere_seguimiento=request.POST.get('requiere_seguimiento') == 'on',
                fecha_seguimiento=request.POST.get('fecha_seguimiento') or None,
                usuario=request.user
            )
            
            # Actualizar fecha última interacción del cliente
            cliente.fecha_ultima_interaccion = timezone.now()
            cliente.save()
            
            messages.success(request, 'Interacción registrada exitosamente.')
            return redirect('gestion:cliente_detail', id_cliente=cliente.id_cliente)
            
        except Exception as e:
            messages.error(request, f'Error al registrar la interacción: {str(e)}')
            return redirect('gestion:cliente_detail', id_cliente=cliente.id_cliente)
    
    # Datos para el formulario
    contactos = cliente.contactos.filter(activo=True).order_by('nombre')
    oportunidades = cliente.oportunidades.exclude(etapa__in=['ganada', 'perdida']).order_by('-fecha_creacion')
    
    context = {
        'cliente': cliente,
        'contactos': contactos,
        'oportunidades': oportunidades,
        'tipo_interaccion_choices': InteraccionCliente.TIPO_INTERACCION_CHOICES,
    }
    
    return render(request, 'crm/interaccion_form.html', context)


@login_required
def oportunidad_detail(request, id_oportunidad):
    """Detalle de una oportunidad específica."""
    
    oportunidad = get_object_or_404(Oportunidad, pk=id_oportunidad)
    
    # Obtener interacciones relacionadas
    interacciones = InteraccionCliente.objects.filter(
        oportunidad=oportunidad
    ).select_related('contacto', 'usuario').order_by('-fecha_interaccion')
    
    # Pedidos relacionados
    pedidos = oportunidad.pedidos.all().order_by('-fecha_pedido')
    
    # Tareas relacionadas
    tareas = Tarea.objects.filter(
        oportunidad=oportunidad
    ).select_related('asignado_a', 'creado_por').order_by('-fecha_creacion')
    
    context = {
        'oportunidad': oportunidad,
        'interacciones': interacciones,
        'pedidos': pedidos,
        'tareas': tareas,
    }
    
    return render(request, 'crm/oportunidad_detail.html', context)


@login_required
@transaction.atomic
def oportunidad_edit(request, id_oportunidad):
    """Editar oportunidad existente."""
    
    oportunidad = get_object_or_404(Oportunidad, pk=id_oportunidad)
    
    if request.method == 'POST':
        try:
            oportunidad.nombre = request.POST.get('nombre')
            oportunidad.descripcion = request.POST.get('descripcion')
            oportunidad.etapa = request.POST.get('etapa')
            oportunidad.prioridad = request.POST.get('prioridad')
            oportunidad.valor_estimado = request.POST.get('valor_estimado')
            oportunidad.probabilidad = request.POST.get('probabilidad', 50)
            oportunidad.fecha_cierre_estimada = request.POST.get('fecha_cierre_estimada')
            oportunidad.proximo_paso = request.POST.get('proximo_paso') or None
            oportunidad.fecha_proximo_paso = request.POST.get('fecha_proximo_paso') or None
            
            # Si se marca como ganada o perdida
            if oportunidad.etapa in ['ganada', 'perdida']:
                oportunidad.fecha_cierre_real = timezone.now().date()
                if oportunidad.etapa == 'perdida':
                    oportunidad.motivo_perdida = request.POST.get('motivo_perdida') or None
            
            usuario_asignado_id = request.POST.get('usuario_asignado')
            if usuario_asignado_id:
                oportunidad.usuario_asignado = User.objects.get(pk=usuario_asignado_id)
            
            oportunidad.save()
            
            messages.success(request, f'Oportunidad {oportunidad.nombre} actualizada exitosamente.')
            return redirect('gestion:oportunidad_detail', id_oportunidad=oportunidad.id_oportunidad)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la oportunidad: {str(e)}')
    
    # Datos para el formulario
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'oportunidad': oportunidad,
        'usuarios': usuarios,
        'etapa_choices': Oportunidad.ETAPA_CHOICES,
        'prioridad_choices': Oportunidad.PRIORIDAD_CHOICES,
    }
    
    return render(request, 'crm/oportunidad_form.html', context)


@login_required
def interacciones_timeline(request):
    """Vista timeline de todas las interacciones."""
    
    # Filtros
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    tipo = request.GET.get('tipo')
    usuario_id = request.GET.get('usuario')
    
    # Query base
    interacciones = InteraccionCliente.objects.select_related(
        'cliente__tercero', 'contacto', 'oportunidad', 'usuario'
    )
    
    # Aplicar filtros
    if fecha_desde:
        interacciones = interacciones.filter(fecha_interaccion__gte=fecha_desde)
    
    if fecha_hasta:
        interacciones = interacciones.filter(fecha_interaccion__lte=fecha_hasta)
    
    if tipo:
        interacciones = interacciones.filter(tipo=tipo)
    
    if usuario_id:
        interacciones = interacciones.filter(usuario_id=usuario_id)
    
    # Ordenar y paginar
    interacciones = interacciones.order_by('-fecha_interaccion')
    paginator = Paginator(interacciones, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    # Estadísticas adicionales
    interacciones_hoy = InteraccionCliente.objects.filter(
        fecha_interaccion__date=timezone.now().date()
    ).count()
    
    pendientes_seguimiento = InteraccionCliente.objects.filter(
        requiere_seguimiento=True,
        fecha_seguimiento__gte=timezone.now().date()
    ).count()
    
    clientes_con_interacciones = InteraccionCliente.objects.values('cliente').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'usuarios': usuarios,
        'tipo_interaccion_choices': InteraccionCliente.TIPO_INTERACCION_CHOICES,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'tipo': tipo,
        'usuario_id': usuario_id,
        'interacciones_hoy': interacciones_hoy,
        'pendientes_seguimiento': pendientes_seguimiento,
        'clientes_con_interacciones': clientes_con_interacciones,
    }
    
    return render(request, 'crm/interacciones_timeline.html', context)