from django.urls import path

from . import views


app_name = "documents"


urlpatterns = [
    # ---------------------------------
    # 校内文書・回覧 TOP
    # ---------------------------------
    path(
        "",
        views.documents_top,
        name="top",
    ),

    # ---------------------------------
    # 旅行命令
    # ---------------------------------
    path(
        "travel/",
        views.travel_order_list,
        name="travel_order_list",
    ),

    path(
        "travel/new/",
        views.travel_order_create,
        name="travel_order_create",
    ),

    path(
        "travel/<int:pk>/",
        views.travel_order_detail,
        name="travel_order_detail",
    ),

    path(
        "travel/<int:pk>/class-adjustment/new/",
        views.travel_class_adjustment_create,
        name="travel_class_adjustment_create",
    ),

    path(
        "travel/<int:pk>/class-adjustment/<int:adjustment_id>/edit/",
        views.travel_class_adjustment_edit,
        name="travel_class_adjustment_edit",
    ),

    path(
        "travel/<int:pk>/class-adjustment/<int:adjustment_id>/delete/",
        views.travel_class_adjustment_delete,
        name="travel_class_adjustment_delete",
    ),
    path(
        "travel/<int:pk>/attachment/new/",
        views.travel_attachment_create,
        name="travel_attachment_create",
    ),

    path(
        "travel/<int:pk>/attachment/<int:attachment_id>/open/",
        views.travel_attachment_open,
        name="travel_attachment_open",
    ),

    path(
        "travel/<int:pk>/attachment/<int:attachment_id>/delete/",
        views.travel_attachment_delete,
        name="travel_attachment_delete",
    ),

    path(
        "travel/<int:pk>/submit/",
        views.travel_order_submit,
        name="travel_order_submit",
    ),
]