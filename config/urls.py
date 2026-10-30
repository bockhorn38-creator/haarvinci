from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "anmelden/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("abmelden/", auth_views.LogoutView.as_view(), name="logout"),
    path("konto/", views.account, name="account"),
    path(
        "konto/passwort/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change.html",
            success_url="/konto/passwort/geaendert/",
        ),
        name="password_change",
    ),
    path(
        "konto/passwort/geaendert/",
        auth_views.PasswordChangeDoneView.as_view(template_name="registration/password_done.html"),
        name="password_change_done",
    ),
    path("kundinnen/", include("customers.urls")),
    path("extensions/", include("extensions.urls")),
    path("kalender/", include("appointments.urls")),
    path("behandlungen/", include("treatments.urls")),
    path("uebernehmen/", include("intake.urls")),
    path("bereit/", views.health, name="health"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
]
