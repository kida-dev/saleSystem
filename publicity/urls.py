from django.urls import path
from . import views

app_name = "publicity"

urlpatterns = [
    path("", views.top, name="top"),
    path(
        "api/schools/search/",
        views.junior_high_school_search,
        name="junior_high_school_search",
    ),
    path(
        "students/",
        views.prospective_student_list,
        name="prospective_student_list",
    ),
    path(
        "students/create/",
        views.prospective_student_create,
        name="prospective_student_create",
    ),
    path(
        "students/<int:pk>/edit/",
        views.prospective_student_edit,
        name="prospective_student_edit",
    ),
    path("schools/", views.school_list, name="school_list"),
    path("schools/print/", views.school_print, name="school_print"),

    path("school/<int:pk>/edit/", views.school_edit, name="school_edit"),
    path("school/<int:pk>/delete/", views.school_delete, name="school_delete"),
    path("teachers/permissions/",views.teacher_permission_manage,name="teacher_permission_manage",),
    path("labels/select/", views.label_select, name="label_select"),
    path("labels/pdf/", views.label_pdf, name="label_pdf"),
    path("labels/class/pdf/", views.class_label_pdf, name="class_label_pdf"),
    path("class/<int:pk>/edit/",views.class_edit,name="class_edit"),
    path("login/denied/",views.login_denied,name="login_denied",),
]