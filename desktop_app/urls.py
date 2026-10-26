from django.urls import include, path

from .views import first_run

urlpatterns = [
    path("einrichten/", first_run, name="desktop_setup"),
    path("", include("config.urls")),
]
