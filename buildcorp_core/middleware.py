class SecurityHeadersMiddleware:
    """
    Middleware de endurecimiento de cabeceras HTTP de seguridad (Defense-in-Depth).
    Añade CSP (Content-Security-Policy), Permissions-Policy y Cross-Origin-Opener-Policy.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response['Permissions-Policy'] = "camera=(), microphone=(), geolocation=(), payment=()"
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        return response
