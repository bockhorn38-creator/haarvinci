from django.urls import path

from extensions import views as extension_views

from . import views

app_name = "customers"
urlpatterns = [
    path("", views.customer_list, name="list"),
    path("neu/", views.customer_create, name="create"),
    path("<uuid:pk>/", views.customer_detail, name="detail"),
    path("<uuid:pk>/bearbeiten/", views.customer_edit, name="edit"),
    path("<uuid:pk>/export/", views.customer_export, name="export"),
    path(
        "<uuid:customer_pk>/extensions/neu/",
        extension_views.position_create,
        name="extension_create",
    ),
    path(
        "<uuid:customer_pk>/extensions/<uuid:pk>/bearbeiten/",
        extension_views.position_edit,
        name="extension_edit",
    ),
    path(
        "<uuid:customer_pk>/extensions/<uuid:pk>/loeschen/",
        extension_views.position_delete,
        name="extension_delete",
    ),
]
