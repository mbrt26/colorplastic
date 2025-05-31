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
