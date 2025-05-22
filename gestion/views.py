from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import (
    Bodegas, Lotes, MovimientosInventario, 
    Materiales, Maquinas, Operarios, Terceros,
    ProduccionMolido, ProduccionLavado, ProduccionPeletizado, ProduccionInyeccion,
    ResiduosProduccion, ProduccionConsumo
)
from .inventario_utils import procesar_movimiento_inventario
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

@login_required
def dashboard(request):
    """Dashboard principal con resumen de inventario y operaciones recientes."""
    total_lotes = Lotes.objects.filter(activo=True).count()
    total_stock = Lotes.objects.filter(activo=True).aggregate(total=Sum('cantidad_actual'))['total'] or 0
    bodegas = Bodegas.objects.all()
    movimientos_recientes = MovimientosInventario.objects.all().order_by('-fecha')[:10]
    
    context = {
        'total_lotes': total_lotes,
        'total_stock': total_stock,
        'bodegas': bodegas,
        'movimientos_recientes': movimientos_recientes,
    }
    return render(request, 'gestion/dashboard.html', context)

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
def produccion_dashboard(request):
    """Dashboard de producción con estado actual de los procesos."""
    context = {
        'molido_reciente': ProduccionMolido.objects.all().order_by('-fecha')[:5],
        'lavado_reciente': ProduccionLavado.objects.all().order_by('-fecha')[:5],
        'peletizado_reciente': ProduccionPeletizado.objects.all().order_by('-fecha')[:5],
        'inyeccion_reciente': ProduccionInyeccion.objects.all().order_by('-fecha')[:5],
    }
    return render(request, 'gestion/produccion_dashboard.html', context)

@login_required
def nuevo_proceso_produccion(request, tipo_proceso):
    """Vista para iniciar un nuevo proceso de producción."""
    # Normalizar el tipo de proceso para que coincida con el almacenado en la base de datos
    tipo_proceso_normalizado = tipo_proceso.capitalize()
    
    # Preparar contexto para el formulario
    context = {
        'tipo_proceso': tipo_proceso_normalizado,  # Usar la versión normalizada
        'operarios': Operarios.objects.filter(activo=True),
        'maquinas': Maquinas.objects.filter(tipo_proceso=tipo_proceso_normalizado, activo=True),
        'materiales': Materiales.objects.all(),
        'bodegas': Bodegas.objects.all(),
        'lotes_disponibles': Lotes.objects.filter(activo=True, cantidad_actual__gt=0)
    }
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                operario = Operarios.objects.get(pk=request.POST.get('operario'))
                maquina = Maquinas.objects.get(pk=request.POST.get('maquina'))
                orden_trabajo = request.POST.get('orden_trabajo')
                turno = request.POST.get('turno')
                lote_entrada = Lotes.objects.get(pk=request.POST.get('lote_entrada'))
                cantidad_entrada = Decimal(request.POST.get('cantidad_entrada'))
                bodega_destino = Bodegas.objects.get(pk=request.POST.get('bodega_destino'))
                observaciones = request.POST.get('observaciones', '')
                
                # Validar cantidad de entrada
                if cantidad_entrada > lote_entrada.cantidad_actual:
                    raise ValidationError('La cantidad a procesar excede el stock disponible.')
                
                # Crear el movimiento de consumo
                procesar_movimiento_inventario(
                    tipo_movimiento='ConsumoProduccion',
                    lote=lote_entrada,
                    cantidad=cantidad_entrada,
                    bodega_origen=lote_entrada.id_bodega_actual,
                    bodega_destino=None,
                    observaciones=f"Consumo para {tipo_proceso_normalizado} - OT: {orden_trabajo}"
                )
                
                # Crear el nuevo lote de producción
                if tipo_proceso_normalizado != 'Inyeccion':
                    material_salida = Materiales.objects.get(pk=request.POST.get('material_salida'))
                    nuevo_lote = Lotes.objects.create(
                        numero_lote=f"{orden_trabajo}-{tipo_proceso_normalizado}",
                        id_material=material_salida,
                        cantidad_inicial=cantidad_entrada,
                        cantidad_actual=cantidad_entrada,
                        id_bodega_actual=bodega_destino,
                        activo=True
                    )
                
                # Registrar el proceso según su tipo
                proceso_data = {
                    'id_operario': operario,
                    'id_maquina': maquina,
                    'orden_trabajo': orden_trabajo,
                    'turno': turno,
                    'id_bodega_destino': bodega_destino,
                    'cantidad_producida': cantidad_entrada,
                    'observaciones': observaciones
                }
                
                if tipo_proceso_normalizado != 'Inyeccion':
                    proceso_data['id_lote_producido'] = nuevo_lote
                
                if tipo_proceso_normalizado == 'Molido':
                    ProduccionMolido.objects.create(**proceso_data)
                elif tipo_proceso_normalizado == 'Lavado':
                    ProduccionLavado.objects.create(**proceso_data)
                elif tipo_proceso_normalizado == 'Peletizado':
                    ProduccionPeletizado.objects.create(**proceso_data)
                elif tipo_proceso_normalizado == 'Inyeccion':
                    ProduccionInyeccion.objects.create(**proceso_data)
                
                messages.success(request, f'Proceso de {tipo_proceso_normalizado} registrado exitosamente.')
                return redirect('gestion:produccion_dashboard')
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al registrar el proceso: {str(e)}')
    
    return render(request, 'gestion/nuevo_proceso.html', context)

@login_required
def produccion_consumo(request):
    """Vista para mostrar los consumos de producción."""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    proceso = request.GET.get('proceso')
    
    # Start with all consumos and use select_related to optimize queries
    consumos = ProduccionConsumo.objects.select_related(
        'id_produccion_molido',
        'id_produccion_lavado',
        'id_produccion_peletizado',
        'id_produccion_inyeccion'
    ).all()
    
    if fecha_inicio:
        consumos = consumos.filter(
            Q(id_produccion_molido__fecha__gte=fecha_inicio) |
            Q(id_produccion_lavado__fecha__gte=fecha_inicio) |
            Q(id_produccion_peletizado__fecha__gte=fecha_inicio) |
            Q(id_produccion_inyeccion__fecha__gte=fecha_inicio)
        )
    if fecha_fin:
        consumos = consumos.filter(
            Q(id_produccion_molido__fecha__lte=fecha_fin) |
            Q(id_produccion_lavado__fecha__lte=fecha_fin) |
            Q(id_produccion_peletizado__fecha__lte=fecha_fin) |
            Q(id_produccion_inyeccion__fecha__lte=fecha_fin)
        )
    if proceso:
        if proceso == 'molido':
            consumos = consumos.filter(id_produccion_molido__isnull=False)
        elif proceso == 'lavado':
            consumos = consumos.filter(id_produccion_lavado__isnull=False)
        elif proceso == 'peletizado':
            consumos = consumos.filter(id_produccion_peletizado__isnull=False)
        elif proceso == 'inyeccion':
            consumos = consumos.filter(id_produccion_inyeccion__isnull=False)
    
    # Order by the most recent production date
    consumos = consumos.annotate(
        fecha_produccion=Coalesce(
            'id_produccion_molido__fecha',
            'id_produccion_lavado__fecha',
            'id_produccion_peletizado__fecha',
            'id_produccion_inyeccion__fecha'
        )
    ).order_by('-fecha_produccion')
    
    context = {
        'consumos': consumos,
    }
    return render(request, 'gestion/produccion_consumo.html', context)

@login_required
def produccion_lavado(request):
    """Vista para mostrar y filtrar la producción de lavado."""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    maquina = request.GET.get('maquina')
    operario = request.GET.get('operario')
    
    producciones = ProduccionLavado.objects.all()
    
    if fecha_inicio:
        producciones = producciones.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        producciones = producciones.filter(fecha__lte=fecha_fin)
    if maquina:
        producciones = producciones.filter(id_maquina=maquina)
    if operario:
        producciones = producciones.filter(id_operario=operario)
    
    producciones = producciones.order_by('-fecha')
    
    context = {
        'producciones': producciones,
        'maquinas': Maquinas.objects.filter(tipo_proceso='Lavado', activo=True),
        'operarios': Operarios.objects.filter(activo=True),
    }
    return render(request, 'gestion/produccion_lavado.html', context)

@login_required
def produccion_peletizado(request):
    """Vista para mostrar y filtrar la producción de peletizado."""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    maquina = request.GET.get('maquina')
    operario = request.GET.get('operario')
    
    producciones = ProduccionPeletizado.objects.all()
    
    if fecha_inicio:
        producciones = producciones.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        producciones = producciones.filter(fecha__lte=fecha_fin)
    if maquina:
        producciones = producciones.filter(id_maquina=maquina)
    if operario:
        producciones = producciones.filter(id_operario=operario)
    
    producciones = producciones.order_by('-fecha')
    
    context = {
        'producciones': producciones,
        'maquinas': Maquinas.objects.filter(tipo_proceso='Peletizado', activo=True),
        'operarios': Operarios.objects.filter(activo=True),
    }
    return render(request, 'gestion/produccion_peletizado.html', context)

@login_required
def residuos_produccion(request):
    """Vista para mostrar y filtrar los residuos de producción."""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo_proceso = request.GET.get('tipo_proceso')
    tipo_residuo = request.GET.get('tipo_residuo')
    
    residuos = ResiduosProduccion.objects.all()
    
    if fecha_inicio:
        residuos = residuos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        residuos = residuos.filter(fecha__lte=fecha_fin)
    if tipo_proceso:
        if tipo_proceso == 'molido':
            residuos = residuos.filter(id_produccion_molido__isnull=False)
        elif tipo_proceso == 'lavado':
            residuos = residuos.filter(id_produccion_lavado__isnull=False)
        elif tipo_proceso == 'peletizado':
            residuos = residuos.filter(id_produccion_peletizado__isnull=False)
        elif tipo_proceso == 'inyeccion':
            residuos = residuos.filter(id_produccion_inyeccion__isnull=False)
    if tipo_residuo:
        residuos = residuos.filter(tipo_residuo=tipo_residuo)
    
    # Calcular métricas para el resumen
    total_residuos = residuos.aggregate(total=Sum('cantidad'))['total'] or 0
    
    # Calcular producción total del período
    produccion_total = Decimal('0.00')
    if fecha_inicio and fecha_fin:
        filtro_fecha = Q(fecha__range=[fecha_inicio, fecha_fin])
        produccion_total += (
            ProduccionMolido.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_producida'))['total'] or 0 +
            ProduccionLavado.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_producida'))['total'] or 0 +
            ProduccionPeletizado.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_producida'))['total'] or 0 +
            ProduccionInyeccion.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_producida'))['total'] or 0
        )
    
    # Calcular porcentaje de merma
    porcentaje_merma = (total_residuos / produccion_total * 100) if produccion_total > 0 else 0
    
    context = {
        'residuos': residuos.order_by('-fecha'),
        'total_residuos': total_residuos,
        'total_produccion': produccion_total,
        'porcentaje_merma': round(porcentaje_merma, 2)
    }
    return render(request, 'gestion/residuos_produccion.html', context)

@login_required
@transaction.atomic
def editar_produccion_lavado(request, id):
    """Vista para editar un registro de producción de lavado."""
    produccion = get_object_or_404(ProduccionLavado, pk=id)
    if request.method == 'POST':
        try:
            produccion.orden_trabajo = request.POST.get('orden_trabajo')
            produccion.turno = request.POST.get('turno')
            produccion.observaciones = request.POST.get('observaciones')
            produccion.save()
            messages.success(request, 'Registro actualizado exitosamente.')
            return redirect('gestion:produccion_lavado')
        except Exception as e:
            messages.error(request, f'Error al actualizar el registro: {str(e)}')
    
    context = {
        'produccion': produccion,
    }
    return render(request, 'gestion/produccion_lavado.html', context)

@login_required
@transaction.atomic
def editar_produccion_peletizado(request, id):
    """Vista para editar un registro de producción de peletizado."""
    produccion = get_object_or_404(ProduccionPeletizado, pk=id)
    if request.method == 'POST':
        try:
            produccion.orden_trabajo = request.POST.get('orden_trabajo')
            produccion.turno = request.POST.get('turno')
            produccion.observaciones = request.POST.get('observaciones')
            produccion.save()
            messages.success(request, 'Registro actualizado exitosamente.')
            return redirect('gestion:produccion_peletizado')
        except Exception as e:
            messages.error(request, f'Error al actualizar el registro: {str(e)}')
    
    context = {
        'produccion': produccion,
    }
    return render(request, 'gestion/produccion_peletizado.html', context)

@login_required
@transaction.atomic
def eliminar_produccion_lavado(request, id):
    """Vista para eliminar un registro de producción de lavado."""
    produccion = get_object_or_404(ProduccionLavado, pk=id)
    if request.method == 'POST':
        try:
            produccion.delete()
            messages.success(request, 'Registro eliminado exitosamente.')
            return redirect('gestion:produccion_lavado')
        except Exception as e:
            messages.error(request, f'Error al eliminar el registro: {str(e)}')
    return redirect('gestion:produccion_lavado')

@login_required
@transaction.atomic
def eliminar_produccion_peletizado(request, id):
    """Vista para eliminar un registro de producción de peletizado."""
    produccion = get_object_or_404(ProduccionPeletizado, pk=id)
    if request.method == 'POST':
        try:
            produccion.delete()
            messages.success(request, 'Registro eliminado exitosamente.')
            return redirect('gestion:produccion_peletizado')
        except Exception as e:
            messages.error(request, f'Error al eliminar el registro: {str(e)}')
    return redirect('gestion:produccion_peletizado')

@login_required
@transaction.atomic
def editar_residuo(request, id):
    """Vista para editar un registro de residuo."""
    residuo = get_object_or_404(ResiduosProduccion, pk=id)
    if request.method == 'POST':
        try:
            residuo.tipo_residuo = request.POST.get('tipo_residuo')
            residuo.cantidad = Decimal(request.POST.get('cantidad'))
            residuo.observaciones = request.POST.get('observaciones')
            residuo.save()
            messages.success(request, 'Residuo actualizado exitosamente.')
            return redirect('gestion:residuos_produccion')
        except Exception as e:
            messages.error(request, f'Error al actualizar el residuo: {str(e)}')
    
    context = {
        'residuo': residuo,
    }
    return render(request, 'gestion/residuos_produccion.html', context)

@login_required
@transaction.atomic
def eliminar_residuo(request, id):
    """Vista para eliminar un registro de residuo."""
    residuo = get_object_or_404(ResiduosProduccion, pk=id)
    if request.method == 'POST':
        try:
            residuo.delete()
            messages.success(request, 'Residuo eliminado exitosamente.')
            return redirect('gestion:residuos_produccion')
        except Exception as e:
            messages.error(request, f'Error al eliminar el residuo: {str(e)}')
    return redirect('gestion:residuos_produccion')

@login_required
def produccion_molido(request):
    """Vista para mostrar y filtrar la producción de molido."""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    maquina = request.GET.get('maquina')
    operario = request.GET.get('operario')
    
    producciones = ProduccionMolido.objects.all()
    
    if fecha_inicio:
        producciones = producciones.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        producciones = producciones.filter(fecha__lte=fecha_fin)
    if maquina:
        producciones = producciones.filter(id_maquina=maquina)
    if operario:
        producciones = producciones.filter(id_operario=operario)
    
    producciones = producciones.order_by('-fecha')
    
    context = {
        'producciones': producciones,
        'maquinas': Maquinas.objects.filter(tipo_proceso='Molido', activo=True),
        'operarios': Operarios.objects.filter(activo=True),
    }
    return render(request, 'gestion/produccion_molido.html', context)

@login_required
def produccion_inyeccion(request):
    """Vista para mostrar y filtrar la producción de inyección."""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    maquina = request.GET.get('maquina')
    operario = request.GET.get('operario')
    
    producciones = ProduccionInyeccion.objects.all()
    
    if fecha_inicio:
        producciones = producciones.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        producciones = producciones.filter(fecha__lte=fecha_fin)
    if maquina:
        producciones = producciones.filter(id_maquina=maquina)
    if operario:
        producciones = producciones.filter(id_operario=operario)
    
    producciones = producciones.order_by('-fecha')
    
    context = {
        'producciones': producciones,
        'maquinas': Maquinas.objects.filter(tipo_proceso='Inyeccion', activo=True),
        'operarios': Operarios.objects.filter(activo=True),
    }
    return render(request, 'gestion/produccion_inyeccion.html', context)

@login_required
@transaction.atomic
def editar_produccion_molido(request, id):
    """Vista para editar un registro de producción de molido."""
    produccion = get_object_or_404(ProduccionMolido, pk=id)
    if request.method == 'POST':
        try:
            produccion.orden_trabajo = request.POST.get('orden_trabajo')
            produccion.turno = request.POST.get('turno')
            produccion.observaciones = request.POST.get('observaciones')
            produccion.save()
            messages.success(request, 'Registro actualizado exitosamente.')
            return redirect('gestion:produccion_molido')
        except Exception as e:
            messages.error(request, f'Error al actualizar el registro: {str(e)}')
    
    context = {
        'produccion': produccion,
    }
    return render(request, 'gestion/produccion_molido.html', context)

@login_required
@transaction.atomic
def editar_produccion_inyeccion(request, id):
    """Vista para editar un registro de producción de inyección."""
    produccion = get_object_or_404(ProduccionInyeccion, pk=id)
    if request.method == 'POST':
        try:
            produccion.orden_trabajo = request.POST.get('orden_trabajo')
            produccion.turno = request.POST.get('turno')
            produccion.observaciones = request.POST.get('observaciones')
            produccion.save()
            messages.success(request, 'Registro actualizado exitosamente.')
            return redirect('gestion:produccion_inyeccion')
        except Exception as e:
            messages.error(request, f'Error al actualizar el registro: {str(e)}')
    
    context = {
        'produccion': produccion,
    }
    return render(request, 'gestion/produccion_inyeccion.html', context)

@login_required
@transaction.atomic
def eliminar_produccion_molido(request, id):
    """Vista para eliminar un registro de producción de molido."""
    produccion = get_object_or_404(ProduccionMolido, pk=id)
    if request.method == 'POST':
        try:
            produccion.delete()
            messages.success(request, 'Registro eliminado exitosamente.')
            return redirect('gestion:produccion_molido')
        except Exception as e:
            messages.error(request, f'Error al eliminar el registro: {str(e)}')
    return redirect('gestion:produccion_molido')

@login_required
@transaction.atomic
def eliminar_produccion_inyeccion(request, id):
    """Vista para eliminar un registro de producción de inyección."""
    produccion = get_object_or_404(ProduccionInyeccion, pk=id)
    if request.method == 'POST':
        try:
            produccion.delete()
            messages.success(request, 'Registro eliminado exitosamente.')
            return redirect('gestion:produccion_inyeccion')
        except Exception as e:
            messages.error(request, f'Error al eliminar el registro: {str(e)}')
    return redirect('gestion:produccion_inyeccion')

@login_required
def lotes(request):
    """Vista para gestionar los lotes."""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                numero_lote = request.POST.get('numero_lote')
                id_material = request.POST.get('id_material')
                cantidad_inicial = Decimal(request.POST.get('cantidad_inicial'))
                unidad_medida = request.POST.get('unidad_medida')
                id_bodega = request.POST.get('id_bodega')
                fecha_vencimiento = request.POST.get('fecha_vencimiento')
                costo_unitario = request.POST.get('costo_unitario')
                proveedor = request.POST.get('proveedor')
                clasificacion = request.POST.get('clasificacion')
                observaciones = request.POST.get('observaciones')

                # Crear nuevo lote
                Lotes.objects.create(
                    numero_lote=numero_lote,
                    id_material_id=id_material,
                    cantidad_inicial=cantidad_inicial,
                    cantidad_actual=cantidad_inicial,
                    unidad_medida=unidad_medida,
                    id_bodega_actual_id=id_bodega,
                    fecha_vencimiento=fecha_vencimiento if fecha_vencimiento else None,
                    costo_unitario=costo_unitario if costo_unitario else None,
                    proveedor_origen_id=proveedor if proveedor else None,
                    clasificacion=clasificacion if clasificacion else None,
                    observaciones=observaciones,
                    activo=True
                )
                messages.success(request, 'Lote creado exitosamente.')
                return redirect('gestion:lotes')
        except Exception as e:
            messages.error(request, f'Error al crear el lote: {str(e)}')

    lotes_list = Lotes.objects.all().order_by('-fecha_creacion')
    materiales_list = Materiales.objects.all()
    bodegas_list = Bodegas.objects.all()
    proveedores_list = Terceros.objects.filter(tipo='Proveedor')
    
    context = {
        'lotes': lotes_list,
        'materiales': materiales_list,
        'bodegas': bodegas_list,
        'proveedores': proveedores_list,
    }
    return render(request, 'gestion/lotes.html', context)

@login_required
def maquinas(request):
    """Vista para gestionar las máquinas."""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            tipo_proceso = request.POST.get('tipo_proceso')
            descripcion = request.POST.get('descripcion')
            activo = request.POST.get('activo', 'off') == 'on'

            Maquinas.objects.create(
                nombre=nombre,
                tipo_proceso=tipo_proceso,
                descripcion=descripcion,
                activo=activo
            )
            messages.success(request, 'Máquina creada exitosamente.')
            return redirect('gestion:maquinas')
        except Exception as e:
            messages.error(request, f'Error al crear la máquina: {str(e)}')

    maquinas_list = Maquinas.objects.all()
    context = {
        'maquinas': maquinas_list,
    }
    return render(request, 'gestion/maquinas.html', context)

@login_required
def materiales(request):
    """Vista para gestionar los materiales."""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            tipo = request.POST.get('tipo')
            descripcion = request.POST.get('descripcion', '')

            Materiales.objects.create(
                nombre=nombre,
                tipo=tipo,
                descripcion=descripcion
            )
            messages.success(request, 'Material creado exitosamente.')
            return redirect('gestion:materiales')
        except Exception as e:
            messages.error(request, f'Error al crear el material: {str(e)}')

    materiales_list = Materiales.objects.all()
    context = {
        'materiales': materiales_list,
    }
    return render(request, 'gestion/materiales.html', context)

@login_required
def operarios(request):
    """Vista para gestionar los operarios."""
    if request.method == 'POST':
        try:
            codigo = request.POST.get('codigo')
            nombre_completo = request.POST.get('nombre_completo')
            activo = request.POST.get('activo', 'off') == 'on'

            Operarios.objects.create(
                codigo=codigo,
                nombre_completo=nombre_completo,
                activo=activo
            )
            messages.success(request, 'Operario creado exitosamente.')
            return redirect('gestion:operarios')
        except Exception as e:
            messages.error(request, f'Error al crear el operario: {str(e)}')

    operarios_list = Operarios.objects.all()
    context = {
        'operarios': operarios_list,
    }
    return render(request, 'gestion/operarios.html', context)

@login_required
def terceros(request):
    """Vista para gestionar los terceros."""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            tipo = request.POST.get('tipo')
            identificacion = request.POST.get('identificacion')
            direccion = request.POST.get('direccion')
            telefono = request.POST.get('telefono')
            email = request.POST.get('email')

            Terceros.objects.create(
                nombre=nombre,
                tipo=tipo,
                identificacion=identificacion,
                direccion=direccion,
                telefono=telefono,
                email=email
            )
            messages.success(request, 'Tercero creado exitosamente.')
            return redirect('gestion:terceros')
        except Exception as e:
            messages.error(request, f'Error al crear el tercero: {str(e)}')

    terceros_list = Terceros.objects.all()
    context = {
        'terceros': terceros_list,
    }
    return render(request, 'gestion/terceros.html', context)

@login_required
def bodegas(request):
    """Vista para gestionar las bodegas."""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion', '')

            Bodegas.objects.create(
                nombre=nombre,
                descripcion=descripcion
            )
            messages.success(request, 'Bodega creada exitosamente.')
            return redirect('gestion:bodegas')
        except Exception as e:
            messages.error(request, f'Error al crear la bodega: {str(e)}')

    bodegas_list = Bodegas.objects.all()
    context = {
        'bodegas': bodegas_list,
    }
    return render(request, 'gestion/bodegas.html', context)

# Funciones de edición
@login_required
@transaction.atomic
def editar_lote(request, id):
    """Vista para editar un lote."""
    lote = get_object_or_404(Lotes, pk=id)
    if request.method == 'POST':
        try:
            lote.numero_lote = request.POST.get('numero_lote')
            lote.id_material_id = request.POST.get('id_material')
            lote.id_bodega_actual_id = request.POST.get('id_bodega')
            lote.fecha_vencimiento = request.POST.get('fecha_vencimiento') or None
            lote.costo_unitario = request.POST.get('costo_unitario') or None
            lote.proveedor_origen_id = request.POST.get('proveedor') or None
            lote.clasificacion = request.POST.get('clasificacion') or None
            lote.observaciones = request.POST.get('observaciones')
            lote.save()
            messages.success(request, 'Lote actualizado exitosamente.')
            return redirect('gestion:lotes')
        except Exception as e:
            messages.error(request, f'Error al actualizar el lote: {str(e)}')
    
    context = {
        'lote': lote,
        'materiales': Materiales.objects.all(),
        'bodegas': Bodegas.objects.all(),
        'proveedores': Terceros.objects.filter(tipo='Proveedor'),
    }
    return render(request, 'gestion/editar_lote.html', context)

@login_required
@transaction.atomic
def editar_maquina(request, id):
    """Vista para editar una máquina."""
    maquina = get_object_or_404(Maquinas, pk=id)
    if request.method == 'POST':
        try:
            maquina.nombre = request.POST.get('nombre')
            maquina.tipo_proceso = request.POST.get('tipo_proceso')
            maquina.descripcion = request.POST.get('descripcion')
            maquina.activo = request.POST.get('activo', 'off') == 'on'
            maquina.save()
            messages.success(request, 'Máquina actualizada exitosamente.')
            return redirect('gestion:maquinas')
        except Exception as e:
            messages.error(request, f'Error al actualizar la máquina: {str(e)}')
    
    context = {
        'maquina': maquina,
    }
    return render(request, 'gestion/editar_maquina.html', context)

@login_required
@transaction.atomic
def editar_material(request, id):
    """Vista para editar un material."""
    material = get_object_or_404(Materiales, pk=id)
    if request.method == 'POST':
        try:
            material.nombre = request.POST.get('nombre')
            material.tipo = request.POST.get('tipo')
            material.descripcion = request.POST.get('descripcion')
            material.save()
            messages.success(request, 'Material actualizado exitosamente.')
            return redirect('gestion:materiales')
        except Exception as e:
            messages.error(request, f'Error al actualizar el material: {str(e)}')
    
    context = {
        'material': material,
    }
    return render(request, 'gestion/editar_material.html', context)

@login_required
@transaction.atomic
def editar_operario(request, id):
    """Vista para editar un operario."""
    operario = get_object_or_404(Operarios, pk=id)
    if request.method == 'POST':
        try:
            operario.codigo = request.POST.get('codigo')
            operario.nombre_completo = request.POST.get('nombre_completo')
            operario.activo = request.POST.get('activo', 'off') == 'on'
            operario.save()
            messages.success(request, 'Operario actualizado exitosamente.')
            return redirect('gestion:operarios')
        except Exception as e:
            messages.error(request, f'Error al actualizar el operario: {str(e)}')
    
    context = {
        'operario': operario,
    }
    return render(request, 'gestion/editar_operario.html', context)

@login_required
@transaction.atomic
def editar_tercero(request, id):
    """Vista para editar un tercero."""
    tercero = get_object_or_404(Terceros, pk=id)
    if request.method == 'POST':
        try:
            tercero.nombre = request.POST.get('nombre')
            tercero.tipo = request.POST.get('tipo')
            tercero.identificacion = request.POST.get('identificacion')
            tercero.direccion = request.POST.get('direccion')
            tercero.telefono = request.POST.get('telefono')
            tercero.email = request.POST.get('email')
            tercero.save()
            messages.success(request, 'Tercero actualizado exitosamente.')
            return redirect('gestion:terceros')
        except Exception as e:
            messages.error(request, f'Error al actualizar el tercero: {str(e)}')
    
    context = {
        'tercero': tercero,
    }
    return render(request, 'gestion/editar_tercero.html', context)

@login_required
@transaction.atomic
def editar_bodega(request, id):
    """Vista para editar una bodega."""
    bodega = get_object_or_404(Bodegas, pk=id)
    if request.method == 'POST':
        try:
            bodega.nombre = request.POST.get('nombre')
            bodega.descripcion = request.POST.get('descripcion', '')
            bodega.save()
            messages.success(request, 'Bodega actualizada exitosamente.')
            return redirect('gestion:bodegas')
        except Exception as e:
            messages.error(request, f'Error al actualizar la bodega: {str(e)}')
    
    context = {
        'bodega': bodega,
    }
    return render(request, 'gestion/editar_bodega.html', context)

# Funciones de eliminación
@login_required
@transaction.atomic
def eliminar_lote(request, id):
    """Vista para eliminar un lote."""
    lote = get_object_or_404(Lotes, pk=id)
    if request.method == 'POST':
        try:
            lote.activo = False
            lote.save()
            messages.success(request, 'Lote eliminado exitosamente.')
            return redirect('gestion:lotes')
        except Exception as e:
            messages.error(request, f'Error al eliminar el lote: {str(e)}')
    return redirect('gestion:lotes')

@login_required
@transaction.atomic
def eliminar_maquina(request, id):
    """Vista para eliminar una máquina."""
    maquina = get_object_or_404(Maquinas, pk=id)
    if request.method == 'POST':
        try:
            maquina.delete()
            messages.success(request, 'Máquina eliminada exitosamente.')
            return redirect('gestion:maquinas')
        except Exception as e:
            messages.error(request, f'Error al eliminar la máquina: {str(e)}')
    return redirect('gestion:maquinas')

@login_required
@transaction.atomic
def eliminar_material(request, id):
    """Vista para eliminar un material."""
    material = get_object_or_404(Materiales, pk=id)
    if request.method == 'POST':
        try:
            material.delete()
            messages.success(request, 'Material eliminado exitosamente.')
            return redirect('gestion:materiales')
        except Exception as e:
            messages.error(request, f'Error al eliminar el material: {str(e)}')
    return redirect('gestion:materiales')

@login_required
@transaction.atomic
def eliminar_operario(request, id):
    """Vista para eliminar un operario."""
    operario = get_object_or_404(Operarios, pk=id)
    if request.method == 'POST':
        try:
            operario.delete()
            messages.success(request, 'Operario eliminado exitosamente.')
            return redirect('gestion:operarios')
        except Exception as e:
            messages.error(request, f'Error al eliminar el operario: {str(e)}')
    return redirect('gestion:operarios')

@login_required
@transaction.atomic
def eliminar_tercero(request, id):
    """Vista para eliminar un tercero."""
    tercero = get_object_or_404(Terceros, pk=id)
    if request.method == 'POST':
        try:
            tercero.delete()
            messages.success(request, 'Tercero eliminado exitosamente.')
            return redirect('gestion:terceros')
        except Exception as e:
            messages.error(request, f'Error al eliminar el tercero: {str(e)}')
    return redirect('gestion:terceros')

@login_required
@transaction.atomic
def eliminar_bodega(request, id):
    """Vista para eliminar una bodega."""
    bodega = get_object_or_404(Bodegas, pk=id)
    if request.method == 'POST':
        try:
            bodega.delete()
            messages.success(request, 'Bodega eliminada exitosamente.')
            return redirect('gestion:bodegas')
        except Exception as e:
            messages.error(request, f'Error al eliminar la bodega: {str(e)}')
    return redirect('gestion:bodegas')
