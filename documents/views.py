from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
    # -----------------------------------------
    # ログイン中の教員を取得
    # -----------------------------------------
    try:
        teacher = request.user.publicity_teacher

    except Teacher.DoesNotExist:
        teacher = None

    if teacher is None:
        return render(
            request,
            "documents/travel_approval_list.html",
            {
                "teacher_error": (
                    "ログインユーザーに教員情報が"
                    "登録されていません。"
                ),
                "pending_steps": [],
                "completed_steps": [],
            },
        )

    # -----------------------------------------
    # 自分が現在確認しなければならない文書
    # -----------------------------------------
    pending_steps = (
        TravelApprovalStep.objects
        .filter(
            approver=teacher,
            status="pending",
        )
        .select_related(
            "travel_order",
            "travel_order__responsible_teacher",
            "travel_order__created_by",
        )
        .order_by(
            "travel_order__start_datetime"
        )
    )

    # -----------------------------------------
    # 自分が既に処理した文書
    #
    # approved / returned の両方を残す
    # -----------------------------------------
    completed_steps = (
        TravelApprovalStep.objects
        .filter(
            approver=teacher,
            status__in=[
                "approved",
                "returned",
            ],
        )
        .select_related(
            "travel_order",
            "travel_order__responsible_teacher",
            "travel_order__created_by",
        )
        .order_by(
            "-updated_at"
        )
    )

    return render(
        request,
        "documents/travel_approval_list.html",
        {
            "teacher": teacher,
            "pending_steps": pending_steps,
            "completed_steps": completed_steps,
        },
    )

@login_required
def travel_order_list(request):
    travel_orders = (
        TravelOrder.objects
        .filter(responsible_teacher__user=request.user)
        .select_related(
            "responsible_teacher",
            "created_by",
        )
        .prefetch_related(
            "companions__teacher",
        )
        .order_by("-start_datetime")
    )

    return render(
        request,
        "documents/travel_order_list.html",
        {
            "travel_orders": travel_orders,
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

    return render(
        request,
        "documents/travel_order_detail.html",
        {
            "travel_order": travel_order,
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

    file_handle = attachment.file.open("rb")

    response = FileResponse(
        file_handle,
        content_type=(
            "application/octet-stream"
        ),
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="{attachment.original_name}"'
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
        5,  # 二原さん
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

    return redirect(
        "documents:travel_order_detail",
        pk=travel_order.pk,
    )