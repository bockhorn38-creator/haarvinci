from django.urls import path

from . import views

app_name = "appointments"
urlpatterns = [
    path("", views.calendar_view, name="calendar"),
    path("neu/", views.appointment_form, name="create"),
    path("dauer/", views.duration, name="duration"),
    path("google/", views.google_settings, name="google"),
    path("arten/neu/", views.type_create, name="type_create"),
    path("kundin/<uuid:pk>/", views.customer_appointments, name="customer"),
    path("google-termin/<int:pk>/", views.external_detail, name="external"),
    path("<uuid:pk>/", views.appointment_detail, name="detail"),
    path("<uuid:pk>/bearbeiten/", views.appointment_form, name="edit"),
    path("<uuid:pk>/absagen/", views.appointment_cancel, name="cancel"),
]
