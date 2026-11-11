from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Obra,
    Contratista,
    CategoriaHerramienta,
    Herramienta,
    PrestamoHerramienta,
    ItemPrestamo,
    DevolucionActa,
    MantenimientoPreventivo,
    AlertaMorosidad,
    RegistroAuditoria,
)

admin.site.site_header = "BuildCorp Enterprise — Control Central de Activos"
admin.site.site_title = "BuildCorp Portal Admin"
admin.site.index_title = "Panel Operativo de Maquinaria, Obras y Alquileres"


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'supervisor_nombre', 'supervisor_telefono', 'fecha_inicio', 'fecha_estimada_cierre', 'estado_obra')
    list_filter = ('activa', 'fecha_inicio')
    search_fields = ('codigo', 'nombre', 'supervisor_nombre', 'direccion')

    @admin.display(description="Operación")
    def estado_obra(self, obj):
        if obj.activa:
            return format_html('<span style="background:#111; color:#fff; padding:3px 8px; font-weight:700; border-radius:3px; font-size:11px;">ACTIVA</span>')
        return format_html('<span style="background:#eee; color:#666; padding:3px 8px; border:1px solid #ccc; border-radius:3px; font-size:11px;">CERRADA</span>')


@admin.register(Contratista)
class ContratistaAdmin(admin.ModelAdmin):
    list_display = ('rut', 'razon_social', 'representante_legal', 'telefono', 'estado_badge', 'fecha_bloqueo')
    list_filter = ('estado',)
    search_fields = ('rut', 'razon_social', 'representante_legal', 'email')
    actions = ['bloquear_seleccionados', 'desbloquear_seleccionados']

    @admin.display(description="Estado Operativo")
    def estado_badge(self, obj):
        if obj.estado == 'HABILITADO':
            return format_html('<span style="background:#000; color:#fff; padding:3px 8px; font-weight:700; border-radius:3px; font-size:11px;">HABILITADO</span>')
        elif obj.estado == 'BLOQUEADO_MOROSIDAD':
            return format_html('<span style="background:#fff; color:#000; border:2px solid #000; padding:2px 7px; font-weight:800; border-radius:3px; font-size:11px;">BLOQUEADO (MORA)</span>')
        return format_html('<span style="background:#e5e5e5; color:#333; padding:3px 8px; border-radius:3px; font-size:11px;">SUSPENDIDO</span>')

    @admin.action(description="Bloquear contratistas seleccionados por morosidad")
    def bloquear_seleccionados(self, request, queryset):
        for c in queryset:
            c.bloquear_por_morosidad(motivo="Bloqueo manual administrativo desde panel central.")
        self.message_user(request, f"{queryset.count()} contratista(s) bloqueado(s) exitosamente.")

    @admin.action(description="Desbloquear y habilitar contratistas seleccionados")
    def desbloquear_seleccionados(self, request, queryset):
        for c in queryset:
            c.desbloquear()
        self.message_user(request, f"{queryset.count()} contratista(s) habilitado(s) nuevamente.")


@admin.register(CategoriaHerramienta)
class CategoriaHerramientaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'frecuencia_mantenimiento_horas', 'dias_maximo_prestamo')
    search_fields = ('nombre',)


@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = ('foto_preview', 'codigo_inventario', 'nombre', 'categoria', 'marca', 'modelo', 'estado_badge', 'horas_uso_acumuladas', 'bodega_actual', 'obra_actual')
    list_filter = ('estado', 'categoria', 'bodega_actual', 'obra_actual')
    search_fields = ('codigo_inventario', 'nombre', 'marca', 'modelo', 'numero_serie')
    actions = ['enviar_a_mantenimiento', 'marcar_como_disponible']

    @admin.display(description="Foto")
    def foto_preview(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="height:34px; width:46px; object-fit:cover; border-radius:4px; border:1px solid #ddd;" />', obj.imagen.url)
        return format_html('<span style="color:#aaa; font-size:11px;">Sin foto</span>')

    @admin.display(description="Estado Activo")
    def estado_badge(self, obj):
        estilos = {
            'DISPONIBLE': 'background:#000; color:#fff;',
            'EN_USO': 'background:#fff; color:#000; border:1px solid #000;',
            'MANTENIMIENTO': 'background:#444; color:#fff;',
            'DADO_DE_BAJA': 'background:#eee; color:#888; text-decoration:line-through;',
        }
        style = estilos.get(obj.estado, 'background:#999; color:#fff;')
        return format_html(f'<span style="{style} padding:3px 8px; font-weight:700; border-radius:3px; font-size:11px;">{obj.get_estado_display()}</span>')

    @admin.action(description="Enviar activos seleccionados a Mantenimiento Técnico")
    def enviar_a_mantenimiento(self, request, queryset):
        for h in queryset:
            h.estado = 'MANTENIMIENTO'
            h.save(update_fields=['estado'])
            MantenimientoPreventivo.objects.create(
                codigo_orden=f"MTO-MANUAL-{h.codigo_inventario}-{timezone.now().strftime('%Y%m%d%H%M')}",
                herramienta=h,
                tipo='PREVENTIVO',
                horas_al_momento=h.horas_uso_acumuladas,
                fecha_programada=timezone.now().date(),
                descripcion_trabajo="Envío manual a mantenimiento preventivo desde Django Admin.",
                tecnico_responsable="Taller BuildCorp"
            )
        self.message_user(request, f"{queryset.count()} herramienta(s) enviada(s) a mantenimiento.")

    @admin.action(description="Marcar activos como Disponibles en Bodega")
    def marcar_como_disponible(self, request, queryset):
        queryset.update(estado='DISPONIBLE', obra_actual=None)
        self.message_user(request, f"{queryset.count()} herramienta(s) marcadas como disponibles.")


class ItemPrestamoInline(admin.TabularInline):
    model = ItemPrestamo
    extra = 1
    fields = ('herramienta', 'horas_uso_iniciales', 'horas_uso_finales', 'devuelto', 'observaciones_devolucion')


@admin.register(PrestamoHerramienta)
class PrestamoHerramientaAdmin(admin.ModelAdmin):
    list_display = ('codigo_prestamo', 'contratista', 'obra', 'fecha_prestamo', 'fecha_pactada_devolucion', 'estado_badge', 'preview_firma')
    list_filter = ('estado', 'obra', 'fecha_prestamo')
    search_fields = ('codigo_prestamo', 'contratista__razon_social', 'receptor_nombre', 'receptor_rut')
    inlines = [ItemPrestamoInline]
    actions = ['ejecutar_evaluacion_morosidad']

    @admin.display(description="Estado Préstamo")
    def estado_badge(self, obj):
        if obj.estado == 'ACTIVO':
            return format_html('<span style="background:#000; color:#fff; padding:3px 8px; font-weight:700; border-radius:3px; font-size:11px;">ACTIVO EN OBRA</span>')
        elif obj.estado == 'VENCIDO_MOROSO':
            return format_html('<span style="background:#fff; color:#000; border:2px solid #000; padding:2px 7px; font-weight:900; border-radius:3px; font-size:11px;">MOROSO / VENCIDO</span>')
        elif obj.estado == 'DEVUELTO':
            return format_html('<span style="background:#eee; color:#333; padding:3px 8px; border-radius:3px; font-size:11px;">DEVUELTO CONFORME</span>')
        return format_html('<span style="background:#666; color:#fff; padding:3px 8px; border-radius:3px; font-size:11px;">OBSERVADO</span>')

    @admin.display(description="Firma Despacho")
    def preview_firma(self, obj):
        if obj.firma_digital_entrega and len(obj.firma_digital_entrega) > 50:
            return format_html('<img src="{}" style="height:26px; max-width:80px; background:#fff; border:1px solid #ddd; padding:1px; border-radius:3px;" />', obj.firma_digital_entrega)
        return format_html('<span style="color:#aaa; font-size:11px;">Sin firma</span>')

    @admin.action(description="Evaluar morosidad y aplicar bloqueo automático")
    def ejecutar_evaluacion_morosidad(self, request, queryset):
        afectados = 0
        for prestamo in queryset:
            prestamo.evaluar_morosidad()
            if prestamo.estado == 'VENCIDO_MOROSO':
                afectados += 1
        self.message_user(request, f"Evaluación completada. {afectados} préstamo(s) detectado(s) en morosidad con bloqueo activado.")


@admin.register(DevolucionActa)
class DevolucionActaAdmin(admin.ModelAdmin):
    list_display = ('prestamo', 'fecha_devolucion', 'recibido_por', 'entregado_por_nombre', 'costo_penalizacion', 'preview_firma')
    search_fields = ('prestamo__codigo_prestamo', 'entregado_por_nombre', 'entregado_por_rut')

    @admin.display(description="Firma Recepción")
    def preview_firma(self, obj):
        if obj.firma_digital_devolucion and len(obj.firma_digital_devolucion) > 50:
            return format_html('<img src="{}" style="height:26px; max-width:80px; background:#fff; border:1px solid #ddd; padding:1px; border-radius:3px;" />', obj.firma_digital_devolucion)
        return format_html('<span style="color:#aaa; font-size:11px;">Sin firma</span>')


@admin.register(MantenimientoPreventivo)
class MantenimientoPreventivoAdmin(admin.ModelAdmin):
    list_display = ('codigo_orden', 'herramienta', 'tipo', 'estado_badge', 'fecha_programada', 'tecnico_responsable', 'costo')
    list_filter = ('tipo', 'estado', 'fecha_programada')
    search_fields = ('codigo_orden', 'herramienta__nombre', 'herramienta__codigo_inventario', 'tecnico_responsable')
    actions = ['marcar_completado']

    @admin.display(description="Estado Trabajo")
    def estado_badge(self, obj):
        estilos = {
            'PROGRAMADO': 'background:#fff; color:#000; border:1px solid #000;',
            'EN_PROCESO': 'background:#222; color:#fff;',
            'COMPLETADO': 'background:#000; color:#fff; font-weight:bold;',
            'CANCELADO': 'background:#eee; color:#777; text-decoration:line-through;',
        }
        style = estilos.get(obj.estado, 'background:#999; color:#fff;')
        return format_html(f'<span style="{style} padding:3px 8px; border-radius:3px; font-size:11px;">{obj.get_estado_display()}</span>')

    @admin.action(description="Completar mantenimiento y reactivar herramienta a Disponible")
    def marcar_completado(self, request, queryset):
        for mto in queryset:
            mto.finalizar_mantenimiento(costo_final=mto.costo, nuevas_horas_proximo=100)
        self.message_user(request, f"{queryset.count()} orden(es) de mantenimiento completada(s) y herramientas reactivadas.")


@admin.register(AlertaMorosidad)
class AlertaMorosidadAdmin(admin.ModelAdmin):
    list_display = ('prestamo', 'contratista', 'dias_retraso', 'gravedad', 'contratista_bloqueado', 'resuelta', 'fecha_generacion')
    list_filter = ('gravedad', 'resuelta', 'contratista_bloqueado')
    search_fields = ('contratista__razon_social', 'prestamo__codigo_prestamo')
    actions = ['resolver_alertas_seleccionadas']

    @admin.action(description="Resolver alertas y regularizar contratistas")
    def resolver_alertas_seleccionadas(self, request, queryset):
        for a in queryset:
            a.resolver()
        self.message_user(request, f"{queryset.count()} alerta(s) resuelta(s).")


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'usuario_nombre', 'modulo', 'accion', 'identificador_objeto', 'ip_origen', 'hash_preview')
    list_filter = ('modulo', 'accion', 'fecha_hora')
    search_fields = ('usuario_nombre', 'identificador_objeto', 'descripcion_detalle', 'hash_integridad')
    readonly_fields = ('usuario', 'usuario_nombre', 'accion', 'modulo', 'identificador_objeto', 'descripcion_detalle', 'ip_origen', 'fecha_hora', 'hash_integridad')

    @admin.display(description="Hash SHA-256 (ISO)")
    def hash_preview(self, obj):
        return format_html(f'<code style="font-size:10px;">{obj.hash_integridad[:16]}...</code>')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
