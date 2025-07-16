from django.urls import path
from . import views
from .views import api
from .views import crm

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
    path('produccion/homogeneizacion/', views.produccion_homogeneizacion, name='produccion_homogeneizacion'),
    
    # Edición y eliminación de procesos
    path('produccion/molido/editar/<uuid:id>/', views.editar_produccion_molido, name='editar_produccion_molido'),
    path('produccion/lavado/editar/<uuid:id>/', views.editar_produccion_lavado, name='editar_produccion_lavado'),
    path('produccion/peletizado/editar/<uuid:id>/', views.editar_produccion_peletizado, name='editar_produccion_peletizado'),
    path('produccion/inyeccion/editar/<uuid:id>/', views.editar_produccion_inyeccion, name='editar_produccion_inyeccion'),
    path('produccion/homogeneizacion/editar/<uuid:id>/', views.editar_produccion_homogeneizacion, name='editar_produccion_homogeneizacion'),
    
    path('produccion/molido/eliminar/<uuid:id>/', views.eliminar_produccion_molido, name='eliminar_produccion_molido'),
    path('produccion/lavado/eliminar/<uuid:id>/', views.eliminar_produccion_lavado, name='eliminar_produccion_lavado'),
    path('produccion/peletizado/eliminar/<uuid:id>/', views.eliminar_produccion_peletizado, name='eliminar_produccion_peletizado'),
    path('produccion/inyeccion/eliminar/<uuid:id>/', views.eliminar_produccion_inyeccion, name='eliminar_produccion_inyeccion'),
    path('produccion/homogeneizacion/eliminar/<uuid:id>/', views.eliminar_produccion_homogeneizacion, name='eliminar_produccion_homogeneizacion'),
    
    # URLs para Paros de Producción
    path('produccion/molido/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_molido, name='registrar_paro_molido'),
    path('produccion/lavado/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_lavado, name='registrar_paro_lavado'),
    path('produccion/peletizado/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_peletizado, name='registrar_paro_peletizado'),
    path('produccion/inyeccion/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_inyeccion, name='registrar_paro_inyeccion'),
    path('produccion/homogeneizacion/<uuid:id_produccion>/registrar-paro/', views.registrar_paro_homogeneizacion, name='registrar_paro_homogeneizacion'),
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
    
    # URLs del CRM
    path('crm/', crm.crm_dashboard, name='crm_dashboard'),
    path('crm/clientes/', crm.clientes_list, name='clientes_list'),
    path('crm/clientes/nuevo/', crm.cliente_create, name='cliente_create'),
    path('crm/clientes/<uuid:id_cliente>/', crm.cliente_detail, name='cliente_detail'),
    path('crm/clientes/<uuid:id_cliente>/editar/', crm.cliente_edit, name='cliente_edit'),
    path('crm/clientes/<uuid:id_cliente>/contacto/nuevo/', crm.contacto_create, name='contacto_create'),
    path('crm/clientes/<uuid:id_cliente>/interaccion/nueva/', crm.interaccion_create, name='interaccion_create'),
    path('crm/oportunidades/', crm.oportunidades_list, name='oportunidades_list'),
    path('crm/oportunidades/nueva/', crm.oportunidad_create, name='oportunidad_create'),
    path('crm/oportunidades/<uuid:id_oportunidad>/', crm.oportunidad_detail, name='oportunidad_detail'),
    path('crm/oportunidades/<uuid:id_oportunidad>/editar/', crm.oportunidad_edit, name='oportunidad_edit'),
    path('crm/interacciones/', crm.interacciones_timeline, name='interacciones_timeline'),
    
    # API endpoints del CRM
    path('api/crm/contactos-por-cliente/', crm.get_contactos_by_cliente, name='get_contactos_by_cliente'),
    
    # URLs de Pedidos
    path('pedidos/', views.pedidos_dashboard, name='pedidos_dashboard'),
    path('pedidos/lista/', views.pedidos_list, name='pedidos_list'),
    path('pedidos/nuevo/', views.pedido_create, name='pedido_create'),
    path('pedidos/<uuid:id_pedido>/', views.pedido_detail, name='pedido_detail'),
    path('pedidos/<uuid:id_pedido>/editar/', views.pedido_edit, name='pedido_edit'),
    path('pedidos/<uuid:id_pedido>/cambiar-estado/', views.pedido_cambiar_estado, name='pedido_cambiar_estado'),
    path('pedidos/<uuid:id_pedido>/generar-orden/', views.generar_orden_produccion, name='generar_orden_produccion'),
    
    # API endpoints de Pedidos
    path('api/materiales/info/', views.get_materiales_info, name='get_materiales_info'),
    
    # URLs de Órdenes de Producción
    path('ordenes/', views.ordenes_dashboard, name='ordenes_dashboard'),
    path('ordenes/lista/', views.ordenes_list, name='ordenes_list'),
    path('ordenes/<uuid:id_orden>/', views.orden_detail, name='orden_detail'),
    path('ordenes/<uuid:id_orden>/planificar/', views.planificar_procesos, name='planificar_procesos'),
    path('ordenes/<uuid:id_orden>/cambiar-estado/', views.cambiar_estado_orden, name='cambiar_estado_orden'),
    path('ordenes/proceso/<uuid:id_planificacion>/actualizar/', views.actualizar_progreso_proceso, name='actualizar_progreso_proceso'),
    path('ordenes/calendario/', views.calendario_produccion, name='calendario_produccion'),
    
    # URLs de Tareas
    path('tareas/', views.tareas_dashboard, name='tareas_dashboard'),
    path('tareas/mis-tareas/', views.mis_tareas, name='mis_tareas'),
    path('tareas/equipo/', views.tareas_equipo, name='tareas_equipo'),
    path('tareas/nueva/', views.tarea_create, name='tarea_create'),
    path('tareas/<uuid:id_tarea>/', views.tarea_detail, name='tarea_detail'),
    path('tareas/<uuid:id_tarea>/editar/', views.tarea_edit, name='tarea_edit'),
    path('tareas/<uuid:id_tarea>/cambiar-estado/', views.cambiar_estado_tarea, name='cambiar_estado_tarea'),
    path('tareas/subtarea/<uuid:id_subtarea>/toggle/', views.toggle_subtarea, name='toggle_subtarea'),
    path('tareas/<uuid:id_tarea>/comentario/', views.agregar_comentario, name='agregar_comentario'),
    path('tareas/calendario/', views.calendario_tareas, name='calendario_tareas'),
    path('tareas/plantillas/', views.plantillas_list, name='plantillas_list'),
    path('tareas/plantillas/nueva/', views.plantilla_create, name='plantilla_create'),
    
    # URLs de PQRS
    path('pqrs/', views.pqrs_dashboard, name='pqrs_dashboard'),
    path('pqrs/lista/', views.pqrs_list, name='pqrs_list'),
    path('pqrs/nueva/', views.pqrs_create, name='pqrs_create'),
    path('pqrs/mis-pqrs/', views.mis_pqrs, name='mis_pqrs'),
    path('pqrs/<uuid:pqrs_id>/', views.pqrs_detail, name='pqrs_detail'),
    path('pqrs/<uuid:pqrs_id>/editar/', views.pqrs_edit, name='pqrs_edit'),
    path('pqrs/<uuid:pqrs_id>/seguimiento/', views.agregar_seguimiento, name='agregar_seguimiento'),
    path('pqrs/<uuid:pqrs_id>/cambiar-estado/', views.cambiar_estado_pqrs, name='cambiar_estado_pqrs'),
]