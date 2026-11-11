from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    ObraViewSet,
    ContratistaViewSet,
    CategoriaHerramientaViewSet,
    HerramientaViewSet,
    PrestamoHerramientaViewSet,
    DevolucionActaViewSet,
    MantenimientoPreventivoViewSet,
    AlertaMorosidadViewSet,
)

router = DefaultRouter()
router.register(r'obras', ObraViewSet)
router.register(r'contratistas', ContratistaViewSet)
router.register(r'categorias', CategoriaHerramientaViewSet)
router.register(r'herramientas', HerramientaViewSet)
router.register(r'prestamos', PrestamoHerramientaViewSet)
router.register(r'devoluciones', DevolucionActaViewSet)
router.register(r'mantenimientos', MantenimientoPreventivoViewSet)
router.register(r'alertas', AlertaMorosidadViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
