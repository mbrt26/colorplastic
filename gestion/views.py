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
    ResiduosProduccion, ProduccionConsumo, MotivoParo, ParosProduccion
)
from .inventario_utils import procesar_movimiento_inventario
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import uuid
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Despacho, DetalleDespacho
from django import forms
from django.http import JsonResponse
from django.views.decorators.http import require_GET

class DespachoForm(forms.ModelForm):
    class Meta:
        model = Despacho
        fields = ['numero_remision', 'tercero', 'direccion_entrega', 'estado', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

class DetalleDespachoFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        total = 0
        for form in self.forms:
            if not form.is_valid():
                continue
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                cantidad = form.cleaned_data.get('cantidad', 0)
                if cantidad <= 0:
                    raise forms.ValidationError('La cantidad debe ser mayor que cero.')
                total += cantidad
        if total <= 0:
            raise forms.ValidationError('Debe incluir al menos un producto en el despacho.')

DetalleDespachoFormSet = forms.inlineformset_factory(
    Despacho, DetalleDespacho,
    fields=['producto', 'cantidad', 'bodega_origen'],
    extra=1,
    can_delete=True,
    formset=DetalleDespachoFormSet,
)

class DespachoListView(LoginRequiredMixin, ListView):
    model = Despacho
    template_name = 'gestion/despacho_list.html'
    context_object_name = 'despachos'
    ordering = ['-fecha_creacion']

class DespachoCreateView(LoginRequiredMixin, CreateView):
    model = Despacho
    form_class = DespachoForm
    template_name = 'gestion/despacho_form.html'
    success_url = reverse_lazy('gestion:despacho_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = DetalleDespachoFormSet(self.request.POST)
        else:
            context['formset'] = DetalleDespachoFormSet()
        return context

    def form_valid(self, form):
        form.instance.usuario_creacion = self.request.user
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class DespachoUpdateView(LoginRequiredMixin, UpdateView):
    model = Despacho
    form_class = DespachoForm
    template_name = 'gestion/despacho_form.html'
    success_url = reverse_lazy('gestion:despacho_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = DetalleDespachoFormSet(
                self.request.POST, instance=self.object)
        else:
            context['formset'] = DetalleDespachoFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class DespachoDetailView(LoginRequiredMixin, DetailView):
    model = Despacho
    template_name = 'gestion/despacho_detail.html'
    context_object_name = 'despacho'

@login_required
def dashboard(request):
    """Dashboard principal con resumen de inventario y operaciones recientes."""
    total_lotes = Lotes.objects.filter(activo=True).count()
    total_stock = Lotes.objects.filter(activo=True).aggregate(total=Sum('cantidad_actual'))['total'] or 0
    bodegas = Bodegas.objects.all()
    movimientos_recientes = MovimientosInventario.objects.all().order_by('-fecha')[:10]
    
    # Obtener los paros más recientes de todos los procesos
    paros_recientes = ParosProduccion.objects.select_related(
        'id_produccion_molido',
        'id_produccion_lavado',
        'id_produccion_peletizado',
        'id_produccion_inyeccion',
        'id_operario_reporta',
        'motivo'
    ).order_by('-fecha_hora_inicio')[:10]
    
    context = {
        'total_lotes': total_lotes,
        'total_stock': total_stock,
        'bodegas': bodegas,
        'movimientos_recientes': movimientos_recientes,
        'paros_recientes': paros_recientes,  # Añadir paros al contexto
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
    from django.utils import timezone
    from django.db.models import Sum, Avg, Count
    from datetime import timedelta
    
    hoy = timezone.now().date()
    inicio_dia = timezone.make_aware(timezone.datetime.combine(hoy, timezone.datetime.min.time()))
    fin_dia = timezone.make_aware(timezone.datetime.combine(hoy, timezone.datetime.max.time()))
    
    # Obtener producciones recientes (últimas 5 de cada tipo)
    molido_reciente = ProduccionMolido.objects.select_related(
        'id_lote_producido', 'id_operario', 'id_maquina'
    ).all().order_by('-fecha')[:5]
    
    lavado_reciente = ProduccionLavado.objects.select_related(
        'id_lote_producido', 'id_operario', 'id_maquina'
    ).all().order_by('-fecha')[:5]
    
    peletizado_reciente = ProduccionPeletizado.objects.select_related(
        'id_lote_producido', 'id_operario', 'id_maquina'
    ).all().order_by('-fecha')[:5]
    
    inyeccion_reciente = ProduccionInyeccion.objects.select_related(
        'id_operario', 'id_maquina'
    ).all().order_by('-fecha')[:5]
    
    # Calcular estadísticas del día
    procesos_hoy = (
        ProduccionMolido.objects.filter(fecha__range=[inicio_dia, fin_dia]).count() +
        ProduccionLavado.objects.filter(fecha__range=[inicio_dia, fin_dia]).count() +
        ProduccionPeletizado.objects.filter(fecha__range=[inicio_dia, fin_dia]).count() +
        ProduccionInyeccion.objects.filter(fecha__range=[inicio_dia, fin_dia]).count()
    )
    
    # Calcular eficiencia promedio del día
    eficiencias = []
    for modelo in [ProduccionMolido, ProduccionLavado, ProduccionPeletizado, ProduccionInyeccion]:
        producciones = modelo.objects.filter(fecha__range=[inicio_dia, fin_dia])
        for prod in producciones:
            if prod.cantidad_entrada and prod.cantidad_entrada > 0:
                eficiencias.append((prod.cantidad_salida / prod.cantidad_entrada) * 100)
    
    eficiencia_promedio = sum(eficiencias) / len(eficiencias) if eficiencias else 0
    
    # Calcular total producido hoy
    total_producido = (
        ProduccionMolido.objects.filter(fecha__range=[inicio_dia, fin_dia]).aggregate(
            total=Sum('cantidad_salida'))['total'] or 0
    ) + (
        ProduccionLavado.objects.filter(fecha__range=[inicio_dia, fin_dia]).aggregate(
            total=Sum('cantidad_salida'))['total'] or 0
    ) + (
        ProduccionPeletizado.objects.filter(fecha__range=[inicio_dia, fin_dia]).aggregate(
            total=Sum('cantidad_salida'))['total'] or 0
    ) + (
        ProduccionInyeccion.objects.filter(fecha__range=[inicio_dia, fin_dia]).aggregate(
            total=Sum('cantidad_salida'))['total'] or 0
    )
    
    # Contar paros activos (sin fecha de fin)
    paros_activos = ParosProduccion.objects.filter(fecha_hora_fin__isnull=True).count()
    
    context = {
        'molido_reciente': molido_reciente,
        'lavado_reciente': lavado_reciente,
        'peletizado_reciente': peletizado_reciente,
        'inyeccion_reciente': inyeccion_reciente,
        'total_procesos_hoy': procesos_hoy,
        'eficiencia_promedio': eficiencia_promedio,
        'total_producido_kg': total_producido,
        'paros_activos': paros_activos,
    }
    return render(request, 'gestion/produccion_dashboard.html', context)

@login_required
def nuevo_proceso_produccion(request, tipo_proceso):
    """Vista para iniciar un nuevo proceso de producción.

    El movimiento de inventario por consumos se genera automáticamente a
    través de la señal ``post_save`` de :class:`ProduccionConsumo`.
    """
    # Normalizar el tipo de proceso para que coincida con el almacenado en la base de datos
    tipo_proceso_mapping = {
        'molido': 'Molido',
        'lavado': 'Lavado',
        'peletizado': 'Peletizado',
        'inyeccion': 'Inyeccion',
        'Molido': 'Molido',
        'Lavado': 'Lavado',
        'Peletizado': 'Peletizado',
        'Inyeccion': 'Inyeccion'
    }
    
    tipo_proceso_normalizado = tipo_proceso_mapping.get(tipo_proceso, tipo_proceso.capitalize())
    
    # Obtener lotes disponibles con validación adicional en tiempo real
    lotes_disponibles = Lotes.objects.filter(
        activo=True, 
        cantidad_actual__gt=0
    ).select_related('id_material', 'id_bodega_actual').order_by('numero_lote')
    
    # Re-validar las cantidades en tiempo real para evitar discrepancias
    lotes_validados = []
    for lote in lotes_disponibles:
        # Verificar que el lote realmente tenga stock disponible
        lote_actual = Lotes.objects.get(pk=lote.pk)
        if lote_actual.activo and lote_actual.cantidad_actual > 0:
            lotes_validados.append(lote_actual)
    
    # Preparar contexto para el formulario
    context = {
        'tipo_proceso': tipo_proceso_normalizado,
        'operarios': Operarios.objects.filter(activo=True),
        'maquinas': Maquinas.objects.filter(tipo_proceso=tipo_proceso_normalizado, activo=True),
        'materiales': Materiales.objects.all(),
        'bodegas': Bodegas.objects.all(),
        'lotes_disponibles': lotes_validados,
        'motivos_paro': MotivoParo.objects.all(),
    }
    
    if request.method == 'POST':
        # AÑADIR LOGGING DETALLADO PARA DEPURACIÓN
        import logging
        import json
        
        logger = logging.getLogger(__name__)
        logger.error("=== INICIO DEPURACIÓN VISTA WEB ===")
        
        # Log de todos los datos POST
        post_data = {}
        for key, value in request.POST.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                post_data[key] = list(value)
            else:
                post_data[key] = value
        
        logger.error(f"Datos POST recibidos: {json.dumps(post_data, indent=2, default=str)}")
        
        try:
            with transaction.atomic():
                logger.error("Iniciando transacción atómica")
                
                # Obtener datos del formulario
                operario = Operarios.objects.get(pk=request.POST.get('operario'))
                maquina = Maquinas.objects.get(pk=request.POST.get('maquina'))
                orden_trabajo = request.POST.get('orden_trabajo')
                turno = request.POST.get('turno')
                bodega_destino = Bodegas.objects.get(pk=request.POST.get('bodega_destino'))
                observaciones = request.POST.get('observaciones', '')
                archivo_adjunto = request.FILES.get('archivo_adjunto')
                
                logger.error(f"Datos básicos obtenidos: operario={operario.nombre_completo}, maquina={maquina.nombre}, OT={orden_trabajo}")
                
                # Obtener lotes y cantidades
                lotes_entrada = request.POST.getlist('lote_entrada[]')
                cantidades_entrada = request.POST.getlist('cantidad_entrada[]')
                
                logger.error(f"Lotes entrada: {lotes_entrada}")
                logger.error(f"Cantidades entrada: {cantidades_entrada}")
                
                # Validar que hay al menos un lote
                if not lotes_entrada:
                    logger.error("ERROR: No hay lotes de entrada")
                    raise ValidationError('Debe seleccionar al menos un lote de entrada')
                
                # Calcular cantidad total de entrada
                cantidad_total_entrada = Decimal('0')
                for cantidad in cantidades_entrada:
                    cantidad_total_entrada += Decimal(cantidad)
                
                logger.error(f"Cantidad total entrada: {cantidad_total_entrada}")
                
                # Por defecto, la cantidad de salida es igual a la de entrada
                # En la práctica, esto debería ajustarse según el proceso específico
                cantidad_total_salida = cantidad_total_entrada
                
                # Crear el lote de producción (excepto para inyección)
                nuevo_lote = None
                if tipo_proceso_normalizado != 'Inyeccion':
                    material_salida = Materiales.objects.get(pk=request.POST.get('material_salida'))
                    
                    # Generar número de lote único
                    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                    numero_lote_unico = f"{orden_trabajo}-{tipo_proceso_normalizado}-{timestamp}"
                    
                    logger.error(f"Creando lote de producción: {numero_lote_unico}")
                    
                    # CREAR EL LOTE DIRECTAMENTE SIN MOVIMIENTO DE INVENTARIO ADICIONAL
                    # El lote se crea con la cantidad correcta y YA está en inventario
                    nuevo_lote = Lotes.objects.create(
                        numero_lote=numero_lote_unico,
                        id_material=material_salida,
                        cantidad_inicial=cantidad_total_salida,
                        cantidad_actual=cantidad_total_salida,
                        id_bodega_actual=bodega_destino,
                        activo=True
                    )
                    
                    logger.error(f"Lote de producción creado: {nuevo_lote.id_lote}")
                
                # Procesar cada lote de entrada (SOLO CONSUMOS)
                logger.error("=== INICIANDO PROCESAMIENTO DE LOTES ===")
                
                for i, (lote_id, cantidad) in enumerate(zip(lotes_entrada, cantidades_entrada)):
                    logger.error(f"--- Procesando lote {i+1}/{len(lotes_entrada)} ---")
                    
                    # FORZAR RE-CONSULTA FRESH DEL LOTE para evitar problemas de cache
                    lote = Lotes.objects.select_for_update().get(pk=lote_id)
                    cantidad = Decimal(cantidad)
                    
                    logger.error(f"Lote obtenido (FRESH): {lote.numero_lote} (ID: {lote.id_lote})")
                    logger.error(f"Stock actual (FRESH): {lote.cantidad_actual}")
                    logger.error(f"Cantidad a procesar: {cantidad}")
                    logger.error(f"Activo (FRESH): {lote.activo}")
                    
                    # Validaciones básicas antes de procesar
                    if not lote.activo:
                        logger.error(f"ERROR: Lote {lote.numero_lote} no está activo")
                        raise ValidationError(f'El lote {lote.numero_lote} no está activo.')
                    
                    if cantidad <= 0:
                        logger.error(f"ERROR: Cantidad inválida {cantidad}")
                        raise ValidationError(f'La cantidad debe ser mayor que cero para el lote {lote.numero_lote}.')
                    
                    # VALIDACIÓN ADICIONAL DE STOCK ANTES DE PROCESAR
                    if lote.cantidad_actual < cantidad:
                        logger.error(f"ERROR: Stock insuficiente - Disponible: {lote.cantidad_actual}, Requerido: {cantidad}")
                        raise ValidationError(f'Stock insuficiente para el lote {lote.numero_lote}. Disponible: {lote.cantidad_actual}, requerido: {cantidad}')
                    
                    # El descuento de inventario ya no se realiza aquí.
                    # Se delega a la señal post_save asociada a ProduccionConsumo
                    # para evitar duplicar movimientos y garantizar consistencia.
                    logger.error(
                        "Validaciones completas OK - el movimiento de inventario "
                        "será procesado por la señal post_save de ProduccionConsumo"
                    )
                
                logger.error("=== LOTES PROCESADOS - REGISTRANDO PROCESO ===")

                # Registrar el proceso según su tipo
                proceso_data = {
                    'id_operario': operario,
                    'id_maquina': maquina,
                    'orden_trabajo': orden_trabajo,
                    'turno': turno,
                    'id_bodega_destino': bodega_destino,
                    'cantidad_entrada': cantidad_total_entrada,
                    'cantidad_salida': cantidad_total_salida,
                    'observaciones': observaciones,
                    'archivo_adjunto': archivo_adjunto
                }
                
                if nuevo_lote:
                    proceso_data['id_lote_producido'] = nuevo_lote
                
                # Crear el proceso correspondiente
                if tipo_proceso_normalizado == 'Molido':
                    proceso = ProduccionMolido.objects.create(**proceso_data)
                    logger.error(f"Proceso de molido creado: {proceso.id_produccion}")
                elif tipo_proceso_normalizado == 'Lavado':
                    proceso = ProduccionLavado.objects.create(**proceso_data)
                elif tipo_proceso_normalizado == 'Peletizado':
                    proceso_data['numero_mezclas'] = request.POST.get('numero_mezclas', 1)
                    proceso = ProduccionPeletizado.objects.create(**proceso_data)
                elif tipo_proceso_normalizado == 'Inyeccion':
                    proceso_data['numero_mezclas'] = request.POST.get('numero_mezclas', 1)
                    proceso = ProduccionInyeccion.objects.create(**proceso_data)

                logger.error("=== REGISTRANDO CONSUMOS ===")

                # Registrar consumos en la tabla ProduccionConsumo
                for lote_id, cantidad in zip(lotes_entrada, cantidades_entrada):
                    lote = Lotes.objects.get(pk=lote_id)
                    consumo_data = {
                        'id_lote_consumido': lote,
                        'cantidad_consumida': Decimal(cantidad),
                        'id_bodega_origen': lote.id_bodega_actual,
                    }
                    
                    # Asignar el proceso correspondiente
                    if tipo_proceso_normalizado == 'Molido':
                        consumo_data['id_produccion_molido'] = proceso
                    elif tipo_proceso_normalizado == 'Lavado':
                        consumo_data['id_produccion_lavado'] = proceso
                    elif tipo_proceso_normalizado == 'Peletizado':
                        consumo_data['id_produccion_peletizado'] = proceso
                    elif tipo_proceso_normalizado == 'Inyeccion':
                        consumo_data['id_produccion_inyeccion'] = proceso
                    
                    consumo = ProduccionConsumo.objects.create(**consumo_data)
                    logger.error(f"Consumo registrado: {consumo.id_consumo}")
                
                logger.error("=== PROCESO COMPLETADO EXITOSAMENTE ===")
                messages.success(request, f'Proceso de {tipo_proceso_normalizado} registrado exitosamente.')
                return redirect('gestion:produccion_dashboard')
            
        except ValidationError as e:
            logger.error(f"ValidationError: {str(e)}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Exception general: {str(e)}")
            logger.error(f"Tipo: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
            ProduccionMolido.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_salida'))['total'] or 0 +
            ProduccionLavado.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_salida'))['total'] or 0 +
            ProduccionPeletizado.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_salida'))['total'] or 0 +
            ProduccionInyeccion.objects.filter(filtro_fecha).aggregate(total=Sum('cantidad_salida'))['total'] or 0
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

@login_required
@transaction.atomic
def registrar_paro_molido(request, id_produccion):
    """Vista para registrar un paro en la producción de molido."""
    produccion = get_object_or_404(ProduccionMolido, pk=id_produccion)
    if request.method == 'POST':
        try:
            paro = ParosProduccion.objects.create(
                id_produccion_molido=produccion,
                fecha_hora_inicio=request.POST.get('fecha_hora_inicio'),
                fecha_hora_fin=request.POST.get('fecha_hora_fin'),
                motivo=request.POST.get('motivo'),
                id_operario_reporta=Operarios.objects.get(pk=request.POST.get('id_operario_reporta')),
                observaciones=request.POST.get('observaciones')
            )
            messages.success(request, 'Paro registrado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al registrar el paro: {str(e)}')
    return redirect('gestion:produccion_molido')

@login_required
@transaction.atomic
def eliminar_paro(request, id_paro):
    """Vista para eliminar un paro de producción."""
    paro = get_object_or_404(ParosProduccion, pk=id_paro)
    if request.method == 'POST':
        try:
            tipo_proceso = None
            if paro.id_produccion_molido:
                tipo_proceso = 'molido'
            elif paro.id_produccion_lavado:
                tipo_proceso = 'lavado'
            elif paro.id_produccion_peletizado:
                tipo_proceso = 'peletizado'
            elif paro.id_produccion_inyeccion:
                tipo_proceso = 'inyeccion'
            
            paro.delete()
            messages.success(request, 'Paro eliminado exitosamente.')
            
            if tipo_proceso:
                return redirect(f'gestion:produccion_{tipo_proceso}')
        except Exception as e:
            messages.error(request, f'Error al eliminar el paro: {str(e)}')
    return redirect('gestion:produccion_dashboard')

@login_required
@transaction.atomic
def registrar_paro_lavado(request, id_produccion):
    """Vista para registrar un paro en la producción de lavado."""
    produccion = get_object_or_404(ProduccionLavado, pk=id_produccion)
    if request.method == 'POST':
        try:
            paro = ParosProduccion.objects.create(
                id_produccion_lavado=produccion,
                fecha_hora_inicio=request.POST.get('fecha_hora_inicio'),
                fecha_hora_fin=request.POST.get('fecha_hora_fin'),
                motivo=request.POST.get('motivo'),
                id_operario_reporta=Operarios.objects.get(pk=request.POST.get('id_operario_reporta')),
                observaciones=request.POST.get('observaciones')
            )
            messages.success(request, 'Paro registrado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al registrar el paro: {str(e)}')
    return redirect('gestion:produccion_lavado')

@login_required
@transaction.atomic
def registrar_paro_peletizado(request, id_produccion):
    """Vista para registrar un paro en la producción de peletizado."""
    produccion = get_object_or_404(ProduccionPeletizado, pk=id_produccion)
    if request.method == 'POST':
        try:
            paro = ParosProduccion.objects.create(
                id_produccion_peletizado=produccion,
                fecha_hora_inicio=request.POST.get('fecha_hora_inicio'),
                fecha_hora_fin=request.POST.get('fecha_hora_fin'),
                motivo=request.POST.get('motivo'),
                id_operario_reporta=Operarios.objects.get(pk=request.POST.get('id_operario_reporta')),
                observaciones=request.POST.get('observaciones')
            )
            messages.success(request, 'Paro registrado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al registrar el paro: {str(e)}')
    return redirect('gestion:produccion_peletizado')

@login_required
@transaction.atomic
def registrar_paro_inyeccion(request, id_produccion):
    """Vista para registrar un paro en la producción de inyección."""
    produccion = get_object_or_404(ProduccionInyeccion, pk=id_produccion)
    if request.method == 'POST':
        try:
            paro = ParosProduccion.objects.create(
                id_produccion_inyeccion=produccion,
                fecha_hora_inicio=request.POST.get('fecha_hora_inicio'),
                fecha_hora_fin=request.POST.get('fecha_hora_fin'),
                motivo=request.POST.get('motivo'),
                id_operario_reporta=Operarios.objects.get(pk=request.POST.get('id_operario_reporta')),
                observaciones=request.POST.get('observaciones')
            )
            messages.success(request, 'Paro registrado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al registrar el paro: {str(e)}')
    return redirect('gestion:produccion_inyeccion')

@login_required
def motivos_paro(request):
    """Vista para gestionar los motivos de paro."""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            MotivoParo.objects.create(nombre=nombre)
            messages.success(request, 'Motivo de paro creado exitosamente.')
            return redirect('gestion:motivos_paro')
        except Exception as e:
            messages.error(request, f'Error al crear el motivo de paro: {str(e)}')
    
    motivos = MotivoParo.objects.all()
    context = {
        'motivos': motivos,
    }
    return render(request, 'gestion/motivos_paro.html', context)

@login_required
@transaction.atomic
def editar_motivo_paro(request, id):
    """Vista para editar un motivo de paro."""
    motivo = get_object_or_404(MotivoParo, pk=id)
    if request.method == 'POST':
        try:
            motivo.nombre = request.POST.get('nombre')
            motivo.save()
            messages.success(request, 'Motivo de paro actualizado exitosamente.')
            return redirect('gestion:motivos_paro')
        except Exception as e:
            messages.error(request, f'Error al actualizar el motivo de paro: {str(e)}')
    
    context = {
        'motivo': motivo,
    }
    return render(request, 'gestion/motivos_paro.html', context)

@login_required
@transaction.atomic
def eliminar_motivo_paro(request, id):
    """Vista para eliminar un motivo de paro."""
    motivo = get_object_or_404(MotivoParo, pk=id)
    if request.method == 'POST':
        try:
            motivo.delete()
            messages.success(request, 'Motivo de paro eliminado exitosamente.')
            return redirect('gestion:motivos_paro')
        except Exception as e:
            messages.error(request, f'Error al eliminar el motivo de paro: {str(e)}')
    return redirect('gestion:motivos_paro')

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
def despacho_form(request):
    """Vista para gestionar el despacho de materiales a clientes."""
    # Obtener lote preseleccionado si viene en la URL
    lote_id = request.GET.get('lote')
    lote_preseleccionado = None
    if (lote_id):
        lote_preseleccionado = get_object_or_404(Lotes, pk=lote_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                lote = get_object_or_404(Lotes, pk=request.POST.get('id_lote'))
                cantidad = Decimal(request.POST.get('cantidad'))
                destino_tercero = get_object_or_404(Terceros, pk=request.POST.get('id_destino_tercero'))
                consecutivo_soporte = request.POST.get('consecutivo_soporte')
                observaciones = request.POST.get('observaciones')

                # Procesar el despacho como un movimiento de inventario
                procesar_movimiento_inventario(
                    tipo_movimiento='Venta',
                    lote=lote,
                    cantidad=cantidad,
                    bodega_origen=lote.id_bodega_actual,
                    id_destino_tercero=destino_tercero,
                    consecutivo_soporte=consecutivo_soporte,
                    observaciones=observaciones,
                    usuario=request.user
                )

                messages.success(request, f'Despacho realizado exitosamente. Remisión/Factura: {consecutivo_soporte}')
                return redirect('gestion:inventario_global')

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al procesar el despacho: {str(e)}')
            
    # Preparar datos para el formulario
    lotes_disponibles = Lotes.objects.filter(activo=True).exclude(pk=lote_id) if lote_id else Lotes.objects.filter(activo=True)
    clientes = Terceros.objects.filter(activo=True).order_by('nombre')

    context = {
        'lote_preseleccionado': lote_preseleccionado,
        'lotes_disponibles': lotes_disponibles,
        'clientes': clientes,
    }
    return render(request, 'gestion/despacho_form.html', context)

@login_required
def despachos(request):
    """Vista para mostrar y filtrar los despachos realizados."""
    # Iniciar con todos los despachos (movimientos tipo Venta)
    despachos = MovimientosInventario.objects.filter(
        tipo_movimiento='Venta'
    ).select_related(
        'id_lote',
        'id_lote__id_material',
        'id_destino_tercero'
    ).order_by('-fecha')

    # Aplicar filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    cliente = request.GET.get('cliente')

    if fecha_inicio:
        despachos = despachos.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        despachos = despachos.filter(fecha__date__lte=fecha_fin)
    if cliente:
        despachos = despachos.filter(id_destino_tercero_id=cliente)

    # Obtener lista de clientes para el filtro
    clientes = Terceros.objects.filter(tipo='Cliente', activo=True).order_by('nombre')

    context = {
        'despachos': despachos,
        'clientes': clientes,
    }
    return render(request, 'gestion/despachos.html', context)

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

@login_required
def test_proceso_directo(request):
    """Vista de prueba para procesar un lote directamente sin formulario."""
    if request.method == 'GET':
        # Mostrar información del lote y botón para procesarlo
        lote = Lotes.objects.filter(numero_lote='1-Lavado-20250529201736').first()
        
        context = {
            'lote': lote,
            'mensaje': 'Esta es una vista de prueba para procesar el lote directamente'
        }
        
        return render(request, 'gestion/test_proceso.html', context)
    
    elif request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Log inicial
            logger.error("=== INICIO PRUEBA PROCESO DIRECTO ===")
            
            # Obtener el lote específico
            lote = Lotes.objects.select_for_update().get(numero_lote='1-Lavado-20250529201736')
            logger.error(f"Lote obtenido: {lote.numero_lote}")
            logger.error(f"Stock antes: {lote.cantidad_actual}")
            logger.error(f"Activo: {lote.activo}")
            
            # Procesar directamente
            cantidad = Decimal('0.5')  # Cantidad fija para prueba
            
            with transaction.atomic():
                logger.error("Iniciando transacción atómica")
                
                # Verificar stock nuevamente dentro de la transacción
                lote.refresh_from_db()
                logger.error(f"Stock después de refresh: {lote.cantidad_actual}")
                
                if lote.cantidad_actual < cantidad:
                    logger.error(f"ERROR: Stock insuficiente - Disponible: {lote.cantidad_actual}, Requerido: {cantidad}")
                    raise ValidationError(f'Stock insuficiente. Disponible: {lote.cantidad_actual}, Requerido: {cantidad}')
                
                logger.error("Llamando a procesar_movimiento_inventario...")
                
                movimiento = procesar_movimiento_inventario(
                    tipo_movimiento='ConsumoProduccion',
                    lote=lote,
                    cantidad=cantidad,
                    bodega_origen=lote.id_bodega_actual,
                    bodega_destino=None,
                    produccion_referencia='TEST-DIRECTO',
                    observaciones='Prueba de proceso directo'
                )
                
                logger.error(f"✓ Movimiento procesado: {movimiento.id_movimiento}")
                
                # Verificar estado final
                lote.refresh_from_db()
                logger.error(f"Stock después: {lote.cantidad_actual}")
                logger.error(f"Activo después: {lote.activo}")
                
                messages.success(request, f'Proceso directo completado exitosamente. Movimiento: {movimiento.id_movimiento}')
            
        except Exception as e:
            logger.error(f"ERROR en proceso directo: {str(e)}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            messages.error(request, f'Error en proceso directo: {str(e)}')
        
        return redirect('gestion:test_proceso_directo')
