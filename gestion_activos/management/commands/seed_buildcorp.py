import base64
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from gestion_activos.models import (
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


class Command(BaseCommand):
    help = "Carga inicial de datos de prueba para BuildCorp con Trazabilidad ISO 27001"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando sembrado de datos para BuildCorp..."))

        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@buildcorp.cl", "is_staff": True, "is_superuser": True}
        )
        admin_user.set_password("admin123")
        admin_user.save()

        bodeguero, _ = User.objects.get_or_create(
            username="bodega_central",
            defaults={"email": "bodega@buildcorp.cl", "first_name": "Carlos", "last_name": "Valenzuela", "is_staff": True}
        )
        bodeguero.set_password("bodega123")
        bodeguero.save()

        supervisor, _ = User.objects.get_or_create(
            username="supervisor_obra",
            defaults={"email": "supervisor@buildcorp.cl", "first_name": "Manuel", "last_name": "Rios", "is_staff": False}
        )
        supervisor.set_password("super123")
        supervisor.save()

        obras_data = [
            {
                "codigo": "OBRA-HOSP-01",
                "nombre": "Nuevo Hospital Regional Temuco - Fase Estructural",
                "direccion": "Av. Alemania 01450, Temuco",
                "supervisor_nombre": "Ing. Patricio Soto",
                "supervisor_telefono": "+56 9 8765 4321",
                "fecha_inicio": timezone.now().date() - timedelta(days=60),
                "fecha_estimada_cierre": timezone.now().date() + timedelta(days=240),
                "activa": True,
            },
            {
                "codigo": "OBRA-TORRE-02",
                "nombre": "Edificio Residencial Vista Volcán",
                "direccion": "Calle Los Pablos 2300, Temuco",
                "supervisor_nombre": "Arq. Lorena Méndez",
                "supervisor_telefono": "+56 9 9876 5432",
                "fecha_inicio": timezone.now().date() - timedelta(days=30),
                "fecha_estimada_cierre": timezone.now().date() + timedelta(days=150),
                "activa": True,
            },
            {
                "codigo": "OBRA-VIAL-03",
                "nombre": "Mejoramiento Vial Ruta Costera Cautín",
                "direccion": "Ruta S-40 Km 12, Carahue",
                "supervisor_nombre": "Ing. Gonzalo Espinoza",
                "supervisor_telefono": "+56 9 5555 4444",
                "fecha_inicio": timezone.now().date() - timedelta(days=90),
                "fecha_estimada_cierre": timezone.now().date() + timedelta(days=60),
                "activa": True,
            },
        ]
        obras = {}
        for od in obras_data:
            obra, _ = Obra.objects.update_or_create(codigo=od["codigo"], defaults=od)
            obras[od["codigo"]] = obra

        contratistas_data = [
            {
                "rut": "76.432.190-5",
                "razon_social": "Constructora e Ingeniería Cordillera SpA",
                "representante_legal": "Juan Pablo Morales",
                "email": "jpmorales@cordilleraconstruye.cl",
                "telefono": "+56 9 7111 2233",
                "estado": "HABILITADO",
            },
            {
                "rut": "77.890.340-K",
                "razon_social": "Montajes Industriales y Estructuras Sur Ltda",
                "representante_legal": "Fernando Tapia Vera",
                "email": "ftapia@montajessur.cl",
                "telefono": "+56 9 6222 3344",
                "estado": "HABILITADO",
            },
            {
                "rut": "76.999.888-2",
                "razon_social": "Obras Viales y Movimiento de Tierra Los Andes SA",
                "representante_legal": "Carolina Paz Henríquez",
                "email": "chenriquez@vialeslosandes.cl",
                "telefono": "+56 9 8333 4455",
                "estado": "HABILITADO",
            },
            {
                "rut": "78.555.444-1",
                "razon_social": "Instalaciones y Climatización Maipo SpA",
                "representante_legal": "Raúl Cárdenas Silva",
                "email": "rcardenas@maipoinstalaciones.cl",
                "telefono": "+56 9 9444 5566",
                "estado": "BLOQUEADO_MOROSIDAD",
                "motivo_bloqueo": "Bloqueo preventivo automático por retención indebida de martillos demoledores.",
                "fecha_bloqueo": timezone.now() - timedelta(days=4),
            },
        ]
        contratistas = {}
        for cd in contratistas_data:
            c, _ = Contratista.objects.update_or_create(rut=cd["rut"], defaults=cd)
            contratistas[cd["rut"]] = c

        cats_data = [
            {
                "nombre": "Maquinaria Pesada Ligera",
                "descripcion": "Generadores diésel, placas compactadoras, alisadoras de pavimento.",
                "frecuencia_mantenimiento_horas": 150,
                "dias_maximo_prestamo": 20,
            },
            {
                "nombre": "Demolición y Perforación",
                "descripcion": "Martillos demoledores neumáticos y electro-neumáticos, rotomartillos SDS Max.",
                "frecuencia_mantenimiento_horas": 80,
                "dias_maximo_prestamo": 10,
            },
            {
                "nombre": "Corte y Desbaste",
                "descripcion": "Esmeriles angulares 7\" y 9\", cortadoras de pavimento y sierras circulares.",
                "frecuencia_mantenimiento_horas": 60,
                "dias_maximo_prestamo": 7,
            },
            {
                "nombre": "Medición y Geomensura",
                "descripcion": "Niveles láser ópticos, estaciones totales, medidores de distancia.",
                "frecuencia_mantenimiento_horas": 200,
                "dias_maximo_prestamo": 15,
            },
        ]
        categorias = {}
        for catd in cats_data:
            cat, _ = CategoriaHerramienta.objects.update_or_create(nombre=catd["nombre"], defaults=catd)
            categorias[catd["nombre"]] = cat

        herramientas_data = [
            {
                "codigo_inventario": "BC-DEM-001",
                "nombre": "Martillo Demoledor Hexagonal 30kg 2000W",
                "categoria": categorias["Demolición y Perforación"],
                "marca": "Bosch",
                "modelo": "GSH 27 VC",
                "numero_serie": "BOS-98214-GSH",
                "estado": "DISPONIBLE",
                "horas_uso_acumuladas": 45,
                "horas_proximo_mantenimiento": 80,
                "bodega_actual": "Bodega Central - Pasillo A3",
                "valor_reposicion": 1850000.00,
                "imagen_url": "/static/images/herramientas/martillo_demoledor.svg",
            },
            {
                "codigo_inventario": "BC-GEN-002",
                "nombre": "Generador Diésel Insonorizado 7.5 kVA",
                "categoria": categorias["Maquinaria Pesada Ligera"],
                "marca": "Kipor",
                "modelo": "KDE6700TA",
                "numero_serie": "KIP-55410-DIE",
                "estado": "EN_USO",
                "horas_uso_acumuladas": 110,
                "horas_proximo_mantenimiento": 150,
                "bodega_actual": "En Terreno",
                "obra_actual": obras["OBRA-HOSP-01"],
                "valor_reposicion": 2400000.00,
                "imagen_url": "/static/images/herramientas/generador_diesel.svg",
            },
            {
                "codigo_inventario": "BC-MED-003",
                "nombre": "Nivel Láser Autonivelante 360° Rotatorio",
                "categoria": categorias["Medición y Geomensura"],
                "marca": "DeWalt",
                "modelo": "DW089LG",
                "numero_serie": "DEW-77142-LAS",
                "estado": "DISPONIBLE",
                "horas_uso_acumuladas": 30,
                "horas_proximo_mantenimiento": 200,
                "bodega_actual": "Bodega Central - Módulo Instrumentación",
                "valor_reposicion": 850000.00,
                "imagen_url": "/static/images/herramientas/nivel_laser.svg",
            },
            {
                "codigo_inventario": "BC-COR-004",
                "nombre": "Cortadora de Pavimento a Gasolina 14\"",
                "categoria": categorias["Corte y Desbaste"],
                "marca": "Husqvarna",
                "modelo": "K770",
                "numero_serie": "HUS-11203-COR",
                "estado": "MANTENIMIENTO",
                "horas_uso_acumuladas": 62,
                "horas_proximo_mantenimiento": 60,
                "bodega_actual": "Taller Mecánico Central",
                "valor_reposicion": 1600000.00,
                "imagen_url": "/static/images/herramientas/cortadora_pavimento.svg",
            },
            {
                "codigo_inventario": "BC-DEM-005",
                "nombre": "Rotomartillo SDS Max 1500W",
                "categoria": categorias["Demolición y Perforación"],
                "marca": "Makita",
                "modelo": "HR4013C",
                "numero_serie": "MAK-33091-ROTO",
                "estado": "DISPONIBLE",
                "horas_uso_acumuladas": 22,
                "horas_proximo_mantenimiento": 80,
                "bodega_actual": "Bodega Central - Pasillo A1",
                "valor_reposicion": 920000.00,
                "imagen_url": "/static/images/herramientas/rotomartillo.svg",
            },
        ]
        herramientas = {}
        for hd in herramientas_data:
            h, _ = Herramienta.objects.update_or_create(codigo_inventario=hd["codigo_inventario"], defaults=hd)
            herramientas[hd["codigo_inventario"]] = h

        mto_data = {
            "codigo_orden": "MTO-2026-COR-001",
            "herramienta": herramientas["BC-COR-004"],
            "tipo": "PREVENTIVO",
            "estado": "EN_PROCESO",
            "horas_al_momento": 62,
            "fecha_programada": timezone.now().date() - timedelta(days=1),
            "tecnico_responsable": "Mecánico Jefe Roberto Alarcón",
            "costo": 85000.00,
            "descripcion_trabajo": "Cambio de correas de transmisión, filtro de aire y bujía por cumplimiento de umbral de 60 horas.",
            "repuestos_utilizados": "Filtro aire OEM K770, Bujía NGK, Correa Poly-V",
        }
        MantenimientoPreventivo.objects.update_or_create(codigo_orden=mto_data["codigo_orden"], defaults=mto_data)

        dummy_signature = (
            "data:image/svg+xml;utf8,"
            "<svg xmlns='http://www.w3.org/2000/svg' width='250' height='90'>"
            "<path d='M10 50 Q 50 10, 90 50 T 170 50 T 230 40' stroke='black' stroke-width='3' fill='none'/>"
            "<text x='10' y='80' font-family='sans-serif' font-size='12' fill='black'>Firma Digital Verificada</text>"
            "</svg>"
        )

        p1, _ = PrestamoHerramienta.objects.update_or_create(
            codigo_prestamo="PREST-2026-0001",
            defaults={
                "contratista": contratistas["76.432.190-5"],
                "obra": obras["OBRA-HOSP-01"],
                "fecha_prestamo": timezone.now() - timedelta(days=3),
                "fecha_pactada_devolucion": timezone.now().date() + timedelta(days=7),
                "estado": "ACTIVO",
                "responsable_despacho": bodeguero,
                "receptor_nombre": "Víctor Cifuentes Carrasco",
                "receptor_rut": "15.420.331-8",
                "firma_digital_entrega": dummy_signature,
                "observaciones_entrega": "Equipos entregados con kit de cables y manuales.",
            }
        )
        ItemPrestamo.objects.get_or_create(
            prestamo=p1,
            herramienta=herramientas["BC-GEN-002"],
            defaults={"horas_uso_iniciales": 95, "devuelto": False}
        )

        p2, _ = PrestamoHerramienta.objects.update_or_create(
            codigo_prestamo="PREST-2026-0002",
            defaults={
                "contratista": contratistas["78.555.444-1"],
                "obra": obras["OBRA-TORRE-02"],
                "fecha_prestamo": timezone.now() - timedelta(days=15),
                "fecha_pactada_devolucion": timezone.now().date() - timedelta(days=4),
                "estado": "VENCIDO_MOROSO",
                "responsable_despacho": bodeguero,
                "receptor_nombre": "Raúl Cárdenas Silva",
                "receptor_rut": "12.876.543-1",
                "firma_digital_entrega": dummy_signature,
                "observaciones_entrega": "Salida sin novedades con compromiso de entrega en 10 días.",
            }
        )
        AlertaMorosidad.objects.update_or_create(
            prestamo=p2,
            contratista=contratistas["78.555.444-1"],
            defaults={
                "dias_retraso": 4,
                "gravedad": "CRITICA",
                "contratista_bloqueado": True,
                "resuelta": False,
            }
        )

        # Sembrar Registros Iniciales de Auditoría ISO
        auditorias_data = [
            {
                "usuario": admin_user,
                "usuario_nombre": "admin",
                "accion": "CREACION",
                "modulo": "HERRAMIENTAS",
                "identificador_objeto": "BC-GEN-002",
                "descripcion_detalle": "Ingreso al parque de Generador Diésel Kipor KDE6700TA con número de serie KIP-55410-DIE",
                "ip_origen": "192.168.1.50",
                "fecha_hora": timezone.now() - timedelta(days=10),
            },
            {
                "usuario": bodeguero,
                "usuario_nombre": "bodega_central",
                "accion": "DESPACHO_PRESTAMO",
                "modulo": "PRESTAMOS",
                "identificador_objeto": "PREST-2026-0001",
                "descripcion_detalle": "Despacho con firma digital a Constructora Cordillera SpA para obra Hospital Regional Temuco.",
                "ip_origen": "192.168.1.55",
                "fecha_hora": timezone.now() - timedelta(days=3),
            },
            {
                "usuario": None,
                "usuario_nombre": "SISTEMA_AUTOMATICO",
                "accion": "BLOQUEO_MOROSIDAD",
                "modulo": "CONTRATISTAS",
                "identificador_objeto": "78.555.444-1",
                "descripcion_detalle": "Bloqueo preventivo automático ejecutado sobre Instalaciones Maipo SpA por vencimiento en préstamo PREST-2026-0002",
                "ip_origen": "127.0.0.1",
                "fecha_hora": timezone.now() - timedelta(days=4),
            },
            {
                "usuario": supervisor,
                "usuario_nombre": "supervisor_obra",
                "accion": "ORDEN_MANTENIMIENTO",
                "modulo": "MANTENIMIENTO",
                "identificador_objeto": "MTO-2026-COR-001",
                "descripcion_detalle": "Envío a taller por umbral de 60 horas para Cortadora de Pavimento BC-COR-004.",
                "ip_origen": "192.168.1.60",
                "fecha_hora": timezone.now() - timedelta(days=1),
            },
        ]

        for ad in auditorias_data:
            RegistroAuditoria.objects.get_or_create(
                identificador_objeto=ad["identificador_objeto"],
                accion=ad["accion"],
                defaults=ad
            )

        self.stdout.write(self.style.SUCCESS("Sembrado de datos BuildCorp completado exitosamente con Bitácora ISO 27001."))
