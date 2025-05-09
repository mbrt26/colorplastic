from django.contrib import admin
# Updated import to include all models
from .models import (
    Materiales, Bodegas, Terceros, Operarios, Maquinas, Lotes, MovimientosInventario,
    ProduccionMolido, ProduccionLavado, ProduccionPeletizado, ProduccionInyeccion,
    ProduccionConsumo, ParosProduccion, ResiduosProduccion
)

# Register your models here.

# --- Inline Admin Classes ---

class ProduccionConsumoInline(admin.TabularInline):
    model = ProduccionConsumo
    extra = 1 # Number of extra forms to add consumptions
    autocomplete_fields = ['id_lote_consumido', 'id_bodega_origen']
    readonly_fields = [] # Could make some fields readonly if needed
    fields = ('id_lote_consumido', 'cantidad_consumida', 'id_bodega_origen') # Define field order/inclusion
    verbose_name = "Consumo de Material"
    verbose_name_plural = "Consumos de Materiales"

# Specific inlines for each production type using the correct fk_name
class ProduccionConsumoMolidoInline(ProduccionConsumoInline):
    fk_name = 'id_produccion_molido'

class ProduccionConsumoLavadoInline(ProduccionConsumoInline):
    fk_name = 'id_produccion_lavado'

class ProduccionConsumoPeletizadoInline(ProduccionConsumoInline):
    fk_name = 'id_produccion_peletizado'

class ProduccionConsumoInyeccionInline(ProduccionConsumoInline):
    fk_name = 'id_produccion_inyeccion'

class ParosProduccionInline(admin.TabularInline):
    model = ParosProduccion
    extra = 0 # Usually don't add paros directly here, but allow viewing/editing
    autocomplete_fields = ['id_operario_reporta']
    fields = ('fecha_hora_inicio', 'fecha_hora_fin', 'motivo', 'id_operario_reporta', 'observaciones')
    readonly_fields = ('duracion',) # Display calculated duration
    verbose_name = "Paro de Producción"
    verbose_name_plural = "Paros de Producción"

# Specific inlines for Paros
class ParosProduccionMolidoInline(ParosProduccionInline):
    fk_name = 'id_produccion_molido'

class ParosProduccionLavadoInline(ParosProduccionInline):
    fk_name = 'id_produccion_lavado'

class ParosProduccionPeletizadoInline(ParosProduccionInline):
    fk_name = 'id_produccion_peletizado'

class ParosProduccionInyeccionInline(ParosProduccionInline):
    fk_name = 'id_produccion_inyeccion'


class ResiduosProduccionInline(admin.TabularInline):
    model = ResiduosProduccion
    extra = 0
    fields = ('fecha', 'tipo_residuo', 'cantidad', 'unidad_medida', 'observaciones')
    readonly_fields = ('fecha',) # Fecha defaults to now
    verbose_name = "Residuo de Producción"
    verbose_name_plural = "Residuos de Producción"

# Specific inlines for Residuos
class ResiduosProduccionMolidoInline(ResiduosProduccionInline):
    fk_name = 'id_produccion_molido'

class ResiduosProduccionLavadoInline(ResiduosProduccionInline):
    fk_name = 'id_produccion_lavado'

class ResiduosProduccionPeletizadoInline(ResiduosProduccionInline):
    fk_name = 'id_produccion_peletizado'

class ResiduosProduccionInyeccionInline(ResiduosProduccionInline):
    fk_name = 'id_produccion_inyeccion'


# --- Custom Admin Classes ---

# Admin classes for models used in autocomplete_fields
@admin.register(Materiales)
class MaterialesAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo')
    list_filter = ('tipo',)
    search_fields = ('nombre', 'descripcion')

@admin.register(Bodegas)
class BodegasAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre', 'descripcion')

@admin.register(Terceros)
class TercerosAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'identificacion', 'telefono')
    list_filter = ('tipo',)
    search_fields = ('nombre', 'identificacion')

@admin.register(Operarios)
class OperariosAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'codigo', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre_completo', 'codigo')
    list_editable = ('activo',) # Allow quick editing of 'activo'

@admin.register(Maquinas)
class MaquinasAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_proceso')
    list_filter = ('tipo_proceso',)
    search_fields = ('nombre', 'descripcion')

@admin.register(Lotes)
class LotesAdmin(admin.ModelAdmin):
    list_display = ('numero_lote', 'id_material', 'cantidad_actual', 'unidad_medida', 'id_bodega_actual', 'clasificacion', 'activo', 'fecha_creacion', 'fecha_modificacion', 'usuario_modificacion')
    list_filter = ('activo', 'id_bodega_actual__nombre', 'id_material__nombre', 'clasificacion', 'fecha_creacion') # Filter by name is often better
    search_fields = ('numero_lote', 'id_material__nombre', 'observaciones')
    # Make calculated/signal-managed fields readonly
    readonly_fields = ('cantidad_actual', 'activo', 'fecha_creacion', 'fecha_modificacion', 'usuario_modificacion')
    autocomplete_fields = ['id_material', 'id_bodega_actual', 'proveedor_origen'] # Autocomplete FKs
    list_per_page = 25
    fieldsets = (
        (None, {
            'fields': ('numero_lote', 'id_material', 'cantidad_inicial', 'unidad_medida', 'id_bodega_actual')
        }),
        ('Detalles Adicionales', {
            'fields': ('clasificacion', 'costo_unitario', 'proveedor_origen', 'fecha_vencimiento', 'observaciones'),
            'classes': ('collapse',) # Collapse this section by default
        }),
        ('Estado e Información de Auditoría', {
            'fields': ('cantidad_actual', 'activo', 'fecha_creacion', 'fecha_modificacion', 'usuario_modificacion'),
            'classes': ('collapse',)
        }),
    )

    # Action to recalculate 'activo' status (though save() should handle it)
    def recalcular_activo(self, request, queryset):
        updated_count = 0
        for lote in queryset:
            original_activo = lote.activo
            lote.activo = lote.cantidad_actual > 0
            if lote.activo != original_activo:
                lote.save(update_fields=['activo']) # Only save if changed
                updated_count += 1
        self.message_user(request, f"{updated_count} lotes actualizados.")
    recalcular_activo.short_description = "Recalcular estado 'Activo' de lotes seleccionados"

    actions = [recalcular_activo]


@admin.register(MovimientosInventario)
class MovimientosInventarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo_movimiento', 'id_lote', 'cantidad', 'origen', 'destino', 'consecutivo_soporte')
    list_filter = ('tipo_movimiento', 'fecha', 'id_origen_bodega__nombre', 'id_destino_bodega__nombre') # Filter by name
    search_fields = ('id_lote__numero_lote', 'consecutivo_soporte', 'factura_remision', 'observaciones', 'produccion_referencia')
    autocomplete_fields = ['id_lote', 'id_origen_bodega', 'id_destino_bodega', 'id_origen_tercero', 'id_destino_tercero'] # Improve FK selection
    list_per_page = 25
    date_hierarchy = 'fecha' # Allow date navigation
    readonly_fields = ('fecha',) # Fecha is auto_now_add

    # Methods to display unified origin/destination in list_display
    def origen(self, obj):
        if obj.id_origen_bodega:
            return f"Bod: {obj.id_origen_bodega.nombre}"
        elif obj.id_origen_tercero:
            return f"Ter: {obj.id_origen_tercero.nombre}"
        return '-'
    origen.short_description = 'Origen'
    origen.admin_order_field = 'id_origen_bodega__nombre' # Allow sorting

    def destino(self, obj):
        if obj.id_destino_bodega:
            return f"Bod: {obj.id_destino_bodega.nombre}"
        elif obj.id_destino_tercero:
            return f"Ter: {obj.id_destino_tercero.nombre}"
        return '-'
    destino.short_description = 'Destino'
    destino.admin_order_field = 'id_destino_bodega__nombre' # Allow sorting

# --- Base Admin for Production Models ---
class BaseProduccionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'orden_trabajo', 'id_lote_producido', 'cantidad_producida', 'id_maquina', 'id_operario', 'id_bodega_destino')
    list_filter = ('fecha', 'id_maquina__nombre', 'id_operario__nombre_completo', 'id_bodega_destino__nombre')
    search_fields = ('orden_trabajo', 'id_lote_producido__numero_lote', 'observaciones')
    autocomplete_fields = ['id_lote_producido', 'id_operario', 'id_maquina', 'id_bodega_destino']
    readonly_fields = ('id_produccion', 'fecha') # ID and creation date
    date_hierarchy = 'fecha'
    list_per_page = 20
    fieldsets = (
         (None, {
            'fields': ('fecha', 'turno', 'orden_trabajo', 'id_operario', 'id_maquina')
        }),
        ('Lote Producido', {
            'fields': ('id_lote_producido', 'cantidad_producida', 'id_bodega_destino')
        }),
         ('Detalles Adicionales', {
            'fields': ('observaciones',),
             'classes': ('collapse',)
        }),
    )
    # Inlines will be added by subclasses

# --- Custom Admin for Specific Production Models with Inlines ---

@admin.register(ProduccionMolido)
class ProduccionMolidoAdmin(BaseProduccionAdmin):
    inlines = [ProduccionConsumoMolidoInline, ParosProduccionMolidoInline, ResiduosProduccionMolidoInline]
    # Add specific fields if any
    fieldsets = BaseProduccionAdmin.fieldsets # Inherit fieldsets

@admin.register(ProduccionLavado)
class ProduccionLavadoAdmin(BaseProduccionAdmin):
    inlines = [ProduccionConsumoLavadoInline, ParosProduccionLavadoInline, ResiduosProduccionLavadoInline]
    fieldsets = BaseProduccionAdmin.fieldsets

@admin.register(ProduccionPeletizado)
class ProduccionPeletizadoAdmin(BaseProduccionAdmin):
    # Add numero_mezclas to list_display and fieldsets
    list_display = BaseProduccionAdmin.list_display + ('numero_mezclas',)
    inlines = [ProduccionConsumoPeletizadoInline, ParosProduccionPeletizadoInline, ResiduosProduccionPeletizadoInline]
    # Add numero_mezclas to fieldsets
    fieldsets = (
         (None, {
            'fields': ('fecha', 'turno', 'orden_trabajo', 'id_operario', 'id_maquina')
        }),
        ('Lote Producido', {
            'fields': ('id_lote_producido', 'cantidad_producida', 'id_bodega_destino', 'numero_mezclas') # Added numero_mezclas
        }),
         ('Detalles Adicionales', {
            'fields': ('observaciones',),
             'classes': ('collapse',)
        }),
    )


@admin.register(ProduccionInyeccion)
class ProduccionInyeccionAdmin(BaseProduccionAdmin):
    # Add numero_mezclas to list_display and fieldsets
    list_display = BaseProduccionAdmin.list_display + ('numero_mezclas',)
    inlines = [ProduccionConsumoInyeccionInline, ParosProduccionInyeccionInline, ResiduosProduccionInyeccionInline]
    # Add numero_mezclas to fieldsets
    fieldsets = (
         (None, {
            'fields': ('fecha', 'turno', 'orden_trabajo', 'id_operario', 'id_maquina')
        }),
        ('Lote Producido', {
            'fields': ('id_lote_producido', 'cantidad_producida', 'id_bodega_destino', 'numero_mezclas') # Added numero_mezclas
        }),
         ('Detalles Adicionales', {
            'fields': ('observaciones',),
             'classes': ('collapse',)
        }),
    )

# --- Admin for Related Production Data (Optional but useful) ---

@admin.register(ProduccionConsumo)
class ProduccionConsumoAdmin(admin.ModelAdmin):
    list_display = ('get_produccion_ref', 'id_lote_consumido', 'cantidad_consumida', 'id_bodega_origen')
    search_fields = ('id_lote_consumido__numero_lote', 'id_produccion_molido__orden_trabajo', 'id_produccion_lavado__orden_trabajo', 'id_produccion_peletizado__orden_trabajo', 'id_produccion_inyeccion__orden_trabajo')
    autocomplete_fields = ['id_lote_consumido', 'id_bodega_origen', 'id_produccion_molido', 'id_produccion_lavado', 'id_produccion_peletizado', 'id_produccion_inyeccion']
    list_filter = ('id_bodega_origen__nombre',)

    def get_produccion_ref(self, obj):
        prod = obj.get_produccion_padre()
        if prod:
            # Link to the parent production admin page
            from django.urls import reverse
            from django.utils.html import format_html
            url = reverse(f'admin:gestion_{prod._meta.model_name}_change', args=[prod.pk])
            return format_html('<a href="{}">{} OT:{}</a>', url, prod._meta.verbose_name, prod.orden_trabajo or 'N/A')
        return "N/A"
    get_produccion_ref.short_description = 'Producción Asociada'


@admin.register(ParosProduccion)
class ParosProduccionAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora_inicio', 'fecha_hora_fin', 'duracion', 'motivo', 'id_operario_reporta', 'get_produccion_ref')
    list_filter = ('fecha_hora_inicio', 'id_operario_reporta__nombre_completo')
    search_fields = ('motivo', 'observaciones', 'id_produccion_molido__orden_trabajo', 'id_produccion_lavado__orden_trabajo', 'id_produccion_peletizado__orden_trabajo', 'id_produccion_inyeccion__orden_trabajo')
    autocomplete_fields = ['id_operario_reporta', 'id_produccion_molido', 'id_produccion_lavado', 'id_produccion_peletizado', 'id_produccion_inyeccion']
    readonly_fields = ('duracion',)
    date_hierarchy = 'fecha_hora_inicio'

    def get_produccion_ref(self, obj):
        # Similar to ProduccionConsumoAdmin
        prod = obj.get_produccion_padre()
        if prod:
            from django.urls import reverse
            from django.utils.html import format_html
            url = reverse(f'admin:gestion_{prod._meta.model_name}_change', args=[prod.pk])
            return format_html('<a href="{}">{} OT:{}</a>', url, prod._meta.verbose_name, prod.orden_trabajo or 'N/A')
        return "N/A"
    get_produccion_ref.short_description = 'Producción Asociada'


@admin.register(ResiduosProduccion)
class ResiduosProduccionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo_residuo', 'cantidad', 'unidad_medida', 'get_produccion_ref')
    list_filter = ('fecha', 'tipo_residuo', 'unidad_medida')
    search_fields = ('tipo_residuo', 'observaciones', 'id_produccion_molido__orden_trabajo', 'id_produccion_lavado__orden_trabajo', 'id_produccion_peletizado__orden_trabajo', 'id_produccion_inyeccion__orden_trabajo')
    autocomplete_fields = ['id_produccion_molido', 'id_produccion_lavado', 'id_produccion_peletizado', 'id_produccion_inyeccion']
    date_hierarchy = 'fecha'

    def get_produccion_ref(self, obj):
        # Similar to ProduccionConsumoAdmin
        prod = obj.get_produccion_padre()
        if prod:
            from django.urls import reverse
            from django.utils.html import format_html
            url = reverse(f'admin:gestion_{prod._meta.model_name}_change', args=[prod.pk])
            return format_html('<a href="{}">{} OT:{}</a>', url, prod._meta.verbose_name, prod.orden_trabajo or 'N/A')
        return "N/A"
    get_produccion_ref.short_description = 'Producción Asociada'

# Note: Models without explicit @admin.register are not shown in admin unless registered with admin.site.register()
# We have registered all relevant models using decorators.
