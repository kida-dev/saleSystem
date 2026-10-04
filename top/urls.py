from django.urls import path

from . import views


app_name = "top"


urlpatterns = [
    path("", views.top, name="top"),
]