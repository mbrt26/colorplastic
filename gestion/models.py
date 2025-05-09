import uuid
from django.db import models
from django.utils import timezone # Import timezone
from django.conf import settings # Import settings to get AUTH_USER_MODEL
from django.core.exceptions import ValidationError # Import for clean method
from django.db.models import CheckConstraint, Q, F, Index, Expression # Import for constraints and indexes

# Create your models here.

class Materiales(models.Model):
    TIPO_MATERIAL_CHOICES = [
        ('Molido', 'Molido'),
        ('Lavado', 'Lavado'),
        ('Peletizado', 'Peletizado'),
        ('Inyeccion', 'Inyección'),
        ('Original', 'Original'),
        ('Entero', 'Entero'),
        ('Aglutinada', 'Aglutinada'),
        ('Pigmento', 'Pigmento'),
        ('Aditivo', 'Aditivo'),
    ]
    id_material = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    tipo = models.CharField(max_length=20, choices=TIPO_MATERIAL_CHOICES, verbose_name='Tipo')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')

    def __str__(self):
        return f'{self.nombre} ({self.tipo})'

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'

class Bodegas(models.Model):
    id_bodega = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Bodega'
        verbose_name_plural = 'Bodegas'

class Terceros(models.Model):
    TIPO_TERCERO_CHOICES = [
        ('Proveedor', 'Proveedor'),
        ('Cliente', 'Cliente'),
    ]
    id_tercero = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    tipo = models.CharField(max_length=10, choices=TIPO_TERCERO_CHOICES, verbose_name='Tipo')
    identificacion = models.CharField(max_length=50, blank=True, null=True, verbose_name='Identificación (NIT)')
    direccion = models.TextField(blank=True, null=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=50, blank=True, null=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')

    def __str__(self):
        return f'{self.nombre} ({self.tipo})'

    class Meta:
        verbose_name = 'Tercero'
        verbose_name_plural = 'Terceros'

class Operarios(models.Model):
    id_operario = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True, verbose_name='Código')
    nombre_completo = models.CharField(max_length=150, verbose_name='Nombre Completo')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return f'{self.nombre_completo} ({self.codigo})'

    class Meta:
        verbose_name = 'Operario'
        verbose_name_plural = 'Operarios'

class Maquinas(models.Model):
    TIPO_PROCESO_CHOICES = [
        ('Molido', 'Molido'),
        ('Lavado', 'Lavado'),
        ('Peletizado', 'Peletizado'),
        ('Inyeccion', 'Inyección'),
    ]
    id_maquina = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    tipo_proceso = models.CharField(max_length=20, choices=TIPO_PROCESO_CHOICES, verbose_name='Tipo de Proceso')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return f'{self.nombre} ({self.tipo_proceso})'

    class Meta:
        verbose_name = 'Máquina'
        verbose_name_plural = 'Máquinas'

# --- Moved BaseProduccion Definition Up ---
class BaseProduccion(models.Model):
    """Modelo abstracto base para todos los tipos de producción."""
    id_produccion = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fecha = models.DateTimeField(default=timezone.now, verbose_name='Fecha Producción')
    turno = models.CharField(max_length=50, blank=True, null=True, verbose_name='Turno')
    orden_trabajo = models.CharField(max_length=50, blank=True, null=True, verbose_name='Orden de Trabajo')
    id_operario = models.ForeignKey(Operarios, on_delete=models.PROTECT, verbose_name='Operario')
    cantidad_producida = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Cantidad Producida')
    id_bodega_destino = models.ForeignKey(Bodegas, on_delete=models.PROTECT, verbose_name='Bodega Destino Lote Producido')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')

    class Meta:
        abstract = True # Important: This makes it an abstract base class
        ordering = ['-fecha']

# --- Nuevos Modelos ---

class Lotes(models.Model):
    id_lote = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_lote = models.CharField(max_length=100, unique=True, verbose_name='Número de Lote')
    id_material = models.ForeignKey(Materiales, on_delete=models.PROTECT, verbose_name='Material')
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cantidad Inicial')
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Cantidad Actual')
    unidad_medida = models.CharField(max_length=10, choices=[('kg', 'Kilogramos'), ('unidad', 'Unidades')], default='kg')
    id_bodega_actual = models.ForeignKey(Bodegas, on_delete=models.PROTECT, verbose_name='Bodega Actual')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha Creación')
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name='Fecha Vencimiento')
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Costo Unitario')
    proveedor_origen = models.ForeignKey(Terceros, on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_proveidos', verbose_name='Proveedor Origen')
    activo = models.BooleanField(default=True, editable=False, verbose_name='Activo') # Editable=False, calculated by signal
    clasificacion = models.CharField(max_length=50, choices=[('A', 'A'), ('B', 'B'), ('C', 'C')], null=True, blank=True, verbose_name='Clasificación Calidad')
    observaciones = models.TextField(blank=True, null=True)
    # --- Audit Fields ---
    usuario_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, # Allow null for now, setting user from signals is complex
        verbose_name='Último Usuario Modificador',
        related_name='lotes_modificados'
    )
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Fecha Modificación') # Track last modification

    # REMOVED custom save method - logic moved to signals or handled by constraints/defaults

    def save(self, *args, **kwargs):
        # Solo igualar cantidad_actual a cantidad_inicial si el lote es nuevo
        if self._state.adding:
            self.cantidad_actual = self.cantidad_inicial
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_lote} ({self.id_material.nombre})"

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['-fecha_creacion']
        # --- DB Constraints ---
        constraints = [
            CheckConstraint(check=Q(cantidad_actual__gte=0), name='check_cantidad_actual_no_negativa')
        ]
        # --- Indexes for Query Optimization ---
        indexes = [
            Index(fields=['id_material', 'id_bodega_actual'], name='idx_lote_material_bodega'),
            Index(fields=['numero_lote'], name='idx_lote_numero'), # Index for numero_lote lookups
        ]

class MovimientosInventario(models.Model):
    id_movimiento = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha Movimiento')
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=[
            ('Compra', 'Compra'),
            ('Venta', 'Venta'),
            ('Traslado', 'Traslado'),
            ('AjustePositivo', 'Ajuste Positivo'),
            ('AjusteNegativo', 'Ajuste Negativo'),
            ('ConsumoProduccion', 'Consumo Producción'),
            ('IngresoServicio', 'Ingreso por Servicio'), # Ej: Material que vuelve de un proceso externo
            ('SalidaServicio', 'Salida a Servicio'),    # Ej: Material enviado a proceso externo
        ]
    )
    id_lote = models.ForeignKey(Lotes, on_delete=models.PROTECT, verbose_name='Lote Afectado')
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cantidad Movida')
    id_origen_bodega = models.ForeignKey(Bodegas, on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos_salida', verbose_name='Bodega Origen')
    id_destino_bodega = models.ForeignKey(Bodegas, on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos_entrada', verbose_name='Bodega Destino')
    id_origen_tercero = models.ForeignKey(Terceros, on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos_entrega', verbose_name='Tercero Origen (Proveedor/Cliente)')
    id_destino_tercero = models.ForeignKey(Terceros, on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos_recibe', verbose_name='Tercero Destino (Cliente/Proveedor)')
    consecutivo_soporte = models.CharField(max_length=100, null=True, blank=True, verbose_name='Consecutivo Soporte (Factura/Remisión/OT)')
    factura_remision = models.CharField(max_length=100, null=True, blank=True, verbose_name='Factura/Remisión Asociada')
    produccion_referencia = models.CharField(max_length=100, null=True, blank=True, verbose_name='ID Producción Relacionada') # Store UUID as string
    observaciones = models.TextField(blank=True, null=True)
    # --- Audit Fields (Optional here, Lotes audit might be enough) ---
    # usuario_creacion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_creados')

    def clean(self):
        # Basic validation for required fields based on type
        if self.tipo_movimiento in ['Venta', 'SalidaServicio', 'ConsumoProduccion', 'AjusteNegativo', 'Traslado'] and not self.id_origen_bodega:
            raise ValidationError(f"Movimiento de tipo '{self.tipo_movimiento}' requiere una Bodega Origen.")
        if self.tipo_movimiento in ['Compra', 'IngresoServicio', 'AjustePositivo', 'Traslado'] and not self.id_destino_bodega:
            raise ValidationError(f"Movimiento de tipo '{self.tipo_movimiento}' requiere una Bodega Destino.")
        if self.tipo_movimiento == 'Traslado' and self.id_origen_bodega == self.id_destino_bodega:
             raise ValidationError("En un Traslado, la bodega origen y destino no pueden ser la misma.")
        if self.cantidad <= 0:
            raise ValidationError("La cantidad movida debe ser mayor que cero.")

    def save(self, *args, **kwargs):
        # Evita recursión infinita: solo guardar normalmente
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_movimiento} - Lote: {self.id_lote.numero_lote} - Cant: {self.cantidad}"

    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha']

# --- Production Models Now Inherit Correctly ---
class ProduccionMolido(BaseProduccion):
    id_maquina = models.ForeignKey(Maquinas, limit_choices_to={'tipo_proceso': 'Molido'}, on_delete=models.PROTECT, verbose_name='Molino')
    # ADDED: id_lote_producido con related_name único
    id_lote_producido = models.OneToOneField(Lotes, on_delete=models.PROTECT, related_name='produccion_molido_origen', verbose_name='Lote Producido')
    # REMOVED: clasificacion_producida - Assuming classification is on the Lote
    # clasificacion_producida = models.CharField(max_length=10, choices=Lotes.CLASIFICACION_CHOICES, blank=True, null=True, verbose_name='Clasificación Producida')

    def save(self, *args, **kwargs):
        from .inventario_utils import procesar_movimiento_inventario
        if self._state.adding:
            procesar_movimiento_inventario(
                tipo_movimiento='AjustePositivo',
                lote=self.id_lote_producido,
                cantidad=self.cantidad_producida,
                bodega_destino=self.id_bodega_destino,
                produccion_referencia=str(self.id_produccion),
                observaciones=f"Producción: {self.__class__.__name__} OT:{self.orden_trabajo}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Molido OT:{self.orden_trabajo or 'N/A'} - Lote:{self.id_lote_producido.numero_lote} - Fecha:{self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'Producción Molido'
        verbose_name_plural = 'Producciones Molido'

class ProduccionLavado(BaseProduccion):
    id_maquina = models.ForeignKey(Maquinas, limit_choices_to={'tipo_proceso': 'Lavado'}, on_delete=models.PROTECT, verbose_name='Sistema Lavado')
    # ADDED: id_lote_producido con related_name único
    id_lote_producido = models.OneToOneField(Lotes, on_delete=models.PROTECT, related_name='produccion_lavado_origen', verbose_name='Lote Producido')
    # REMOVED: clasificacion_producida
    # clasificacion_producida = models.CharField(max_length=10, choices=Lotes.CLASIFICACION_CHOICES, blank=True, null=True, verbose_name='Clasificación Producida')

    def save(self, *args, **kwargs):
        from .inventario_utils import procesar_movimiento_inventario
        if self._state.adding:
            procesar_movimiento_inventario(
                tipo_movimiento='AjustePositivo',
                lote=self.id_lote_producido,
                cantidad=self.cantidad_producida,
                bodega_destino=self.id_bodega_destino,
                produccion_referencia=str(self.id_produccion),
                observaciones=f"Producción: {self.__class__.__name__} OT:{self.orden_trabajo}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lavado OT:{self.orden_trabajo or 'N/A'} - Lote:{self.id_lote_producido.numero_lote} - Fecha:{self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'Producción Lavado'
        verbose_name_plural = 'Producciones Lavado'

class ProduccionPeletizado(BaseProduccion):
    id_maquina = models.ForeignKey(Maquinas, limit_choices_to={'tipo_proceso': 'Peletizado'}, on_delete=models.PROTECT, verbose_name='Peletizadora')
    # ADDED: id_lote_producido con related_name único
    id_lote_producido = models.OneToOneField(Lotes, on_delete=models.PROTECT, related_name='produccion_peletizado_origen', verbose_name='Lote Producido')
    numero_mezclas = models.PositiveIntegerField(default=1, verbose_name='Número de Mezclas')
    completado = models.BooleanField(default=False, verbose_name='Completado')
    estado = models.CharField(max_length=20, choices=[('en_proceso', 'En Proceso'), ('completado', 'Completado')], default='en_proceso', verbose_name='Estado')

    def save(self, *args, **kwargs):
        from .inventario_utils import procesar_movimiento_inventario
        if self._state.adding:
            procesar_movimiento_inventario(
                tipo_movimiento='AjustePositivo',
                lote=self.id_lote_producido,
                cantidad=self.cantidad_producida,
                bodega_destino=self.id_bodega_destino,
                produccion_referencia=str(self.id_produccion),
                observaciones=f"Producción: {self.__class__.__name__} OT:{self.orden_trabajo}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Peletizado OT:{self.orden_trabajo or 'N/A'} - Lote:{self.id_lote_producido.numero_lote} - Fecha:{self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'Producción Peletizado'
        verbose_name_plural = 'Producciones Peletizado'

class ProduccionInyeccion(BaseProduccion):
    id_maquina = models.ForeignKey(Maquinas, limit_choices_to={'tipo_proceso': 'Inyeccion'}, on_delete=models.PROTECT, verbose_name='Inyectora')
    # ADDED: id_lote_producido con related_name único
    id_lote_producido = models.OneToOneField(Lotes, on_delete=models.PROTECT, related_name='produccion_inyeccion_origen', verbose_name='Lote Producido')
    numero_mezclas = models.PositiveIntegerField(default=1, verbose_name='Número de Mezclas')

    def save(self, *args, **kwargs):
        from .inventario_utils import procesar_movimiento_inventario
        if self._state.adding:
            procesar_movimiento_inventario(
                tipo_movimiento='AjustePositivo',
                lote=self.id_lote_producido,
                cantidad=self.cantidad_producida,
                bodega_destino=self.id_bodega_destino,
                produccion_referencia=str(self.id_produccion),
                observaciones=f"Producción: {self.__class__.__name__} OT:{self.orden_trabajo}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inyección OT:{self.orden_trabajo or 'N/A'} - Lote:{self.id_lote_producido.numero_lote} - Fecha:{self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'Producción Inyección'
        verbose_name_plural = 'Producciones Inyección'

class ProduccionConsumo(models.Model):
    # Para vincular a las diferentes tablas de producción, usamos claves foráneas opcionales.
    # Otra opción sería usar GenericForeignKey, pero puede ser más complejo de manejar.
    id_consumo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_produccion_molido = models.ForeignKey(ProduccionMolido, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_molido') # Unique related_name
    id_produccion_lavado = models.ForeignKey(ProduccionLavado, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_lavado') # Unique related_name
    id_produccion_peletizado = models.ForeignKey(ProduccionPeletizado, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_peletizado') # Unique related_name
    id_produccion_inyeccion = models.ForeignKey(ProduccionInyeccion, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_inyeccion') # Unique related_name

    id_lote_consumido = models.ForeignKey(Lotes, on_delete=models.PROTECT, related_name='consumos_en_produccion', verbose_name='Lote Consumido')
    cantidad_consumida = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Cantidad Consumida')
    id_bodega_origen = models.ForeignKey(Bodegas, on_delete=models.PROTECT, verbose_name='Bodega Origen Consumo')

    def get_produccion_padre(self):
        # Método helper para obtener la referencia a la producción padre
        if self.id_produccion_molido: return self.id_produccion_molido
        if self.id_produccion_lavado: return self.id_produccion_lavado
        if self.id_produccion_peletizado: return self.id_produccion_peletizado
        if self.id_produccion_inyeccion: return self.id_produccion_inyeccion
        return None

    def save(self, *args, **kwargs):
        # La señal post_save se encargará de procesar el movimiento de inventario
        super().save(*args, **kwargs)

    def __str__(self):
        produccion = self.get_produccion_padre()
        prod_str = f"Prod ID: {produccion.id_produccion}" if produccion else "Producción Desconocida"
        return f"Consumo para {prod_str} - Lote: {self.id_lote_consumido.numero_lote} - Cant: {self.cantidad_consumida}"

    class Meta:
        verbose_name = 'Consumo de Producción'
        verbose_name_plural = 'Consumos de Producción'
        # Asegurar que solo una FK de producción esté llena (se puede hacer con un CheckConstraint)
        # constraints = [
        #     models.CheckConstraint(...)
        # ]


class ParosProduccion(models.Model):
    id_paro = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Vinculación similar a ProduccionConsumo
    id_produccion_molido = models.ForeignKey(ProduccionMolido, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_molido') # Unique related_name
    id_produccion_lavado = models.ForeignKey(ProduccionLavado, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_lavado') # Unique related_name
    id_produccion_peletizado = models.ForeignKey(ProduccionPeletizado, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_peletizado') # Unique related_name
    id_produccion_inyeccion = models.ForeignKey(ProduccionInyeccion, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_inyeccion') # Unique related_name

    fecha_hora_inicio = models.DateTimeField(verbose_name='Fecha/Hora Inicio Paro')
    fecha_hora_fin = models.DateTimeField(verbose_name='Fecha/Hora Fin Paro')
    motivo = models.TextField(verbose_name='Motivo del Paro')
    id_operario_reporta = models.ForeignKey(Operarios, on_delete=models.PROTECT, verbose_name='Operario que Reporta')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')

    @property
    def duracion(self):
        return self.fecha_hora_fin - self.fecha_hora_inicio

    def get_produccion_padre(self):
        # Método helper
        if self.id_produccion_molido: return self.id_produccion_molido
        if self.id_produccion_lavado: return self.id_produccion_lavado
        if self.id_produccion_peletizado: return self.id_produccion_peletizado
        if self.id_produccion_inyeccion: return self.id_produccion_inyeccion
        return None

    def __str__(self):
        produccion = self.get_produccion_padre()
        prod_str = f"Prod ID: {produccion.id_produccion}" if produccion else "Producción Desconocida"
        return f"Paro en {prod_str} - Motivo: {self.motivo[:50]}..."

    class Meta:
        verbose_name = 'Paro de Producción'
        verbose_name_plural = 'Paros de Producción'
        ordering = ['-fecha_hora_inicio']


class ResiduosProduccion(models.Model):
    id_residuo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Vinculación similar a ProduccionConsumo
    id_produccion_molido = models.ForeignKey(ProduccionMolido, on_delete=models.CASCADE, blank=True, null=True, related_name='residuos_molido') # Unique related_name
    id_produccion_lavado = models.ForeignKey(ProduccionLavado, on_delete=models.CASCADE, blank=True, null=True, related_name='residuos_lavado') # Unique related_name
    id_produccion_peletizado = models.ForeignKey(ProduccionPeletizado, on_delete=models.CASCADE, blank=True, null=True, related_name='residuos_peletizado') # Unique related_name
    id_produccion_inyeccion = models.ForeignKey(ProduccionInyeccion, on_delete=models.CASCADE, blank=True, null=True, related_name='residuos_inyeccion') # Unique related_name

    fecha = models.DateTimeField(default=timezone.now, verbose_name='Fecha Registro Residuo')
    tipo_residuo = models.CharField(max_length=100, verbose_name='Tipo de Residuo')
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cantidad Residuo')
    # --- Fixed unidad_medida choices ---
    unidad_medida = models.CharField(max_length=10, choices=[('kg', 'Kilogramos'), ('unidad', 'Unidades')], default='kg', verbose_name='Unidad de Medida')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')

    def get_produccion_padre(self):
        # Método helper
        if self.id_produccion_molido: return self.id_produccion_molido
        if self.id_produccion_lavado: return self.id_produccion_lavado
        if self.id_produccion_peletizado: return self.id_produccion_peletizado
        if self.id_produccion_inyeccion: return self.id_produccion_inyeccion
        return None

    def __str__(self):
        produccion = self.get_produccion_padre()
        prod_str = f"Prod ID: {produccion.id_produccion}" if produccion else "Producción Desconocida"
        return f"Residuo de {prod_str} - Tipo: {self.tipo_residuo} - Cant: {self.cantidad} {self.unidad_medida}"

    class Meta:
        verbose_name = 'Residuo de Producción'
        verbose_name_plural = 'Residuos de Producción'
        ordering = ['-fecha']

# --- Fin Modelos de Producción ---
