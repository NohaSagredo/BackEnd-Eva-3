from django.urls import path
from . import views

urlpatterns = [
    # Tablero
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # CRUD Herramientas / Activos
    path('herramientas/', views.herramientas_list_view, name='herramientas'),
    path('herramientas/nueva/', views.herramientas_crear_view, name='herramientas_crear'),
    path('herramientas/<int:herramienta_id>/editar/', views.herramientas_editar_view, name='herramientas_editar'),
    path('herramientas/<int:herramienta_id>/eliminar/', views.herramientas_eliminar_view, name='herramientas_eliminar'),
    
    # CRUD Obras / Faenas
    path('obras/', views.obras_list_view, name='obras'),
    path('obras/nueva/', views.obras_crear_view, name='obras_crear'),
    path('obras/<int:obra_id>/editar/', views.obras_editar_view, name='obras_editar'),
    path('obras/<int:obra_id>/eliminar/', views.obras_eliminar_view, name='obras_eliminar'),

    # Préstamos y Firma Digital
    path('prestamos/', views.prestamos_list_view, name='prestamos'),
    path('prestamos/nuevo/', views.nuevo_prestamo_view, name='nuevo_prestamo'),
    path('prestamos/<int:prestamo_id>/devolver/', views.devolucion_prestamo_view, name='devolucion_prestamo'),
    path('prestamos/<int:prestamo_id>/imprimir/', views.imprimir_prestamo_view, name='imprimir_prestamo'),
    
    # CRUD Contratistas
    path('contratistas/', views.contratistas_list_view, name='contratistas'),
    path('contratistas/nuevo/', views.contratistas_crear_view, name='contratistas_crear'),
    path('contratistas/<int:contratista_id>/editar/', views.contratistas_editar_view, name='contratistas_editar'),
    path('contratistas/<int:contratista_id>/eliminar/', views.contratistas_eliminar_view, name='contratistas_eliminar'),

    # CRUD Mantenimientos
    path('mantenimientos/', views.mantenimientos_list_view, name='mantenimientos'),
    path('mantenimientos/nuevo/', views.mantenimientos_crear_view, name='mantenimientos_crear'),
    path('mantenimientos/<int:mantenimiento_id>/eliminar/', views.mantenimientos_eliminar_view, name='mantenimientos_eliminar'),
    
    # Auditoría y Trazabilidad ISO
    path('auditoria/', views.auditoria_list_view, name='auditoria'),
    path('auditoria/exportar/csv/', views.exportar_auditoria_csv_view, name='auditoria_exportar_csv_alias'),
    
    # Exportaciones CSV Estandarizadas
    path('reportes/herramientas/csv/', views.exportar_herramientas_csv_view, name='exportar_herramientas_csv'),
    path('reportes/prestamos/csv/', views.exportar_prestamos_csv_view, name='exportar_prestamos_csv'),
    path('reportes/mantenimientos/csv/', views.exportar_mantenimientos_csv_view, name='exportar_mantenimientos_csv'),
    path('reportes/auditoria/csv/', views.exportar_auditoria_csv_view, name='exportar_auditoria_csv'),
]
