from django.conf import settings
from django.db import models


class TravelOrder(models.Model):
    """旅行命令"""

    STATUS_CHOICES = [
        ("draft", "下書き"),
        ("circulating", "回覧中"),
        ("approved", "校長承認済"),
        ("returned", "差戻し"),
        ("cancelled", "取消"),
    ]

    DEPARTURE_CHOICES = [
        ("school", "学校"),
        ("home", "自宅"),
        ("other", "その他"),
    ]

    TRANSPORT_CHOICES = [
        ("private_car", "自家用車"),
        ("ride", "同乗"),
        ("school_car", "校用車"),
        ("microbus", "マイクロバス"),
        ("large_bus", "大型バス"),
        ("public", "公共交通機関"),
        ("other", "その他"),
    ]

    # ---------------------------------
    # 管理情報
    # ---------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_travel_orders",
        verbose_name="作成者",
    )

    responsible_teacher = models.ForeignKey(
        "publicity.Teacher",
        on_delete=models.PROTECT,
        related_name="responsible_travel_orders",
        verbose_name="責任者",
    )

    status = models.CharField(
        "状態",
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    # ---------------------------------
    # 出張基本情報
    # ---------------------------------
    destination_area = models.CharField(
        "用務地",
        max_length=200,
    )

    destination_name = models.CharField(
        "施設・会場名",
        max_length=200,
        blank=True,
    )

    purpose = models.TextField(
        "用務",
    )

    start_datetime = models.DateTimeField(
        "出張開始日時",
    )

    end_datetime = models.DateTimeField(
        "出張終了日時",
    )

    # ---------------------------------
    # 移動
    # ---------------------------------
    departure_place = models.CharField(
        "出発地",
        max_length=20,
        choices=DEPARTURE_CHOICES,
        default="school",
    )

    departure_place_other = models.CharField(
        "その他の出発地",
        max_length=200,
        blank=True,
    )

    transportation = models.CharField(
        "交通手段",
        max_length=30,
        choices=TRANSPORT_CHOICES,
    )

    transportation_other = models.CharField(
        "その他の交通手段",
        max_length=200,
        blank=True,
    )

    # ---------------------------------
    # 旅費・道路関係
    # ---------------------------------
    separate_travel_expense = models.BooleanField(
        "旅費別途支給",
        default=False,
    )

    use_toll_road = models.BooleanField(
        "有料道路使用希望",
        default=False,
    )

    use_etc = models.BooleanField(
        "ETC使用希望",
        default=False,
    )

    # ---------------------------------
    # 休日・振替
    # ---------------------------------
    is_holiday_trip = models.BooleanField(
        "休業日の出張",
        default=False,
    )

    take_substitute_holiday = models.BooleanField(
        "振替休日を取得する",
        default=False,
    )

    substitute_holiday_date = models.DateField(
        "振替休日取得予定日",
        null=True,
        blank=True,
    )

    no_substitute_holiday_reason = models.TextField(
        "振替休日を取得しない理由",
        blank=True,
    )

    # ---------------------------------
    # その他
    # ---------------------------------
    notes = models.TextField(
        "備考",
        blank=True,
    )

    # ---------------------------------
    # 日時管理
    # ---------------------------------
    submitted_at = models.DateTimeField(
        "回覧申請日時",
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        "校長承認日時",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "作成日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "旅行命令"
        verbose_name_plural = "旅行命令"
        ordering = ["-start_datetime", "-created_at"]

    def __str__(self):
        return (
            f"{self.start_datetime:%Y/%m/%d} "
            f"{self.responsible_teacher.name} "
            f"{self.destination_area}"
        )


class TravelCompanion(models.Model):
    """旅行命令の同行教職員"""

    travel_order = models.ForeignKey(
        TravelOrder,
        on_delete=models.CASCADE,
        related_name="companions",
        verbose_name="旅行命令",
    )

    teacher = models.ForeignKey(
        "publicity.Teacher",
        on_delete=models.PROTECT,
        related_name="travel_companions",
        verbose_name="同行者",
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "旅行同行者"
        verbose_name_plural = "旅行同行者"
        constraints = [
            models.UniqueConstraint(
                fields=["travel_order", "teacher"],
                name="unique_travel_order_companion",
            )
        ]

    def __str__(self):
        return f"{self.travel_order} / {self.teacher}"


class TravelClassAdjustment(models.Model):
    """出張に伴う授業処置"""

    travel_order = models.ForeignKey(
        TravelOrder,
        on_delete=models.CASCADE,
        related_name="class_adjustments",
        verbose_name="旅行命令",
    )

    date = models.DateField(
        "月日",
    )

    period = models.PositiveSmallIntegerField(
        "校時",
    )

    department = models.CharField(
        "科",
        max_length=100,
        blank=True,
    )

    grade = models.PositiveSmallIntegerField(
        "学年",
        null=True,
        blank=True,
    )

    class_name = models.CharField(
        "組",
        max_length=50,
        blank=True,
    )

    subject = models.CharField(
        "科目",
        max_length=100,
        blank=True,
    )

    substitute_teacher = models.CharField(
        "代行",
        max_length=100,
        blank=True,
    )

    class Meta:
        verbose_name = "旅行命令 授業処置"
        verbose_name_plural = "旅行命令 授業処置"
        ordering = ["date", "period"]

    def __str__(self):
        return f"{self.date} {self.period}校時 {self.subject}"


class TravelAttachment(models.Model):
    """旅行命令に添付する案内・要項等"""

    travel_order = models.ForeignKey(
        TravelOrder,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="旅行命令",
    )

    file = models.FileField(
        "添付ファイル",
        upload_to="travel_orders/%Y/%m/",
    )

    original_name = models.CharField(
        "元ファイル名",
        max_length=255,
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="travel_attachments",
        verbose_name="登録者",
    )

    uploaded_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "旅行命令 添付資料"
        verbose_name_plural = "旅行命令 添付資料"

    def __str__(self):
        return self.original_name or self.file.name

class TravelApprovalStep(models.Model):
    """
    旅行命令1件ごとの回覧・承認者。

    回覧開始時に、その時点の承認ルートを
    TravelOrderごとに保存する。
    """

    STATUS_CHOICES = [
        ("waiting", "待機中"),
        ("pending", "確認待ち"),
        ("approved", "承認済"),
        ("returned", "差戻し"),
    ]

    travel_order = models.ForeignKey(
        TravelOrder,
        on_delete=models.CASCADE,
        related_name="approval_steps",
        verbose_name="旅行命令",
    )

    approver = models.ForeignKey(
        "publicity.Teacher",
        on_delete=models.PROTECT,
        related_name="travel_approval_steps",
        verbose_name="承認者",
    )

    step_order = models.PositiveSmallIntegerField(
        "回覧順",
    )

    status = models.CharField(
        "状態",
        max_length=20,
        choices=STATUS_CHOICES,
        default="waiting",
    )

    approved_at = models.DateTimeField(
        "承認日時",
        null=True,
        blank=True,
    )

    returned_at = models.DateTimeField(
        "差戻し日時",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "作成日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "旅行命令 回覧者"
        verbose_name_plural = "旅行命令 回覧者"

        ordering = [
            "travel_order",
            "step_order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "travel_order",
                    "step_order",
                ],
                name="unique_travel_approval_step_order",
            ),
            models.UniqueConstraint(
                fields=[
                    "travel_order",
                    "approver",
                ],
                name="unique_travel_approval_approver",
            ),
        ]

    def __str__(self):
        return (
            f"{self.travel_order} / "
            f"{self.step_order} / "
            f"{self.approver.name}"
        )


class TravelApprovalHistory(models.Model):
    """
    旅行命令の回覧履歴。

    申請・承認・差戻し・再申請を
    削除せず時系列で保存する。
    """

    ACTION_CHOICES = [
        ("submitted", "申請"),
        ("approved", "承認"),
        ("returned", "差戻し"),
        ("resubmitted", "再申請"),
        ("cancelled", "取消"),
    ]

    travel_order = models.ForeignKey(
        TravelOrder,
        on_delete=models.CASCADE,
        related_name="approval_histories",
        verbose_name="旅行命令",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="travel_approval_histories",
        verbose_name="操作ユーザー",
    )

    actor_teacher = models.ForeignKey(
        "publicity.Teacher",
        on_delete=models.PROTECT,
        related_name="travel_approval_histories",
        verbose_name="操作教員",
        null=True,
        blank=True,
    )

    action = models.CharField(
        "操作",
        max_length=20,
        choices=ACTION_CHOICES,
    )

    step_order = models.PositiveSmallIntegerField(
        "回覧順",
        null=True,
        blank=True,
    )

    comment = models.TextField(
        "コメント・差戻し理由",
        blank=True,
    )

    created_at = models.DateTimeField(
        "操作日時",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "旅行命令 回覧履歴"
        verbose_name_plural = "旅行命令 回覧履歴"

        ordering = [
            "created_at",
            "id",
        ]

    def __str__(self):
        return (
            f"{self.travel_order} / "
            f"{self.get_action_display()} / "
            f"{self.created_at:%Y/%m/%d %H:%M}"
        )