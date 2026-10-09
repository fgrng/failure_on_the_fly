"""Throwaway #296: three Evallauf layouts inside the Vignette context.

Run: uv run python -m vignetten.prototype_296
No database, persistence or model calls. Only the preview server mounts the route.
"""

import os
from wsgiref.simple_server import make_server

os.environ.setdefault("SECRET_KEY", "prototype-296-local-only")
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

import django
from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import path

settings.DEBUG = True
settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
settings.MIDDLEWARE = []
settings.TEMPLATES[0]["OPTIONS"]["context_processors"] = []
# Preview edits must be visible on refresh, including changed stylesheet links.
settings.TEMPLATES[0]["APP_DIRS"] = False
settings.TEMPLATES[0]["OPTIONS"]["loaders"] = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]
django.setup()

from config.urls import urlpatterns  # noqa: E402 — URLs need initialized apps.


def preview(request: HttpRequest) -> HttpResponse:
    """Render the authoring shell with in-memory sample results."""
    return render(
        request,
        "vignetten/prototype_296.html",
        {"zeige_entwicklung": True, "request": request},
    )


urlpatterns.insert(0, path("vignetten/296/", preview))
# The isolated preview serves no production views or mutations.
settings.ROOT_URLCONF = "config.urls"

if __name__ == "__main__":
    app = StaticFilesHandler(get_wsgi_application())

    # Keep reverse names from the real app, but reject every other live route.
    def only_preview(environ: dict, start_response: object) -> object:
        """Limit the local server to the mock page and static assets."""
        if environ["PATH_INFO"] == "/":
            start_response("302 Found", [("Location", "/vignetten/296/")])
            return [b""]
        if environ["PATH_INFO"] != "/vignetten/296/" and not environ[
            "PATH_INFO"
        ].startswith("/static/"):
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"Prototype: /vignetten/296/"]
        return app(environ, start_response)

    print("#296: http://127.0.0.1:8296/vignetten/296/?variant=C", flush=True)
    with make_server("127.0.0.1", 8296, only_preview) as server:
        server.serve_forever()
