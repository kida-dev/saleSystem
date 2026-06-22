from django.urls import path
from . import views

app_name = "publicity"

urlpatterns = [
    path("", views.top, name="top"),

    path("schools/", views.school_list, name="school_list"),
    path("schools/print/", views.school_print, name="school_print"),

    path("school/<int:pk>/edit/", views.school_edit, name="school_edit"),
    path("school/<int:pk>/delete/", views.school_delete, name="school_delete"),

    path("labels/select/", views.label_select, name="label_select"),
    path("labels/pdf/", views.label_pdf, name="label_pdf"),
    path("labels/class/pdf/", views.class_label_pdf, name="class_label_pdf"),
    path("class/<int:pk>/edit/",views.class_edit,name="class_edit"),
]