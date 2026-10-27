from django.urls import path

from . import views

app_name = "extensions"
urlpatterns = [path("", views.position_list, name="list")]
