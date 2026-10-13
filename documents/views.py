from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .services.travel_notifications import queue_travel_notification

from .forms import (
    TravelAttachmentForm,
    TravelClassAdjustmentForm,
    TravelOrderForm,
)
from publicity.models import Teacher

from .models import (
    TravelApprovalHistory,
    TravelApprovalStep,
    TravelAttachment,
    TravelClassAdjustment,
    TravelCompanion,
    TravelOrder,
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
