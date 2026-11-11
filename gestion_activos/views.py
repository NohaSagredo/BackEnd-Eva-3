import csv
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse

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
from .security import (
    validar_y_sanitizar_imagen,
    esta_bloqueado_por_fuerza_bruta,
    registrar_intento_fallido_login,
    resetear_intentos_login,
)


# ==============================================================================
# MOTOR DE AUDITORÍA Y TRAZABILIDAD ISO 27001 / ISO 9001
# ==============================================================================

def registrar_auditoria_iso(request, accion, modulo, identificador, detalle):
    ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR') or '127.0.0.1'
    if ',' in ip:
        ip = ip.split(',')[0].strip()
        
    usuario = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    usuario_nombre = usuario.username if usuario else 'SISTEMA_AUTOMATICO'

    return RegistroAuditoria.objects.create(
        usuario=usuario,
        usuario_nombre=usuario_nombre,
        accion=accion,
        modulo=modulo,
        identificador_objeto=identificador,
        descripcion_detalle=detalle,
        ip_origen=ip,
        fecha_hora=timezone.now()
    )


# ==============================================================================
# MANEJADORES DE ERROR PERSONALIZADOS (404, 500, 403, 400)
# ==============================================================================

def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)


def custom_500_view(request):
    return render(request, '500.html', status=500)


def custom_403_view(request, exception=None):
    return render(request, '403.html', status=403)


def custom_400_view(request, exception=None):
    return render(request, '400.html', status=400)


# ==============================================================================
# AUTENTICACIÓN
# ==============================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if esta_bloqueado_por_fuerza_bruta(request, username):
            messages.error(
                request,
                "Acceso bloqueado temporalmente debido a múltiples intentos fallidos de autenticación. "
                "Por motivos de seguridad, debe esperar 5 minutos antes de volver a intentarlo."
            )
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            resetear_intentos_login(request, username)
            login(request, user)
            registrar_auditoria_iso(request, 'AUTENTICACION', 'SEGURIDAD', user.username, "Inicio de sesión exitoso en plataforma")
            messages.success(request, f"Sesión iniciada correctamente. Bienvenido, {user.username}.")
            
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('dashboard')
        else:
            intentos = registrar_intento_fallido_login(request, username)
            if intentos >= 5:
                registrar_auditoria_iso(
                    request,
                    'BLOQUEO_SEGURIDAD',
                    'SEGURIDAD',
                    username or 'DESCONOCIDO',
                    f"Bloqueo de seguridad activado por fuerza bruta: {intentos} intentos fallidos acumulados"
                )
                messages.error(
                    request,
                    "Ha superado el límite de 5 intentos fallidos. Su acceso ha sido bloqueado preventivamente por 5 minutos."
                )
            else:
                registrar_auditoria_iso(
                    request,
                    'AUTENTICACION',
                    'SEGURIDAD',
                    username or 'DESCONOCIDO',
                    f"Intento fallido de autenticación ({intentos}/5)"
                )
                messages.error(
                    request,
                    f"Credenciales incorrectas. Intento {intentos} de 5 antes del bloqueo preventivo."
                )

    return render(request, 'login.html')


def logout_view(request):
    if request.user.is_authenticated:
        registrar_auditoria_iso(request, 'AUTENTICACION', 'SEGURIDAD', request.user.username, "Cierre voluntario de sesión")
    logout(request)
    messages.info(request, "Sesión cerrada de forma segura.")
    return redirect('login')


# ==============================================================================
# TABLERO DE CONTROL Y MONITOREO
# ==============================================================================

@login_required
def dashboard_view(request):
    prestamos_activos = PrestamoHerramienta.objects.filter(estado='ACTIVO')
    for p in prestamos_activos:
        estado_previo = p.estado
        p.evaluar_morosidad()
        if p.estado == 'VENCIDO_MOROSO' and estado_previo != 'VENCIDO_MOROSO':
            registrar_auditoria_iso(
                request,
                'BLOQUEO_MOROSIDAD',
                'CONTRATISTAS',
                p.contratista.rut,
                f"Bloqueo automático por morosidad crítica detectada en préstamo {p.codigo_prestamo}"
            )

    total_activos = Herramienta.objects.count()
    disponibles = Herramienta.objects.filter(estado='DISPONIBLE').count()
    en_uso = Herramienta.objects.filter(estado='EN_USO').count()
    mantenimiento = Herramienta.objects.filter(estado='MANTENIMIENTO').count()
    
    prestamos_en_curso = PrestamoHerramienta.objects.filter(estado='ACTIVO').count()
    alertas_morosidad = AlertaMorosidad.objects.filter(resuelta=False).select_related('prestamo', 'contratista')
    contratistas_bloqueados = Contratista.objects.filter(estado='BLOQUEADO_MOROSIDAD').count()

    ultimos_prestamos = PrestamoHerramienta.objects.select_related('contratista', 'obra', 'responsable_despacho').order_by('-fecha_prestamo')[:6]
    proximos_mtos = MantenimientoPreventivo.objects.filter(estado__in=['PROGRAMADO', 'EN_PROCESO']).select_related('herramienta')[:5]

    context = {
        'total_activos': total_activos,
        'disponibles': disponibles,
        'en_uso': en_uso,
        'mantenimiento': mantenimiento,
        'prestamos_en_curso': prestamos_en_curso,
        'alertas_morosidad': alertas_morosidad,
        'contratistas_bloqueados': contratistas_bloqueados,
        'ultimos_prestamos': ultimos_prestamos,
        'proximos_mtos': proximos_mtos,
        'now': timezone.now(),
    }
    return render(request, 'dashboard.html', context)


# ==============================================================================
# CRUD HERRAMIENTAS / ACTIVOS
# ==============================================================================

@login_required
def herramientas_list_view(request):
    estado = request.GET.get('estado', '')
    query = request.GET.get('q', '').strip()

    herramientas = Herramienta.objects.select_related('categoria', 'obra_actual').all()

    if estado:
        herramientas = herramientas.filter(estado=estado)
    if query:
        herramientas = herramientas.filter(
            Q(codigo_inventario__icontains=query) |
            Q(nombre__icontains=query) |
            Q(marca__icontains=query) |
            Q(modelo__icontains=query)
        )

    context = {
        'herramientas': herramientas,
        'estado_filtro': estado,
        'query': query,
        'total': herramientas.count(),
    }
    return render(request, 'herramientas.html', context)


@login_required
def herramientas_crear_view(request):
    categorias = CategoriaHerramienta.objects.all()

    if request.method == 'POST':
        codigo = request.POST.get('codigo_inventario', '').strip().upper()
        if Herramienta.objects.filter(codigo_inventario=codigo).exists():
            messages.error(request, f"El código '{codigo}' ya existe en el inventario. Por favor escribe otro.")
            return render(request, 'herramienta_form.html', {'categorias': categorias, 'editando': False})

        categoria_id = request.POST.get('categoria')
        categoria = get_object_or_404(CategoriaHerramienta, pk=categoria_id)

        try:
            horas_acumuladas = max(0, int(request.POST.get('horas_uso_acumuladas', 0) or 0))
        except (ValueError, TypeError):
            horas_acumuladas = 0

        try:
            horas_proximo = max(1, int(request.POST.get('horas_proximo_mantenimiento', 100) or 100))
        except (ValueError, TypeError):
            horas_proximo = 100

        try:
            valor_reposicion = max(0.0, float(request.POST.get('valor_reposicion', 0) or 0))
        except (ValueError, TypeError):
            valor_reposicion = 0.0

        herramienta = Herramienta(
            codigo_inventario=codigo,
            categoria=categoria,
            nombre=request.POST.get('nombre', '').strip(),
            marca=request.POST.get('marca', '').strip(),
            modelo=request.POST.get('modelo', '').strip(),
            numero_serie=request.POST.get('numero_serie', '').strip(),
            estado=request.POST.get('estado', 'DISPONIBLE'),
            horas_uso_acumuladas=horas_acumuladas,
            horas_proximo_mantenimiento=horas_proximo,
            bodega_actual=request.POST.get('bodega_actual', 'Bodega Central').strip(),
            valor_reposicion=valor_reposicion,
            imagen_url=request.POST.get('imagen_url', '').strip(),
        )

        if 'imagen' in request.FILES:
            try:
                herramienta.imagen = validar_y_sanitizar_imagen(request.FILES['imagen'])
            except ValidationError as err:
                messages.error(request, f"Archivo de imagen rechazado por seguridad: {err.message}")
                return render(request, 'herramienta_form.html', {'categorias': categorias, 'editando': False})
        
        herramienta.save()
        registrar_auditoria_iso(
            request, 'CREACION', 'HERRAMIENTAS', herramienta.codigo_inventario,
            f"Alta de activo '{herramienta.nombre}', marca {herramienta.marca}, reposición ${herramienta.valor_reposicion:,.0f} CLP"
        )
        messages.success(request, f"Herramienta '{herramienta.nombre}' guardada con éxito.")
        return redirect('herramientas')

    return render(request, 'herramienta_form.html', {'categorias': categorias, 'editando': False})


@login_required
def herramientas_editar_view(request, herramienta_id):
    herramienta = get_object_or_404(Herramienta, pk=herramienta_id)
    categorias = CategoriaHerramienta.objects.all()

    if request.method == 'POST':
        categoria_id = request.POST.get('categoria')
        herramienta.categoria = get_object_or_404(CategoriaHerramienta, pk=categoria_id)
        herramienta.nombre = request.POST.get('nombre', '').strip()
        herramienta.marca = request.POST.get('marca', '').strip()
        herramienta.modelo = request.POST.get('modelo', '').strip()
        herramienta.numero_serie = request.POST.get('numero_serie', '').strip()
        herramienta.estado = request.POST.get('estado', herramienta.estado)

        try:
            herramienta.horas_uso_acumuladas = max(0, int(request.POST.get('horas_uso_acumuladas', herramienta.horas_uso_acumuladas) or 0))
        except (ValueError, TypeError):
            pass

        try:
            herramienta.horas_proximo_mantenimiento = max(1, int(request.POST.get('horas_proximo_mantenimiento', herramienta.horas_proximo_mantenimiento) or 100))
        except (ValueError, TypeError):
            pass

        herramienta.bodega_actual = request.POST.get('bodega_actual', herramienta.bodega_actual).strip()

        try:
            herramienta.valor_reposicion = max(0.0, float(request.POST.get('valor_reposicion', herramienta.valor_reposicion) or 0))
        except (ValueError, TypeError):
            pass
        
        img_url = request.POST.get('imagen_url', '').strip()
        if img_url:
            herramienta.imagen_url = img_url

        if 'imagen' in request.FILES:
            try:
                herramienta.imagen = validar_y_sanitizar_imagen(request.FILES['imagen'])
            except ValidationError as err:
                messages.error(request, f"Archivo de imagen rechazado por seguridad: {err.message}")
                return render(request, 'herramienta_form.html', {'herramienta': herramienta, 'categorias': categorias, 'editando': True})

        herramienta.save()
        registrar_auditoria_iso(
            request, 'MODIFICACION', 'HERRAMIENTAS', herramienta.codigo_inventario,
            f"Modificación de ficha técnica y parámetros de '{herramienta.nombre}'"
        )
        messages.success(request, f"Herramienta '{herramienta.codigo_inventario}' actualizada con éxito.")
        return redirect('herramientas')

    return render(request, 'herramienta_form.html', {'herramienta': herramienta, 'categorias': categorias, 'editando': True})


@login_required
@require_POST
def herramientas_eliminar_view(request, herramienta_id):
    herramienta = get_object_or_404(Herramienta, pk=herramienta_id)
    
    prestamos_activos = ItemPrestamo.objects.filter(herramienta=herramienta, prestamo__estado='ACTIVO')
    if prestamos_activos.exists():
        messages.error(request, f"No se puede eliminar '{herramienta.codigo_inventario}' porque está prestada en una obra en este momento.")
        return redirect('herramientas')

    codigo = herramienta.codigo_inventario
    nombre = herramienta.nombre
    herramienta.delete()
    registrar_auditoria_iso(request, 'ELIMINACION', 'HERRAMIENTAS', codigo, f"Baja definitiva y retiro de inventario del activo '{nombre}'")
    messages.warning(request, f"Herramienta '{codigo}' eliminada.")
    return redirect('herramientas')


# ==============================================================================
# CRUD CONTRATISTAS
# ==============================================================================

@login_required
def contratistas_list_view(request):
    if request.method == 'POST':
        cid = request.POST.get('contratista_id')
        accion = request.POST.get('accion')
        contratista = get_object_or_404(Contratista, pk=cid)
        if accion == 'bloquear':
            motivo = request.POST.get('motivo', 'Bloqueo administrativo directo.')
            contratista.bloquear_por_morosidad(motivo)
            registrar_auditoria_iso(request, 'BLOQUEO_MOROSIDAD', 'CONTRATISTAS', contratista.rut, f"Bloqueo disciplinario manual: {motivo}")
            messages.warning(request, f"El contratista '{contratista.razon_social}' fue bloqueado.")
        elif accion == 'desbloquear':
            contratista.desbloquear()
            AlertaMorosidad.objects.filter(contratista=contratista, resuelta=False).update(
                resuelta=True,
                fecha_resolucion=timezone.now()
            )
            registrar_auditoria_iso(request, 'DESBLOQUEO_CONTRATISTA', 'CONTRATISTAS', contratista.rut, "Levantamiento de bloqueo y regularización operativa")
            messages.success(request, f"El contratista '{contratista.razon_social}' fue habilitado.")
        return redirect('contratistas')

    contratistas = Contratista.objects.all().order_by('razon_social')
    return render(request, 'contratistas.html', {'contratistas': contratistas})


@login_required
def contratistas_crear_view(request):
    if request.method == 'POST':
        rut = request.POST.get('rut', '').strip()
        if Contratista.objects.filter(rut=rut).exists():
            messages.error(request, f"El RUT '{rut}' ya se encuentra registrado.")
            return render(request, 'contratista_form.html', {'editando': False})

        c = Contratista.objects.create(
            rut=rut,
            razon_social=request.POST.get('razon_social', '').strip(),
            representante_legal=request.POST.get('representante_legal', '').strip(),
            email=request.POST.get('email', '').strip(),
            telefono=request.POST.get('telefono', '').strip(),
            estado=request.POST.get('estado', 'HABILITADO'),
            motivo_bloqueo=request.POST.get('motivo_bloqueo', '').strip()
        )
        registrar_auditoria_iso(request, 'CREACION', 'CONTRATISTAS', c.rut, f"Alta de empresa subcontratista '{c.razon_social}'")
        messages.success(request, f"Contratista '{c.razon_social}' guardado con éxito.")
        return redirect('contratistas')

    return render(request, 'contratista_form.html', {'editando': False})


@login_required
def contratistas_editar_view(request, contratista_id):
    contratista = get_object_or_404(Contratista, pk=contratista_id)

    if request.method == 'POST':
        contratista.rut = request.POST.get('rut', '').strip()
        contratista.razon_social = request.POST.get('razon_social', '').strip()
        contratista.representante_legal = request.POST.get('representante_legal', '').strip()
        contratista.email = request.POST.get('email', '').strip()
        contratista.telefono = request.POST.get('telefono', '').strip()
        contratista.estado = request.POST.get('estado', contratista.estado)
        contratista.motivo_bloqueo = request.POST.get('motivo_bloqueo', '').strip()
        contratista.save()

        registrar_auditoria_iso(request, 'MODIFICACION', 'CONTRATISTAS', contratista.rut, f"Actualización de datos comerciales de '{contratista.razon_social}'")
        messages.success(request, f"Contratista '{contratista.razon_social}' actualizado con éxito.")
        return redirect('contratistas')

    return render(request, 'contratista_form.html', {'contratista': contratista, 'editando': True})


@login_required
@require_POST
def contratistas_eliminar_view(request, contratista_id):
    contratista = get_object_or_404(Contratista, pk=contratista_id)
    
    if contratista.prestamos.filter(estado__in=['ACTIVO', 'VENCIDO_MOROSO']).exists():
        messages.error(request, f"No se puede eliminar a '{contratista.razon_social}' porque tiene herramientas prestadas o atrasadas pendientes.")
        return redirect('contratistas')

    rut = contratista.rut
    nombre = contratista.razon_social
    contratista.delete()
    registrar_auditoria_iso(request, 'ELIMINACION', 'CONTRATISTAS', rut, f"Eliminación de contratista '{nombre}'")
    messages.warning(request, f"Contratista '{nombre}' eliminado.")
    return redirect('contratistas')


# ==============================================================================
# CRUD OBRAS / FAENAS
# ==============================================================================

@login_required
def obras_list_view(request):
    obras = Obra.objects.all().order_by('-activa', 'nombre')
    return render(request, 'obras.html', {'obras': obras})


@login_required
def obras_crear_view(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()
        if Obra.objects.filter(codigo=codigo).exists():
            messages.error(request, f"El código de obra '{codigo}' ya existe.")
            return render(request, 'obra_form.html', {'editando': False})

        obra = Obra.objects.create(
            codigo=codigo,
            nombre=request.POST.get('nombre', '').strip(),
            direccion=request.POST.get('direccion', '').strip(),
            supervisor_nombre=request.POST.get('supervisor_nombre', '').strip(),
            supervisor_telefono=request.POST.get('supervisor_telefono', '').strip(),
            fecha_inicio=request.POST.get('fecha_inicio'),
            fecha_estimada_cierre=request.POST.get('fecha_estimada_cierre'),
            activa=(request.POST.get('activa') == 'True')
        )
        registrar_auditoria_iso(request, 'CREACION', 'OBRAS', obra.codigo, f"Apertura de centro de faena '{obra.nombre}'")
        messages.success(request, f"Obra '{obra.nombre}' guardada con éxito.")
        return redirect('obras')

    return render(request, 'obra_form.html', {'editando': False})


@login_required
def obras_editar_view(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)

    if request.method == 'POST':
        obra.nombre = request.POST.get('nombre', '').strip()
        obra.direccion = request.POST.get('direccion', '').strip()
        obra.supervisor_nombre = request.POST.get('supervisor_nombre', '').strip()
        obra.supervisor_telefono = request.POST.get('supervisor_telefono', '').strip()
        obra.fecha_inicio = request.POST.get('fecha_inicio')
        obra.fecha_estimada_cierre = request.POST.get('fecha_estimada_cierre')
        obra.activa = (request.POST.get('activa') == 'True')
        obra.save()

        registrar_auditoria_iso(request, 'MODIFICACION', 'OBRAS', obra.codigo, f"Actualización de parámetros operativos de obra '{obra.nombre}'")
        messages.success(request, f"Obra '{obra.codigo}' actualizada con éxito.")
        return redirect('obras')

    return render(request, 'obra_form.html', {'obra': obra, 'editando': True})


@login_required
@require_POST
def obras_eliminar_view(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    if obra.prestamos.filter(estado='ACTIVO').exists():
        messages.error(request, f"No se puede eliminar la obra '{obra.nombre}' porque tiene herramientas en uso.")
        return redirect('obras')

    codigo = obra.codigo
    nombre = obra.nombre
    obra.delete()
    registrar_auditoria_iso(request, 'ELIMINACION', 'OBRAS', codigo, f"Cierre definitivo de obra '{nombre}'")
    messages.warning(request, f"Obra '{codigo}' eliminada.")
    return redirect('obras')


# ==============================================================================
# PRÉSTAMOS, FIRMA DIGITAL Y DEVOLUCIÓN
# ==============================================================================

@login_required
def prestamos_list_view(request):
    # Evaluar morosidad en tiempo real para mantener estados y alertas al día
    for p in PrestamoHerramienta.objects.filter(estado='ACTIVO'):
        p.evaluar_morosidad()

    estado = request.GET.get('estado', '')
    query = request.GET.get('q', '').strip()

    prestamos = PrestamoHerramienta.objects.select_related('contratista', 'obra', 'responsable_despacho').prefetch_related('items__herramienta').all()

    if estado:
        prestamos = prestamos.filter(estado=estado)
    if query:
        prestamos = prestamos.filter(
            Q(codigo_prestamo__icontains=query) |
            Q(contratista__razon_social__icontains=query) |
            Q(obra__nombre__icontains=query) |
            Q(receptor_nombre__icontains=query)
        )

    context = {
        'prestamos': prestamos,
        'estado_filtro': estado,
        'query': query,
    }
    return render(request, 'prestamos.html', context)


@login_required
def nuevo_prestamo_view(request):
    obras = Obra.objects.filter(activa=True)
    contratistas = Contratista.objects.all().order_by('razon_social')
    herramientas_disponibles = Herramienta.objects.filter(estado='DISPONIBLE').select_related('categoria')

    if request.method == 'POST':
        contratista_id = request.POST.get('contratista')
        obra_id = request.POST.get('obra')
        fecha_devolucion = request.POST.get('fecha_pactada_devolucion')
        receptor_nombre = request.POST.get('receptor_nombre', '').strip()
        receptor_rut = request.POST.get('receptor_rut', '').strip()
        firma_digital = request.POST.get('firma_digital_entrega', '').strip()
        observaciones = request.POST.get('observaciones_entrega', '').strip()
        herramientas_ids = request.POST.getlist('herramientas')

        contratista = get_object_or_404(Contratista, pk=contratista_id)

        if contratista.estado == 'BLOQUEADO_MOROSIDAD':
            registrar_auditoria_iso(
                request, 'BLOQUEO_MOROSIDAD', 'PRESTAMOS', contratista.rut,
                f"Intento frustrado de despacho: contratista '{contratista.razon_social}' está bloqueado por morosidad"
            )
            messages.error(
                request,
                f"No se puede prestar: El contratista '{contratista.razon_social}' tiene herramientas atrasadas. "
                f"Debe devolverlas antes de recibir nuevas."
            )
            return redirect('nuevo_prestamo')

        if not herramientas_ids:
            messages.error(request, "Debes seleccionar al menos una herramienta para prestar.")
            return redirect('nuevo_prestamo')

        if not firma_digital:
            messages.error(request, "La firma en pantalla es obligatoria para registrar la entrega.")
            return redirect('nuevo_prestamo')

        obra = get_object_or_404(Obra, pk=obra_id)
        folio = f"PREST-{timezone.now().strftime('%Y%m%d')}-{PrestamoHerramienta.objects.count() + 1:04d}"

        with transaction.atomic():
            prestamo = PrestamoHerramienta.objects.create(
                codigo_prestamo=folio,
                contratista=contratista,
                obra=obra,
                fecha_pactada_devolucion=fecha_devolucion,
                responsable_despacho=request.user,
                receptor_nombre=receptor_nombre,
                receptor_rut=receptor_rut,
                firma_digital_entrega=firma_digital,
                observaciones_entrega=observaciones,
                estado='ACTIVO'
            )

            nombres_items = []
            for hid in herramientas_ids:
                herramienta = Herramienta.objects.select_for_update().get(pk=hid)
                if herramienta.estado != 'DISPONIBLE':
                    raise ValueError(f"La herramienta {herramienta.codigo_inventario} ya no está disponible.")
                
                ItemPrestamo.objects.create(
                    prestamo=prestamo,
                    herramienta=herramienta,
                    horas_uso_iniciales=herramienta.horas_uso_acumuladas,
                    devuelto=False
                )
                herramienta.estado = 'EN_USO'
                herramienta.obra_actual = obra
                herramienta.bodega_actual = f"En obra: {obra.nombre}"
                herramienta.save(update_fields=['estado', 'obra_actual', 'bodega_actual'])
                nombres_items.append(herramienta.codigo_inventario)

        registrar_auditoria_iso(
            request, 'DESPACHO_PRESTAMO', 'PRESTAMOS', prestamo.codigo_prestamo,
            f"Emisión de guía de despacho a contratista '{contratista.razon_social}' para obra '{obra.nombre}'. "
            f"Activos: {', '.join(nombres_items)}. Firmado por receptor: '{receptor_nombre}' (RUT: {receptor_rut})"
        )
        messages.success(request, f"Préstamo {prestamo.codigo_prestamo} registrado con éxito.")
        return redirect('prestamos')

    context = {
        'obras': obras,
        'contratistas': contratistas,
        'herramientas_disponibles': herramientas_disponibles,
        'hoy': timezone.now().date(),
    }
    return render(request, 'nuevo_prestamo.html', context)


@login_required
def devolucion_prestamo_view(request, prestamo_id):
    prestamo = get_object_or_404(
        PrestamoHerramienta.objects.select_related('contratista', 'obra').prefetch_related('items__herramienta'),
        pk=prestamo_id
    )

    if prestamo.estado == 'DEVUELTO':
        messages.info(request, f"El préstamo {prestamo.codigo_prestamo} ya fue devuelto.")
        return redirect('prestamos')

    if request.method == 'POST':
        entregado_por_nombre = request.POST.get('entregado_por_nombre', '').strip()
        entregado_por_rut = request.POST.get('entregado_por_rut', '').strip()
        firma_digital_recepcion = request.POST.get('firma_digital_recepcion', '').strip()
        observaciones = request.POST.get('observaciones_recepcion', '').strip()
        costo_penalizacion = request.POST.get('costo_penalizacion', '0')

        if not firma_digital_recepcion:
            messages.error(request, "Debes ingresar la firma en pantalla para confirmar la devolución.")
            return redirect('devolucion_prestamo', prestamo_id=prestamo.id)

        try:
            penalizacion = float(costo_penalizacion)
        except ValueError:
            penalizacion = 0.0

        with transaction.atomic():
            DevolucionActa.objects.create(
                prestamo=prestamo,
                recibido_por=request.user,
                entregado_por_nombre=entregado_por_nombre,
                entregado_por_rut=entregado_por_rut,
                firma_digital_devolucion=firma_digital_recepcion,
                costo_penalizacion=penalizacion,
                observaciones_recepcion=observaciones
            )

            for item in prestamo.items.select_related('herramienta'):
                horas_finales_str = request.POST.get(f'horas_final_{item.id}', str(item.herramienta.horas_uso_acumuladas))
                try:
                    horas_finales = int(horas_finales_str)
                except ValueError:
                    horas_finales = item.herramienta.horas_uso_acumuladas

                item.horas_uso_finales = horas_finales
                item.devuelto = True
                item.observaciones_devolucion = request.POST.get(f'obs_item_{item.id}', '')
                item.save()

                herramienta = item.herramienta
                herramienta.horas_uso_acumuladas = horas_finales
                herramienta.obra_actual = None
                herramienta.bodega_actual = "Bodega Central"

                if herramienta.horas_uso_acumuladas >= herramienta.horas_proximo_mantenimiento:
                    herramienta.estado = 'MANTENIMIENTO'
                    mto = MantenimientoPreventivo.objects.create(
                        codigo_orden=f"MTO-AUTO-{herramienta.codigo_inventario}-{timezone.now().strftime('%Y%m%d%H%M')}",
                        herramienta=herramienta,
                        tipo='PREVENTIVO',
                        horas_al_momento=herramienta.horas_uso_acumuladas,
                        fecha_programada=timezone.now().date(),
                        descripcion_trabajo=f"Mantenimiento programado automático por superar umbral ({herramienta.horas_uso_acumuladas} hrs).",
                        tecnico_responsable="Taller Mecánico Central BuildCorp"
                    )
                    registrar_auditoria_iso(
                        request, 'ORDEN_MANTENIMIENTO', 'MANTENIMIENTO', mto.codigo_orden,
                        f"Disparo automático de mantenimiento preventivo para '{herramienta.codigo_inventario}' al alcanzar {herramienta.horas_uso_acumuladas} hrs"
                    )
                else:
                    herramienta.estado = 'DISPONIBLE'
                
                herramienta.save(update_fields=['horas_uso_acumuladas', 'estado', 'obra_actual', 'bodega_actual'])

            prestamo.estado = 'DEVUELTO'
            prestamo.fecha_real_devolucion = timezone.now()
            prestamo.save(update_fields=['estado', 'fecha_real_devolucion'])

            alertas = AlertaMorosidad.objects.filter(prestamo=prestamo, resuelta=False)
            for a in alertas:
                a.resolver()

        registrar_auditoria_iso(
            request, 'RECEPCION_DEVOLUCION', 'PRESTAMOS', prestamo.codigo_prestamo,
            f"Devolución y cierre de préstamo con firma digital. Entregado por '{entregado_por_nombre}' (RUT: {entregado_por_rut}). "
            f"Penalización aplicada: ${penalizacion:,.0f} CLP"
        )
        messages.success(request, f"Devolución del préstamo {prestamo.codigo_prestamo} registrada con éxito.")
        return redirect('prestamos')

    context = {
        'prestamo': prestamo,
    }
    return render(request, 'devolucion_prestamo.html', context)


@login_required
def imprimir_prestamo_view(request, prestamo_id):
    prestamo = get_object_or_404(
        PrestamoHerramienta.objects.select_related('contratista', 'obra', 'responsable_despacho').prefetch_related('items__herramienta__categoria'),
        pk=prestamo_id
    )
    return render(request, 'imprimir_prestamo.html', {'prestamo': prestamo})


# ==============================================================================
# CRUD MANTENIMIENTOS
# ==============================================================================

@login_required
def mantenimientos_list_view(request):
    if request.method == 'POST':
        mid = request.POST.get('mantenimiento_id')
        costo_str = request.POST.get('costo', '0')
        mto = get_object_or_404(MantenimientoPreventivo, pk=mid)
        try:
            costo = float(costo_str)
        except ValueError:
            costo = 0.0
        mto.finalizar_mantenimiento(costo_final=costo, nuevas_horas_proximo=100)
        registrar_auditoria_iso(
            request, 'CIERRE_MANTENIMIENTO', 'MANTENIMIENTO', mto.codigo_orden,
            f"Cierre de mantenimiento para activo '{mto.herramienta.codigo_inventario}' con costo ${costo:,.0f} CLP. Herramienta reactivada a DISPONIBLE."
        )
        messages.success(request, f"Mantenimiento terminado. La herramienta {mto.herramienta.codigo_inventario} vuelve a estar disponible.")
        return redirect('mantenimientos')

    mantenimientos = MantenimientoPreventivo.objects.select_related('herramienta').order_by('-fecha_programada')
    return render(request, 'mantenimientos.html', {'mantenimientos': mantenimientos})


@login_required
def mantenimientos_crear_view(request):
    herramientas = Herramienta.objects.all().order_by('codigo_inventario')

    if request.method == 'POST':
        herramienta_id = request.POST.get('herramienta')
        herramienta = get_object_or_404(Herramienta, pk=herramienta_id)
        
        folio = f"MTO-MANUAL-{herramienta.codigo_inventario}-{timezone.now().strftime('%Y%m%d%H%M')}"
        costo_estimado = float(request.POST.get('costo_estimado', 0) or 0)

        with transaction.atomic():
            mto = MantenimientoPreventivo.objects.create(
                codigo_orden=folio,
                herramienta=herramienta,
                tipo=request.POST.get('tipo', 'PREVENTIVO'),
                horas_al_momento=herramienta.horas_uso_acumuladas,
                fecha_programada=request.POST.get('fecha_programada'),
                tecnico_responsable=request.POST.get('tecnico_responsable', '').strip(),
                costo=costo_estimado,
                descripcion_trabajo=request.POST.get('descripcion_trabajo', '').strip(),
                repuestos_utilizados=request.POST.get('repuestos_utilizados', '').strip(),
                estado='EN_PROCESO'
            )
            herramienta.estado = 'MANTENIMIENTO'
            herramienta.save(update_fields=['estado'])

        registrar_auditoria_iso(
            request, 'ORDEN_MANTENIMIENTO', 'MANTENIMIENTO', mto.codigo_orden,
            f"Apertura manual de orden {mto.tipo} para {herramienta.codigo_inventario} asignada a '{mto.tecnico_responsable}'"
        )
        messages.success(request, f"Orden de mantenimiento {mto.codigo_orden} creada. La herramienta pasa a revisión.")
        return redirect('mantenimientos')

    context = {
        'herramientas': herramientas,
        'hoy': timezone.now().date(),
    }
    return render(request, 'mantenimiento_form.html', context)


@login_required
@require_POST
def mantenimientos_eliminar_view(request, mantenimiento_id):
    mto = get_object_or_404(MantenimientoPreventivo, pk=mantenimiento_id)
    herramienta = mto.herramienta

    with transaction.atomic():
        mto.estado = 'CANCELADO'
        mto.save(update_fields=['estado'])
        if not MantenimientoPreventivo.objects.filter(herramienta=herramienta, estado__in=['PROGRAMADO', 'EN_PROCESO']).exclude(pk=mto.pk).exists():
            herramienta.estado = 'DISPONIBLE'
            herramienta.save(update_fields=['estado'])

    registrar_auditoria_iso(request, 'ELIMINACION', 'MANTENIMIENTO', mto.codigo_orden, f"Cancelación de orden de mantenimiento para {herramienta.codigo_inventario}")
    messages.info(request, f"Orden de mantenimiento {mto.codigo_orden} cancelada.")
    return redirect('mantenimientos')


# ==============================================================================
# AUDITORÍA Y TRAZABILIDAD ISO (VISTA & EXPORTACIÓN)
# ==============================================================================

@login_required
def auditoria_list_view(request):
    modulo = request.GET.get('modulo', '')
    query = request.GET.get('q', '').strip()

    registros = RegistroAuditoria.objects.select_related('usuario').all()

    if modulo:
        registros = registros.filter(modulo=modulo)
    if query:
        registros = registros.filter(
            Q(usuario_nombre__icontains=query) |
            Q(identificador_objeto__icontains=query) |
            Q(descripcion_detalle__icontains=query) |
            Q(hash_integridad__icontains=query)
        )

    context = {
        'registros': registros[:100],  # Mostrar los 100 más recientes
        'modulo_filtro': modulo,
        'query': query,
        'total': registros.count(),
    }
    return render(request, 'auditoria.html', context)


@login_required
def exportar_auditoria_csv_view(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"bitacora_auditoria_iso_buildcorp_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        'ID EVENTO', 'FECHA Y HORA (CLT)', 'USUARIO OPERADOR', 'MÓDULO AFECTADO',
        'TIPO DE ACCIÓN', 'FOLIO / OBJETO', 'DETALLE PERICIAL DE LA OPERACIÓN',
        'DIRECCIÓN IP ORIGEN', 'HASH CRIPTOGRÁFICO SHA-256 (INMUTABILIDAD ISO)'
    ])

    for reg in RegistroAuditoria.objects.all():
        writer.writerow([
            reg.id,
            reg.fecha_hora.strftime('%d/%m/%Y %H:%M:%S'),
            reg.usuario_nombre,
            reg.get_modulo_display(),
            reg.get_accion_display(),
            reg.identificador_objeto,
            reg.descripcion_detalle,
            reg.ip_origen or '127.0.0.1',
            reg.hash_integridad
        ])

    return response


# ==============================================================================
# EXPORTACIONES CSV ESTANDARIZADAS (UTF-8 BOM + Delimitador ';')
# ==============================================================================

@login_required
def exportar_herramientas_csv_view(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"catalogo_herramientas_buildcorp_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        'CÓDIGO INVENTARIO', 'NOMBRE', 'CATEGORÍA', 'MARCA', 'MODELO',
        'N° DE SERIE', 'ESTADO', 'HORAS USO ACUMULADAS', 'HORAS PRÓXIMO MTO',
        'UBICACIÓN ACTUAL', 'VALOR REPOSICIÓN (CLP)'
    ])

    for h in Herramienta.objects.select_related('categoria', 'obra_actual').all():
        ubicacion = h.obra_actual.nombre if h.obra_actual else h.bodega_actual
        writer.writerow([
            h.codigo_inventario,
            h.nombre,
            h.categoria.nombre,
            h.marca,
            h.modelo,
            h.numero_serie or 'N/A',
            h.get_estado_display(),
            h.horas_uso_acumuladas,
            h.horas_proximo_mantenimiento,
            ubicacion,
            f"{h.valor_reposicion:.0f}"
        ])

    return response


@login_required
def exportar_prestamos_csv_view(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"guias_prestamos_buildcorp_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        'FOLIO PRÉSTAMO', 'CONTRATISTA', 'RUT CONTRATISTA', 'OBRA DESTINO',
        'FECHA EMISIÓN', 'FECHA PACTADA DEVOLUCIÓN', 'FECHA REAL DEVOLUCIÓN',
        'ESTADO', 'RECEPTOR EN OBRA', 'RUT RECEPTOR', 'TIENE FIRMA DIGITAL'
    ])

    for p in PrestamoHerramienta.objects.select_related('contratista', 'obra').all():
        writer.writerow([
            p.codigo_prestamo,
            p.contratista.razon_social,
            p.contratista.rut,
            p.obra.nombre,
            p.fecha_prestamo.strftime('%d/%m/%Y %H:%M'),
            p.fecha_pactada_devolucion.strftime('%d/%m/%Y'),
            p.fecha_real_devolucion.strftime('%d/%m/%Y %H:%M') if p.fecha_real_devolucion else 'PENDIENTE',
            p.get_estado_display(),
            p.receptor_nombre,
            p.receptor_rut,
            'SÍ' if p.firma_digital_entrega else 'NO'
        ])

    return response


@login_required
def exportar_mantenimientos_csv_view(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"ordenes_mantenimiento_buildcorp_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        'N° ORDEN', 'CÓDIGO ACTIVO', 'HERRAMIENTA', 'TIPO SERVICIO',
        'HORÓMETRO INGRESO', 'FECHA PROGRAMADA', 'FECHA EJECUCIÓN',
        'ESTADO', 'TÉCNICO / TALLER', 'COSTO FINAL (CLP)'
    ])

    for m in MantenimientoPreventivo.objects.select_related('herramienta').all():
        writer.writerow([
            m.codigo_orden,
            m.herramienta.codigo_inventario,
            m.herramienta.nombre,
            m.get_tipo_display(),
            m.horas_al_momento,
            m.fecha_programada.strftime('%d/%m/%Y'),
            m.fecha_ejecucion.strftime('%d/%m/%Y') if m.fecha_ejecucion else 'PENDIENTE',
            m.get_estado_display(),
            m.tecnico_responsable,
            f"{m.costo:.0f}"
        ])

    return response
