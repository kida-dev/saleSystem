from django.contrib.auth.decorators import login_required
from django.db import transaction
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.http import FileResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .services.travel_notifications import queue_travel_notification
from .services.post_report_notifications import queue_post_report_notification

from .forms import (
    TravelAttachmentForm,
    TravelClassAdjustmentForm,
    TravelOrderForm,
    TravelPostReportForm,
    TravelPostReportAttachmentForm,
)
from publicity.models import Teacher

from .models import (
    TravelApprovalHistory,
    TravelApprovalStep,
    TravelAttachment,
    TravelClassAdjustment,
    TravelCompanion,
    TravelOrder,
    TravelPostReport,
    TravelPostReportApprovalStep,
    TravelPostReportOfficeCheck,
    TravelPostReportHistory,
    TravelPostReportAttachment,
    TravelExpenseSettlement, TravelExpenseItem, TravelExpenseHistory,
)


@login_required
def documents_top(request):
    return render(
        request,
        "documents/documents_top.html",
    )

@login_required
def travel_approval_list(request):
    """
    旧承認一覧から統合画面へ転送
    """
    return redirect(
        "documents:travel_order_list"
    )

@login_required
def travel_order_list(request):
    """
    旅行命令の統合一覧

    ・自分の確認待ち
    ・自分の申請一覧
    ・申請の進捗状況
    ・管理者向け全教員の提出済み申請
    """
    from django.db.models import Q

    # ---------------------------------
    # ログイン教員
    # ---------------------------------
    try:
        teacher = request.user.publicity_teacher
        if not teacher.is_active:
            teacher = None
    except Teacher.DoesNotExist:
        teacher = None

    # ---------------------------------
    # 自分の確認待ち
    # ---------------------------------
    if teacher:
        pending_steps = list(
            TravelApprovalStep.objects
            .filter(
                approver=teacher,
                status="pending",
                travel_order__status="circulating",
            )
            .select_related(
                "travel_order",
                "travel_order__responsible_teacher",
            )
            .order_by(
                "travel_order__start_datetime",
                "step_order",
            )
        )
    else:
        pending_steps = []

    # ---------------------------------
    # 自分の申請一覧
    # ---------------------------------
    travel_orders = list(
        TravelOrder.objects
        .filter(
            Q(responsible_teacher__user=request.user)
            | Q(created_by=request.user)
        )
        .distinct()
        .select_related(
            "responsible_teacher",
            "created_by",
        )
        .prefetch_related(
            "companions__teacher",
            "approval_steps__approver",
        )
        .order_by("-start_datetime", "-pk")
    )

    status_counts = {
        "draft": 0,
        "circulating": 0,
        "returned": 0,
        "approved": 0,
        "cancelled": 0,
    }

    for order in travel_orders:

        status_counts[order.status] = (
            status_counts.get(order.status, 0) + 1
        )

        if order.status == "circulating":

            pending_step = next(
                (
                    step
                    for step in order.approval_steps.all()
                    if step.status == "pending"
                ),
                None,
            )

            if pending_step:
                order.progress_text = (
                    f"{pending_step.approver.name}の確認待ち"
                )
            else:
                order.progress_text = (
                    "回覧状況を確認してください"
                )

        elif order.status == "approved":
            order.progress_text = "全員承認完了"

        elif order.status == "returned":
            order.progress_text = (
                "差戻し：修正・再申請待ち"
            )

        elif order.status == "draft":
            order.progress_text = "未申請"

        else:
            order.progress_text = "取消済み"

    # 管理者は提出済みの全教員の旅行命令を確認可能
    is_admin = request.user.is_superuser or bool(
        teacher and teacher.role == "system_admin"
    )
    all_travel_orders = []
    if is_admin:
        all_travel_orders = list(
            TravelOrder.objects
            .exclude(status="draft")
            .select_related("responsible_teacher", "created_by")
            .prefetch_related("approval_steps__approver")
            .order_by("-start_datetime", "-pk")
        )
        for order in all_travel_orders:
            if order.status == "circulating":
                pending_step = next(
                    (step for step in order.approval_steps.all()
                     if step.status == "pending"),
                    None,
                )
                order.progress_text = (
                    f"{pending_step.approver.name}の確認待ち"
                    if pending_step else "回覧状況を確認してください"
                )
            elif order.status == "approved":
                order.progress_text = "全員承認完了"
            elif order.status == "returned":
                order.progress_text = "差戻し：修正・再申請待ち"
            else:
                order.progress_text = "取消済み"

    return render(
        request,
        "documents/travel_order_list.html",
        {
            "teacher": teacher,
            "pending_steps": pending_steps,
            "travel_orders": travel_orders,
            "status_counts": status_counts,
            "is_admin": is_admin,
            "all_travel_orders": all_travel_orders,
        },
    )

@login_required
def travel_order_create(request):
    # ログインユーザーに紐づくTeacherを取得
    try:
        teacher = request.user.publicity_teacher
    except Exception:
        teacher = None

    # Teacherが登録されていない場合
    if teacher is None:
        return render(
            request,
            "documents/travel_order_form.html",
            {
                "form": None,
                "teacher_error": (
                    "ログインユーザーに教員情報が"
                    "登録されていません。"
                ),
            },
        )

    if request.method == "POST":
        form = TravelOrderForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            # TravelOrderと同行者を一括で保存
            with transaction.atomic():
                travel_order = form.save(
                    commit=False
                )

                travel_order.created_by = (
                    request.user
                )

                travel_order.responsible_teacher = (
                    teacher
                )

                travel_order.status = "draft"

                travel_order.save()

                # 同行者を保存
                companions = form.get_companions()

                for companion_teacher in companions:
                    TravelCompanion.objects.create(
                        travel_order=travel_order,
                        teacher=companion_teacher,
                    )

            return redirect(
                "documents:travel_order_detail",
                pk=travel_order.pk,
            )

    else:
        form = TravelOrderForm(
            user=request.user,
        )

    return render(
        request,
        "documents/travel_order_form.html",
        {
            "form": form,
            "teacher": teacher,
        },
    )


@login_required
def travel_order_detail(request, pk):
    travel_order = get_object_or_404(
        TravelOrder.objects
        .select_related(
            "responsible_teacher",
            "created_by",
        )
        .prefetch_related(
            "companions",
            "class_adjustments",
            "attachments",
            "approval_steps__approver",
            "approval_histories__actor_teacher",
        ),
        pk=pk,
    )

    try:
        teacher = request.user.publicity_teacher
    except Teacher.DoesNotExist:
        teacher = None

    is_owner = (
        travel_order.created_by_id == request.user.id
        or travel_order.responsible_teacher.user_id == request.user.id
    )
    is_reviewer = bool(teacher and travel_order.approval_steps.filter(approver=teacher).exists())
    is_admin = request.user.is_superuser or bool(
        teacher and teacher.is_active and teacher.role == "system_admin"
    )
    if not (is_owner or is_reviewer or is_admin):
        return HttpResponseForbidden("この旅行命令を閲覧する権限がありません。")

    pending_step = None
    if teacher and teacher.is_active and travel_order.status == "circulating":
        pending_step = travel_order.approval_steps.filter(
            approver=teacher, status="pending"
        ).first()

    return render(
        request,
        "documents/travel_order_detail.html",
        {
            "travel_order": travel_order,
            "can_approve": pending_step is not None,
            "approval_histories": travel_order.approval_histories.all(),
        },
    )

@login_required
def travel_class_adjustment_create(request, pk):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related(
            "responsible_teacher",
            "created_by",
        ),
        pk=pk,
    )

    # 下書き・差戻し状態だけ編集可能
    if travel_order.status not in [
        "draft",
        "returned",
    ]:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # 責任者本人または作成者だけ操作可能
    is_responsible = (
        travel_order.responsible_teacher.user_id
        == request.user.id
    )

    is_creator = (
        travel_order.created_by_id
        == request.user.id
    )

    if not is_responsible and not is_creator:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    if request.method == "POST":
        form = TravelClassAdjustmentForm(
            request.POST
        )

        if form.is_valid():
            adjustment = form.save(
                commit=False
            )

            adjustment.travel_order = (
                travel_order
            )

            adjustment.save()

            return redirect(
                "documents:travel_order_detail",
                pk=travel_order.pk,
            )

    else:
        form = TravelClassAdjustmentForm(
            initial={
                "date": (
                    travel_order
                    .start_datetime
                    .date()
                )
            }
        )

    return render(
        request,
        "documents/travel_class_adjustment_form.html",
        {
            "form": form,
            "travel_order": travel_order,
        },
    )

@login_required
def travel_class_adjustment_edit(request, pk, adjustment_id):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related(
            "responsible_teacher",
            "created_by",
        ),
        pk=pk,
    )

    adjustment = get_object_or_404(
        TravelClassAdjustment,
        pk=adjustment_id,
        travel_order=travel_order,
    )

    # 下書き・差戻し状態だけ編集可能
    if travel_order.status not in [
        "draft",
        "returned",
    ]:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # 責任者本人または作成者だけ操作可能
    is_responsible = (
        travel_order.responsible_teacher.user_id
        == request.user.id
    )

    is_creator = (
        travel_order.created_by_id
        == request.user.id
    )

    if not is_responsible and not is_creator:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    if request.method == "POST":
        form = TravelClassAdjustmentForm(
            request.POST,
            instance=adjustment,
        )

        if form.is_valid():
            form.save()

            return redirect(
                "documents:travel_order_detail",
                pk=travel_order.pk,
            )

    else:
        form = TravelClassAdjustmentForm(
            instance=adjustment,
        )

    return render(
        request,
        "documents/travel_class_adjustment_form.html",
        {
            "form": form,
            "travel_order": travel_order,
            "adjustment": adjustment,
            "is_edit": True,
        },
    )


@login_required
def travel_class_adjustment_delete(
    request,
    pk,
    adjustment_id,
):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related(
            "responsible_teacher",
            "created_by",
        ),
        pk=pk,
    )

    adjustment = get_object_or_404(
        TravelClassAdjustment,
        pk=adjustment_id,
        travel_order=travel_order,
    )

    # 下書き・差戻し状態だけ削除可能
    if travel_order.status not in [
        "draft",
        "returned",
    ]:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # 責任者本人または作成者だけ操作可能
    is_responsible = (
        travel_order.responsible_teacher.user_id
        == request.user.id
    )

    is_creator = (
        travel_order.created_by_id
        == request.user.id
    )

    if not is_responsible and not is_creator:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # GETでは削除しない
    if request.method == "POST":
        adjustment.delete()

    return redirect(
        "documents:travel_order_detail",
        pk=travel_order.pk,
    )

@login_required
def travel_attachment_create(request, pk):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related(
            "responsible_teacher",
            "created_by",
        ),
        pk=pk,
    )

    # 下書き・差戻しだけ添付可能
    if travel_order.status not in [
        "draft",
        "returned",
    ]:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # 責任者または作成者のみ
    is_responsible = (
        travel_order.responsible_teacher.user_id
        == request.user.id
    )

    is_creator = (
        travel_order.created_by_id
        == request.user.id
    )

    if not is_responsible and not is_creator:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    if request.method == "POST":
        form = TravelAttachmentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            attachment = form.save(
                commit=False
            )

            attachment.travel_order = travel_order
            attachment.uploaded_by = request.user

            attachment.original_name = (
                request.FILES["file"].name
            )

            attachment.save()

            return redirect(
                "documents:travel_order_detail",
                pk=travel_order.pk,
            )

    else:
        form = TravelAttachmentForm()

    return render(
        request,
        "documents/travel_attachment_form.html",
        {
            "form": form,
            "travel_order": travel_order,
        },
    )

@login_required
def travel_attachment_open(
    request,
    pk,
    attachment_id,
):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related(
            "responsible_teacher",
            "created_by",
        ),
        pk=pk,
    )

    attachment = get_object_or_404(
        TravelAttachment,
        pk=attachment_id,
        travel_order=travel_order,
    )

    # -----------------------------------------
    # 閲覧権限
    # -----------------------------------------

    is_responsible = (
        travel_order.responsible_teacher.user_id
        == request.user.id
    )

    is_creator = (
        travel_order.created_by_id
        == request.user.id
    )

    # 回覧者として登録されているか
    is_approver = (
        travel_order.approval_steps
        .filter(approver__user=request.user)
        .exists()
    )

    # システム管理者か
    try:
        teacher = request.user.publicity_teacher

        is_system_admin = (
            teacher.is_active
            and teacher.role == "system_admin"
        )

    except Teacher.DoesNotExist:
        is_system_admin = False

    if not (
        is_responsible
        or is_creator
        or is_approver
        or is_system_admin
        or request.user.is_superuser
    ):
        return redirect(
            "documents:travel_order_list"
        )

    # -----------------------------------------
    # 非公開ストレージからファイルを取得
    # -----------------------------------------

    import mimetypes
    import os

    # アップロード時の元ファイル名を取得
    filename = attachment.original_name

    # ファイル名が取得できない場合は保存名を使用
    if not filename:
        filename = os.path.basename(attachment.file.name)

    # ファイルの種類を判定
    content_type, _ = mimetypes.guess_type(filename)

    if not content_type:
        content_type = "application/octet-stream"

    # ファイルを開く
    file_handle = attachment.file.open("rb")

    # 元のファイル名でダウンロード
    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )

    return response

@login_required
def travel_attachment_delete(
    request,
    pk,
    attachment_id,
):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related(
            "responsible_teacher",
            "created_by",
        ),
        pk=pk,
    )

    attachment = get_object_or_404(
        TravelAttachment,
        pk=attachment_id,
        travel_order=travel_order,
    )

    # 下書き・差戻しだけ削除可能
    if travel_order.status not in [
        "draft",
        "returned",
    ]:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    is_responsible = (
        travel_order.responsible_teacher.user_id
        == request.user.id
    )

    is_creator = (
        travel_order.created_by_id
        == request.user.id
    )

    if not is_responsible and not is_creator:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    if request.method == "POST":

        # DBレコードだけでなく実ファイルも削除
        attachment.file.delete(
            save=False
        )

        attachment.delete()

    return redirect(
        "documents:travel_order_detail",
        pk=travel_order.pk,
    )

@login_required
def travel_order_submit(request, pk):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related(
            "responsible_teacher",
            "created_by",
        ),
        pk=pk,
    )

    # GETでは申請処理を行わない
    if request.method != "POST":
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # 下書き・差戻しのみ申請可能
    if travel_order.status not in [
        "draft",
        "returned",
    ]:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # 責任者または作成者だけ申請可能
    is_responsible = (
        travel_order.responsible_teacher.user_id
        == request.user.id
    )

    is_creator = (
        travel_order.created_by_id
        == request.user.id
    )

    if not is_responsible and not is_creator:
        return redirect(
            "documents:travel_order_detail",
            pk=travel_order.pk,
        )

    # -----------------------------------------
    # 回覧ルート
    # -----------------------------------------
    approval_route = [
        6,  # 黒仁田先生
        5,  # 二原さん（事務次長）
        4,  # 宮路事務長 ← 追加
        3,  # 落合教頭
        2,  # 川崎教頭
        1,  # 竹元校長
    ]

    approvers = {}

    for employee_number in approval_route:
        try:
            approvers[employee_number] = (
                Teacher.objects.get(
                    employee_number=employee_number,
                    is_active=True,
                )
            )

        except Teacher.DoesNotExist:
            # 回覧者が見つからない場合は
            # 中途半端に回覧開始しない
            return redirect(
                "documents:travel_order_detail",
                pk=travel_order.pk,
            )

    # 差戻しからの再申請かどうか
    is_resubmission = (
        travel_order.status == "returned"
    )

    # -----------------------------------------
    # ここから一括処理
    # -----------------------------------------
    with transaction.atomic():

        # 再申請の場合もルートを最初から作り直す
        travel_order.approval_steps.all().delete()

        for step_order, employee_number in enumerate(
            approval_route,
            start=1,
        ):
            approver = approvers[employee_number]

            TravelApprovalStep.objects.create(
                travel_order=travel_order,
                approver=approver,
                step_order=step_order,
                status=(
                    "pending"
                    if step_order == 1
                    else "waiting"
                ),
            )

        # 旅行命令本体を回覧中へ
        travel_order.status = "circulating"
        travel_order.submitted_at = timezone.now()

        # 差戻し後の再申請の場合、
        # 過去の校長承認日時が残らないようにする
        travel_order.approved_at = None

        travel_order.save(
            update_fields=[
                "status",
                "submitted_at",
                "approved_at",
                "updated_at",
            ]
        )

        # 操作者のTeacherを取得
        try:
            actor_teacher = (
                request.user.publicity_teacher
            )
        except Teacher.DoesNotExist:
            actor_teacher = None

        # 履歴を追加
        TravelApprovalHistory.objects.create(
            travel_order=travel_order,
            actor=request.user,
            actor_teacher=actor_teacher,
            action=(
                "resubmitted"
                if is_resubmission
                else "submitted"
            ),
            comment="",
        )

        # DB確定後に最初の承認者へ通知（失敗しても申請は維持）。
        queue_travel_notification(
            travel_order=travel_order,
            notification_type="review_request",
            recipient_teacher=approvers[approval_route[0]],
            detail_url=request.build_absolute_uri(
                redirect("documents:travel_order_detail", pk=travel_order.pk).url
            ),
        )

    return redirect(
        "documents:travel_order_detail",
        pk=travel_order.pk,
    )

@login_required
@require_POST
def travel_order_review(request, pk):
    action = request.POST.get("action")
    comment = request.POST.get("comment", "").strip()
    if action not in ("approved", "returned"):
        return HttpResponseForbidden("操作が不正です。")
    if action == "returned" and not comment:
        return HttpResponseForbidden("差戻し理由を入力してください。")
    if len(comment) > 2000:
        return HttpResponseForbidden("コメントは2000文字以内にしてください。")

    try:
        teacher = request.user.publicity_teacher
    except Teacher.DoesNotExist:
        return HttpResponseForbidden("教員情報がありません。")
    if not teacher.is_active:
        return HttpResponseForbidden("在籍中の教員のみ操作できます。")

    with transaction.atomic():
        order = get_object_or_404(
            TravelOrder.objects.select_for_update(), pk=pk
        )
        if order.status != "circulating":
            return HttpResponseForbidden("現在は承認できない状態です。")
        step = order.approval_steps.select_for_update().filter(
            approver=teacher, status="pending"
        ).first()
        if step is None:
            return HttpResponseForbidden("現在の承認担当者ではありません。")
        now = timezone.now()
        if action == "approved":
            step.status = "approved"
            step.approved_at = now
            step.save(update_fields=["status", "approved_at", "updated_at"])
            next_step = order.approval_steps.filter(
                step_order__gt=step.step_order
            ).order_by("step_order").first()
            if next_step:
                if next_step.status != "waiting":
                    return HttpResponseForbidden("回覧状態が不正です。")
                next_step.status = "pending"
                next_step.save(update_fields=["status", "updated_at"])
            else:
                order.status = "approved"
                order.approved_at = now
                order.save(update_fields=["status", "approved_at", "updated_at"])
        else:
            step.status = "returned"
            step.returned_at = now
            step.save(update_fields=["status", "returned_at", "updated_at"])
            order.status = "returned"
            order.save(update_fields=["status", "updated_at"])

        TravelApprovalHistory.objects.create(
            travel_order=order,
            actor=request.user,
            actor_teacher=teacher,
            action=action,
            step_order=step.step_order,
            comment=comment,
        )

        # 送信処理はコミット後。承認処理とは独立させる。
        if action == "returned":
            recipient = order.responsible_teacher
            notification_type = "returned"
        elif next_step:
            recipient = next_step.approver
            notification_type = "review_request"
        else:
            recipient = order.responsible_teacher
            notification_type = "completed"

        queue_travel_notification(
            travel_order=order,
            notification_type=notification_type,
            recipient_teacher=recipient,
            detail_url=request.build_absolute_uri(
                redirect("documents:travel_order_detail", pk=order.pk).url
            ),
            comment=comment if action == "returned" else "",
        )
    return redirect("documents:travel_order_detail", pk=pk)


# ============================================================
# 出張後報告：承認済み旅行命令から作成・下書き保存
# ============================================================
@login_required
def travel_post_report_edit(request, pk):
    travel_order = get_object_or_404(
        TravelOrder.objects.select_related("responsible_teacher", "created_by"),
        pk=pk,
    )

    # 旅行命令の承認完了後のみ作成可能
    if travel_order.status != "approved":
        return HttpResponseForbidden("旅行命令の承認完了後に作成できます。")

    # 報告は出張者本人が作成する（管理職による代理提出は別途検討）
    if travel_order.responsible_teacher.user_id != request.user.pk:
        return HttpResponseForbidden("出張者本人のみ作成できます。")

    report, _ = TravelPostReport.objects.get_or_create(travel_order=travel_order)
    if report.status not in ("draft", "returned"):
        return HttpResponseForbidden("回覧中・承認済みの報告は編集できません。")

    if request.method == "POST":
        form = TravelPostReportForm(request.POST, instance=report)
        # 複数ファイルを個別に検証。エラーがあれば報告書も保存しない。
        uploads = request.FILES.getlist("attachments")
        upload_errors = []
        validated_uploads = []
        if len(uploads) > 10:
            upload_errors.append("一度に添付できるファイルは10件までです。")
        for upload in uploads[:10]:
            attachment_form = TravelPostReportAttachmentForm(files={"file": upload})
            if not attachment_form.is_valid():
                upload_errors.extend(
                    str(error) for errors in attachment_form.errors.values() for error in errors
                )
            else:
                validated_uploads.append(upload)
        if form.is_valid() and not upload_errors:
            with transaction.atomic():
                form.save()
                for upload in validated_uploads:
                    TravelPostReportAttachment.objects.create(
                        report=report,
                        file=upload,
                        original_name=upload.name[:255],
                        uploaded_by=request.user,
                    )
            return redirect("documents:travel_post_report_edit", pk=travel_order.pk)
    else:
        form = TravelPostReportForm(instance=report)
        upload_errors = []

    return render(
        request,
        "documents/travel_post_report_form.html",
        {
            "travel_order": travel_order,
            "report": report,
            "form": form,
            "upload_errors": upload_errors,
            "attachments": report.attachments.order_by("-uploaded_at"),
        },
    )


@login_required
def travel_post_report_attachment_open(request, pk, attachment_id):
    order = get_object_or_404(TravelOrder.objects.select_related("responsible_teacher", "created_by"), pk=pk)
    report = get_object_or_404(TravelPostReport, travel_order=order)
    attachment = get_object_or_404(TravelPostReportAttachment, pk=attachment_id, report=report)
    teacher = Teacher.objects.filter(user=request.user, is_active=True).first()
    is_owner = (order.created_by_id == request.user.pk or order.responsible_teacher.user_id == request.user.pk)
    is_reviewer = bool(teacher and (order.approval_steps.filter(approver=teacher).exists() or report.approval_steps.filter(approver=teacher).exists() or report.office_checks.filter(checker=teacher).exists()))
    is_admin = request.user.is_superuser or bool(teacher and teacher.role == "system_admin")
    if not (is_owner or is_reviewer or is_admin):
        return HttpResponseForbidden("添付ファイルを閲覧する権限がありません。")
    import mimetypes
    import os
    from django.utils.text import get_valid_filename
    mime = mimetypes.guess_type(attachment.original_name or attachment.file.name)[0] or "application/octet-stream"
    if mime not in ("application/pdf", "image/jpeg", "image/png"):
        mime = "application/octet-stream"
    response = FileResponse(attachment.file.open("rb"), content_type=mime, as_attachment=True, filename=get_valid_filename(os.path.basename(attachment.original_name or attachment.file.name)))
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def travel_post_report_attachment_delete(request, pk, attachment_id):
    order = get_object_or_404(TravelOrder.objects.select_related("responsible_teacher"), pk=pk)
    if order.responsible_teacher.user_id != request.user.pk:
        return HttpResponseForbidden("出張者本人のみ削除できます。")
    report = get_object_or_404(TravelPostReport, travel_order=order)
    if report.status not in ("draft", "returned"):
        return HttpResponseForbidden("回覧中・承認済みの添付資料は削除できません。")
    attachment = get_object_or_404(TravelPostReportAttachment, pk=attachment_id, report=report)
    # DBから先に削除。クラウド上の実ファイルは保存先の運用ポリシーに従い保持。
    attachment.delete()
    return redirect("documents:travel_post_report_edit", pk=pk)


# 出張後報告の回覧開始：事務次長 → 事務長 → 教頭 → 教頭 → 校長
@login_required
@require_POST
def travel_post_report_submit(request, pk):
    order = get_object_or_404(
        TravelOrder.objects.select_related("responsible_teacher"), pk=pk
    )
    if order.status != "approved" or order.responsible_teacher.user_id != request.user.pk:
        return HttpResponseForbidden("この報告書を提出する権限がありません。")
    if request.POST.get("submission_agreement") != "yes":
        return HttpResponseForbidden("内容確認と提出への同意が必要です。")

    # 既存の旅行命令と同じ職員番号を使用する。氏名の取り違えを防ぐため確認する。
    route = [(5, "office"), (4, "office"), (3, "management"),
             (2, "management"), (1, "management")]
    teachers = list(Teacher.objects.filter(
        employee_number__in=[number for number, _ in route], is_active=True
    ))
    by_number = {teacher.employee_number: teacher for teacher in teachers}
    if len(by_number) != 5:
        return HttpResponseForbidden("回覧者5名の教員登録を確認してください。")

    with transaction.atomic():
        report = get_object_or_404(
            TravelPostReport.objects.select_for_update(), travel_order=order
        )
        if report.status not in ("draft", "returned"):
            return HttpResponseForbidden("この報告書はすでに回覧中、または承認済みです。")
        if not (report.report_content or "").strip():
            return HttpResponseForbidden("復命事項を入力して下書き保存してから提出してください。")
        # 往路・復路の距離は提出時に必須
        # 0kmは有効な入力として扱う
        if (
            report.outbound_distance_km is None
            or report.inbound_distance_km is None
        ):
            return HttpResponseForbidden(
                "往路・復路の距離を入力してから提出してください。"
            )

        # マイナス値は禁止
        if (
            report.outbound_distance_km < 0
            or report.inbound_distance_km < 0
        ):
            return HttpResponseForbidden(
                "距離には0以上の数値を入力してください。"
            )
        # 前回の回覧記録は履歴に残し、承認ステップだけ再作成する。
        report.office_checks.all().delete()
        report.approval_steps.all().delete()
        for index, (number, kind) in enumerate(route, start=1):
            if kind == "office":
                TravelPostReportOfficeCheck.objects.create(
                    report=report, checker=by_number[number],
                    step_order=index, status="pending" if index == 1 else "waiting",
                )
            else:
                TravelPostReportApprovalStep.objects.create(
                    report=report, approver=by_number[number],
                    step_order=index, status="waiting",
                )
        report.status = "circulating"
        report.submitted_by = request.user
        report.submitted_at = timezone.now()
        report.approved_at = None
        # 再提出時は旧精算を未確定に戻す。旧明細は確認用に残し、再保存を必須とする。
        TravelExpenseSettlement.objects.filter(report=report).update(saved_at=None, finalized_at=None, finalized_by=None)
        report.accounting_finalized_at = None
        report.accounting_saved_at = None
        report.accounting_distance_km = None
        report.accounting_rate_yen = None
        report.accounting_allowance_yen = 0
        report.school_account_amount = 0
        report.extracurricular_amount = 0
        report.athletics_support_amount = 0
        report.external_travel_amount = 0
        report.save(update_fields=["status", "submitted_by", "submitted_at", "approved_at",
            "accounting_finalized_at", "accounting_saved_at", "accounting_distance_km",
            "accounting_rate_yen", "accounting_allowance_yen", "school_account_amount",
            "extracurricular_amount", "athletics_support_amount", "external_travel_amount", "updated_at"])
        TravelPostReportHistory.objects.create(
            report=report, actor=request.user,
            action="submitted", comment="本人確認・同意のうえ5段階回覧を開始",
        )
        queue_post_report_notification(
            report=report, notification_type="review_request",
            recipient_teacher=by_number[5],
        )
    return redirect("documents:travel_post_report_list")


# 出張後報告：事務2名→管理職3名の順次確認
@login_required
def travel_post_report_review(request, pk):
    order = get_object_or_404(TravelOrder.objects.select_related("responsible_teacher", "created_by"), pk=pk)
    report = get_object_or_404(TravelPostReport, travel_order=order)
    teacher = Teacher.objects.filter(user=request.user, is_active=True).first()
    office = list(report.office_checks.select_related("checker").order_by("step_order"))
    management = list(report.approval_steps.select_related("approver").order_by("step_order"))
    steps = sorted(
        [{"order": s.step_order, "name": s.checker.name, "status": s.status, "date": s.checked_at, "kind": "office"} for s in office]
        + [{"order": s.step_order, "name": s.approver.name, "status": s.status, "date": s.approved_at, "kind": "management"} for s in management],
        key=lambda item: item["order"],
    )
    owner = order.created_by_id == request.user.pk or order.responsible_teacher.user_id == request.user.pk
    reviewer = bool(teacher and any(s.checker_id == teacher.pk for s in office) or teacher and any(s.approver_id == teacher.pk for s in management))
    admin = request.user.is_superuser or bool(teacher and teacher.role == "system_admin")
    if not (owner or reviewer or admin):
        return HttpResponseForbidden("この報告書を閲覧する権限がありません。")
    can_review = bool(teacher and report.status == "circulating" and (
        any(s.checker_id == teacher.pk and s.status == "pending" for s in office)
        or any(s.approver_id == teacher.pk and s.status == "pending" for s in management)
    ))
    is_office_staff = bool(teacher and teacher.employee_number in (4, 5)
                           and any(s.checker_id == teacher.pk for s in office))
    # 事務長確認が終わると旅費は確定し、後続の管理職回覧では編集不可。
    can_edit_accounting = False
    return render(request, "documents/travel_post_report_review.html", {
        "travel_order": order, "report": report, "steps": steps,
        "attachments": report.attachments.order_by("uploaded_at"),
        "histories": report.histories.select_related("actor").order_by("created_at", "pk"),
        "can_review": can_review,
        "is_office_staff": is_office_staff,
        "can_edit_accounting": can_edit_accounting,
        "settlement_exists": TravelExpenseSettlement.objects.filter(report=report).exists() if is_office_staff else False,
    })


@login_required
@require_POST
def travel_post_report_review_action(request, pk):
    action = request.POST.get("action")
    comment = (request.POST.get("comment") or "").strip()
    if action not in ("approve", "return"):
        return HttpResponseForbidden("操作が正しくありません。")
    if action == "return" and not comment:
        return HttpResponseForbidden("差戻し理由を入力してください。")
    teacher = Teacher.objects.filter(user=request.user, is_active=True).first()
    if teacher is None:
        return HttpResponseForbidden("教員アカウントが必要です。")
    with transaction.atomic():
        report = get_object_or_404(TravelPostReport.objects.select_for_update(), travel_order_id=pk)
        if report.status != "circulating":
            return HttpResponseForbidden("回覧中の報告書ではありません。")
        office = list(report.office_checks.select_for_update().order_by("step_order"))
        management = list(report.approval_steps.select_for_update().order_by("step_order"))
        all_steps = sorted([(s.step_order, "office", s) for s in office] +
                           [(s.step_order, "management", s) for s in management], key=lambda x: x[0])
        if len(all_steps) != 5 or [s[0] for s in all_steps] != [1, 2, 3, 4, 5]:
            return HttpResponseForbidden("回覧順序に問題があります。")
        current = next(((i, kind, step) for i, (_, kind, step) in enumerate(all_steps) if step.status == "pending"), None)
        if current is None:
            return HttpResponseForbidden("確認待ちの担当者がいません。")
        index, kind, step = current
        assigned_id = step.checker_id if kind == "office" else step.approver_id
        if assigned_id != teacher.pk:
            return HttpResponseForbidden("現在の担当者のみ操作できます。")
        now = timezone.now()
        if action == "return":
            if kind == "office":
                # 事務確認モデルにはreturnedがないため、待機中に戻し報告書を差戻し状態にする。
                step.status = "waiting"
                step.save(update_fields=["status"])
            else:
                step.status = "returned"
                step.returned_at = now
                step.save(update_fields=["status", "returned_at"])
            report.status = "returned"
            report.save(update_fields=["status", "updated_at"])
            TravelPostReportHistory.objects.create(report=report, actor=request.user,
                action="returned", comment=f"{teacher.name}：{comment}")
        else:
            if kind == "office":
                settlement = TravelExpenseSettlement.objects.filter(report=report).first()
                if not settlement or settlement.saved_at is None or not settlement.source or not settlement.payment_date:
                    return HttpResponseForbidden("旅費精算ページで支出元・振込予定日・明細を保存してください。")
                if step.step_order == 2 and settlement.finalized_at is None:
                    return HttpResponseForbidden("事務長は旅費精算ページで会計確定してから承認してください。")

            if kind == "office":
                step.status = "checked"
                step.checked_at = now
                step.save(update_fields=["status", "checked_at"])
            else:
                step.status = "approved"
                step.approved_at = now
                step.save(update_fields=["status", "approved_at"])
            TravelPostReportHistory.objects.create(report=report, actor=request.user,
                action="office_checked" if kind == "office" else "approved",
                comment=comment)
            if index + 1 < len(all_steps):
                next_step = all_steps[index + 1][2]
                if next_step.status != "waiting":
                    return HttpResponseForbidden("次の承認者の状態が正しくありません。")
                next_step.status = "pending"
                next_step.save(update_fields=["status"])
            else:
                report.status = "approved"
                report.approved_at = now
                report.save(update_fields=["status", "approved_at", "updated_at"])
        # DBの確定後にメール送信。差戻し・承認操作はメール失敗の影響を受けない。
        if action == "return":
            recipient_teacher = report.travel_order.responsible_teacher
            notification_type = "returned"
        elif index + 1 < len(all_steps):
            next_kind = all_steps[index + 1][1]
            next_step = all_steps[index + 1][2]
            recipient_teacher = (
                next_step.checker if next_kind == "office" else next_step.approver
            )
            notification_type = "review_request"
        else:
            recipient_teacher = report.travel_order.responsible_teacher
            notification_type = "completed"
        queue_post_report_notification(
            report=report, notification_type=notification_type,
            recipient_teacher=recipient_teacher,
            comment=comment if action == "return" else "",
        )
    return redirect("documents:travel_post_report_review", pk=pk)


# ============================================================
# 復命書一覧：本人・現在の確認担当者・管理者
# ============================================================
@login_required
def travel_post_report_list(request):
    from django.db.models import Q

    teacher = Teacher.objects.filter(user=request.user, is_active=True).first()
    is_admin = request.user.is_superuser or bool(
        teacher and teacher.role == "system_admin"
    )

    base = (TravelPostReport.objects
            .select_related("travel_order", "travel_order__responsible_teacher",
                            "travel_order__created_by")
            .prefetch_related("office_checks__checker", "approval_steps__approver")
            .order_by("-travel_order__start_datetime", "-pk"))

    own_reports = list(base.filter(
        Q(travel_order__responsible_teacher__user=request.user)
        | Q(travel_order__created_by=request.user)
    ).distinct())

    if teacher:
        pending_reports = list(base.filter(status="circulating").filter(
            Q(office_checks__checker=teacher, office_checks__status="pending")
            | Q(approval_steps__approver=teacher, approval_steps__status="pending")
        ).distinct())
    else:
        pending_reports = []

    # 管理職・事務担当者は自分が回覧者となっている提出済み報告を参照できる。
    if is_admin:
        all_reports = list(base.exclude(status="draft"))
    elif teacher:
        all_reports = list(base.exclude(status="draft").filter(
            Q(office_checks__checker=teacher) | Q(approval_steps__approver=teacher)
        ).distinct())
    else:
        all_reports = []

    for report in own_reports + pending_reports + all_reports:
        report.progress_text = "未提出" if report.status == "draft" else (
            "差戻し・修正待ち" if report.status == "returned" else (
                "承認完了" if report.status == "approved" else "回覧状況を確認"
            )
        )
        if report.status == "circulating":
            for step in sorted(
                list(report.office_checks.all()) + list(report.approval_steps.all()),
                key=lambda item: item.step_order,
            ):
                if step.status == "pending":
                    person = getattr(step, "checker", None) or getattr(step, "approver", None)
                    report.progress_text = f"{person.name}の確認待ち"
                    break

    return render(request, "documents/travel_post_report_list.html", {
        "own_reports": own_reports,
        "pending_reports": pending_reports,
        "all_reports": all_reports,
        "is_admin": is_admin,
    })


# ============================================================
# 事務室専用・独立した旅費精算ページ
# ============================================================
def _expense_office_teacher(request, report):
    teacher = Teacher.objects.filter(user=request.user, is_active=True, employee_number__in=(4, 5)).first()
    if not teacher:
        return None
    if not report.office_checks.filter(checker=teacher).exists():
        return None
    return teacher


@login_required
def travel_expense_settlement(request, pk):
    report = get_object_or_404(TravelPostReport.objects.select_related("travel_order", "travel_order__responsible_teacher"), travel_order_id=pk)
    teacher = _expense_office_teacher(request, report)
    if teacher is None:
        return HttpResponseForbidden("事務室担当者のみ利用できます。")
    settlement = TravelExpenseSettlement.objects.filter(report=report).first()
    office_steps = list(report.office_checks.order_by("step_order"))
    active = next((x for x in office_steps if x.status == "pending"), None)
    can_edit = bool(report.status == "circulating" and active and active.checker_id == teacher.pk and not (settlement and settlement.finalized_at))
    can_change_date = bool(settlement and report.status == "approved" and teacher.employee_number in (4, 5))
    return render(request, "documents/travel_expense_settlement.html", {
        "report": report, "order": report.travel_order, "settlement": settlement,
        "items": settlement.items.all() if settlement else [],
        "sources": TravelExpenseSettlement.SOURCE_CHOICES,
        "categories": TravelExpenseItem.CATEGORY_CHOICES,
        "can_edit": can_edit, "can_finalize": bool(can_edit and teacher.employee_number == 4 and settlement and settlement.saved_at),
        "can_change_date": can_change_date,
        "histories": settlement.histories.select_related("actor")[:20] if settlement else [],
    })


@login_required
@require_POST
def travel_expense_settlement_action(request, pk):
    from datetime import date
    from django.core.exceptions import ValidationError
    from django.utils.dateparse import parse_date
    action = request.POST.get("action")
    if action not in ("save", "finalize", "change_date"):
        return HttpResponseBadRequest("不正な操作です。")
    with transaction.atomic():
        report = get_object_or_404(TravelPostReport.objects.select_for_update(), travel_order_id=pk)
        teacher = _expense_office_teacher(request, report)
        if not teacher:
            return HttpResponseForbidden("事務室担当者のみ操作できます。")
        settlement, _ = TravelExpenseSettlement.objects.select_for_update().get_or_create(report=report)
        active = report.office_checks.filter(status="pending", checker=teacher).exists()
        editable = report.status == "circulating" and active and settlement.finalized_at is None
        if action in ("save", "finalize") and not editable:
            return HttpResponseForbidden("現在の担当者のみ保存・確定できます。")
        if action == "change_date":
            if report.status != "approved" or settlement.finalized_at is None:
                return HttpResponseForbidden("最終承認後の確定済精算のみ日付変更できます。")
            value = parse_date(request.POST.get("payment_date", ""))
            if not value:
                return HttpResponseBadRequest("正しい振込予定日を入力してください。")
            old = settlement.payment_date
            settlement.payment_date = value
            settlement.save(update_fields=["payment_date"])
            TravelExpenseHistory.objects.create(settlement=settlement, actor=request.user, action="payment_date_changed", detail=f"振込予定日：{old} → {value}（通知は別途実施してください）")
            return redirect("documents:travel_expense_settlement", pk=pk)
        if action == "finalize":
            if teacher.employee_number != 4 or settlement.saved_at is None or not settlement.source or not settlement.payment_date:
                return HttpResponseForbidden("事務長のみ、保存済み精算を確定できます。")
            settlement.finalized_at = timezone.now()
            settlement.finalized_by = request.user
            settlement.save(update_fields=["finalized_at", "finalized_by"])
            report.accounting_finalized_at = settlement.finalized_at
            report.save(update_fields=["accounting_finalized_at", "updated_at"])
            TravelExpenseHistory.objects.create(settlement=settlement, actor=request.user, action="finalized", detail=f"会計確定：{settlement.total_yen}円")
            return redirect("documents:travel_expense_settlement", pk=pk)
        source = request.POST.get("source", "")
        source_other = request.POST.get("source_other", "").strip()[:200]
        if source not in dict(TravelExpenseSettlement.SOURCE_CHOICES) or (source == "other" and not source_other):
            return HttpResponseBadRequest("支出元を選択してください。その他は名称も必要です。")
        payment_date = parse_date(request.POST.get("payment_date", ""))
        if payment_date is None:
            return HttpResponseBadRequest("振込予定日を入力してください。")
        categories = request.POST.getlist("category")
        descriptions = request.POST.getlist("description")
        quantities = request.POST.getlist("quantity")
        prices = request.POST.getlist("unit_price")
        amounts = request.POST.getlist("amount_yen")
        count = len(categories)
        if not (1 <= count <= 40 and count == len(descriptions) == len(quantities) == len(prices) == len(amounts)):
            return HttpResponseBadRequest("明細は1〜40件で入力してください。")
        rows = []
        total = 0
        try:
            for i, (category, description, q, price, raw_amount) in enumerate(zip(categories, descriptions, quantities, prices, amounts), start=1):
                if category not in dict(TravelExpenseItem.CATEGORY_CHOICES) or len(description) > 200:
                    raise ValueError("項目が不正です")
                quantity = Decimal(q) if q.strip() else None
                unit_price = Decimal(price) if price.strip() else None
                for value, maximum in ((quantity, Decimal("9999999")), (unit_price, Decimal("99999999"))):
                    if value is not None and (not value.is_finite() or value < 0 or value > maximum or value.as_tuple().exponent < -2):
                        raise ValueError("数量・単価は0以上、小数点以下2桁までです")
                if quantity is not None and unit_price is not None:
                    amount = int((quantity * unit_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                else:
                    if not raw_amount.strip():
                        raise ValueError("数量・単価を省略する場合は金額を入力してください")
                    entered = Decimal(raw_amount)
                    if not entered.is_finite() or entered != entered.to_integral_value() or entered < 0:
                        raise ValueError("金額は0以上の整数で入力してください")
                    amount = int(entered)
                if amount > 2147483647:
                    raise ValueError("明細金額が大きすぎます")
                total += amount
                if total > 2147483647:
                    raise ValueError("合計が大きすぎます")
                rows.append(TravelExpenseItem(settlement=settlement, position=i, category=category, description=description.strip(), quantity=quantity, unit_price=unit_price, amount_yen=amount))
        except (ValueError, InvalidOperation, OverflowError) as exc:
            return HttpResponseBadRequest(f"明細の入力を確認してください：{exc}")
        old_total = settlement.total_yen
        settlement.source, settlement.source_other = source, source_other
        settlement.payment_date, settlement.total_yen = payment_date, total
        settlement.saved_at, settlement.saved_by = timezone.now(), request.user
        settlement.save()
        settlement.items.all().delete()
        TravelExpenseItem.objects.bulk_create(rows)
        # 旧表示との互換性を維持するが、計算の正本は精算モデルに置く。
        report.school_account_amount = total
        report.accounting_saved_at = settlement.saved_at
        report.save(update_fields=["school_account_amount", "accounting_saved_at", "updated_at"])
        TravelExpenseHistory.objects.create(settlement=settlement, actor=request.user, action="saved", detail=f"支出元：{settlement.get_source_display()}、金額：{old_total}円 → {total}円、明細{count}件")
    return redirect("documents:travel_expense_settlement", pk=pk)
