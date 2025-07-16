from .dashboard import dashboard, produccion_dashboard
from .inventario import (
    inventario_bodega, traslado_form, inventario_global,
    ingreso_materiales, procesar_ingreso_material, detalle_ingreso_material,
    buscar_proveedores, verificar_numero_lote
)
from .produccion import (
    nuevo_proceso_produccion, produccion_consumo, produccion_lavado,
    produccion_peletizado, residuos_produccion, editar_produccion_lavado,
    editar_produccion_peletizado, eliminar_produccion_lavado,
    eliminar_produccion_peletizado, editar_residuo, eliminar_residuo,
    produccion_molido, produccion_inyeccion, editar_produccion_molido,
    editar_produccion_inyeccion, eliminar_produccion_molido,
    eliminar_produccion_inyeccion, registrar_paro_molido, registrar_paro_lavado,
    registrar_paro_peletizado, registrar_paro_inyeccion, eliminar_paro,
    produccion_homogeneizacion, editar_produccion_homogeneizacion,
    eliminar_produccion_homogeneizacion, registrar_paro_homogeneizacion,
    test_proceso_directo
)
from .administracion import (
    lotes, editar_lote, eliminar_lote, maquinas, editar_maquina,
    eliminar_maquina, materiales, editar_material, eliminar_material,
    operarios, editar_operario, eliminar_operario, terceros, editar_tercero,
    eliminar_tercero, bodegas, editar_bodega, eliminar_bodega,
    motivos_paro, editar_motivo_paro, eliminar_motivo_paro,
    generar_plantilla_materiales, importar_materiales_excel,
    generar_plantilla_operarios, importar_operarios_excel,
    generar_plantilla_terceros, importar_terceros_excel
)
from .despachos import despachos, detalle_despacho, eliminar_detalle_despacho, editar_despacho, cambiar_estado_despacho
from .crm import (
    crm_dashboard, clientes_list, cliente_detail, cliente_create, cliente_edit,
    oportunidades_list, oportunidad_create, get_contactos_by_cliente,
    contacto_create, interaccion_create, oportunidad_detail, oportunidad_edit,
    interacciones_timeline
)
from .pedidos import (
    pedidos_dashboard, pedidos_list, pedido_detail, pedido_create, pedido_edit,
    pedido_cambiar_estado, generar_orden_produccion, get_materiales_info
)
from .ordenes_produccion import (
    ordenes_dashboard, ordenes_list, orden_detail, planificar_procesos,
    actualizar_progreso_proceso, calendario_produccion, cambiar_estado_orden
)
from .tareas import (
    tareas_dashboard, mis_tareas, tareas_equipo, tarea_detail, tarea_create,
    tarea_edit, cambiar_estado_tarea, toggle_subtarea, agregar_comentario,
    calendario_tareas, plantillas_list, plantilla_create
)
from .pqrs import (
    pqrs_dashboard, pqrs_list, pqrs_detail, pqrs_create, pqrs_edit,
    agregar_seguimiento, cambiar_estado_pqrs, mis_pqrs
)

__all__ = [
    'dashboard', 'produccion_dashboard',
    'inventario_bodega', 'traslado_form', 'inventario_global',
    'ingreso_materiales', 'procesar_ingreso_material', 'detalle_ingreso_material',
    'buscar_proveedores', 'verificar_numero_lote',
    'nuevo_proceso_produccion', 'produccion_consumo', 'produccion_lavado',
    'produccion_peletizado', 'residuos_produccion', 'editar_produccion_lavado',
    'editar_produccion_peletizado', 'eliminar_produccion_lavado',
    'eliminar_produccion_peletizado', 'editar_residuo', 'eliminar_residuo',
    'produccion_molido', 'produccion_inyeccion', 'editar_produccion_molido',
    'editar_produccion_inyeccion', 'eliminar_produccion_molido',
    'eliminar_produccion_inyeccion', 'registrar_paro_molido',
    'registrar_paro_lavado', 'registrar_paro_peletizado',
    'registrar_paro_inyeccion', 'eliminar_paro', 'produccion_homogeneizacion',
    'editar_produccion_homogeneizacion', 'eliminar_produccion_homogeneizacion',
    'registrar_paro_homogeneizacion', 'test_proceso_directo',
    'lotes', 'editar_lote', 'eliminar_lote', 'maquinas', 'editar_maquina',
    'eliminar_maquina', 'materiales', 'editar_material', 'eliminar_material',
    'operarios', 'editar_operario', 'eliminar_operario', 'terceros',
    'editar_tercero', 'eliminar_tercero', 'bodegas', 'editar_bodega',
    'eliminar_bodega', 'motivos_paro', 'editar_motivo_paro',
    'eliminar_motivo_paro', 'generar_plantilla_materiales', 'importar_materiales_excel',
    'generar_plantilla_operarios', 'importar_operarios_excel',
    'generar_plantilla_terceros', 'importar_terceros_excel',
    'despachos', 'detalle_despacho', 'eliminar_detalle_despacho', 'editar_despacho', 'cambiar_estado_despacho',
    'crm_dashboard', 'clientes_list', 'cliente_detail', 'cliente_create', 'cliente_edit',
    'oportunidades_list', 'oportunidad_create', 'get_contactos_by_cliente',
    'contacto_create', 'interaccion_create', 'oportunidad_detail', 'oportunidad_edit',
    'interacciones_timeline',
    'pedidos_dashboard', 'pedidos_list', 'pedido_detail', 'pedido_create', 'pedido_edit',
    'pedido_cambiar_estado', 'generar_orden_produccion', 'get_materiales_info',
    'ordenes_dashboard', 'ordenes_list', 'orden_detail', 'planificar_procesos',
    'actualizar_progreso_proceso', 'calendario_produccion', 'cambiar_estado_orden',
    'tareas_dashboard', 'mis_tareas', 'tareas_equipo', 'tarea_detail', 'tarea_create',
    'tarea_edit', 'cambiar_estado_tarea', 'toggle_subtarea', 'agregar_comentario',
    'calendario_tareas', 'plantillas_list', 'plantilla_create',
    'pqrs_dashboard', 'pqrs_list', 'pqrs_detail', 'pqrs_create', 'pqrs_edit',
    'agregar_seguimiento', 'cambiar_estado_pqrs', 'mis_pqrs'
]
