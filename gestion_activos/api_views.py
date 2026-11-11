from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import (
    Obra,
    Contratista,
    CategoriaHerramienta,
    Herramienta,
    PrestamoHerramienta,
    DevolucionActa,
    MantenimientoPreventivo,
    AlertaMorosidad,
)
from .serializers import (
    ObraSerializer,
    ContratistaSerializer,
    CategoriaHerramientaSerializer,
    HerramientaSerializer,
    PrestamoHerramientaSerializer,
    DevolucionActaSerializer,
    MantenimientoPreventivoSerializer,
    AlertaMorosidadSerializer,
)
from .views import registrar_auditoria_iso


class ObraViewSet(viewsets.ModelViewSet):
    queryset = Obra.objects.all()
    serializer_class = ObraSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['activa']
    search_fields = ['codigo', 'nombre', 'supervisor_nombre']


class ContratistaViewSet(viewsets.ModelViewSet):
    queryset = Contratista.objects.all()
    serializer_class = ContratistaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['estado']
    search_fields = ['rut', 'razon_social', 'representante_legal']

    @action(detail=True, methods=['post'])
    def bloquear(self, request, pk=None):
        contratista = self.get_object()
        motivo = request.data.get('motivo', 'Bloqueo manual administrativo.')
        contratista.bloquear_por_morosidad(motivo)
        registrar_auditoria_iso(
            request._request,
            'BLOQUEO_MOROSIDAD',
            'CONTRATISTAS',
            contratista.rut,
            f"Bloqueo manual administrativo vía REST API: {motivo}"
        )
        return Response({'status': 'Contratista bloqueado', 'estado': contratista.estado})

    @action(detail=True, methods=['post'])
    def desbloquear(self, request, pk=None):
        contratista = self.get_object()
        contratista.desbloquear()
        registrar_auditoria_iso(
            request._request,
            'DESBLOQUEO_CONTRATISTA',
            'CONTRATISTAS',
            contratista.rut,
            "Desbloqueo y reactivación de contratista vía REST API"
        )
        return Response({'status': 'Contratista habilitado', 'estado': contratista.estado})


class CategoriaHerramientaViewSet(viewsets.ModelViewSet):
    queryset = CategoriaHerramienta.objects.all()
    serializer_class = CategoriaHerramientaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class HerramientaViewSet(viewsets.ModelViewSet):
    queryset = Herramienta.objects.select_related('categoria', 'obra_actual').all()
    serializer_class = HerramientaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'categoria', 'bodega_actual', 'obra_actual']
    search_fields = ['codigo_inventario', 'nombre', 'marca', 'modelo', 'numero_serie']
    ordering_fields = ['codigo_inventario', 'horas_uso_acumuladas', 'fecha_adquisicion']

    @action(detail=True, methods=['post'])
    def registrar_horas(self, request, pk=None):
        herramienta = self.get_object()
        try:
            horas = int(request.data.get('horas', 0))
        except (ValueError, TypeError):
            horas = 0

        if horas > 0:
            herramienta.registrar_horas(horas)
            registrar_auditoria_iso(
                request._request,
                'MODIFICACION',
                'HERRAMIENTAS',
                herramienta.codigo_inventario,
                f"Registro de {horas} hrs de uso en faena vía REST API"
            )
            return Response({
                'status': 'Horas registradas',
                'horas_totales': herramienta.horas_uso_acumuladas,
                'estado': herramienta.estado
            })
        return Response({'error': 'Parámetro horas inválido'}, status=status.HTTP_400_BAD_REQUEST)


class PrestamoHerramientaViewSet(viewsets.ModelViewSet):
    queryset = PrestamoHerramienta.objects.select_related('contratista', 'obra', 'responsable_despacho').prefetch_related('items__herramienta').all()
    serializer_class = PrestamoHerramientaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'obra', 'contratista']
    search_fields = ['codigo_prestamo', 'contratista__razon_social', 'receptor_nombre']
    ordering_fields = ['fecha_prestamo', 'fecha_pactada_devolucion']

    @action(detail=True, methods=['post'])
    def evaluar_morosidad(self, request, pk=None):
        prestamo = self.get_object()
        prestamo.evaluar_morosidad()
        return Response({
            'codigo_prestamo': prestamo.codigo_prestamo,
            'estado': prestamo.estado,
            'contratista_estado': prestamo.contratista.estado
        })


class DevolucionActaViewSet(viewsets.ModelViewSet):
    queryset = DevolucionActa.objects.select_related('prestamo', 'recibido_por').all()
    serializer_class = DevolucionActaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class MantenimientoPreventivoViewSet(viewsets.ModelViewSet):
    queryset = MantenimientoPreventivo.objects.select_related('herramienta').all()
    serializer_class = MantenimientoPreventivoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['tipo', 'estado']
    search_fields = ['codigo_orden', 'herramienta__nombre', 'tecnico_responsable']

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        mto = self.get_object()
        costo = request.data.get('costo', mto.costo)
        nuevas_horas = int(request.data.get('nuevas_horas_proximo', 100))
        mto.finalizar_mantenimiento(costo_final=costo, nuevas_horas_proximo=nuevas_horas)
        registrar_auditoria_iso(
            request._request,
            'CIERRE_MANTENIMIENTO',
            'MANTENIMIENTO',
            mto.codigo_orden,
            f"Cierre de mantenimiento vía REST API. Costo: ${float(costo):,.0f} CLP"
        )
        return Response({'status': 'Mantenimiento finalizado y herramienta reactivada', 'estado': mto.estado})


class AlertaMorosidadViewSet(viewsets.ModelViewSet):
    queryset = AlertaMorosidad.objects.select_related('prestamo', 'contratista').all()
    serializer_class = AlertaMorosidadSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['gravedad', 'resuelta', 'contratista_bloqueado']

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        alerta.resolver()
        registrar_auditoria_iso(
            request._request,
            'DESBLOQUEO_CONTRATISTA',
            'CONTRATISTAS',
            alerta.contratista.rut,
            f"Resolución de alerta morosidad #{alerta.id} y normalización de contratista vía REST API"
        )
        return Response({'status': 'Alerta resuelta', 'contratista_estado': alerta.contratista.estado})
