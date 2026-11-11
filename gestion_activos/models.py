import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


class Obra(models.Model):
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código de Obra")
    nombre = models.CharField(max_length=150, verbose_name="Nombre del Proyecto / Faena")
    direccion = models.CharField(max_length=250, verbose_name="Ubicación / Dirección")
    supervisor_nombre = models.CharField(max_length=120, verbose_name="Supervisor a Cargo")
    supervisor_telefono = models.CharField(max_length=25, verbose_name="Teléfono Supervisor")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_estimada_cierre = models.DateField(verbose_name="Fecha Estimada de Cierre")
    activa = models.BooleanField(default=True, verbose_name="Obra en Operación")

    class Meta:
        verbose_name = "Obra / Faena"
        verbose_name_plural = "Obras / Faenas"
        ordering = ['-activa', 'nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Contratista(models.Model):
    ESTADOS = [
        ('HABILITADO', 'Habilitado para Retiro'),
        ('BLOQUEADO_MOROSIDAD', 'Bloqueado por Morosidad'),
        ('SUSPENDIDO', 'Suspendido por Disciplina / Daño'),
    ]

    rut = models.CharField(max_length=15, unique=True, verbose_name="RUT / DNI Empresa")
    razon_social = models.CharField(max_length=150, verbose_name="Razón Social / Contratista")
    representante_legal = models.CharField(max_length=120, verbose_name="Representante Legal")
    email = models.EmailField(verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=25, verbose_name="Teléfono de Contacto")
    estado = models.CharField(max_length=25, choices=ESTADOS, default='HABILITADO', verbose_name="Estado Operativo")
    motivo_bloqueo = models.TextField(blank=True, default="", verbose_name="Motivo de Bloqueo")
    fecha_bloqueo = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Bloqueo")

    class Meta:
        verbose_name = "Subcontratista"
        verbose_name_plural = "Subcontratistas"
        ordering = ['razon_social']

    def __str__(self):
        return f"{self.razon_social} ({self.rut}) [{self.get_estado_display()}]"

    @property
    def esta_habilitado(self):
        return self.estado == 'HABILITADO'

    def bloquear_por_morosidad(self, motivo="Atraso en devolución de herramientas pactadas."):
        self.estado = 'BLOQUEADO_MOROSIDAD'
        self.motivo_bloqueo = motivo
        self.fecha_bloqueo = timezone.now()
        self.save(update_fields=['estado', 'motivo_bloqueo', 'fecha_bloqueo'])

    def desbloquear(self):
        self.estado = 'HABILITADO'
        self.motivo_bloqueo = ""
        self.fecha_bloqueo = None
        self.save(update_fields=['estado', 'motivo_bloqueo', 'fecha_bloqueo'])


class CategoriaHerramienta(models.Model):
    nombre = models.CharField(max_length=80, unique=True, verbose_name="Nombre de Categoría")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción Técnica")
    frecuencia_mantenimiento_horas = models.PositiveIntegerField(
        default=100,
        verbose_name="Frecuencia Mantenimiento (Horas de Uso)"
    )
    dias_maximo_prestamo = models.PositiveIntegerField(
        default=15,
        verbose_name="Días Máximos de Préstamo Estándar"
    )

    class Meta:
        verbose_name = "Categoría de Herramienta"
        verbose_name_plural = "Categorías de Herramientas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Herramienta(models.Model):
    ESTADOS = [
        ('DISPONIBLE', 'Disponible en Bodega'),
        ('EN_USO', 'En Uso en Obra'),
        ('MANTENIMIENTO', 'En Mantenimiento Técnico'),
        ('DADO_DE_BAJA', 'Dado de Baja / Desecho'),
    ]

    codigo_inventario = models.CharField(max_length=30, unique=True, verbose_name="Código Inventario / SKU")
    nombre = models.CharField(max_length=120, verbose_name="Nombre del Activo")
    categoria = models.ForeignKey(CategoriaHerramienta, on_delete=models.PROTECT, related_name="herramientas")
    marca = models.CharField(max_length=80, verbose_name="Marca")
    modelo = models.CharField(max_length=80, verbose_name="Modelo")
    numero_serie = models.CharField(max_length=80, blank=True, default="", verbose_name="Número de Serie")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='DISPONIBLE', verbose_name="Estado Actual")
    horas_uso_acumuladas = models.PositiveIntegerField(default=0, verbose_name="Horas de Uso Acumuladas")
    horas_proximo_mantenimiento = models.PositiveIntegerField(default=100, verbose_name="Horas Umbral Mantenimiento")
    fecha_proximo_mantenimiento = models.DateField(null=True, blank=True, verbose_name="Fecha Límite Mantenimiento")
    bodega_actual = models.CharField(max_length=100, default="Bodega Central", verbose_name="Bodega / Ubicación Física")
    obra_actual = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="herramientas_asignadas")
    valor_reposicion = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Valor de Reposición (CLP)")
    fecha_adquisicion = models.DateField(auto_now_add=True, verbose_name="Fecha de Adquisición")
    imagen = models.ImageField(upload_to='herramientas/', null=True, blank=True, verbose_name="Fotografía / Plano Referencial")
    imagen_url = models.CharField(max_length=500, blank=True, default="", verbose_name="URL Imagen Vectorial / Externa")

    class Meta:
        verbose_name = "Herramienta / Activo"
        verbose_name_plural = "Herramientas / Activos"
        ordering = ['codigo_inventario']

    def __str__(self):
        return f"[{self.codigo_inventario}] {self.nombre} ({self.marca} {self.modelo}) - {self.get_estado_display()}"

    @property
    def get_imagen_url(self):
        if self.imagen:
            return self.imagen.url
        if self.imagen_url:
            return self.imagen_url
        return "/static/images/herramientas/default_tool.svg"

    def registrar_horas(self, horas_agregadas):
        self.horas_uso_acumuladas += horas_agregadas
        if self.horas_uso_acumuladas >= self.horas_proximo_mantenimiento:
            self.estado = 'MANTENIMIENTO'
            MantenimientoPreventivo.objects.create(
                codigo_orden=f"MTO-AUTO-{self.codigo_inventario}-{timezone.now().strftime('%Y%m%d%H%M')}",
                herramienta=self,
                tipo='PREVENTIVO',
                horas_al_momento=self.horas_uso_acumuladas,
                fecha_programada=timezone.now().date(),
                descripcion_trabajo=f"Disparo automático de mantenimiento por cumplir {self.horas_uso_acumuladas} horas de trabajo.",
                tecnico_responsable="Taller Central BuildCorp"
            )
        self.save(update_fields=['horas_uso_acumuladas', 'estado'])


class PrestamoHerramienta(models.Model):
    ESTADOS = [
        ('ACTIVO', 'Préstamo Activo / En Terreno'),
        ('DEVUELTO', 'Devuelto Conforme'),
        ('VENCIDO_MOROSO', 'Vencido / En Morosidad'),
        ('DEVUELTO_OBSERVADO', 'Devuelto con Daños / Incompleto'),
    ]

    codigo_prestamo = models.CharField(max_length=30, unique=True, verbose_name="N° Folio Préstamo")
    contratista = models.ForeignKey(Contratista, on_delete=models.PROTECT, related_name="prestamos")
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name="prestamos")
    fecha_prestamo = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora de Salida")
    fecha_pactada_devolucion = models.DateField(verbose_name="Fecha Pactada de Devolución")
    fecha_real_devolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha y Hora Real Devolución")
    estado = models.CharField(max_length=25, choices=ESTADOS, default='ACTIVO', verbose_name="Estado de Préstamo")
    responsable_despacho = models.ForeignKey(User, on_delete=models.PROTECT, related_name="despachos_realizados")
    receptor_nombre = models.CharField(max_length=120, verbose_name="Nombre Quien Recibe en Obra")
    receptor_rut = models.CharField(max_length=15, verbose_name="RUT Quien Recibe")
    firma_digital_entrega = models.TextField(verbose_name="Firma Digital Entrega (Base64)")
    observaciones_entrega = models.TextField(blank=True, default="", verbose_name="Observaciones de Entrega")

    class Meta:
        verbose_name = "Préstamo / Guía de Entrega"
        verbose_name_plural = "Préstamos / Guías de Entrega"
        ordering = ['-fecha_prestamo']

    def __str__(self):
        return f"{self.codigo_prestamo} | {self.contratista.razon_social} -> {self.obra.nombre}"

    def clean(self):
        super().clean()
        if not self.pk and self.contratista.estado == 'BLOQUEADO_MOROSIDAD':
            raise ValidationError(
                f"Bloqueo de Seguridad: El contratista '{self.contratista.razon_social}' se encuentra "
                f"BLOQUEADO POR MOROSIDAD. Se prohíben nuevas entregas hasta saldar pendientes."
            )

    def evaluar_morosidad(self):
        hoy = timezone.now().date()
        if self.estado == 'ACTIVO' and self.fecha_pactada_devolucion < hoy:
            self.estado = 'VENCIDO_MOROSO'
            self.save(update_fields=['estado'])
            dias_retraso = (hoy - self.fecha_pactada_devolucion).days
            
            alerta, created = AlertaMorosidad.objects.get_or_create(
                prestamo=self,
                contratista=self.contratista,
                defaults={'dias_retraso': dias_retraso, 'contratista_bloqueado': True}
            )
            if not created:
                alerta.dias_retraso = dias_retraso
                alerta.save(update_fields=['dias_retraso'])

            self.contratista.bloquear_por_morosidad(
                motivo=f"Retención morosa en préstamo {self.codigo_prestamo} ({dias_retraso} días de atraso en {self.obra.nombre})."
            )


class ItemPrestamo(models.Model):
    prestamo = models.ForeignKey(PrestamoHerramienta, on_delete=models.CASCADE, related_name="items")
    herramienta = models.ForeignKey(Herramienta, on_delete=models.PROTECT, related_name="prestamos_registrados")
    horas_uso_iniciales = models.PositiveIntegerField(default=0, verbose_name="Horómetro Inicial")
    horas_uso_finales = models.PositiveIntegerField(null=True, blank=True, verbose_name="Horómetro Final")
    devuelto = models.BooleanField(default=False, verbose_name="Item Devuelto")
    observaciones_devolucion = models.TextField(blank=True, default="", verbose_name="Observaciones de Retorno")

    class Meta:
        verbose_name = "Detalle de Herramienta Prestada"
        verbose_name_plural = "Detalles de Herramientas Prestadas"
        unique_together = ('prestamo', 'herramienta')

    def __str__(self):
        return f"{self.herramienta.nombre} en {self.prestamo.codigo_prestamo}"


class DevolucionActa(models.Model):
    prestamo = models.OneToOneField(PrestamoHerramienta, on_delete=models.CASCADE, related_name="acta_devolucion")
    fecha_devolucion = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora de Recepción")
    recibido_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name="recepciones_bodega")
    entregado_por_nombre = models.CharField(max_length=120, verbose_name="Nombre Responsable que Devuelve")
    entregado_por_rut = models.CharField(max_length=15, verbose_name="RUT Responsable que Devuelve")
    firma_digital_devolucion = models.TextField(verbose_name="Firma Digital Recepción (Base64)")
    costo_penalizacion = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Penalización por Retraso o Daño (CLP)")
    observaciones_recepcion = models.TextField(blank=True, default="", verbose_name="Observaciones de Recepción")

    class Meta:
        verbose_name = "Acta de Devolución"
        verbose_name_plural = "Actas de Devolución"

    def __str__(self):
        return f"Acta Retorno {self.prestamo.codigo_prestamo} ({self.fecha_devolucion.strftime('%d/%m/%Y')})"


class MantenimientoPreventivo(models.Model):
    TIPOS = [
        ('PREVENTIVO', 'Mantenimiento Preventivo Periódico'),
        ('CORRECTIVO', 'Reparación Correctiva por Daño'),
        ('CALIBRACION', 'Inspección y Calibración Técnica'),
    ]
    ESTADOS = [
        ('PROGRAMADO', 'Programado / Pendiente'),
        ('EN_PROCESO', 'En Taller / En Proceso'),
        ('COMPLETADO', 'Completado / Operativa'),
        ('CANCELADO', 'Cancelado'),
    ]

    codigo_orden = models.CharField(max_length=40, unique=True, verbose_name="N° Orden de Trabajo")
    herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE, related_name="mantenimientos")
    tipo = models.CharField(max_length=20, choices=TIPOS, default='PREVENTIVO', verbose_name="Tipo de Mantenimiento")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROGRAMADO', verbose_name="Estado de Orden")
    horas_al_momento = models.PositiveIntegerField(verbose_name="Horómetro al Ingreso")
    fecha_programada = models.DateField(verbose_name="Fecha Programada")
    fecha_ejecucion = models.DateField(null=True, blank=True, verbose_name="Fecha de Ejecución Real")
    tecnico_responsable = models.CharField(max_length=120, verbose_name="Técnico / Taller Asignado")
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo de Mantención (CLP)")
    descripcion_trabajo = models.TextField(verbose_name="Descripción del Servicio")
    repuestos_utilizados = models.TextField(blank=True, default="", verbose_name="Repuestos Utilizados")

    class Meta:
        verbose_name = "Orden de Mantenimiento"
        verbose_name_plural = "Órdenes de Mantenimiento"
        ordering = ['-fecha_programada']

    def __str__(self):
        return f"{self.codigo_orden} - {self.herramienta.nombre} [{self.get_estado_display()}]"

    def finalizar_mantenimiento(self, costo_final=0, nuevas_horas_proximo=100):
        self.estado = 'COMPLETADO'
        self.fecha_ejecucion = timezone.now().date()
        self.costo = costo_final
        self.save()

        self.herramienta.estado = 'DISPONIBLE'
        self.herramienta.horas_proximo_mantenimiento = self.herramienta.horas_uso_acumuladas + nuevas_horas_proximo
        self.herramienta.save(update_fields=['estado', 'horas_proximo_mantenimiento'])


class AlertaMorosidad(models.Model):
    GRAVEDADES = [
        ('LEVE', 'Retraso 1-2 Días (Aviso Preventivo)'),
        ('MODERADA', 'Retraso 3-5 Días (Multa Aplicable)'),
        ('CRITICA', 'Retraso > 5 Días (Bloqueo Automático Activo)'),
    ]

    prestamo = models.ForeignKey(PrestamoHerramienta, on_delete=models.CASCADE, related_name="alertas")
    contratista = models.ForeignKey(Contratista, on_delete=models.CASCADE, related_name="alertas_morosidad")
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Alerta")
    dias_retraso = models.PositiveIntegerField(default=1, verbose_name="Días de Retraso")
    gravedad = models.CharField(max_length=20, choices=GRAVEDADES, default='CRITICA', verbose_name="Nivel de Gravedad")
    contratista_bloqueado = models.BooleanField(default=True, verbose_name="Bloqueo Ejecutado")
    resuelta = models.BooleanField(default=False, verbose_name="Alerta Regularizada")
    fecha_resolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Resolución")

    class Meta:
        verbose_name = "Alerta de Morosidad"
        verbose_name_plural = "Alertas de Morosidad"
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"Alerta {self.contratista.razon_social} - {self.dias_retraso} días atraso"

    def resolver(self):
        self.resuelta = True
        self.fecha_resolucion = timezone.now()
        self.save(update_fields=['resuelta', 'fecha_resolucion'])
        otras_alertas = AlertaMorosidad.objects.filter(contratista=self.contratista, resuelta=False).exclude(pk=self.pk)
        if not otras_alertas.exists():
            self.contratista.desbloquear()


# ==============================================================================
# AUDITORÍA ISO 27001 / ISO 9001 (TRAZABILIDAD TOTAL DE ACCIONES)
# ==============================================================================

class RegistroAuditoria(models.Model):
    ACCIONES = [
        ('CREACION', 'Alta / Creación de Registro'),
        ('MODIFICACION', 'Modificación de Datos'),
        ('ELIMINACION', 'Baja / Eliminación de Registro'),
        ('DESPACHO_PRESTAMO', 'Emisión de Guía de Despacho con Firma'),
        ('RECEPCION_DEVOLUCION', 'Recepción de Herramientas con Firma'),
        ('BLOQUEO_MOROSIDAD', 'Bloqueo Disciplinario de Contratista'),
        ('DESBLOQUEO_CONTRATISTA', 'Levantamiento de Bloqueo / Regularización'),
        ('ORDEN_MANTENIMIENTO', 'Apertura de Orden de Mantenimiento'),
        ('CIERRE_MANTENIMIENTO', 'Finalización de Mantenimiento Técnico'),
        ('AUTENTICACION', 'Inicio / Cierre de Sesión'),
        ('BLOQUEO_SEGURIDAD', 'Bloqueo por Fuerza Bruta / Amenaza'),
        ('OPERACION_API', 'Operación Automatizada vía REST API'),
    ]

    MODULOS = [
        ('HERRAMIENTAS', 'Catálogo de Activos'),
        ('PRESTAMOS', 'Módulo de Préstamos y Firma Digital'),
        ('CONTRATISTAS', 'Padrón de Contratistas'),
        ('OBRAS', 'Obras y Faenas'),
        ('MANTENIMIENTO', 'Servicio Técnico'),
        ('SEGURIDAD', 'Autenticación y Sesiones'),
    ]

    usuario = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_auditoria",
        verbose_name="Usuario Responsable"
    )
    usuario_nombre = models.CharField(max_length=150, verbose_name="Nombre / Identificador Usuario")
    accion = models.CharField(max_length=30, choices=ACCIONES, verbose_name="Tipo de Acción")
    modulo = models.CharField(max_length=30, choices=MODULOS, verbose_name="Módulo Afectado")
    identificador_objeto = models.CharField(max_length=100, verbose_name="Folio / Código / RUT Afectado")
    descripcion_detalle = models.TextField(verbose_name="Detalle de la Operación")
    ip_origen = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP de Origen")
    fecha_hora = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="Estampa de Tiempo (UTC/CLT)")
    hash_integridad = models.CharField(max_length=64, blank=True, verbose_name="Hash Criptográfico SHA-256 (Inmutabilidad ISO)")

    class Meta:
        verbose_name = "Registro de Auditoría ISO"
        verbose_name_plural = "Bitácora de Auditoría ISO (Trazabilidad)"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"[{self.fecha_hora.strftime('%d/%m/%Y %H:%M:%S')}] {self.usuario_nombre} -> {self.get_accion_display()} ({self.identificador_objeto})"

    def save(self, *args, **kwargs):
        if not self.hash_integridad:
            cadena_hash = f"{self.fecha_hora.isoformat()}|{self.usuario_nombre}|{self.accion}|{self.identificador_objeto}|{self.ip_origen}|{self.descripcion_detalle}"
            self.hash_integridad = hashlib.sha256(cadena_hash.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)
