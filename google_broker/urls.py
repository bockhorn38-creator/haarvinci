from django.urls import path

from . import views

urlpatterns = [
    path("mobil/start/", views.begin),
    path("mobil/abschliessen/", views.finish),
    path("mobil/erneuern/", views.refresh),
    path("mobil/trennen/", views.disconnect),
    path("oauth/google/callback/", views.callback),
]
