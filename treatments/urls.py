from django.urls import path

from . import views

app_name = "treatments"
urlpatterns = [
    path("", views.overview, name="list"),
    path("neu/", views.treatment_form, name="create"),
    path("statistik/", views.statistics, name="statistics"),
    path("preise/", views.prices, name="prices"),
    path("preise/<uuid:pk>/", views.prices, name="price_edit"),
    path("<uuid:pk>/", views.detail, name="detail"),
    path("<uuid:pk>/bearbeiten/", views.treatment_form, name="edit"),
    path("<uuid:pk>/stornieren/", views.cancel, name="cancel"),
    path("<uuid:pk>/zahlungen/neu/", views.payment_form, name="payment"),
    path("<uuid:pk>/erstattung/", views.payment_form, {"refund": True}, name="refund"),
    path("buchung/<uuid:pk>/stornieren/", views.payment_void, name="void"),
]
