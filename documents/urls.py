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

    path(
        "travel/approval/",
        views.travel_approval_list,
        name="travel_approval_list",
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
        "travel/<int:pk>/review/",
        views.travel_order_review,
        name="travel_order_review",
    ),

    # 復命書の統合一覧
    path(
        "post-reports/",
        views.travel_post_report_list,
        name="travel_post_report_list",
    ),

    # 出張後報告（復命書・行程旅費報告）の作成・編集
    path(
        "travel/<int:pk>/post-report/",
        views.travel_post_report_edit,
        name="travel_post_report_edit",
    ),

    path(
        "travel/<int:pk>/post-report/review/",
        views.travel_post_report_review,
        name="travel_post_report_review",
    ),
    path(
        "travel/<int:pk>/post-report/review/action/",
        views.travel_post_report_review_action,
        name="travel_post_report_review_action",
    ),

    path(
        "travel/<int:pk>/post-report/submit/",
        views.travel_post_report_submit,
        name="travel_post_report_submit",
    ),

    path(
        "travel/<int:pk>/post-report/attachment/<int:attachment_id>/open/",
        views.travel_post_report_attachment_open,
        name="travel_post_report_attachment_open",
    ),
    path(
        "travel/<int:pk>/post-report/attachment/<int:attachment_id>/delete/",
        views.travel_post_report_attachment_delete,
        name="travel_post_report_attachment_delete",
    ),

    path(
        "travel/<int:pk>/submit/",
        views.travel_order_submit,
        name="travel_order_submit",
    ),
    path(
        'travel/<int:pk>/expense/',
        views.travel_expense_settlement,
        name='travel_expense_settlement',
    ),
    path(
        'travel/<int:pk>/expense/action/',
        views.travel_expense_settlement_action,
        name='travel_expense_settlement_action',
    ),
]