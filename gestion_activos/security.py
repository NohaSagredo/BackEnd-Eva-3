import os
import uuid
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.cache import cache

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_PIL_FORMATS = {'JPEG', 'PNG', 'WEBP'}

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutos


def validar_y_sanitizar_imagen(uploaded_file):
    """
    Valida tamaño, extensión, tipo MIME e integridad interna de imagen (Pillow)
    y sanitiza el nombre de archivo para prevenir Path Traversal y ejecución de scripts.
    """
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError("El archivo excede el tamaño máximo permitido de 5 MB.")

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Extensión de archivo no autorizada ({ext}). Solo se permiten: .jpg, .jpeg, .png, .webp.")

    if hasattr(uploaded_file, 'content_type') and uploaded_file.content_type and uploaded_file.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"Tipo de contenido no autorizado ({uploaded_file.content_type}).")

    try:
        img = Image.open(uploaded_file)
        img.verify()
        if img.format.upper() not in ALLOWED_PIL_FORMATS:
            raise ValidationError(f"Formato interno de imagen no soportado ({img.format}).")
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError("El archivo subido no es una imagen válida o contiene datos corruptos.")
    finally:
        uploaded_file.seek(0)

    clean_name = f"{uuid.uuid4().hex[:12]}{ext}"
    uploaded_file.name = clean_name
    return uploaded_file


def get_client_ip(request):
    """Obtiene la dirección IP real del cliente considerando proxies inversos."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def registrar_intento_fallido_login(request, username):
    """Incrementa el contador de intentos fallidos de autenticación por IP y usuario."""
    ip = get_client_ip(request)
    cache_key = f"brute_force_login_{ip}"
    intentos = cache.get(cache_key, 0) + 1
    cache.set(cache_key, intentos, LOCKOUT_DURATION_SECONDS)
    return intentos


def esta_bloqueado_por_fuerza_bruta(request, username):
    """Verifica si la IP o usuario ha superado el umbral de intentos fallidos."""
    ip = get_client_ip(request)
    cache_key = f"brute_force_login_{ip}"
    intentos = cache.get(cache_key, 0)
    return intentos >= MAX_LOGIN_ATTEMPTS


def resetear_intentos_login(request, username):
    """Limpia el contador de intentos fallidos tras una autenticación exitosa."""
    ip = get_client_ip(request)
    cache.delete(f"brute_force_login_{ip}")
