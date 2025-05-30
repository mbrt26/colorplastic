from django.urls import path
from . import views
from .views import api

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
    path('materiales/plantilla-excel/', views.generar_plantilla_materiales, name='generar_plantilla_materiales'),
    path('materiales/importar-excel/', views.importar_materiales_excel, name='importar_materiales_excel'),
    
    path('operarios/', views.operarios, name='operarios'),
    path('operarios/editar/<uuid:id>/', views.editar_operario, name='editar_operario'),
    path('operarios/eliminar/<uuid:id>/', views.eliminar_operario, name='eliminar_operario'),
    path('operarios/plantilla-excel/', views.generar_plantilla_operarios, name='generar_plantilla_operarios'),
    path('operarios/importar-excel/', views.importar_operarios_excel, name='importar_operarios_excel'),
    
    path('terceros/', views.terceros, name='terceros'),
    path('terceros/editar/<uuid:id>/', views.editar_tercero, name='editar_tercero'),
    path('terceros/eliminar/<uuid:id>/', views.eliminar_tercero, name='eliminar_tercero'),
    path('terceros/plantilla-excel/', views.generar_plantilla_terceros, name='generar_plantilla_terceros'),
    path('terceros/importar-excel/', views.importar_terceros_excel, name='importar_terceros_excel'),

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

    # Módulo de ingreso de materiales
    path('ingreso-materiales/', views.ingreso_materiales, name='ingreso_materiales'),
    path('ingreso-materiales/procesar/', views.procesar_ingreso_material, name='procesar_ingreso_material'),
    path('ingreso-materiales/detalle/<uuid:movimiento_id>/', views.detalle_ingreso_material, name='detalle_ingreso_material'),

    # Despachos de materiales
    path('despachos/', views.despachos, name='despachos'),
    path('despacho/<int:id>/', views.detalle_despacho, name='detalle_despacho'),
    path('despacho/<int:id>/editar/', views.editar_despacho, name='editar_despacho'),
    path('despacho/<int:id>/cambiar-estado/', views.cambiar_estado_despacho, name='cambiar_estado_despacho'),
    path('despacho/detalle/eliminar/<int:id>/', views.eliminar_detalle_despacho, name='eliminar_detalle_despacho'),
    
    # API endpoints
    path('api/buscar-operarios/', api.buscar_operarios, name='buscar_operarios'),
    path('api/verificar-stock/<uuid:lote_id>/', api.verificar_stock, name='verificar_stock_new'),
    
    # API endpoints para ingreso de materiales
    path('api/buscar-proveedores/', views.buscar_proveedores, name='buscar_proveedores'),
    path('api/verificar-numero-lote/', views.verificar_numero_lote, name='verificar_numero_lote'),
    
    # Vista de prueba para diagnóstico
    path('test-proceso-directo/', views.test_proceso_directo, name='test_proceso_directo'),
]