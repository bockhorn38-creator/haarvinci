from django.urls import path

from . import views

app_name = "intake"
urlpatterns = [
    path("", views.start, name="start"),
    path("vorschau/<uuid:pk>/", views.draft_view, name="draft"),
    path("ergebnis/<uuid:pk>/", views.receipt, name="receipt"),
]
