# Registro de Prompts y Asistencia de Inteligencia Artificial (prompts_ia.md)
**Asignatura:** Desarrollo Backend - INACAP  
**Evaluación:** Evaluación Parcial N°3 (30%)  
**Estudiante:** Rodrigo Nicolás Peña Sagredo  
**Docente:** Marcelo Alvarado Aravena  
**Proyecto Asignado:** Proyecto 4 - BuildCorp: Sistema de Alquiler y Control de Herramientas  

---

## 1. Modelado de Datos y Estructura Relacional (Django ORM)
- **Herramienta IA:** Antigravity (Google DeepMind)
- **Prompt:**
  > "Necesito diseñar los modelos de datos en Django para un sistema de control de herramientas llamado BuildCorp. Debe incluir herramientas con categorías y estados (Disponible, En uso, Mantenimiento, De baja), obras en construcción, contratistas, préstamos de herramientas con detalle de ítems, actas de devolución y órdenes de mantenimiento preventivo. ¿Cómo defino estos modelos asegurando integridad referencial, claves foráneas y buenas prácticas del ORM?"
- **Apoyo y Resultado:**
  - Definición de los modelos principales (`Herramienta`, `CategoriaHerramienta`, `Obra`, `Contratista`, `PrestamoHerramienta`, `ItemPrestamo`, `DevolucionActa`, `MantenimientoPreventivo`).
  - Configuración de relaciones `ForeignKey`, campos de fechas y horas, y estados mediante `TextChoices`.
  - Creación y aplicación exitosa de las migraciones iniciales de base de datos.

---

## 2. Implementación de Reglas de Negocio Clave
- **Herramienta IA:** Antigravity (Google DeepMind)
- **Prompt:**
  > "En BuildCorp necesito aplicar dos reglas de negocio obligatorias: 1) Si un contratista tiene préstamos vencidos, debe quedar bloqueado automáticamente por morosidad impidiendo que se le entreguen nuevas herramientas. 2) Al devolver una herramienta, si las horas de uso acumuladas superan el límite de mantenimiento de su categoría, el sistema debe cambiar su estado a Mantenimiento y generar una orden técnica. ¿Cómo implemento esta lógica en los modelos y vistas de Django?"
- **Apoyo y Resultado:**
  - Implementación del método `evaluar_morosidad()` en el modelo `PrestamoHerramienta` para detectar vencimientos y cambiar el estado del contratista a `BLOQUEADO_MOROSIDAD`.
  - Validación en el método `clean()` del préstamo para bloquear nuevas entregas a contratistas morosos a nivel de modelo.
  - Lógica en la vista de devolución para calcular horas de uso finales y disparar la orden de mantenimiento preventivo si se supera el umbral recomendado.

---

## 3. Operaciones CRUD y Formularios de la Aplicación Web
- **Herramienta IA:** Antigravity (Google DeepMind)
- **Prompt:**
  > "Necesito implementar las operaciones CRUD (crear, listar, editar y eliminar) para herramientas, contratistas, obras y mantenimientos, utilizando vistas protegidas con autenticación de usuarios (`@login_required`). ¿Cómo estructuro las vistas y formularios para validar los datos, evitar caídas y mostrar mensajes de confirmación al usuario?"
- **Apoyo y Resultado:**
  - Creación de las vistas correspondientes en `views.py` gestionando peticiones GET y POST con manejo seguro de transacciones atómicas (`transaction.atomic`).
  - Integración del sistema de alertas flash de Django (`django.contrib.messages`) para notificar al usuario sobre operaciones exitosas o errores.
  - Implementación de plantillas HTML responsivas y accesibles para cada módulo del sistema.

---

## 4. Captura de Firma Digital en Pantalla para Préstamos y Devoluciones
- **Herramienta IA:** Antigravity (Google DeepMind)
- **Prompt:**
  > "¿Cómo puedo integrar un lienzo (canvas) en HTML5 y JavaScript dentro del formulario de entrega y recepción para que el responsable de obra firme directamente en pantalla (con el mouse o pantalla táctil), y guardar esa firma en la base de datos de Django?"
- **Apoyo y Resultado:**
  - Código JavaScript para inicializar el canvas interactivo con eventos de mouse y touch, permitiendo dibujar y limpiar la firma.
  - Serialización del trazo dibujado a formato Base64 (PNG data-URL) que se envía mediante un campo oculto del formulario.
  - Almacenamiento seguro de la firma digital asociada al acta de préstamo y de devolución.

---

## 5. Exposición de API RESTful con Django REST Framework y Swagger
- **Herramienta IA:** Antigravity (Google DeepMind)
- **Prompt:**
  > "Necesito crear una API RESTful para los módulos del sistema utilizando Django REST Framework (DRF) con autenticación JWT y documentación interactiva mediante Swagger/OpenAPI. ¿Cómo configuro los serializers, viewsets y el enrutador de URLs?"
- **Apoyo y Resultado:**
  - Creación de serializadores `ModelSerializer` para cada entidad del dominio en `serializers.py`.
  - Implementación de `ModelViewSet` en `api_views.py` con filtros por búsqueda y ordenamiento (`DjangoFilterBackend`).
  - Configuración del router en `api_urls.py` y configuración de `drf-spectacular` para exponer la documentación Swagger en la ruta `/api/docs/`.

---

## 6. Personalización del Panel de Administración (Django Admin)
- **Herramienta IA:** Antigravity (Google DeepMind)
- **Prompt:**
  > "¿Cómo personalizo el Django Admin para que muestre tablas completas con filtros laterales, barras de búsqueda, acciones para cambiar estados en lote y miniaturas visuales de las fotos de herramientas y firmas digitales?"
- **Apoyo y Resultado:**
  - Registro de los modelos en `admin.py` utilizando clases `ModelAdmin` con `list_display`, `list_filter` y `search_fields`.
  - Creación de acciones administrativas masivas para enviar a mantenimiento o regularizar contratistas.
  - Implementación de métodos auxiliares con `format_html` para previsualizar fotografías de herramientas y firmas digitales directamente en el listado.

---

## 7. Despliegue en la Nube con AWS EC2, PostgreSQL, Gunicorn y Nginx
- **Herramienta IA:** Antigravity (Google DeepMind)
- **Prompt:**
  > "Necesito desplegar mi aplicación Django en una instancia Ubuntu en AWS EC2 (AWS Academy). La solución debe utilizar PostgreSQL como motor de base de datos relacional, Gunicorn como servidor de aplicaciones en segundo plano supervisado por Systemd, y Nginx como proxy reverso en el puerto 80 para servir la web y archivos estáticos. ¿Cuáles son los pasos y configuraciones necesarias?"
- **Apoyo y Resultado:**
  - Instrucciones de instalación de paquetes (`postgresql`, `nginx`, `python3-venv`, `libpq-dev`).
  - Configuración del usuario y base de datos relacional `buildcorp_db` en PostgreSQL.
  - Creación del archivo de servicio Systemd `/etc/systemd/system/buildcorp.service` para mantener Gunicorn en ejecución continua y reinicio automático.
  - Configuración del bloque de servidor en Nginx para servir `/static/`, `/media/` y redirigir el tráfico dinámico a Gunicorn en el puerto local 8000.
