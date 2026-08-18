"""Health check endpoint for uptime monitors (Render, etc.).

GET /healthz/  -> 200 {"status": "ok", "db": "ok", "version": "..."}
Any failure    -> 503 with diagnostic info.
"""
from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def healthz(request):
    # DB ping — single round-trip, no auth, no template.
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        db_ok = True
        db_err = None
    except Exception as exc:  # pragma: no cover - failure path
        db_ok = False
        db_err = str(exc)

    payload = {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "down",
        "debug": settings.DEBUG,
        "django": settings.DJANGO_VERSION if hasattr(settings, "DJANGO_VERSION") else None,
    }
    if db_err:
        payload["error"] = db_err

    return JsonResponse(payload, status=200 if db_ok else 503)