from django.urls import path
from . import views

app_name = "publicity"

urlpatterns = [
    path("", views.top, name="top"),
    path(
        "documents/manage/",
        views.document_management_top,
        name="document_management_top",
    ),
    path(
        "documents/manage/scholarship/select/",
        views.scholarship_document_student_select,
        name="scholarship_document_student_select",
    ),
    path(
        "documents/scholarship-request/",
        views.scholarship_request_document_create,
        name="scholarship_request_document_create",
    ),
    path(
        "documents/manage/scholarship/confirm/",
        views.scholarship_document_confirm,
        name="scholarship_document_confirm",
    ),
    path(
        "documents/scholarship-request/pdf/",
        views.scholarship_request_document_pdf,
        name="scholarship_request_document_pdf",
    ),
    path(
        "documents/manage/scholarship/issue/",
        views.scholarship_document_batch_issue,
        name="scholarship_document_batch_issue",
    ),
    path(
        "documents/manage/history/",
        views.scholarship_document_history,
        name="scholarship_document_history",
    ),
    path(
        "documents/manage/history/<int:document_id>/reprint/",
        views.scholarship_document_reprint,
        name="scholarship_document_reprint",
    ),
    path(
        "documents/manage/history/<int:document_id>/cancel/",
        views.scholarship_document_cancel,
        name="scholarship_document_cancel",
    ),
    path(
        "documents/manage/history/<int:document_id>/correct/",
        views.scholarship_document_correct,
        name="scholarship_document_correct",
    ),
    path(
        "scholarship/manage/",
        views.scholarship_management_list,
        name="scholarship_management_list",
    ),
    path(
        "scholarship/manage/student/<int:student_id>/",
        views.scholarship_assignment_detail,
        name="scholarship_assignment_detail",
    ),
    path(
        "scholarship/manage/student/<int:student_id>/interview/",
        views.scholarship_interview,
        name="scholarship_interview",
    ),
    path(
        "scholarship/quotas/",
        views.scholarship_quota_manage,
        name="scholarship_quota_manage",
    ),
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
    path(
        "students/export/excel/",
        views.prospective_student_excel,
        name="prospective_student_excel",
    ),
    path(
        "recruitment/manage/",
        views.recruitment_response_management_list,
        name="recruitment_response_management_list",
    ),
    path(
        "recruitment/manage/student/<int:student_id>/",
        views.recruitment_response_management_detail,
        name="recruitment_response_management_detail",
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