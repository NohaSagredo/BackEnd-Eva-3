from datetime import timedelta
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

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
from .views import registrar_auditoria_iso


class BuildCorpFullTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='test_admin', password='password123', email='test@buildcorp.cl')
        self.client = Client()
        self.client.force_login(self.user)

        self.obra = Obra.objects.create(
            codigo="OBRA-TEST-01",
            nombre="Obra Test Estructural",
            direccion="Av. Los Aromos 123",
            supervisor_nombre="Ing. Test",
            supervisor_telefono="+56911112222",
            fecha_inicio=timezone.now().date(),
            fecha_estimada_cierre=timezone.now().date() + timedelta(days=90),
            activa=True
        )

        self.contratista = Contratista.objects.create(
            rut="76.111.222-3",
            razon_social="Constructora Prueba SpA",
            representante_legal="Juan Perez",
            email="juan@prueba.cl",
            telefono="+56933334444",
            estado="HABILITADO"
        )

        self.categoria = CategoriaHerramienta.objects.create(
            nombre="Demolición",
            frecuencia_mantenimiento_horas=50,
            dias_maximo_prestamo=10
        )

        self.herramienta = Herramienta.objects.create(
            codigo_inventario="BC-TEST-001",
            nombre="Martillo Demoledor Test",
            categoria=self.categoria,
            marca="Makita",
            modelo="HM1203C",
            estado="DISPONIBLE",
            horas_uso_acumuladas=40,
            horas_proximo_mantenimiento=50,
            valor_reposicion=500000.00,
            imagen_url="/static/images/herramientas/martillo_demoledor.svg"
        )

    def test_registro_horas_dispara_mantenimiento_preventivo_automatico(self):
        self.herramienta.registrar_horas(15)
        self.herramienta.refresh_from_db()

        self.assertEqual(self.herramienta.horas_uso_acumuladas, 55)
        self.assertEqual(self.herramienta.estado, 'MANTENIMIENTO')

        mto = MantenimientoPreventivo.objects.filter(herramienta=self.herramienta, estado='PROGRAMADO').first()
        self.assertIsNotNone(mto)
        self.assertEqual(mto.horas_al_momento, 55)

    def test_evaluacion_morosidad_aplica_bloqueo_automatico(self):
        prestamo = PrestamoHerramienta.objects.create(
            codigo_prestamo="PREST-TEST-MORA",
            contratista=self.contratista,
            obra=self.obra,
            fecha_prestamo=timezone.now() - timedelta(days=10),
            fecha_pactada_devolucion=timezone.now().date() - timedelta(days=3),
            responsable_despacho=self.user,
            receptor_nombre="Carlos Soto",
            receptor_rut="11.222.333-4",
            firma_digital_entrega="data:image/png;base64,mock",
            estado='ACTIVO'
        )

        prestamo.evaluar_morosidad()
        prestamo.refresh_from_db()
        self.contratista.refresh_from_db()

        self.assertEqual(prestamo.estado, 'VENCIDO_MOROSO')
        self.assertEqual(self.contratista.estado, 'BLOQUEADO_MOROSIDAD')

        alerta = AlertaMorosidad.objects.filter(prestamo=prestamo, resuelta=False).first()
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.dias_retraso, 3)
        self.assertTrue(alerta.contratista_bloqueado)

    def test_invariante_bloqueo_rechaza_nuevo_prestamo_a_moroso(self):
        self.contratista.bloquear_por_morosidad("Deuda de herramientas en obra.")

        nuevo_prestamo = PrestamoHerramienta(
            codigo_prestamo="PREST-TEST-RECHAZADO",
            contratista=self.contratista,
            obra=self.obra,
            fecha_pactada_devolucion=timezone.now().date() + timedelta(days=5),
            responsable_despacho=self.user,
            receptor_nombre="Receptor",
            receptor_rut="1.1.1-1",
            firma_digital_entrega="data:image/png;base64,mock"
        )

        with self.assertRaises(ValidationError):
            nuevo_prestamo.clean()

    def test_crud_herramienta_completo(self):
        # CREATE
        resp_create = self.client.post('/herramientas/nueva/', {
            'codigo_inventario': 'BC-NEW-999',
            'categoria': self.categoria.id,
            'nombre': 'Sierra Circular Inalámbrica',
            'marca': 'DeWalt',
            'modelo': 'DCS570B',
            'numero_serie': 'SN-999-DCS',
            'estado': 'DISPONIBLE',
            'horas_uso_acumuladas': '0',
            'horas_proximo_mantenimiento': '80',
            'bodega_actual': 'Bodega Central',
            'valor_reposicion': '250000',
            'imagen_url': '/static/images/herramientas/default_tool.svg'
        })
        self.assertEqual(resp_create.status_code, 302)
        tool = Herramienta.objects.get(codigo_inventario='BC-NEW-999')
        self.assertEqual(tool.nombre, 'Sierra Circular Inalámbrica')
        self.assertEqual(tool.get_imagen_url, '/static/images/herramientas/default_tool.svg')

        # UPDATE
        resp_edit = self.client.post(f'/herramientas/{tool.id}/editar/', {
            'categoria': self.categoria.id,
            'nombre': 'Sierra Circular Pro 20V',
            'marca': 'DeWalt',
            'modelo': 'DCS570B-PRO',
            'numero_serie': 'SN-999-PRO',
            'estado': 'DISPONIBLE',
            'horas_uso_acumuladas': '10',
            'horas_proximo_mantenimiento': '100',
            'bodega_actual': 'Bodega Sur',
            'valor_reposicion': '270000',
            'imagen_url': '/static/images/herramientas/cortadora_pavimento.svg'
        })
        self.assertEqual(resp_edit.status_code, 302)
        tool.refresh_from_db()
        self.assertEqual(tool.nombre, 'Sierra Circular Pro 20V')
        self.assertEqual(tool.bodega_actual, 'Bodega Sur')

        # DELETE
        resp_del = self.client.post(f'/herramientas/{tool.id}/eliminar/')
        self.assertEqual(resp_del.status_code, 302)
        self.assertFalse(Herramienta.objects.filter(codigo_inventario='BC-NEW-999').exists())

    def test_crud_contratista_completo(self):
        # CREATE
        resp = self.client.post('/contratistas/nuevo/', {
            'rut': '79.888.777-6',
            'razon_social': 'Hormigones del Maule SpA',
            'representante_legal': 'Mario Soto',
            'email': 'msoto@hormigonesmaule.cl',
            'telefono': '+56988887777',
            'estado': 'HABILITADO'
        })
        self.assertEqual(resp.status_code, 302)
        c = Contratista.objects.get(rut='79.888.777-6')

        # UPDATE
        resp_edit = self.client.post(f'/contratistas/{c.id}/editar/', {
            'rut': '79.888.777-6',
            'razon_social': 'Hormigones del Maule y Cía Ltda',
            'representante_legal': 'Mario Soto Gomez',
            'email': 'contacto@hormigonesmaule.cl',
            'telefono': '+56999990000',
            'estado': 'HABILITADO'
        })
        self.assertEqual(resp_edit.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.razon_social, 'Hormigones del Maule y Cía Ltda')

        # DELETE
        resp_del = self.client.post(f'/contratistas/{c.id}/eliminar/')
        self.assertEqual(resp_del.status_code, 302)
        self.assertFalse(Contratista.objects.filter(rut='79.888.777-6').exists())

    def test_crud_obras_completo(self):
        # CREATE
        resp = self.client.post('/obras/nueva/', {
            'codigo': 'OBRA-TEST-CRUD',
            'nombre': 'Centro Logístico Temuco',
            'direccion': 'Ruta 5 Sur Km 670',
            'supervisor_nombre': 'Ing. Andrea Gomez',
            'supervisor_telefono': '+56944445555',
            'fecha_inicio': timezone.now().date(),
            'fecha_estimada_cierre': timezone.now().date() + timedelta(days=120),
            'activa': 'True'
        })
        self.assertEqual(resp.status_code, 302)
        obra = Obra.objects.get(codigo='OBRA-TEST-CRUD')

        # UPDATE
        resp_edit = self.client.post(f'/obras/{obra.id}/editar/', {
            'nombre': 'Centro Logístico y Distribución Temuco',
            'direccion': 'Ruta 5 Sur Km 672',
            'supervisor_nombre': 'Ing. Andrea Gomez P.',
            'supervisor_telefono': '+56944445555',
            'fecha_inicio': timezone.now().date(),
            'fecha_estimada_cierre': timezone.now().date() + timedelta(days=150),
            'activa': 'True'
        })
        self.assertEqual(resp_edit.status_code, 302)
        obra.refresh_from_db()
        self.assertEqual(obra.nombre, 'Centro Logístico y Distribución Temuco')

        # DELETE
        resp_del = self.client.post(f'/obras/{obra.id}/eliminar/')
        self.assertEqual(resp_del.status_code, 302)
        self.assertFalse(Obra.objects.filter(codigo='OBRA-TEST-CRUD').exists())

    def test_mantenimiento_manual_y_cancelacion(self):
        resp = self.client.post('/mantenimientos/nuevo/', {
            'herramienta': self.herramienta.id,
            'tipo': 'CORRECTIVO',
            'fecha_programada': timezone.now().date(),
            'tecnico_responsable': 'Taller Mecánico Test',
            'costo_estimado': '45000',
            'descripcion_trabajo': 'Reparación de cable de alimentación cortado',
            'repuestos_utilizados': 'Cable 3x2.5mm'
        })
        self.assertEqual(resp.status_code, 302)
        self.herramienta.refresh_from_db()
        self.assertEqual(self.herramienta.estado, 'MANTENIMIENTO')

        mto = MantenimientoPreventivo.objects.filter(herramienta=self.herramienta, estado='EN_PROCESO').first()
        self.assertIsNotNone(mto)

        # Cancelar mantenimiento
        resp_del = self.client.post(f'/mantenimientos/{mto.id}/eliminar/')
        self.assertEqual(resp_del.status_code, 302)
        self.herramienta.refresh_from_db()
        self.assertEqual(self.herramienta.estado, 'DISPONIBLE')

    def test_vistas_web_impresion_y_errores(self):
        resp_dash = self.client.get('/')
        self.assertEqual(resp_dash.status_code, 200)

        resp_obras = self.client.get('/obras/')
        self.assertEqual(resp_obras.status_code, 200)

        resp_404 = self.client.get('/ruta-no-existe-para-test/')
        self.assertEqual(resp_404.status_code, 404)

    def test_bitacora_auditoria_iso_registro_y_exportacion(self):
        # 1. Verificar registro manual de auditoría con hash SHA-256
        factory = RequestFactory()
        req = factory.get('/')
        req.user = self.user
        req.META['REMOTE_ADDR'] = '192.168.1.50'

        registro = registrar_auditoria_iso(
            req,
            accion='CREACION',
            modulo='HERRAMIENTAS',
            identificador=self.herramienta.codigo_inventario,
            detalle='Alta de herramienta de prueba para verificación ISO'
        )
        self.assertIsNotNone(registro)
        self.assertEqual(registro.usuario, self.user)
        self.assertEqual(registro.accion, 'CREACION')
        self.assertEqual(registro.modulo, 'HERRAMIENTAS')
        self.assertEqual(len(registro.hash_integridad), 64)

        # 2. Verificar vista web de auditoría
        resp_auditoria = self.client.get('/auditoria/')
        self.assertEqual(resp_auditoria.status_code, 200)
        self.assertContains(resp_auditoria, "ISO 27001 / ISO 9001")
        self.assertContains(resp_auditoria, registro.hash_integridad[:16])

        # 3. Filtrado por módulo
        resp_filtro = self.client.get('/auditoria/?modulo=HERRAMIENTAS')
        self.assertEqual(resp_filtro.status_code, 200)
        self.assertContains(resp_filtro, "HERRAMIENTAS")

        # 4. Exportación CSV de auditoría
        resp_csv = self.client.get('/auditoria/exportar/csv/')
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv['Content-Type'], 'text/csv; charset=utf-8')
        content = resp_csv.content.decode('utf-8')
        self.assertIn("FECHA Y HORA (CLT)", content)
        self.assertIn("HASH CRIPTOGRÁFICO SHA-256", content)
        self.assertIn(self.herramienta.codigo_inventario, content)


from io import BytesIO
from PIL import Image as PILImage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from rest_framework.test import APIClient


class BuildCorpSecurityAuditTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='operador_seguro', password='PasswordSeguro123!', email='sec@buildcorp.cl')
        self.client = Client()

    def tearDown(self):
        cache.clear()

    def test_cabeceras_http_de_seguridad_activas(self):
        resp = self.client.get('/login/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(resp.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
        self.assertIn('Content-Security-Policy', resp.headers)
        self.assertIn("default-src 'self'", resp.headers['Content-Security-Policy'])
        self.assertIn('Permissions-Policy', resp.headers)

    def test_mitigacion_open_redirect_en_login(self):
        malicious_urls = [
            'https://malicious-site.com/steal-creds',
            '//attacker.com/fake-portal',
            'http://phishing.org',
        ]
        for url in malicious_urls:
            resp = self.client.post(f'/login/?next={url}', {
                'username': 'operador_seguro',
                'password': 'PasswordSeguro123!'
            })
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.url, '/')
            self.client.logout()

    def test_proteccion_contra_fuerza_bruta_en_login(self):
        for i in range(1, 5):
            resp = self.client.post('/login/', {
                'username': 'operador_seguro',
                'password': f'WrongPass_{i}'
            })
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, f"Intento {i} de 5")

        # Quinto intento fallido activa el bloqueo preventivo
        resp_5 = self.client.post('/login/', {
            'username': 'operador_seguro',
            'password': 'WrongPass_5'
        })
        self.assertEqual(resp_5.status_code, 200)
        self.assertContains(resp_5, "bloqueado preventivamente por 5 minutos")

        # Sexto intento: denegado de inmediato sin validar credenciales
        resp_6 = self.client.post('/login/', {
            'username': 'operador_seguro',
            'password': 'PasswordSeguro123!'
        })
        self.assertEqual(resp_6.status_code, 200)
        self.assertContains(resp_6, "Acceso bloqueado temporalmente")

        # Verificar registro pericial de seguridad en auditoría ISO
        bloqueo_reg = RegistroAuditoria.objects.filter(accion='BLOQUEO_SEGURIDAD').first()
        self.assertIsNotNone(bloqueo_reg)
        self.assertIn("fuerza bruta", bloqueo_reg.descripcion_detalle.lower())

    def test_metodo_http_restringido_en_eliminaciones_previene_get(self):
        self.client.force_login(self.user)
        cat = CategoriaHerramienta.objects.create(nombre="Seguridad", frecuencia_mantenimiento_horas=100, dias_maximo_prestamo=10)
        h = Herramienta.objects.create(
            codigo_inventario="BC-SEC-001",
            nombre="Taladro Percutor",
            categoria=cat,
            marca="Bosch",
            modelo="GSB 13 RE",
            estado="DISPONIBLE",
            horas_proximo_mantenimiento=100
        )

        resp_get = self.client.get(f'/herramientas/{h.id}/eliminar/')
        self.assertEqual(resp_get.status_code, 405)
        self.assertTrue(Herramienta.objects.filter(pk=h.pk).exists())

    def test_validacion_segura_subida_imagenes(self):
        self.client.force_login(self.user)
        cat = CategoriaHerramienta.objects.create(nombre="TestImg", frecuencia_mantenimiento_horas=100, dias_maximo_prestamo=10)

        # 1. Archivo malicioso (script PHP o texto plano disfrazado con extensión .jpg)
        archivo_falso = SimpleUploadedFile("malware.jpg", b"<?php echo 'pwned'; ?>", content_type="image/jpeg")
        resp_fail = self.client.post('/herramientas/nueva/', {
            'codigo_inventario': 'BC-FAIL-01',
            'categoria': cat.id,
            'nombre': 'Herramienta Insegura',
            'marca': 'Test',
            'modelo': 'T1',
            'imagen': archivo_falso
        })
        self.assertContains(resp_fail, "Archivo de imagen rechazado por seguridad")
        self.assertFalse(Herramienta.objects.filter(codigo_inventario='BC-FAIL-01').exists())

        # 2. Imagen PNG válida y auténtica generada mediante Pillow
        buffer = BytesIO()
        img = PILImage.new('RGB', (100, 100), color=(37, 99, 235))
        img.save(buffer, format='PNG')
        buffer.seek(0)
        archivo_valido = SimpleUploadedFile("taladro_real.png", buffer.getvalue(), content_type="image/png")

        resp_ok = self.client.post('/herramientas/nueva/', {
            'codigo_inventario': 'BC-VALID-01',
            'categoria': cat.id,
            'nombre': 'Herramienta Con Imagen Legítima',
            'marca': 'DeWalt',
            'modelo': 'DCD771',
            'imagen': archivo_valido
        })
        self.assertEqual(resp_ok.status_code, 302)
        h_creada = Herramienta.objects.get(codigo_inventario='BC-VALID-01')
        self.assertTrue(h_creada.imagen)
        self.assertTrue(h_creada.imagen.name.endswith('.png'))

    def test_trazabilidad_iso_en_operaciones_api_rest(self):
        api_client = APIClient()
        api_client.force_authenticate(user=self.user)

        contratista = Contratista.objects.create(
            rut="77.999.888-1",
            razon_social="Constructora Delta SpA",
            representante_legal="Ana Rivas",
            email="arivas@delta.cl",
            telefono="+56911223344",
            estado="HABILITADO"
        )

        resp_block = api_client.post(f'/api/contratistas/{contratista.id}/bloquear/', {'motivo': 'Incumplimiento de póliza faena'}, format='json')
        self.assertEqual(resp_block.status_code, 200)

        # Verificar que la acción vía API quedó documentada en la bitácora criptográfica ISO
        reg_api = RegistroAuditoria.objects.filter(identificador_objeto=contratista.rut, accion='BLOQUEO_MOROSIDAD').first()
        self.assertIsNotNone(reg_api)
        self.assertIn("REST API", reg_api.descripcion_detalle)
        self.assertIn("Incumplimiento de póliza faena", reg_api.descripcion_detalle)

