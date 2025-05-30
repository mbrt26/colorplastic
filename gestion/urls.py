from django.urls import path
from . import views
from .views import (
    DespachoListView, DespachoCreateView, DespachoUpdateView, DespachoDetailView,
    DespachoForm, DetalleDespachoFormSet
)

app_name = 'gestion'

urlpatterns = [
    # Dashboard y vistas principales
    path('', views.dashboard, name='dashboard'),
    path('bodega/<uuid:bodega_id>/', views.inventario_bodega, name='inventario_bodega'),
    path('traslado/', views.traslado_form, name='traslado_form'),
    path('despachos/', DespachoListView.as_view(), name='despachos'),  # Añadido para compatibilidad
    path('despacho/', DespachoListView.as_view(), name='despacho_list'),
    path('despacho/crear/', DespachoCreateView.as_view(), name='despacho_create'),
    path('despacho/<int:pk>/editar/', DespachoUpdateView.as_view(), name='despacho_update'),
    path('despacho/<int:pk>/detalle/', DespachoDetailView.as_view(), name='despacho_detail'),
    
    # Producción
    path('produccion/', views.produccion_dashboard, name='produccion_dashboard'),
    path('produccion/nuevo/<str:tipo_proceso>/', views.nuevo_proceso_produccion, name='nuevo_proceso_produccion'),
    path('produccion/residuos/', views.residuos_produccion, name='residuos_produccion'),
    path('produccion/consumos/', views.produccion_consumo, name='produccion_consumo'),
    
    # Vistas de procesos específicos
    path('produccion/molido/', views.produccion_molido, name='produccion_molido'),
    path('produccion/lavado/', views.produccion_lavado, name='produccion_lavado'),
    path('produccion/peletizado/', views.produccion_peletizado, name='produccion_peletizado'),
    path('produccion/inyeccion/', views.produccion_inyeccion, name='produccion_inyeccion'),
    
    # Edición y eliminación de procesos
    path('produccion/molido/editar/<uuid:id>/', views.editar_produccion_molido, name='editar_produccion_molido'),
    path('produccion/lavado/editar/<uuid:id>/', views.editar_produccion_lavado, name='editar_produccion_lavado'),
    path('produccion/peletizado/editar/<uuid:id>/', views.editar_produccion_peletizado, name='editar_produccion_peletizado'),
    path('produccion/inyeccion/editar/<uuid:id>/', views.editar_produccion_inyeccion, name='editar_produccion_inyeccion'),
    
    path('produccion/molido/eliminar/<uuid:id>/', views.eliminar_produccion_molido, name='eliminar_produccion_molido'),
    path('produccion/lavado/eliminar/<uuid:id>/', views.eliminar_produccion_lavado, name='eliminar_produccion_lavado'),
    path('produccion/peletizado/eliminar/<uuid:id>/', views.eliminar_produccion_peletizado, name='eliminar_produccion_peletizado'),
    path('produccion/inyeccion/eliminar/<uuid:id>/', views.eliminar_produccion_inyeccion, name='eliminar_produccion_inyeccion'),
    
    # URLs para Paros de Producción
    path('produccion/molido/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_molido, name='registrar_paro_molido'),
    path('produccion/lavado/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_lavado, name='registrar_paro_lavado'),
    path('produccion/peletizado/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_peletizado, name='registrar_paro_peletizado'),
    path('produccion/inyeccion/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_inyeccion, name='registrar_paro_inyeccion'),
    path('eliminar-paro/<uuid:id_paro>/', views.eliminar_paro, name='eliminar_paro'),

    # Gestión de residuos
    path('residuos/editar/<uuid:id>/', views.editar_residuo, name='editar_residuo'),
    path('residuos/eliminar/<uuid:id>/', views.eliminar_residuo, name='eliminar_residuo'),
    
    # URLs de Administración - CRUD
    path('lotes/', views.lotes, name='lotes'),
    path('lotes/editar/<uuid:id>/', views.editar_lote, name='editar_lote'),
    path('lotes/eliminar/<uuid:id>/', views.eliminar_lote, name='eliminar_lote'),
    
    path('maquinas/', views.maquinas, name='maquinas'),
    path('maquinas/editar/<uuid:id>/', views.editar_maquina, name='editar_maquina'),
    path('maquinas/eliminar/<uuid:id>/', views.eliminar_maquina, name='eliminar_maquina'),
    
    path('materiales/', views.materiales, name='materiales'),
    path('materiales/editar/<uuid:id>/', views.editar_material, name='editar_material'),
    path('materiales/eliminar/<uuid:id>/', views.eliminar_material, name='eliminar_material'),
    
    path('operarios/', views.operarios, name='operarios'),
    path('operarios/editar/<uuid:id>/', views.editar_operario, name='editar_operario'),
    path('operarios/eliminar/<uuid:id>/', views.eliminar_operario, name='eliminar_operario'),
    
    path('terceros/', views.terceros, name='terceros'),
    path('terceros/editar/<uuid:id>/', views.editar_tercero, name='editar_tercero'),
    path('terceros/eliminar/<uuid:id>/', views.eliminar_tercero, name='eliminar_tercero'),

    # Gestión de bodegas
    path('bodegas/', views.bodegas, name='bodegas'),
    path('bodegas/editar/<uuid:id>/', views.editar_bodega, name='editar_bodega'),
    path('bodegas/eliminar/<uuid:id>/', views.eliminar_bodega, name='eliminar_bodega'),

    # Gestión de motivos de paro
    path('motivos-paro/', views.motivos_paro, name='motivos_paro'),
    path('motivos-paro/editar/<uuid:id>/', views.editar_motivo_paro, name='editar_motivo_paro'),
    path('motivos-paro/eliminar/<uuid:id>/', views.eliminar_motivo_paro, name='eliminar_motivo_paro'),

    # Inventario global
    path('inventario/global/', views.inventario_global, name='inventario_global'),
    
    # Despacho form
    path('despacho/form/', views.despacho_form, name='despacho_form'),
    path('despachos/list/', views.despachos, name='despachos_list'),
    
    # API endpoints
    path('api/verificar-stock/<uuid:lote_id>/', views.verificar_stock_api, name='verificar_stock_api'),
    
    # Vista de prueba para diagnóstico
    path('test-proceso-directo/', views.test_proceso_directo, name='test_proceso_directo'),
]