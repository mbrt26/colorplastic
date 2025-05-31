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

