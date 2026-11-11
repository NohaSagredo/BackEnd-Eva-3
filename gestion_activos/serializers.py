from rest_framework import serializers
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
)


class ObraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Obra
        fields = '__all__'


class ContratistaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Contratista
        fields = '__all__'


class CategoriaHerramientaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaHerramienta
        fields = '__all__'


class HerramientaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    obra_nombre = serializers.CharField(source='obra_actual.nombre', read_only=True, default=None)

    class Meta:
        model = Herramienta
        fields = '__all__'


class ItemPrestamoSerializer(serializers.ModelSerializer):
    herramienta_nombre = serializers.CharField(source='herramienta.nombre', read_only=True)
    herramienta_codigo = serializers.CharField(source='herramienta.codigo_inventario', read_only=True)

    class Meta:
        model = ItemPrestamo
        fields = '__all__'


class PrestamoHerramientaSerializer(serializers.ModelSerializer):
    contratista_nombre = serializers.CharField(source='contratista.razon_social', read_only=True)
    obra_nombre = serializers.CharField(source='obra.nombre', read_only=True)
    items = ItemPrestamoSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = PrestamoHerramienta
        fields = '__all__'

    def validate(self, attrs):
        contratista = attrs.get('contratista')
        if contratista and contratista.estado == 'BLOQUEADO_MOROSIDAD':
            raise serializers.ValidationError(
                {"contratista": f"El contratista '{contratista.razon_social}' está BLOQUEADO POR MOROSIDAD. Despacho denegado."}
            )
        return attrs


class DevolucionActaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevolucionActa
        fields = '__all__'


class MantenimientoPreventivoSerializer(serializers.ModelSerializer):
    herramienta_nombre = serializers.CharField(source='herramienta.nombre', read_only=True)
    herramienta_codigo = serializers.CharField(source='herramienta.codigo_inventario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = MantenimientoPreventivo
        fields = '__all__'


class AlertaMorosidadSerializer(serializers.ModelSerializer):
    contratista_nombre = serializers.CharField(source='contratista.razon_social', read_only=True)
    prestamo_folio = serializers.CharField(source='prestamo.codigo_prestamo', read_only=True)

    class Meta:
        model = AlertaMorosidad
        fields = '__all__'
