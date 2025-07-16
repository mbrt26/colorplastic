import uuid
from django.db import models
from django.utils import timezone # Import timezone
from django.conf import settings # Import settings to get AUTH_USER_MODEL
from django.core.exceptions import ValidationError # Import for clean method
from django.db.models import CheckConstraint, Q, F, Index, Expression # Import for constraints and indexes
from django.contrib.auth.models import User  # Import User model
from django.core.validators import MinValueValidator, MaxValueValidator  # Import validators
from datetime import timedelta  # Import timedelta for date calculations

# Create your models here.

class Materiales(models.Model):
    TIPO_MATERIAL_CHOICES = [
        ('MP', 'Materia Prima'),
        ('PI', 'Producto Intermedio'),
        ('PT', 'Producto Terminado'),
        ('IN', 'Insumo'),
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
    activo = models.BooleanField(default=True, verbose_name='Activo')

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
        ('Homogeneizacion', 'Homogeneización'),
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
    TURNO_CHOICES = [
        ('6am-2pm', '6am-2pm'),
        ('6am-12pm', '6am-12pm'),
        ('12pm-6pm', '12pm-6pm'),
        ('2pm-10pm', '2pm-10pm'),
        ('10pm-6am', '10pm-6am'),
        ('6am-6pm', '6am-6pm'),
        ('6pm-6am', '6pm-6am'),
    ]
    
    id_produccion = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fecha = models.DateTimeField(default=timezone.now, verbose_name='Fecha Producción')
    turno = models.CharField(max_length=50, choices=TURNO_CHOICES, blank=True, null=True, verbose_name='Turno')
    orden_trabajo = models.CharField(max_length=50, blank=True, null=True, verbose_name='Orden de Trabajo')
    id_operario = models.ForeignKey(Operarios, on_delete=models.PROTECT, verbose_name='Operario')
    # Campos de cantidad con valores por defecto
    cantidad_entrada = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Cantidad de Entrada')
    cantidad_salida = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Cantidad de Salida')
    id_bodega_destino = models.ForeignKey(Bodegas, on_delete=models.PROTECT, verbose_name='Bodega Destino Lote Producido')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    archivo_adjunto = models.FileField(upload_to='produccion/archivos/', blank=True, null=True, verbose_name='Archivo Adjunto')
    # Agregamos campo para merma
    merma = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Merma (Pérdida)', default=0)

    @property
    def eficiencia(self):
        """Calcula la eficiencia del proceso como porcentaje."""
        if self.cantidad_entrada and self.cantidad_entrada > 0:
            return (self.cantidad_salida / self.cantidad_entrada) * 100
        return 0

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
    # ADDED: id_lote_producido with related_name único
    id_lote_producido = models.OneToOneField(Lotes, on_delete=models.PROTECT, related_name='produccion_molido_origen', verbose_name='Lote Producido')
    # REMOVED: clasificacion_producida - Assuming classification is on the Lote
    # clasificacion_producida = models.CharField(max_length=10, choices=Lotes.CLASIFICACION_CHOICES, blank=True, null=True, verbose_name='Clasificación Producida')

    def save(self, *args, **kwargs):
        from .inventario_utils import procesar_movimiento_inventario
        if self._state.adding:
            # Verificar si el lote ya tiene la cantidad correcta
            if (self.id_lote_producido.id_bodega_actual == self.id_bodega_destino and 
                self.id_lote_producido.cantidad_actual == self.cantidad_salida):
                # El lote ya está configurado correctamente, no crear movimiento duplicado
                print(f"Lote {self.id_lote_producido.numero_lote} ya tiene la cantidad correcta, omitiendo movimiento")
            else:
                procesar_movimiento_inventario(
                    tipo_movimiento='IngresoServicio',
                    lote=self.id_lote_producido,
                    cantidad=self.cantidad_salida,
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
            # Verificar si el lote ya tiene la cantidad correcta
            if (self.id_lote_producido.id_bodega_actual == self.id_bodega_destino and 
                self.id_lote_producido.cantidad_actual == self.cantidad_salida):
                # El lote ya está configurado correctamente, no crear movimiento duplicado
                print(f"Lote {self.id_lote_producido.numero_lote} ya tiene la cantidad correcta, omitiendo movimiento")
            else:
                procesar_movimiento_inventario(
                    tipo_movimiento='IngresoServicio',
                    lote=self.id_lote_producido,
                    cantidad=self.cantidad_salida,
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
            # Verificar si el lote ya tiene la cantidad correcta
            if (self.id_lote_producido.id_bodega_actual == self.id_bodega_destino and 
                self.id_lote_producido.cantidad_actual == self.cantidad_salida):
                # El lote ya está configurado correctamente, no crear movimiento duplicado
                print(f"Lote {self.id_lote_producido.numero_lote} ya tiene la cantidad correcta, omitiendo movimiento")
            else:
                procesar_movimiento_inventario(
                    tipo_movimiento='IngresoServicio',
                    lote=self.id_lote_producido,
                    cantidad=self.cantidad_salida,
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
            # Verificar si el lote ya tiene la cantidad correcta
            if (self.id_lote_producido.id_bodega_actual == self.id_bodega_destino and 
                self.id_lote_producido.cantidad_actual == self.cantidad_salida):
                # El lote ya está configurado correctamente, no crear movimiento duplicado
                print(f"Lote {self.id_lote_producido.numero_lote} ya tiene la cantidad correcta, omitiendo movimiento")
            else:
                procesar_movimiento_inventario(
                    tipo_movimiento='IngresoServicio',
                    lote=self.id_lote_producido,
                    cantidad=self.cantidad_salida,
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

class ProduccionHomogeneizacion(BaseProduccion):
    id_maquina = models.ForeignKey(Maquinas, limit_choices_to={'tipo_proceso': 'Homogeneizacion'}, on_delete=models.PROTECT, verbose_name='Sistema Homogeneización')
    # ADDED: id_lote_producido con related_name único
    id_lote_producido = models.OneToOneField(Lotes, on_delete=models.PROTECT, related_name='produccion_homogeneizacion_origen', verbose_name='Lote Producido')

    def save(self, *args, **kwargs):
        from .inventario_utils import procesar_movimiento_inventario
        if self._state.adding:
            # Verificar si el lote ya tiene la cantidad correcta
            if (self.id_lote_producido.id_bodega_actual == self.id_bodega_destino and 
                self.id_lote_producido.cantidad_actual == self.cantidad_salida):
                # El lote ya está configurado correctamente, no crear movimiento duplicado
                print(f"Lote {self.id_lote_producido.numero_lote} ya tiene la cantidad correcta, omitiendo movimiento")
            else:
                procesar_movimiento_inventario(
                    tipo_movimiento='IngresoServicio',
                    lote=self.id_lote_producido,
                    cantidad=self.cantidad_salida,
                    bodega_destino=self.id_bodega_destino,
                    produccion_referencia=str(self.id_produccion),
                    observaciones=f"Producción: {self.__class__.__name__} OT:{self.orden_trabajo}"
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Homogeneización OT:{self.orden_trabajo or 'N/A'} - Lote:{self.id_lote_producido.numero_lote} - Fecha:{self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'Producción Homogeneización'
        verbose_name_plural = 'Producciones Homogeneización'

class ProduccionConsumo(models.Model):
    # Para vincular a las diferentes tablas de producción, usamos claves foráneas opcionales.
    # Otra opción sería usar GenericForeignKey, pero puede ser más complejo de manejar.
    id_consumo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_produccion_molido = models.ForeignKey(ProduccionMolido, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_molido') # Unique related_name
    id_produccion_lavado = models.ForeignKey(ProduccionLavado, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_lavado') # Unique related_name
    id_produccion_peletizado = models.ForeignKey(ProduccionPeletizado, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_peletizado') # Unique related_name
    id_produccion_inyeccion = models.ForeignKey(ProduccionInyeccion, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_inyeccion') # Unique related_name
    id_produccion_homogeneizacion = models.ForeignKey(ProduccionHomogeneizacion, on_delete=models.CASCADE, blank=True, null=True, related_name='consumos_homogeneizacion') # Unique related_name

    id_lote_consumido = models.ForeignKey(Lotes, on_delete=models.PROTECT, related_name='consumos_en_produccion', verbose_name='Lote Consumido')
    cantidad_consumida = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Cantidad Consumida')
    id_bodega_origen = models.ForeignKey(Bodegas, on_delete=models.PROTECT, verbose_name='Bodega Origen Consumo')

    def get_produccion_padre(self):
        """Devuelve la producción padre sin lanzar errores si fue eliminada."""
        if self.id_produccion_molido_id:
            return ProduccionMolido.objects.filter(pk=self.id_produccion_molido_id).first()
        if self.id_produccion_lavado_id:
            return ProduccionLavado.objects.filter(pk=self.id_produccion_lavado_id).first()
        if self.id_produccion_peletizado_id:
            return ProduccionPeletizado.objects.filter(pk=self.id_produccion_peletizado_id).first()
        if self.id_produccion_inyeccion_id:
            return ProduccionInyeccion.objects.filter(pk=self.id_produccion_inyeccion_id).first()
        if self.id_produccion_homogeneizacion_id:
            return ProduccionHomogeneizacion.objects.filter(pk=self.id_produccion_homogeneizacion_id).first()
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


# Nuevo modelo para motivos de paro
class MotivoParo(models.Model):
    id_motivo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Motivo')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Motivo de Paro'
        verbose_name_plural = 'Motivos de Paros'

class ParosProduccion(models.Model):
    id_paro = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Vinculación similar a ProduccionConsumo
    id_produccion_molido = models.ForeignKey(ProduccionMolido, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_molido') # Unique related_name
    id_produccion_lavado = models.ForeignKey(ProduccionLavado, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_lavado') # Unique related_name
    id_produccion_peletizado = models.ForeignKey(ProduccionPeletizado, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_peletizado') # Unique related_name
    id_produccion_inyeccion = models.ForeignKey(ProduccionInyeccion, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_inyeccion') # Unique related_name
    id_produccion_homogeneizacion = models.ForeignKey(ProduccionHomogeneizacion, on_delete=models.CASCADE, blank=True, null=True, related_name='paros_homogeneizacion') # Unique related_name

    fecha_hora_inicio = models.DateTimeField(verbose_name='Fecha/Hora Inicio Paro')
    fecha_hora_fin = models.DateTimeField(verbose_name='Fecha/Hora Fin Paro')
    motivo = models.ForeignKey(MotivoParo, on_delete=models.PROTECT, verbose_name='Motivo del Paro')
    id_operario_reporta = models.ForeignKey(Operarios, on_delete=models.PROTECT, verbose_name='Operario que Reporta')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')

    @property
    def duracion(self):
        """Calcula la duración del paro en horas y minutos."""
        if self.fecha_hora_inicio and self.fecha_hora_fin:
            diferencia = self.fecha_hora_fin - self.fecha_hora_inicio
            horas = diferencia.total_seconds() / 3600
            return f"{horas:.2f} horas"
        return "N/A"

    @property
    def proceso(self):
        """Retorna el tipo de proceso al que está asociado el paro."""
        if self.id_produccion_molido:
            return "Molido"
        elif self.id_produccion_lavado:
            return "Lavado"
        elif self.id_produccion_peletizado:
            return "Peletizado"
        elif self.id_produccion_inyeccion:
            return "Inyección"
        elif self.id_produccion_homogeneizacion:
            return "Homogeneización"
        return "N/A"

    def get_produccion_padre(self):
        # Método helper
        if self.id_produccion_molido: return self.id_produccion_molido
        if self.id_produccion_lavado: return self.id_produccion_lavado
        if self.id_produccion_peletizado: return self.id_produccion_peletizado
        if self.id_produccion_inyeccion: return self.id_produccion_inyeccion
        if self.id_produccion_homogeneizacion: return self.id_produccion_homogeneizacion
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
    id_produccion_homogeneizacion = models.ForeignKey(ProduccionHomogeneizacion, on_delete=models.CASCADE, blank=True, null=True, related_name='residuos_homogeneizacion') # Unique related_name

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
        if self.id_produccion_homogeneizacion: return self.id_produccion_homogeneizacion
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


class Despacho(models.Model):
    """Cabecera de un despacho de materiales hacia un tercero."""

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("en_proceso", "En Proceso"),
        ("despachado", "Despachado"),
        ("cancelado", "Cancelado"),
    ]

    numero_remision = models.CharField(max_length=50, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_despacho = models.DateTimeField(blank=True, null=True)
    direccion_entrega = models.CharField(max_length=255)
    orden_compra = models.CharField(max_length=100, blank=True, null=True, verbose_name="Orden de Compra")
    archivo_adjunto = models.FileField(upload_to='despachos/archivos/', blank=True, null=True, verbose_name="Archivo Adjunto")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")
    observaciones = models.TextField(blank=True)
    tercero = models.ForeignKey(Terceros, on_delete=models.PROTECT, related_name="despachos")
    usuario_creacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="despachos_creados",
    )

    class Meta:
        verbose_name = "Despacho"
        verbose_name_plural = "Despachos"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.numero_remision} - {self.tercero.nombre}"


class DetalleDespacho(models.Model):
    """Detalle de los productos incluidos en un despacho."""

    despacho = models.ForeignKey(Despacho, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Lotes, on_delete=models.PROTECT)
    bodega_origen = models.ForeignKey(Bodegas, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.numero_lote} - {self.cantidad}"


# --- Modelos CRM ---

class Cliente(models.Model):
    """Modelo extendido para clientes CRM basado en Terceros."""
    
    TIPO_CLIENTE_CHOICES = [
        ('corporativo', 'Corporativo'),
        ('pyme', 'PYME'),
        ('distribuidor', 'Distribuidor'),
        ('gobierno', 'Gobierno'),
        ('exportacion', 'Exportación'),
    ]
    
    ESTADO_CHOICES = [
        ('prospecto', 'Prospecto'),
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('perdido', 'Perdido'),
    ]
    
    id_cliente = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tercero = models.OneToOneField(Terceros, on_delete=models.CASCADE, related_name='cliente_crm')
    tipo_cliente = models.CharField(max_length=20, choices=TIPO_CLIENTE_CHOICES, verbose_name='Tipo de Cliente')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='prospecto', verbose_name='Estado')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')
    fecha_ultima_interaccion = models.DateTimeField(blank=True, null=True, verbose_name='Última Interacción')
    
    # Información comercial
    limite_credito = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Límite de Crédito')
    dias_credito = models.IntegerField(default=0, verbose_name='Días de Crédito')
    descuento_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Descuento Máximo %')
    
    # Información adicional
    sitio_web = models.URLField(blank=True, null=True, verbose_name='Sitio Web')
    industria = models.CharField(max_length=100, blank=True, null=True, verbose_name='Industria')
    numero_empleados = models.IntegerField(blank=True, null=True, verbose_name='Número de Empleados')
    facturacion_anual = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Facturación Anual')
    
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    usuario_asignado = models.ForeignKey(User, on_delete=models.PROTECT, related_name='clientes_asignados', verbose_name='Usuario Asignado')
    
    class Meta:
        verbose_name = 'Cliente CRM'
        verbose_name_plural = 'Clientes CRM'
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"{self.tercero.nombre} ({self.get_tipo_cliente_display()})"


class Contacto(models.Model):
    """Contactos asociados a los clientes."""
    
    TIPO_CONTACTO_CHOICES = [
        ('principal', 'Contacto Principal'),
        ('compras', 'Compras'),
        ('finanzas', 'Finanzas'),
        ('tecnico', 'Técnico'),
        ('logistica', 'Logística'),
        ('otro', 'Otro'),
    ]
    
    id_contacto = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contactos')
    
    # Información personal
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    apellido = models.CharField(max_length=100, verbose_name='Apellido')
    cargo = models.CharField(max_length=100, blank=True, null=True, verbose_name='Cargo')
    tipo_contacto = models.CharField(max_length=20, choices=TIPO_CONTACTO_CHOICES, verbose_name='Tipo de Contacto')
    
    # Información de contacto
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
    celular = models.CharField(max_length=20, blank=True, null=True, verbose_name='Celular')
    
    # Control
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name='contactos_creados')
    
    class Meta:
        verbose_name = 'Contacto'
        verbose_name_plural = 'Contactos'
        ordering = ['nombre', 'apellido']
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.cliente.tercero.nombre}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"


class Oportunidad(models.Model):
    """Oportunidades de negocio en el pipeline comercial."""
    
    ETAPA_CHOICES = [
        ('prospecto', 'Prospecto'),
        ('calificacion', 'Calificación'),
        ('presentacion', 'Presentación'),
        ('propuesta', 'Propuesta'),
        ('negociacion', 'Negociación'),
        ('cierre', 'Cierre'),
        ('ganada', 'Ganada'),
        ('perdida', 'Perdida'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    id_oportunidad = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='oportunidades')
    contacto = models.ForeignKey(Contacto, on_delete=models.PROTECT, related_name='oportunidades')
    
    # Información de la oportunidad
    nombre = models.CharField(max_length=200, verbose_name='Nombre de la Oportunidad')
    descripcion = models.TextField(verbose_name='Descripción')
    etapa = models.CharField(max_length=20, choices=ETAPA_CHOICES, default='prospecto', verbose_name='Etapa')
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='media', verbose_name='Prioridad')
    
    # Información financiera
    valor_estimado = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor Estimado')
    probabilidad = models.IntegerField(default=50, verbose_name='Probabilidad (%)')
    
    # Fechas importantes
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_cierre_estimada = models.DateField(verbose_name='Fecha de Cierre Estimada')
    fecha_cierre_real = models.DateField(blank=True, null=True, verbose_name='Fecha de Cierre Real')
    
    # Seguimiento
    proximo_paso = models.CharField(max_length=200, blank=True, null=True, verbose_name='Próximo Paso')
    fecha_proximo_paso = models.DateField(blank=True, null=True, verbose_name='Fecha Próximo Paso')
    motivo_perdida = models.TextField(blank=True, null=True, verbose_name='Motivo de Pérdida')
    
    # Control
    usuario_asignado = models.ForeignKey(User, on_delete=models.PROTECT, related_name='oportunidades_asignadas')
    
    class Meta:
        verbose_name = 'Oportunidad'
        verbose_name_plural = 'Oportunidades'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} - {self.cliente.tercero.nombre}"
    
    @property
    def valor_ponderado(self):
        return (self.valor_estimado * self.probabilidad) / 100
    
    def save(self, *args, **kwargs):
        # Verificar si es nueva
        es_nueva = self.pk is None
        
        super().save(*args, **kwargs)
        
        # Crear tarea automática si es nueva oportunidad
        if es_nueva:
            Tarea.objects.create(
                titulo=f"Seguimiento inicial - {self.nombre}",
                descripcion=f"Realizar seguimiento inicial de la oportunidad.\nCliente: {self.cliente}\nValor estimado: ${self.valor_estimado:,.0f}",
                tipo='seguimiento',
                prioridad='alta' if self.valor_estimado > 50000000 else 'media',
                modulo_origen='crm',
                oportunidad=self,
                asignado_a=self.usuario_asignado,
                creado_por=self.usuario_asignado,
                fecha_vencimiento=timezone.now() + timedelta(days=3)
            )


class InteraccionCliente(models.Model):
    """Registro de interacciones con clientes."""
    
    TIPO_INTERACCION_CHOICES = [
        ('llamada', 'Llamada'),
        ('email', 'Email'),
        ('reunion', 'Reunión'),
        ('visita', 'Visita'),
        ('cotizacion', 'Cotización'),
        ('seguimiento', 'Seguimiento'),
        ('otro', 'Otro'),
    ]
    
    id_interaccion = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='interacciones')
    contacto = models.ForeignKey(Contacto, on_delete=models.PROTECT, blank=True, null=True, related_name='interacciones')
    oportunidad = models.ForeignKey(Oportunidad, on_delete=models.CASCADE, blank=True, null=True, related_name='interacciones')
    
    # Información de la interacción
    tipo = models.CharField(max_length=20, choices=TIPO_INTERACCION_CHOICES, verbose_name='Tipo de Interacción')
    asunto = models.CharField(max_length=200, verbose_name='Asunto')
    descripcion = models.TextField(verbose_name='Descripción')
    
    # Fechas
    fecha_interaccion = models.DateTimeField(verbose_name='Fecha de Interacción')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    
    # Seguimiento
    requiere_seguimiento = models.BooleanField(default=False, verbose_name='Requiere Seguimiento')
    fecha_seguimiento = models.DateField(blank=True, null=True, verbose_name='Fecha de Seguimiento')
    
    # Control
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='interacciones_registradas')
    
    class Meta:
        verbose_name = 'Interacción'
        verbose_name_plural = 'Interacciones'
        ordering = ['-fecha_interaccion']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cliente.tercero.nombre} - {self.fecha_interaccion.strftime('%Y-%m-%d')}"


# --- Modelos de Pedidos ---

class Pedido(models.Model):
    """Modelo para la gestión de pedidos de clientes."""
    
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('confirmado', 'Confirmado'),
        ('en_produccion', 'En Producción'),
        ('parcial', 'Entrega Parcial'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]
    
    id_pedido = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_pedido = models.CharField(max_length=50, unique=True, verbose_name='Número de Pedido')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='pedidos')
    contacto = models.ForeignKey(Contacto, on_delete=models.PROTECT, related_name='pedidos')
    oportunidad = models.ForeignKey(Oportunidad, on_delete=models.SET_NULL, blank=True, null=True, related_name='pedidos')
    
    # Fechas
    fecha_pedido = models.DateTimeField(auto_now_add=True, verbose_name='Fecha del Pedido')
    fecha_requerida = models.DateField(verbose_name='Fecha Requerida')
    fecha_entrega = models.DateField(blank=True, null=True, verbose_name='Fecha de Entrega Real')
    
    # Estado y control
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador', verbose_name='Estado')
    prioridad = models.CharField(max_length=20, choices=[
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ], default='normal', verbose_name='Prioridad')
    
    # Información comercial
    orden_compra_cliente = models.CharField(max_length=100, blank=True, null=True, verbose_name='Orden de Compra Cliente')
    condiciones_pago = models.CharField(max_length=100, verbose_name='Condiciones de Pago')
    direccion_entrega = models.TextField(verbose_name='Dirección de Entrega')
    
    # Valores
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Subtotal')
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Descuento %')
    descuento_valor = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Descuento')
    iva = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='IVA')
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Total')
    
    # Observaciones
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    notas_internas = models.TextField(blank=True, null=True, verbose_name='Notas Internas')
    
    # Control
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pedidos_creados')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Última Modificación')
    
    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_pedido']
        indexes = [
            models.Index(fields=['numero_pedido']),
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['fecha_requerida']),
        ]
    
    def __str__(self):
        return f"{self.numero_pedido} - {self.cliente.tercero.nombre}"
    
    def calcular_totales(self):
        """Recalcula los totales del pedido basado en sus detalles."""
        detalles = self.detalles.all()
        self.subtotal = sum(detalle.subtotal for detalle in detalles)
        self.descuento_valor = self.subtotal * (self.descuento_porcentaje / 100)
        base_iva = self.subtotal - self.descuento_valor
        self.iva = base_iva * Decimal('0.19')  # IVA 19%
        self.total = base_iva + self.iva
        self.save()
    
    def save(self, *args, **kwargs):
        # Verificar cambio de estado
        estado_anterior = None
        if self.pk:
            estado_anterior = Pedido.objects.filter(pk=self.pk).values_list('estado', flat=True).first()
        
        super().save(*args, **kwargs)
        
        # Crear tarea automática cuando se confirma el pedido
        if estado_anterior == 'borrador' and self.estado == 'confirmado':
            Tarea.objects.create(
                titulo=f"Verificar disponibilidad - {self.numero_pedido}",
                descripcion=f"Verificar disponibilidad de materiales para el pedido {self.numero_pedido}.\nCliente: {self.cliente}\nFecha requerida: {self.fecha_requerida}\nValor total: ${self.total:,.0f}",
                tipo='revision',
                prioridad='urgente' if self.prioridad == 'urgente' else 'alta',
                modulo_origen='pedidos',
                pedido=self,
                asignado_a=self.usuario_creacion,
                creado_por=self.usuario_creacion,
                fecha_vencimiento=min(
                    timezone.now() + timedelta(days=1),
                    datetime.combine(self.fecha_requerida - timedelta(days=2), datetime.min.time()).replace(tzinfo=timezone.get_current_timezone())
                )
            )


class DetallePedido(models.Model):
    """Detalle de los productos incluidos en un pedido."""
    
    id_detalle = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    
    # Producto
    material = models.ForeignKey(Materiales, on_delete=models.PROTECT, verbose_name='Material')
    descripcion_adicional = models.CharField(max_length=500, blank=True, null=True, verbose_name='Descripción Adicional')
    
    # Cantidades
    cantidad = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Cantidad')
    unidad_medida = models.CharField(max_length=20, verbose_name='Unidad de Medida')
    cantidad_entregada = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Cantidad Entregada')
    
    # Especificaciones técnicas
    especificaciones = models.JSONField(blank=True, null=True, verbose_name='Especificaciones Técnicas')
    requiere_proceso_especial = models.BooleanField(default=False, verbose_name='Requiere Proceso Especial')
    proceso_especial = models.TextField(blank=True, null=True, verbose_name='Descripción Proceso Especial')
    
    # Precios
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Precio Unitario')
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Descuento %')
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Subtotal')
    
    # Fechas
    fecha_requerida = models.DateField(blank=True, null=True, verbose_name='Fecha Requerida Específica')
    
    class Meta:
        verbose_name = 'Detalle de Pedido'
        verbose_name_plural = 'Detalles de Pedido'
        ordering = ['pedido', 'material']
    
    def __str__(self):
        return f"{self.material.nombre} - {self.cantidad} {self.unidad_medida}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal antes de guardar
        self.subtotal = self.cantidad * self.precio_unitario * (1 - self.descuento_porcentaje / 100)
        super().save(*args, **kwargs)
        # Actualizar totales del pedido
        self.pedido.calcular_totales()


# --- Modelos de Órdenes de Producción ---

class OrdenProduccion(models.Model):
    """Orden de producción generada a partir de pedidos."""
    
    ESTADO_CHOICES = [
        ('programada', 'Programada'),
        ('en_proceso', 'En Proceso'),
        ('pausada', 'Pausada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    
    id_orden = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_orden = models.CharField(max_length=50, unique=True, verbose_name='Número de Orden')
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name='ordenes_produccion')
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_programada_inicio = models.DateTimeField(verbose_name='Fecha Programada de Inicio')
    fecha_programada_fin = models.DateTimeField(verbose_name='Fecha Programada de Fin')
    fecha_real_inicio = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Real de Inicio')
    fecha_real_fin = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Real de Fin')
    
    # Estado y control
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='programada', verbose_name='Estado')
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='normal', verbose_name='Prioridad')
    porcentaje_avance = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='% Avance')
    
    # Información adicional
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    instrucciones_especiales = models.TextField(blank=True, null=True, verbose_name='Instrucciones Especiales')
    
    # Control
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ordenes_creadas')
    supervisor_asignado = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ordenes_supervisadas', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Orden de Producción'
        verbose_name_plural = 'Órdenes de Producción'
        ordering = ['-prioridad', 'fecha_programada_inicio']
        indexes = [
            models.Index(fields=['numero_orden']),
            models.Index(fields=['estado', 'prioridad']),
            models.Index(fields=['fecha_programada_inicio']),
        ]
    
    def __str__(self):
        return f"{self.numero_orden} - Pedido: {self.pedido.numero_pedido}"
    
    def actualizar_avance(self):
        """Actualiza el porcentaje de avance basado en los detalles."""
        detalles = self.detalles.all()
        if detalles:
            total_peso = sum(d.cantidad_producir for d in detalles)
            total_completado = sum(d.cantidad_producida for d in detalles)
            if total_peso > 0:
                self.porcentaje_avance = (total_completado / total_peso) * 100
                self.save()
    
    def save(self, *args, **kwargs):
        # Verificar si es nueva
        es_nueva = self.pk is None
        
        super().save(*args, **kwargs)
        
        # Crear tareas automáticas cuando se crea la orden
        if es_nueva:
            # Tarea de planificación
            Tarea.objects.create(
                titulo=f"Planificar producción - {self.numero_orden}",
                descripcion=f"Planificar los procesos de producción para la orden {self.numero_orden}.\nPedido: {self.pedido.numero_pedido}\nCliente: {self.pedido.cliente}\nFecha programada: {self.fecha_programada_inicio.date()} al {self.fecha_programada_fin.date()}",
                tipo='accion',
                prioridad=self.prioridad,
                modulo_origen='ordenes',
                orden_produccion=self,
                asignado_a=self.supervisor_asignado if self.supervisor_asignado else self.usuario_creacion,
                creado_por=self.usuario_creacion,
                fecha_vencimiento=self.fecha_programada_inicio - timedelta(days=1)
            )
            
            # Tarea de verificación de materiales
            Tarea.objects.create(
                titulo=f"Verificar materiales - {self.numero_orden}",
                descripcion=f"Verificar disponibilidad y preparar materiales para la orden de producción {self.numero_orden}.",
                tipo='revision',
                prioridad='alta' if self.prioridad in ['urgente', 'alta'] else 'media',
                modulo_origen='ordenes',
                orden_produccion=self,
                asignado_a=self.supervisor_asignado if self.supervisor_asignado else self.usuario_creacion,
                creado_por=self.usuario_creacion,
                fecha_vencimiento=self.fecha_programada_inicio - timedelta(hours=12)
            )


class DetalleOrdenProduccion(models.Model):
    """Detalle de los materiales a producir en una orden."""
    
    id_detalle = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    orden = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='detalles')
    detalle_pedido = models.ForeignKey(DetallePedido, on_delete=models.PROTECT, related_name='ordenes_detalle')
    
    # Material y cantidades
    material = models.ForeignKey(Materiales, on_delete=models.PROTECT, verbose_name='Material a Producir')
    cantidad_producir = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Cantidad a Producir')
    cantidad_producida = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Cantidad Producida')
    unidad_medida = models.CharField(max_length=20, verbose_name='Unidad de Medida')
    
    # Secuencia de procesos
    secuencia_procesos = models.JSONField(verbose_name='Secuencia de Procesos')
    tiempo_estimado_total = models.IntegerField(verbose_name='Tiempo Estimado Total (minutos)')
    
    # Estado
    estado = models.CharField(max_length=20, choices=[
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ], default='pendiente', verbose_name='Estado')
    
    # Fechas
    fecha_inicio = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Inicio')
    fecha_fin = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Fin')
    
    class Meta:
        verbose_name = 'Detalle de Orden de Producción'
        verbose_name_plural = 'Detalles de Orden de Producción'
        ordering = ['orden', 'material']
    
    def __str__(self):
        return f"{self.material.nombre} - {self.cantidad_producir} {self.unidad_medida}"


class PlanificacionProcesos(models.Model):
    """Planificación detallada de procesos para cada detalle de orden."""
    
    TIPO_PROCESO_CHOICES = [
        ('molido', 'Molido'),
        ('lavado', 'Lavado'),
        ('peletizado', 'Peletizado'),
        ('inyeccion', 'Inyección'),
        ('homogeneizacion', 'Homogeneización'),
    ]
    
    id_planificacion = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    detalle_orden = models.ForeignKey(DetalleOrdenProduccion, on_delete=models.CASCADE, related_name='planificaciones')
    
    # Proceso
    tipo_proceso = models.CharField(max_length=20, choices=TIPO_PROCESO_CHOICES, verbose_name='Tipo de Proceso')
    secuencia = models.IntegerField(verbose_name='Orden en la Secuencia')
    
    # Recursos asignados
    maquina = models.ForeignKey(Maquinas, on_delete=models.PROTECT, verbose_name='Máquina Asignada')
    operario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Operario Asignado')
    
    # Planificación
    fecha_programada = models.DateTimeField(verbose_name='Fecha Programada')
    duracion_estimada = models.IntegerField(verbose_name='Duración Estimada (minutos)')
    
    # Enlace con producción actual
    orden_trabajo = models.CharField(max_length=100, unique=True, verbose_name='Orden de Trabajo')
    
    # Estado
    estado = models.CharField(max_length=20, choices=[
        ('programado', 'Programado'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ], default='programado', verbose_name='Estado')
    
    # Ejecución real
    fecha_inicio_real = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Inicio Real')
    fecha_fin_real = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Fin Real')
    cantidad_procesada = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Cantidad Procesada')
    
    # Referencias a producción
    produccion_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='ID Producción Asociada')
    
    class Meta:
        verbose_name = 'Planificación de Proceso'
        verbose_name_plural = 'Planificaciones de Procesos'
        ordering = ['detalle_orden', 'secuencia']
        indexes = [
            models.Index(fields=['orden_trabajo']),
            models.Index(fields=['tipo_proceso', 'estado']),
            models.Index(fields=['fecha_programada']),
        ]
    
    def __str__(self):
        return f"{self.orden_trabajo} - {self.get_tipo_proceso_display()}"


# ======================
# MÓDULO DE TAREAS
# ======================

class Tarea(models.Model):
    """Modelo principal para gestión de tareas."""
    
    # Identificación
    id_tarea = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True, verbose_name='Código')
    titulo = models.CharField(max_length=200, verbose_name='Título')
    descripcion = models.TextField(verbose_name='Descripción')
    
    # Clasificación
    TIPO_CHOICES = [
        ('seguimiento', 'Seguimiento'),
        ('accion', 'Acción Requerida'),
        ('revision', 'Revisión'),
        ('aprobacion', 'Aprobación'),
        ('recordatorio', 'Recordatorio'),
        ('incidencia', 'Incidencia'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media', verbose_name='Prioridad')
    
    MODULO_CHOICES = [
        ('crm', 'CRM'),
        ('pedidos', 'Pedidos'),
        ('ordenes', 'Órdenes de Producción'),
        ('produccion', 'Producción'),
        ('inventario', 'Inventario'),
        ('general', 'General'),
    ]
    modulo_origen = models.CharField(max_length=20, choices=MODULO_CHOICES, verbose_name='Módulo Origen')
    
    # Enlaces a entidades
    cliente = models.ForeignKey('Cliente', on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='tareas', verbose_name='Cliente')
    pedido = models.ForeignKey('Pedido', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='tareas', verbose_name='Pedido')
    orden_produccion = models.ForeignKey('OrdenProduccion', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='tareas', verbose_name='Orden de Producción')
    oportunidad = models.ForeignKey('Oportunidad', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='tareas', verbose_name='Oportunidad')
    
    # Responsables
    asignado_a = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tareas_asignadas',
                                   verbose_name='Asignado a')
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tareas_creadas',
                                   verbose_name='Creado por')
    equipo = models.ManyToManyField(User, related_name='tareas_equipo', blank=True,
                                     verbose_name='Equipo')
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_vencimiento = models.DateTimeField(verbose_name='Fecha de Vencimiento')
    fecha_inicio = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Inicio')
    fecha_completado = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Completado')
    
    # Estado
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('pausada', 'Pausada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('vencida', 'Vencida'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name='Estado')
    porcentaje_avance = models.IntegerField(default=0, verbose_name='Porcentaje de Avance',
                                            validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Etiquetas y categorización
    etiquetas = models.JSONField(default=list, blank=True, verbose_name='Etiquetas')
    categoria = models.CharField(max_length=100, blank=True, verbose_name='Categoría')
    
    # Notificaciones
    enviar_recordatorio = models.BooleanField(default=True, verbose_name='Enviar Recordatorio')
    dias_antes_recordatorio = models.IntegerField(default=1, verbose_name='Días Antes del Recordatorio')
    recordatorio_enviado = models.BooleanField(default=False, verbose_name='Recordatorio Enviado')
    
    def save(self, *args, **kwargs):
        # Generar código automáticamente si no existe
        if not self.codigo:
            prefix = 'TAR'
            last_tarea = Tarea.objects.filter(codigo__startswith=prefix).order_by('-codigo').first()
            if last_tarea:
                last_number = int(last_tarea.codigo.replace(prefix + '-', ''))
                self.codigo = f"{prefix}-{str(last_number + 1).zfill(6)}"
            else:
                self.codigo = f"{prefix}-000001"
        
        # Actualizar estado automáticamente
        if self.estado == 'pendiente' and self.fecha_vencimiento and timezone.now() > self.fecha_vencimiento:
            self.estado = 'vencida'
        
        super().save(*args, **kwargs)
    
    def actualizar_progreso(self):
        """Actualiza el progreso basado en subtareas completadas."""
        if self.subtareas.exists():
            total = self.subtareas.count()
            completadas = self.subtareas.filter(completada=True).count()
            self.porcentaje_avance = int((completadas / total) * 100)
            self.save()
    
    def get_entidad_relacionada(self):
        """Retorna la entidad principal relacionada con la tarea."""
        if self.cliente:
            return self.cliente
        elif self.pedido:
            return self.pedido
        elif self.orden_produccion:
            return self.orden_produccion
        elif self.oportunidad:
            return self.oportunidad
        return None
    
    def __str__(self):
        return f"{self.codigo} - {self.titulo}"
    
    class Meta:
        db_table = 'tareas'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['-prioridad', 'fecha_vencimiento']
        indexes = [
            models.Index(fields=['estado', 'asignado_a']),
            models.Index(fields=['modulo_origen', 'estado']),
            models.Index(fields=['fecha_vencimiento']),
        ]


class Subtarea(models.Model):
    """Subtareas o checklist items de una tarea principal."""
    
    id_subtarea = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tarea_padre = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='subtareas',
                                    verbose_name='Tarea Padre')
    titulo = models.CharField(max_length=200, verbose_name='Título')
    completada = models.BooleanField(default=False, verbose_name='Completada')
    orden = models.IntegerField(default=0, verbose_name='Orden')
    fecha_completado = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Completado')
    completado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name='Completado por')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar progreso de la tarea padre
        self.tarea_padre.actualizar_progreso()
    
    def __str__(self):
        return f"{self.titulo} - {self.tarea_padre.codigo}"
    
    class Meta:
        db_table = 'subtareas'
        verbose_name = 'Subtarea'
        verbose_name_plural = 'Subtareas'
        ordering = ['orden', 'titulo']


class ComentarioTarea(models.Model):
    """Comentarios y seguimiento de tareas."""
    
    id_comentario = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='comentarios',
                              verbose_name='Tarea')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    comentario = models.TextField(verbose_name='Comentario')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    archivos_adjuntos = models.JSONField(default=list, blank=True, verbose_name='Archivos Adjuntos')
    es_interno = models.BooleanField(default=False, verbose_name='Es Interno',
                                     help_text='Marcar para notas internas no visibles al cliente')
    
    def __str__(self):
        return f"Comentario de {self.usuario.get_full_name()} en {self.tarea.codigo}"
    
    class Meta:
        db_table = 'comentarios_tarea'
        verbose_name = 'Comentario de Tarea'
        verbose_name_plural = 'Comentarios de Tareas'
        ordering = ['-fecha']


class PlantillaTarea(models.Model):
    """Plantillas para crear tareas automáticamente."""
    
    id_plantilla = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    descripcion = models.TextField(verbose_name='Descripción')
    modulo = models.CharField(max_length=20, choices=Tarea.MODULO_CHOICES, verbose_name='Módulo')
    
    # Configuración de la tarea
    titulo_template = models.CharField(max_length=200, verbose_name='Título de la Tarea')
    descripcion_template = models.TextField(verbose_name='Descripción de la Tarea')
    tipo = models.CharField(max_length=20, choices=Tarea.TIPO_CHOICES, verbose_name='Tipo')
    prioridad_default = models.CharField(max_length=10, choices=Tarea.PRIORIDAD_CHOICES,
                                         default='media', verbose_name='Prioridad por Defecto')
    dias_para_vencer = models.IntegerField(default=7, verbose_name='Días para Vencer')
    
    # Subtareas predefinidas
    subtareas_template = models.JSONField(default=list, verbose_name='Subtareas',
                                          help_text='Lista de subtareas a crear')
    
    activa = models.BooleanField(default=True, verbose_name='Activa')
    
    # Triggers automáticos
    TRIGGER_CHOICES = [
        ('nueva_oportunidad', 'Nueva Oportunidad CRM'),
        ('pedido_confirmado', 'Pedido Confirmado'),
        ('orden_creada', 'Orden de Producción Creada'),
        ('produccion_iniciada', 'Producción Iniciada'),
        ('cliente_nuevo', 'Cliente Nuevo'),
    ]
    trigger = models.CharField(max_length=50, choices=TRIGGER_CHOICES, blank=True,
                               verbose_name='Trigger Automático')
    
    def crear_tarea(self, usuario, **kwargs):
        """Crea una tarea basada en esta plantilla."""
        fecha_vencimiento = timezone.now() + timedelta(days=self.dias_para_vencer)
        
        tarea = Tarea.objects.create(
            titulo=self.titulo_template.format(**kwargs),
            descripcion=self.descripcion_template.format(**kwargs),
            tipo=self.tipo,
            prioridad=self.prioridad_default,
            modulo_origen=self.modulo,
            asignado_a=usuario,
            creado_por=usuario,
            fecha_vencimiento=fecha_vencimiento,
            **kwargs
        )
        
        # Crear subtareas
        for idx, subtarea_titulo in enumerate(self.subtareas_template):
            Subtarea.objects.create(
                tarea_padre=tarea,
                titulo=subtarea_titulo,
                orden=idx + 1
            )
        
        return tarea
    
    def __str__(self):
        return f"{self.nombre} ({self.modulo})"
    
    class Meta:
        db_table = 'plantillas_tarea'
        verbose_name = 'Plantilla de Tarea'
        verbose_name_plural = 'Plantillas de Tareas'
        ordering = ['modulo', 'nombre']


class PQRS(models.Model):
    """Modelo para gestionar Peticiones, Quejas, Reclamos y Sugerencias."""
    
    TIPO_CHOICES = [
        ('peticion', 'Petición'),
        ('queja', 'Queja'),
        ('reclamo', 'Reclamo'),
        ('sugerencia', 'Sugerencia'),
        ('felicitacion', 'Felicitación'),
    ]
    
    ESTADO_CHOICES = [
        ('recibida', 'Recibida'),
        ('en_proceso', 'En Proceso'),
        ('escalada', 'Escalada'),
        ('solucionada', 'Solucionada'),
        ('cerrada', 'Cerrada'),
        ('cancelada', 'Cancelada'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    CANAL_CHOICES = [
        ('web', 'Sitio Web'),
        ('email', 'Email'),
        ('telefono', 'Teléfono'),
        ('presencial', 'Presencial'),
        ('whatsapp', 'WhatsApp'),
        ('chat', 'Chat'),
        ('otro', 'Otro'),
    ]
    
    # Información básica
    id_pqrs = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_pqrs = models.CharField(max_length=20, unique=True, verbose_name='Número PQRS')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    
    # Información del cliente
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='pqrs', verbose_name='Cliente')
    nombre_contacto = models.CharField(max_length=200, verbose_name='Nombre del Contacto')
    email_contacto = models.EmailField(verbose_name='Email del Contacto')
    telefono_contacto = models.CharField(max_length=50, blank=True, null=True, verbose_name='Teléfono')
    
    # Detalles de la PQRS
    asunto = models.CharField(max_length=200, verbose_name='Asunto')
    descripcion = models.TextField(verbose_name='Descripción')
    canal_recepcion = models.CharField(max_length=20, choices=CANAL_CHOICES, verbose_name='Canal de Recepción')
    
    # Información relacionada
    pedido_relacionado = models.ForeignKey(Pedido, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='pqrs', verbose_name='Pedido Relacionado')
    oportunidad_relacionada = models.ForeignKey(Oportunidad, on_delete=models.SET_NULL, null=True, blank=True,
                                               related_name='pqrs', verbose_name='Oportunidad Relacionada')
    
    # Estado y seguimiento
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='recibida', verbose_name='Estado')
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='media', verbose_name='Prioridad')
    
    # Responsables
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pqrs_creadas',
                                        verbose_name='Usuario que Registró')
    usuario_asignado = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pqrs_asignadas',
                                        verbose_name='Usuario Asignado')
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_asignacion = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Asignación')
    fecha_primera_respuesta = models.DateTimeField(null=True, blank=True, verbose_name='Fecha Primera Respuesta')
    fecha_solucion = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Solución')
    fecha_cierre = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Cierre')
    fecha_vencimiento = models.DateTimeField(verbose_name='Fecha de Vencimiento')
    
    # Resolución
    solucion = models.TextField(blank=True, null=True, verbose_name='Solución')
    satisfaccion_cliente = models.IntegerField(null=True, blank=True, 
                                             validators=[MinValueValidator(1), MaxValueValidator(5)],
                                             verbose_name='Satisfacción del Cliente (1-5)')
    
    # Archivos adjuntos
    archivos_adjuntos = models.JSONField(default=list, blank=True, verbose_name='Archivos Adjuntos')
    
    # Configuración de recordatorios
    enviar_recordatorio = models.BooleanField(default=True, verbose_name='Enviar Recordatorio')
    recordatorio_enviado = models.BooleanField(default=False, verbose_name='Recordatorio Enviado')
    
    # Métrica de tiempo
    tiempo_respuesta = models.DurationField(null=True, blank=True, verbose_name='Tiempo de Respuesta')
    tiempo_solucion = models.DurationField(null=True, blank=True, verbose_name='Tiempo de Solución')
    
    def save(self, *args, **kwargs):
        # Generar número único si es nuevo
        if not self.numero_pqrs:
            year = timezone.now().year
            ultimo_numero = PQRS.objects.filter(
                numero_pqrs__startswith=f"PQRS{year}"
            ).count() + 1
            self.numero_pqrs = f"PQRS{year}{ultimo_numero:05d}"
        
        # Calcular fechas de vencimiento según el tipo
        if not self.fecha_vencimiento:
            if self.tipo in ['reclamo', 'queja']:
                self.fecha_vencimiento = timezone.now() + timedelta(days=3)
            elif self.tipo == 'peticion':
                self.fecha_vencimiento = timezone.now() + timedelta(days=7)
            else:  # sugerencia, felicitacion
                self.fecha_vencimiento = timezone.now() + timedelta(days=15)
        
        # Actualizar fechas de seguimiento
        estado_anterior = None
        if self.pk:
            estado_anterior = PQRS.objects.filter(pk=self.pk).values_list('estado', flat=True).first()
        
        super().save(*args, **kwargs)
        
        # Actualizar métricas de tiempo
        if estado_anterior != self.estado:
            now = timezone.now()
            if self.estado == 'en_proceso' and not self.fecha_primera_respuesta:
                self.fecha_primera_respuesta = now
                self.tiempo_respuesta = now - self.fecha_creacion
            elif self.estado == 'solucionada' and not self.fecha_solucion:
                self.fecha_solucion = now
                self.tiempo_solucion = now - self.fecha_creacion
            elif self.estado == 'cerrada' and not self.fecha_cierre:
                self.fecha_cierre = now
        
        # Crear tarea automática cuando se recibe una PQRS
        if not estado_anterior and self.estado == 'recibida':
            # Determinar prioridad de la tarea
            prioridad_tarea = 'media'
            if self.tipo in ['reclamo', 'queja']:
                prioridad_tarea = 'alta'
            elif self.prioridad == 'critica':
                prioridad_tarea = 'urgente'
            
            Tarea.objects.create(
                titulo=f"Gestionar {self.get_tipo_display()}: {self.asunto}",
                descripcion=f"Gestionar {self.get_tipo_display().lower()} del cliente {self.nombre_contacto}.\n"
                           f"Asunto: {self.asunto}\n"
                           f"Canal: {self.get_canal_recepcion_display()}\n"
                           f"Prioridad: {self.get_prioridad_display()}\n"
                           f"Vencimiento: {self.fecha_vencimiento.strftime('%d/%m/%Y')}",
                tipo='accion',
                prioridad=prioridad_tarea,
                modulo_origen='crm',
                asignado_a=self.usuario_asignado,
                creado_por=self.usuario_creacion,
                fecha_vencimiento=self.fecha_vencimiento,
                cliente=self.cliente,
                pedido=self.pedido_relacionado,
                oportunidad=self.oportunidad_relacionada
            )
    
    @property
    def esta_vencida(self):
        """Verifica si la PQRS está vencida."""
        return self.fecha_vencimiento < timezone.now() and self.estado not in ['solucionada', 'cerrada']
    
    @property
    def tiempo_transcurrido(self):
        """Calcula el tiempo transcurrido desde la creación."""
        return timezone.now() - self.fecha_creacion
    
    @property
    def cumple_sla(self):
        """Verifica si cumple con los SLAs establecidos."""
        if self.estado in ['solucionada', 'cerrada']:
            return not self.esta_vencida
        return self.fecha_vencimiento >= timezone.now()
    
    def __str__(self):
        return f"{self.numero_pqrs} - {self.asunto}"
    
    class Meta:
        db_table = 'pqrs'
        verbose_name = 'PQRS'
        verbose_name_plural = 'PQRS'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', 'prioridad']),
            models.Index(fields=['tipo', 'fecha_creacion']),
            models.Index(fields=['usuario_asignado', 'estado']),
            models.Index(fields=['fecha_vencimiento']),
        ]


class SeguimientoPQRS(models.Model):
    """Modelo para registrar el seguimiento y respuestas a PQRS."""
    
    TIPO_SEGUIMIENTO_CHOICES = [
        ('respuesta', 'Respuesta al Cliente'),
        ('nota_interna', 'Nota Interna'),
        ('escalamiento', 'Escalamiento'),
        ('solucion', 'Solución'),
        ('cambio_estado', 'Cambio de Estado'),
    ]
    
    id_seguimiento = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pqrs = models.ForeignKey(PQRS, on_delete=models.CASCADE, related_name='seguimientos',
                            verbose_name='PQRS')
    
    tipo_seguimiento = models.CharField(max_length=20, choices=TIPO_SEGUIMIENTO_CHOICES, 
                                       verbose_name='Tipo de Seguimiento')
    descripcion = models.TextField(verbose_name='Descripción')
    
    # Información del usuario
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    
    # Archivos adjuntos
    archivos_adjuntos = models.JSONField(default=list, blank=True, verbose_name='Archivos Adjuntos')
    
    # Configuración de visibilidad
    visible_cliente = models.BooleanField(default=True, verbose_name='Visible para Cliente')
    notificar_cliente = models.BooleanField(default=True, verbose_name='Notificar al Cliente')
    
    # Estados anteriores (para cambios de estado)
    estado_anterior = models.CharField(max_length=20, blank=True, null=True, verbose_name='Estado Anterior')
    estado_nuevo = models.CharField(max_length=20, blank=True, null=True, verbose_name='Estado Nuevo')
    
    def __str__(self):
        return f"{self.pqrs.numero_pqrs} - {self.get_tipo_seguimiento_display()}"
    
    class Meta:
        db_table = 'seguimiento_pqrs'
        verbose_name = 'Seguimiento PQRS'
        verbose_name_plural = 'Seguimientos PQRS'
        ordering = ['-fecha']
