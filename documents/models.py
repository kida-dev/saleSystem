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

class TravelNotification(models.Model):
    """旅行命令メール通知の送信履歴。"""

    TYPE_CHOICES = [
        ("review_request", "確認依頼"),
        ("returned", "差戻し通知"),
        ("completed", "承認完了通知"),
    ]
    STATUS_CHOICES = [
        ("queued", "送信待ち"),
        ("sent", "送信完了"),
        ("preview", "コンソール出力済（未送信）"),
        ("failed", "送信失敗"),
        ("skipped", "送信対象なし"),
    ]

    travel_order = models.ForeignKey(
        TravelOrder, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    recipient_email = models.EmailField(blank=True)
    recipient_name = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "旅行命令メール通知"
        verbose_name_plural = "旅行命令メール通知"
        ordering = ["-created_at"]

# ============================================================
# 出張後の報告（旅行命令の承認フローとは独立して管理）
# ============================================================

class TravelPostReport(models.Model):
    """旅行命令1件に対する行程・旅費報告および復命報告。"""

    STATUS_CHOICES = [
        ("draft", "下書き"),
        ("circulating", "管理職回覧中"),
        ("returned", "差戻し"),
        ("approved", "書類承認完了"),
    ]
    PLACE_CHOICES = [
        ("school", "学校"),
        ("home", "自宅"),
        ("other", "その他"),
    ]

    travel_order = models.OneToOneField(
        TravelOrder, on_delete=models.PROTECT,
        related_name="post_report", verbose_name="旅行命令",
    )
    status = models.CharField("状態", max_length=20, choices=STATUS_CHOICES, default="draft")
    departure_place = models.CharField("出発地", max_length=20, choices=PLACE_CHOICES, default="school")
    departure_place_other = models.CharField("その他の出発地", max_length=200, blank=True)
    return_place = models.CharField("帰着地", max_length=20, choices=PLACE_CHOICES, default="school")
    return_place_other = models.CharField("その他の帰着地", max_length=200, blank=True)
    outbound_toll_road = models.BooleanField("往路：高速道路", default=False)
    outbound_general_road = models.BooleanField("往路：一般道路", default=False)
    inbound_toll_road = models.BooleanField("復路：高速道路", default=False)
    inbound_general_road = models.BooleanField("復路：一般道路", default=False)
    outbound_distance_km = models.DecimalField("往路距離（km）", max_digits=8, decimal_places=1, null=True, blank=True)
    inbound_distance_km = models.DecimalField("復路距離（km）", max_digits=8, decimal_places=1, null=True, blank=True)
    travel_distance_km = models.DecimalField("移動距離（km）", max_digits=8, decimal_places=1, null=True, blank=True)
    student_ride = models.CharField(
        "生徒の同乗", max_length=16, default="none",
        choices=[("none", "同乗なし"), ("outbound", "往路のみ"),
                 ("inbound", "復路のみ"), ("roundtrip", "往復")],
    )
    school_account_amount = models.PositiveIntegerField("学校会計（円）", default=0)
    extracurricular_amount = models.PositiveIntegerField("課外活動費（円）", default=0)
    athletics_support_amount = models.PositiveIntegerField("体育後援会費（円）", default=0)
    external_travel_amount = models.PositiveIntegerField("出張先から受領した旅費（円）", default=0)
    external_travel_source = models.CharField("旅費支給元の団体名", max_length=200, blank=True)
    external_travel_received_date = models.DateField("旅費受領日", null=True, blank=True)
    travel_expense_notes = models.TextField("旅費・行程の備考", blank=True)
    report_content = models.TextField("復命事項（内容・感想）", blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="submitted_travel_post_reports", null=True, blank=True,
        verbose_name="提出者",
    )
    submitted_at = models.DateTimeField("本人同意・提出日時", null=True, blank=True)
    approved_at = models.DateTimeField("校長承認日時", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "出張後報告"
        verbose_name_plural = "出張後報告"

    def __str__(self):
        return f"旅行命令 #{self.travel_order_id} / 出張後報告"


class TravelPostReportAttachment(models.Model):
    """出張先からの旅費支給証明、領収書など。"""

    report = models.ForeignKey(
        TravelPostReport, on_delete=models.CASCADE,
        related_name="attachments", verbose_name="出張後報告",
    )
    file = models.FileField("添付ファイル", upload_to="travel_post_reports/%Y/%m/")
    original_name = models.CharField("元ファイル名", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="travel_post_report_attachments", verbose_name="登録者",
    )
    uploaded_at = models.DateTimeField("登録日時", auto_now_add=True)

    class Meta:
        verbose_name = "出張後報告 添付資料"
        verbose_name_plural = "出張後報告 添付資料"


class TravelPostReportApprovalStep(models.Model):
    """教頭2名・校長の出張後報告承認。"""

    STATUS_CHOICES = [
        ("waiting", "待機中"),
        ("pending", "確認待ち"),
        ("approved", "承認済"),
        ("returned", "差戻し"),
    ]
    report = models.ForeignKey(
        TravelPostReport, on_delete=models.CASCADE,
        related_name="approval_steps", verbose_name="出張後報告",
    )
    approver = models.ForeignKey(
        "publicity.Teacher", on_delete=models.PROTECT,
        related_name="post_report_approval_steps", verbose_name="承認者",
    )
    step_order = models.PositiveSmallIntegerField("回覧順")
    status = models.CharField("状態", max_length=20, choices=STATUS_CHOICES, default="waiting")
    approved_at = models.DateTimeField("承認日時", null=True, blank=True)
    returned_at = models.DateTimeField("差戻し日時", null=True, blank=True)

    class Meta:
        verbose_name = "出張後報告 管理職承認"
        verbose_name_plural = "出張後報告 管理職承認"
        ordering = ["report", "step_order"]
        constraints = [
            models.UniqueConstraint(fields=["report", "step_order"], name="unique_post_report_step_order"),
            models.UniqueConstraint(fields=["report", "approver"], name="unique_post_report_approver"),
        ]


class TravelPostReportHistory(models.Model):
    """出張後報告の提出・承認・差戻し・事務確認の操作履歴。"""

    report = models.ForeignKey(
        TravelPostReport, on_delete=models.CASCADE,
        related_name="histories", verbose_name="出張後報告",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="travel_post_report_histories", verbose_name="操作ユーザー",
    )
    action = models.CharField("操作", max_length=40)
    comment = models.TextField("コメント", blank=True)
    created_at = models.DateTimeField("操作日時", auto_now_add=True)

    class Meta:
        verbose_name = "出張後報告 操作履歴"
        verbose_name_plural = "出張後報告 操作履歴"
        ordering = ["created_at", "id"]


class TravelPostReportOfficeCheck(models.Model):
    """校長承認後、事務次長→事務長の確認と精算状態。"""

    STATUS_CHOICES = [
        ("waiting", "待機中"),
        ("pending", "確認待ち"),
        ("checked", "確認済み"),
    ]
    report = models.ForeignKey(
        TravelPostReport, on_delete=models.CASCADE,
        related_name="office_checks", verbose_name="出張後報告",
    )
    checker = models.ForeignKey(
        "publicity.Teacher", on_delete=models.PROTECT,
        related_name="post_report_office_checks", verbose_name="事務確認者",
    )
    step_order = models.PositiveSmallIntegerField("確認順")
    status = models.CharField("状態", max_length=20, choices=STATUS_CHOICES, default="waiting")
    checked_at = models.DateTimeField("確認日時", null=True, blank=True)
    settlement_completed = models.BooleanField("旅費精算完了", default=False)
    settlement_completed_at = models.DateTimeField("旅費精算完了日時", null=True, blank=True)
    notes = models.TextField("事務確認・精算メモ", blank=True)

    class Meta:
        verbose_name = "出張後報告 事務確認"
        verbose_name_plural = "出張後報告 事務確認"
        ordering = ["report", "step_order"]
        constraints = [
            models.UniqueConstraint(fields=["report", "step_order"], name="unique_post_report_office_order"),
            models.UniqueConstraint(fields=["report", "checker"], name="unique_post_report_office_checker"),
        ]


class TravelPostReportNotification(models.Model):
    """復命書のメール通知履歴（旅行命令とは独立）。"""
    TYPE_CHOICES = [("review_request", "確認依頼"), ("returned", "差戻し通知"), ("completed", "承認完了通知")]
    STATUS_CHOICES = [("queued", "送信待ち"), ("sent", "送信完了"), ("preview", "コンソール出力済"), ("failed", "送信失敗"), ("skipped", "宛先なし")]
    report = models.ForeignKey(TravelPostReport, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    recipient_email = models.EmailField(blank=True)
    recipient_name = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "復命書メール通知"
        verbose_name_plural = "復命書メール通知"
        ordering = ["-created_at"]
