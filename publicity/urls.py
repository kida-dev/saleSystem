from django.urls import path
from . import views

app_name = "publicity"

urlpatterns = [
    path("", views.top, name="top"),
    path("schools/", views.school_list, name="school_list"),
    path("labels/select/", views.label_select, name="label_select"),
    path("labels/pdf/", views.label_pdf, name="label_pdf"),
]