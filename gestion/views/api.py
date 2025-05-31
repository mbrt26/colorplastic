"""API endpoints for the gestion app."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from ..models import Operarios, Lotes

@login_required
@require_GET
def buscar_operarios(request):
    """Buscar operarios por nombre para autocompletado."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'operarios': []})
    
    # Buscar operarios activos que coincidan con la consulta
    operarios = Operarios.objects.filter(
        activo=True,
        nombre_completo__icontains=query
    ).values('id_operario', 'nombre_completo', 'codigo').order_by('nombre_completo')[:10]
    
    # Convertir a lista para el JSON
    operarios_list = list(operarios)
    
    return JsonResponse({'operarios': operarios_list})

@login_required
@require_GET
def verificar_stock(request, lote_id):
    """Verificar stock actual de un lote en tiempo real."""
    try:
        lote = Lotes.objects.get(pk=lote_id, activo=True)
        return JsonResponse({
            'stock_actual': float(lote.cantidad_actual),
            'numero_lote': lote.numero_lote
        })
    except Lotes.DoesNotExist:
        return JsonResponse({'error': 'Lote no encontrado'}, status=404)

