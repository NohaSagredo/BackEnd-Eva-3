# BuildCorp — Control de Herramientas y Préstamos
### Evaluación Parcial N°3 — Desarrollo Backend

- **Institución:** INACAP  
- **Docente:** Marcelo Alvarado Aravena  
- **Estudiante:** Rodrigo Nicolás Peña Sagredo  
- **Proyecto:** BuildCorp (Sistema de Gestión de Herramientas, Préstamos con Firma en Pantalla y Control de Atrasos)  
- **Repositorio en GitHub:** [https://github.com/NohaSagredo/BackEnd-Eva-3](https://github.com/NohaSagredo/BackEnd-Eva-3)  
- **Servidor en Producción (AWS EC2):** [http://13.222.134.210/](http://13.222.134.210/)  
- **Documentación Swagger API:** [http://13.222.134.210/api/docs/](http://13.222.134.210/api/docs/)  
- **Panel Django Admin:** [http://13.222.134.210/admin/](http://13.222.134.210/admin/)  

---

## 1. ¿De qué se trata el proyecto?

**BuildCorp** es una aplicación web sencilla y moderna pensada para empresas de construcción. Su objetivo principal es terminar con la pérdida de herramientas, saber exactamente en qué obra está cada equipo y asegurar que las máquinas reciban mantenimiento a tiempo.

### ¿Qué puedes hacer en la aplicación?

1. **Control de Herramientas:** Puedes ver de forma clara todas las herramientas de la empresa, saber cuáles están disponibles en bodega, cuáles están en uso en una obra y cuáles están en reparación.
2. **Préstamos con Firma en Pantalla:** Cuando un contratista retira herramientas, firma directamente en la pantalla usando el mouse o el dedo (en celular/tablet). El sistema guarda la firma y permite imprimir un comprobante en papel o PDF.
3. **Bloqueo Automático por Atraso:** Si un contratista no devuelve las herramientas en la fecha acordada, el sistema lo bloquea de inmediato. Mientras esté bloqueado, **no se le pueden prestar más herramientas** en ninguna obra hasta que devuelva lo pendiente.
4. **Avisos de Mantenimiento:** Cada herramienta acumula horas de uso. Al alcanzar el límite recomendado, el sistema avisa que le toca revisión técnica para evitar que se rompa trabajando.
5. **Devolución Fácil:** Al recibir las herramientas de vuelta, se anotan las horas finales, se revisa su estado y se registra la firma de conformidad de quien entrega.
6. **Historial de Actividades (Auditoría):** Registra cada movimiento realizado en el sistema (quién prestó, quién devolvió, quién bloqueó, fecha y hora) cumpliendo con normas de calidad y seguridad de la información (**ISO 27001 / ISO 9001**).
7. **Descargas a Excel:** Con un solo clic puedes descargar el inventario, los préstamos, las órdenes de mantenimiento y el historial en archivos CSV listos para abrir en Microsoft Excel.

---

## 2. Cuentas de prueba para ingresar

Puedes usar cualquiera de estas tres cuentas para probar el sistema:

| Tipo de Usuario | Usuario | Contraseña | ¿Qué puede hacer? |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin` | `admin123` | Control total del sistema, panel de administración y API. |
| **Jefe de Bodega** | `bodega_central` | `bodega123` | Prestar herramientas, recibir devoluciones y programar mantenciones. |
| **Supervisor de Obra** | `supervisor_obra` | `super123` | Consultar herramientas disponibles y revisar obras en terreno. |

---

## 3. Secciones principales de la aplicación

- **Inicio (`/`):** Panel principal con los números más importantes (herramientas disponibles, en uso, en taller y contratistas con atrasos).
- **Herramientas (`/herramientas/`):** Inventario con fotos, filtros rápidos por estado (disponible, en obra, en taller) y buscador por nombre o código.
- **Préstamos (`/prestamos/`):** Listado de herramientas entregadas, fechas de devolución, visualizador de firmas digitales y botón para imprimir comprobantes.
- **Nuevo Préstamo (`/prestamos/nuevo/`):** Formulario para seleccionar la obra, el contratista, marcar las herramientas y firmar en pantalla.
- **Devolución (`/prestamos/<id>/devolver/`):** Pantalla para registrar el retorno de equipos, actualizar horas de uso y firmar la entrega.
- **Contratistas (`/contratistas/`):** Lista de empresas contratistas, datos de contacto y botones para bloquear o desbloquear manualmente.
- **Obras (`/obras/`):** Lista de obras en construcción, dirección y supervisor a cargo.
- **Mantenimiento (`/mantenimientos/`):** Control de herramientas en taller y registro de reparaciones terminadas.
- **Historial (`/auditoria/`):** Registro de actividades para saber quién hizo cada acción en el sistema.
- **Documentación API (`/api/docs/`):** Documentación interactiva de la API REST (Swagger) para desarrolladores.

---

## 4. Cómo instalar y ejecutar en tu computador

Sigue estos sencillos pasos en tu terminal (Linux o macOS):

### Paso 1: Clonar el proyecto
```bash
git clone https://github.com/NohaSagredo/BackEnd-Eva-3.git
cd BackEnd-Eva-3
```

### Paso 2: Activar el entorno virtual
```bash
python3 -m venv env
source env/bin/activate
```

### Paso 3: Instalar las dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Preparar la base de datos con datos de ejemplo
```bash
python manage.py migrate
python manage.py seed_buildcorp
```

### Paso 5: Ejecutar las pruebas automáticas
Para verificar que todo funcione al 100%:
```bash
python manage.py test
```
*(Se ejecutan 15 pruebas automáticas que comprueban la lógica de negocio y la seguridad).*

### Paso 6: Iniciar la aplicación
```bash
python manage.py runserver 127.0.0.1:8000
```
Abre tu navegador en: [http://127.0.0.1:8000](http://127.0.0.1:8000) e inicia sesión con `admin` / `admin123`.

---

## 5. Servidor desplegado en la nube (AWS EC2)

La aplicación web y su base de datos relacional PostgreSQL se encuentran completamente operativas y disponibles en la nube de Amazon Web Services (AWS EC2):

- **Dirección Web Pública:** [http://13.222.134.210/](http://13.222.134.210/)
- **Documentación Swagger API:** [http://13.222.134.210/api/docs/](http://13.222.134.210/api/docs/)
- **Panel Django Admin:** [http://13.222.134.210/admin/](http://13.222.134.210/admin/)
- **Motor de Base de Datos:** PostgreSQL nativo en la instancia EC2.
- **Servidor Web:** Nginx en puerto 80 con Proxy Reverso y Gunicorn bajo servicio continuo Systemd.
