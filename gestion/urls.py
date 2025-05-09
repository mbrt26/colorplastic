from django.urls import path
from . import views

app_name = 'gestion'

urlpatterns = [
    # Dashboard y vistas principales
    path('', views.dashboard, name='dashboard'),
    path('bodega/<uuid:bodega_id>/', views.inventario_bodega, name='inventario_bodega'),
    path('traslado/', views.traslado_form, name='traslado_form'),
    
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
]