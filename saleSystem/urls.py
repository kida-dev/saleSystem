from django.contrib import admin
from django.urls import path, include
from publicity import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.top, name="top"),
    path("publicity/", include("publicity.urls")),
    path("labels/class/pdf/", views.class_label_pdf, name="class_label_pdf"),
]