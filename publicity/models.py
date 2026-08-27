from django.conf import settings
from django.db import models


class JuniorHighSchool(models.Model):
    number = models.IntegerField(
        "No",
        blank=True,
        null=True,
    )

    name = models.CharField(
        "学校名",
        max_length=200,
    )

    city = models.CharField(
        "市町村",
        max_length=100,
        blank=True,
    )

    principal_name = models.CharField(
        "校長名",
        max_length=100,
        blank=True,
    )

    tel = models.CharField(
        "電話番号",
        max_length=30,
        blank=True,
    )

    address = models.CharField(
        "住所",
        max_length=255,
        blank=True,
    )

    third_grade_total = models.IntegerField(
        "3年合計",
        default=0,
    )

    school_code = models.CharField(
        "学校コード",
        max_length=13,
        blank=True,
        null=True,
        unique=True,
        help_text="文部科学省が付与する13桁の学校コード",
    )

    prefecture = models.CharField(
        "都道府県",
        max_length=20,
        blank=True,
    )

    school_type = models.CharField(
        "学校種",
        max_length=50,
        blank=True,
    )

    establishment_type = models.CharField(
        "設置区分",
        max_length=50,
        blank=True,
    )

    official_postal_code = models.CharField(
        "学校郵便番号",
        max_length=8,
        blank=True,
    )

    official_address = models.CharField(
        "学校所在地",
        max_length=255,
        blank=True,
    )

    is_from_mext = models.BooleanField(
        "文科省データ",
        default=False,
    )

    is_active = models.BooleanField(
        "使用中",
        default=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "中学校情報"
        verbose_name_plural = "中学校情報"
        ordering = ["number", "id"]

    def __str__(self):
        return self.name

class JuniorHighClass(models.Model):
    school = models.ForeignKey(
        JuniorHighSchool,
        on_delete=models.CASCADE,
        related_name="classes",
        verbose_name="中学校"
    )
    
    class_name = models.CharField("クラス名", max_length=50)
    boys = models.IntegerField("男子", default=0)
    girls = models.IntegerField("女子", default=0)
    total = models.IntegerField("計", default=0)

    class Meta:
        verbose_name = "中学校クラス人数"
        verbose_name_plural = "中学校クラス人数"
        ordering = ["school__number", "id"]

    def __str__(self):
        return f"{self.school.name} {self.class_name}"

class Club(models.Model):
    name = models.CharField(
        "部活動名",
        max_length=100,
        unique=True,
    )

    is_active = models.BooleanField(
        "使用中",
        default=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "部活動"
        verbose_name_plural = "部活動"

    def __str__(self):
        return self.name


class ScholarshipCategory(models.Model):
    name = models.CharField(
        "奨学金区分名",
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        "説明",
        blank=True,
    )

    is_active = models.BooleanField(
        "使用中",
        default=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "奨学金区分"
        verbose_name_plural = "奨学金区分"

    def __str__(self):
        return self.name

# ============================================================
# 寮費区分マスタ
# ============================================================

class DormitoryBenefitCategory(models.Model):

    name = models.CharField(
        "寮費区分名",
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        "説明",
        blank=True,
    )

    is_active = models.BooleanField(
        "使用中",
        default=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "寮費区分"
        verbose_name_plural = "寮費区分"

    def __str__(self):
        return self.name


class ProspectiveStudent(models.Model):

    # ============================================================
    # 基本情報
    # ============================================================

    name = models.CharField(
        "氏名",
        max_length=100,
    )

    name_kana = models.CharField(
        "ふりがな",
        max_length=100,
        blank=True,
    )

    club = models.ForeignKey(
        Club,
        verbose_name="部活動",
        on_delete=models.PROTECT,
        related_name="prospective_students",
    )

    postal_code = models.CharField(
        "郵便番号",
        max_length=8,
        blank=True,
        help_text="例：886-0001",
    )

    address = models.CharField(
        "住所",
        max_length=255,
        blank=True,
    )

    junior_high_school = models.ForeignKey(
        "JuniorHighSchool",
        verbose_name="中学校",
        on_delete=models.PROTECT,
        related_name="prospective_students",
    )

    # ============================================================
    # 奨学金関係
    # ============================================================

    scholarship_wanted = models.BooleanField(
        "奨学金希望",
        default=False,
    )

    junior_high_loan_scholarship_applied = models.BooleanField(
        "中学3年時申込可能な貸与型奨学金に申込済み",
        default=False,
    )

    scholarship_category = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="奨学金区分",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="prospective_students",
    )

    # ============================================================
    # 中学校への連絡状況
    # ============================================================

    CONTACT_STATUS_CHOICES = [
        (
            "not_contacted",
            "未連絡",
        ),
        (
            "contacted",
            "連絡済",
        ),
        (
            "waiting",
            "返答待ち",
        ),
        (
            "responded",
            "返答あり",
        ),
    ]

    contact_status = models.CharField(
        "中学校連絡状況",
        max_length=20,
        choices=CONTACT_STATUS_CHOICES,
        default="not_contacted",
    )

    contact_date = models.DateField(
        "中学校連絡日",
        blank=True,
        null=True,
    )

    contact_memo = models.TextField(
        "中学校からの連絡内容",
        blank=True,
    )

    # ============================================================
    # 部顧問への確認
    # ============================================================

    ADVISOR_RESPONSE_CHOICES = [
        (
            "not_confirmed",
            "未確認",
        ),
        (
            "waiting",
            "確認中",
        ),
        (
            "accept",
            "面談する",
        ),
        (
            "decline",
            "面談しない",
        ),
    ]

    advisor_response = models.CharField(
        "部顧問返答",
        max_length=20,
        choices=ADVISOR_RESPONSE_CHOICES,
        default="not_confirmed",
    )

    advisor_response_memo = models.TextField(
        "部顧問返答メモ",
        blank=True,
    )

    # ============================================================
    # 面談管理
    # ============================================================

    INTERVIEW_STATUS_CHOICES = [
        (
            "not_decided",
            "未確認",
        ),
        (
            "scheduled",
            "面談予定",
        ),
        (
            "completed",
            "面談済",
        ),
        (
            "declined",
            "面談なし",
        ),
    ]

    interview_status = models.CharField(
        "面談状況",
        max_length=20,
        choices=INTERVIEW_STATUS_CHOICES,
        default="not_decided",
    )

    interview_date = models.DateField(
        "面談日",
        blank=True,
        null=True,
    )

    interview_memo = models.TextField(
        "面談メモ",
        blank=True,
    )

    # ============================================================
    # 面談結果
    # ============================================================

    INTERVIEW_RESULT_CHOICES = [
        (
            "undecided",
            "未判定",
        ),
        (
            "considering",
            "継続検討",
        ),
        (
            "candidate",
            "奨学生候補",
        ),
        (
            "declined",
            "見送り",
        ),
    ]

    interview_result = models.CharField(
        "面談結果",
        max_length=20,
        choices=INTERVIEW_RESULT_CHOICES,
        default="undecided",
    )

    # ============================================================
    # 管理職メモ
    # ============================================================

    management_memo = models.TextField(
        "管理職メモ",
        blank=True,
    )

    # ============================================================
    # 担当者
    # ============================================================

    registered_by = models.ForeignKey(
        "Teacher",
        verbose_name="登録者",
        on_delete=models.PROTECT,
        related_name="registered_prospective_students",
    )

    assigned_teacher = models.ForeignKey(
        "Teacher",
        verbose_name="担当教員",
        on_delete=models.PROTECT,
        related_name="assigned_prospective_students",
    )

    # ============================================================
    # その他
    # ============================================================

    dormitory = models.BooleanField(
        "寮希望",
        default=False,
    )

    notes = models.TextField(
        "備考",
        blank=True,
    )

    is_active = models.BooleanField(
        "有効",
        default=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    # ============================================================
    # Meta
    # ============================================================

    class Meta:

        ordering = [
            "-created_at",
            "name",
        ]

        verbose_name = "募集対象生徒"
        verbose_name_plural = "募集対象生徒"

    # ============================================================
    # 表示
    # ============================================================

    def __str__(self):

        return (
            f"{self.name}"
            f"（{self.junior_high_school.name}）"
        )

    @property
    def principal_name(self):

        return (
            self.junior_high_school.principal_name
            or ""
        )

class ScholarshipShippingRecord(models.Model):

    SHIPPING_TYPE_CHOICES = [
        ("mail", "郵送"),
        ("hand_delivery", "持参"),
        ("resend", "再発送"),
    ]

    student = models.ForeignKey(
        ProspectiveStudent,
        on_delete=models.PROTECT,
        related_name="scholarship_shipping_records",
        verbose_name="対象生徒",
    )

    document = models.ForeignKey(
        "ScholarshipRequestDocument",
        on_delete=models.PROTECT,
        related_name="shipping_records",
        verbose_name="発行文書",
        null=True,
        blank=True,
    )

    shipping_type = models.CharField(
        "発送方法",
        max_length=20,
        choices=SHIPPING_TYPE_CHOICES,
        default="mail",
    )

    shipping_order = models.PositiveIntegerField(
        "発送順",
        null=True,
        blank=True,
    )

    is_shipped = models.BooleanField(
        "発送済み",
        default=False,
    )

    shipped_at = models.DateTimeField(
        "発送日時",
        null=True,
        blank=True,
    )

    notes = models.CharField(
        "発送メモ",
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        "Teacher",
        on_delete=models.PROTECT,
        related_name="created_shipping_records",
        verbose_name="登録者",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "奨学生文書発送履歴"
        verbose_name_plural = "奨学生文書発送履歴"

        ordering = [
            "shipping_order",
            "student__junior_high_school__prefecture",
            "student__junior_high_school__city",
            "student__junior_high_school__name",
            "student__name",
        ]

    def __str__(self):

        status = (
            "発送済み"
            if self.is_shipped
            else "未発送"
        )

        return (
            f"{self.student.name} "
            f"{self.get_shipping_type_display()} "
            f"{status}"
        )

class Teacher(models.Model):
    ROLE_CHOICES = [
        ("club_advisor", "部活動顧問"),
        ("publicity_admin", "広報管理者"),
        ("system_admin", "システム管理者"),
    ]
    employee_number = models.PositiveIntegerField(
        "職員番号",
        unique=True,
    )

    position = models.CharField(
        "職名",
        max_length=50,
        blank=True,
    )

    name = models.CharField(
        "氏名",
        max_length=100,
        blank=True
    )

    assignment = models.CharField(
        "担任・校務",
        max_length=150,
        blank=True,
    )

    subject = models.CharField(
        "教科",
        max_length=100,
        blank=True,
    )

    responsibility = models.CharField(
        "役職・主任",
        max_length=200,
        blank=True,
    )

    club = models.CharField(
        "顧問部活動",
        max_length=100,
        blank=True,
    )

    role = models.CharField(
        "システム権限",
        max_length=30,
        choices=ROLE_CHOICES,
        default="club_advisor",
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="ログインユーザー",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="publicity_teacher",
    )

    is_active = models.BooleanField(
        "在籍中",
        default=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    ROLE_CHOICES = [
        ("club_advisor", "部活動顧問"),
        ("publicity_admin", "広報管理者"),
        ("system_admin", "システム管理者"),
    ]
    class Meta:
        ordering = ["employee_number"]
        verbose_name = "教員"
        verbose_name_plural = "教員"

    def __str__(self):
        return f"{self.employee_number}　{self.name}"
    @property
    def is_system_admin(self):
        return self.role == "system_admin"

    @property
    def is_publicity_admin(self):
        return self.role in ["system_admin", "publicity_admin"]


class TeacherLoginEmail(models.Model):
    EMAIL_TYPE_CHOICES = [
        ("school", "学校用"),
        ("personal", "個人用"),
        ("other", "その他"),
    ]

    teacher = models.ForeignKey(
        Teacher,
        verbose_name="教員",
        on_delete=models.CASCADE,
        related_name="login_emails",
    )

    email = models.EmailField(
        "ログイン用メールアドレス",
        unique=True,
    )

    email_type = models.CharField(
        "メール種別",
        max_length=20,
        choices=EMAIL_TYPE_CHOICES,
        default="school",
    )

    is_allowed = models.BooleanField(
        "ログインを許可する",
        default=True,
    )

    is_primary = models.BooleanField(
        "主メールアドレス",
        default=False,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    class Meta:
        ordering = ["teacher__employee_number", "email_type"]
        verbose_name = "教員ログイン用メール"
        verbose_name_plural = "教員ログイン用メール"

    def __str__(self):
        return f"{self.teacher.name}：{self.email}"

class DocumentType(models.Model):
    """
    送付する書類の種類
    """

    name = models.CharField(
        "書類名",
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        "説明",
        blank=True,
    )

    is_active = models.BooleanField(
        "使用中",
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "書類種類"
        verbose_name_plural = "書類種類"

    def __str__(self):
        return self.name

class DeliveryMethod(models.Model):

    name = models.CharField(
        "送付方法",
        max_length=50,
        unique=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "送付方法"
        verbose_name_plural = "送付方法"

    def __str__(self):
        return self.name

class DocumentHistory(models.Model):

    student = models.ForeignKey(
        ProspectiveStudent,
        on_delete=models.CASCADE,
        related_name="document_histories",
        verbose_name="対象生徒",
    )

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        verbose_name="書類種類",
    )

    delivery_method = models.ForeignKey(
        DeliveryMethod,
        on_delete=models.PROTECT,
        verbose_name="送付方法",
    )

    sent_by = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        verbose_name="送付担当",
    )

    sent_date = models.DateField(
        "送付日",
    )

    memo = models.TextField(
        "備考",
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "-sent_date",
            "-created_at",
        ]

        verbose_name = "送付履歴"

        verbose_name_plural = "送付履歴"

    def __str__(self):
        return (
            f"{self.student.name}"
            f" - "
            f"{self.document_type.name}"
        )

class DocumentNumberSequence(models.Model):
    fiscal_year = models.IntegerField(
        "年度（西暦）",
        unique=True,
        help_text="例：2026",
    )

    last_number = models.PositiveIntegerField(
        "最終発行番号",
        default=0,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "文書番号管理"
        verbose_name_plural = "文書番号管理"
        ordering = ["-fiscal_year"]

    def __str__(self):
        reiwa_year = self.fiscal_year - 2018

        return (
            f"令和{reiwa_year}年度 "
            f"最終番号：{self.last_number}"
        )

class ScholarshipRequestDocument(models.Model):

    STATUS_CHOICES = [
        ("issued", "発行済"),
        ("corrected", "訂正済み"),
        ("cancelled", "取消"),
    ]

    school = models.ForeignKey(
        JuniorHighSchool,
        verbose_name="送付先中学校",
        on_delete=models.PROTECT,
        related_name="scholarship_request_documents",
    )

    students = models.ManyToManyField(
        ProspectiveStudent,
        verbose_name="対象生徒",
        related_name="scholarship_request_documents",
    )

    fiscal_year = models.IntegerField(
        "年度（西暦）",
    )

    recruitment_year = models.CharField(
        "募集年度",
        max_length=20,
        blank=True,
        help_text="例：令和9年度",
    )

    document_number = models.CharField(
        "文書番号",
        max_length=50,
    )

    issue_date = models.DateField(
        "発行日",
    )

    seasonal_greeting = models.CharField(
        "時候の挨拶",
        max_length=50,
    )

    principal_name = models.CharField(
        "校長名",
        max_length=100,
    )

    created_by = models.ForeignKey(
        Teacher,
        verbose_name="作成者",
        on_delete=models.PROTECT,
        related_name="created_scholarship_request_documents",
    )

    created_at = models.DateTimeField(
        "作成日時",
        auto_now_add=True,
    )

    status = models.CharField(
        "状態",
        max_length=20,
        choices=STATUS_CHOICES,
        default="issued",
    )
    corrected_from = models.ForeignKey(
        "self",
        verbose_name="訂正元文書",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="corrected_documents",
    )

    correction_reason = models.TextField(
        "訂正理由",
        blank=True,
    )

    class Meta:
        verbose_name = "奨学生募集依頼文書"
        verbose_name_plural = "奨学生募集依頼文書"
        ordering = [
            "-issue_date",
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.document_number} "
            f"{self.school.name}"
        )

# ============================================================
# 奨学生候補管理
# ============================================================

class ScholarshipAssignment(models.Model):

    STATUS_CHOICES = [
        ("not_started", "未対応"),
        ("rank_set", "ランク設定済"),
        ("interview_scheduled", "面談予定"),
        ("interviewed", "面談済"),
        ("temporary_accepted", "仮承諾済"),
        ("adjusting", "ランク調整中"),
        ("conference_confirmed", "連絡会確認済"),
        ("finalized", "最終確定"),
        ("accepted", "正式承諾"),
        ("declined", "辞退"),
    ]

    student = models.OneToOneField(
        ProspectiveStudent,
        verbose_name="対象生徒",
        on_delete=models.CASCADE,
        related_name="scholarship_assignment",
    )

    # --------------------------------------------------------
    # 個人面談時に最初に提示したランク
    # --------------------------------------------------------

    interview_rank = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="面談時ランク",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interview_assignments",
    )

    # --------------------------------------------------------
    # 現在検討中のランク
    # 面談後の変更は基本的にここへ反映
    # --------------------------------------------------------

    current_rank = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="現在ランク",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_assignments",
    )

    # --------------------------------------------------------
    # 生徒指導連絡会後の最終確定ランク
    # --------------------------------------------------------

    final_rank = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="最終確定ランク",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="final_assignments",
    )

    status = models.CharField(
        "進行状況",
        max_length=30,
        choices=STATUS_CHOICES,
        default="not_started",
    )

    # --------------------------------------------------------
    # 面談時の仮承諾
    # --------------------------------------------------------

    temporary_accepted = models.BooleanField(
        "面談時仮承諾",
        default=False,
    )

    temporary_accepted_at = models.DateTimeField(
        "仮承諾日時",
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # 最終通知後の正式承諾
    # --------------------------------------------------------

    final_accepted = models.BooleanField(
        "正式承諾",
        default=False,
    )

    final_accepted_at = models.DateTimeField(
        "正式承諾日時",
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # 最終ランク確定
    # --------------------------------------------------------

    finalized_at = models.DateTimeField(
        "最終確定日時",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "奨学生候補管理"
        verbose_name_plural = "奨学生候補管理"
        ordering = [
            "-updated_at",
        ]

    def __str__(self):
        return (
            f"{self.student.name} "
            f"奨学生候補管理"
        )

    # --------------------------------------------------------
    # 寮費待遇
    # --------------------------------------------------------

    interview_dormitory_benefit = models.ForeignKey(
        DormitoryBenefitCategory,
        verbose_name="面談時寮費区分",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interview_assignments",
    )

    current_dormitory_benefit = models.ForeignKey(
        DormitoryBenefitCategory,
        verbose_name="現在寮費区分",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_assignments",
    )

    final_dormitory_benefit = models.ForeignKey(
        DormitoryBenefitCategory,
        verbose_name="最終確定寮費区分",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="final_assignments",
    )


# ============================================================
# 奨学生ランク変更履歴
# ============================================================

class ScholarshipRankHistory(models.Model):

    assignment = models.ForeignKey(
        ScholarshipAssignment,
        verbose_name="奨学生候補",
        on_delete=models.CASCADE,
        related_name="rank_histories",
    )

    previous_rank = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="変更前ランク",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    new_rank = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="変更後ランク",
        on_delete=models.PROTECT,
        related_name="+",
    )

    reason = models.TextField(
        "変更理由",
        blank=True,
    )

    changed_by = models.ForeignKey(
        Teacher,
        verbose_name="変更者",
        on_delete=models.PROTECT,
        related_name="scholarship_rank_changes",
    )

    changed_at = models.DateTimeField(
        "変更日時",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "奨学生ランク変更履歴"
        verbose_name_plural = "奨学生ランク変更履歴"
        ordering = [
            "-changed_at",
        ]

    def __str__(self):

        old_rank = (
            self.previous_rank.name
            if self.previous_rank
            else "未設定"
        )

        return (
            f"{self.assignment.student.name} "
            f"{old_rank} → {self.new_rank.name}"
        )


# ============================================================
# 奨学生面談
# ============================================================

class ScholarshipInterview(models.Model):

    RESULT_CHOICES = [
        ("pending", "未実施"),
        ("temporary_accepted", "仮承諾"),
        ("considering", "検討中"),
        ("declined", "辞退"),
    ]

    assignment = models.ForeignKey(
        ScholarshipAssignment,
        verbose_name="奨学生候補",
        on_delete=models.CASCADE,
        related_name="interviews",
    )

    scheduled_at = models.DateTimeField(
        "面談予定日時",
        null=True,
        blank=True,
    )

    interviewed_at = models.DateTimeField(
        "面談実施日時",
        null=True,
        blank=True,
    )

    interviewer = models.ForeignKey(
        Teacher,
        verbose_name="面談担当者",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scholarship_interviews",
    )

    presented_rank = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="面談時提示ランク",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    result = models.CharField(
        "面談結果",
        max_length=30,
        choices=RESULT_CHOICES,
        default="pending",
    )

    notes = models.TextField(
        "面談記録・備考",
        blank=True,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    presented_dormitory_benefit = models.ForeignKey(
        DormitoryBenefitCategory,
        verbose_name="面談時提示寮費区分",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "奨学生面談"
        verbose_name_plural = "奨学生面談"
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.assignment.student.name} "
            f"面談"
        )

# ============================================================
# 寮費区分変更履歴
# ============================================================

class DormitoryBenefitHistory(models.Model):

    assignment = models.ForeignKey(
        ScholarshipAssignment,
        verbose_name="奨学生候補",
        on_delete=models.CASCADE,
        related_name="dormitory_benefit_histories",
    )

    previous_benefit = models.ForeignKey(
        DormitoryBenefitCategory,
        verbose_name="変更前寮費区分",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    new_benefit = models.ForeignKey(
        DormitoryBenefitCategory,
        verbose_name="変更後寮費区分",
        on_delete=models.PROTECT,
        related_name="+",
    )

    reason = models.TextField(
        "変更理由",
        blank=True,
    )

    changed_by = models.ForeignKey(
        Teacher,
        verbose_name="変更者",
        on_delete=models.PROTECT,
        related_name="dormitory_benefit_changes",
    )

    changed_at = models.DateTimeField(
        "変更日時",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "寮費区分変更履歴"
        verbose_name_plural = "寮費区分変更履歴"
        ordering = [
            "-changed_at",
        ]

    def __str__(self):

        old_benefit = (
            self.previous_benefit.name
            if self.previous_benefit
            else "未設定"
        )

        return (
            f"{self.assignment.student.name} "
            f"{old_benefit} → {self.new_benefit.name}"
        )

class ScholarshipQuota(models.Model):

    fiscal_year = models.IntegerField(
        "年度（西暦）",
        help_text="例：2027",
    )

    club = models.ForeignKey(
        Club,
        verbose_name="部活動",
        on_delete=models.PROTECT,
        related_name="scholarship_quotas",
    )

    category = models.ForeignKey(
        ScholarshipCategory,
        verbose_name="奨学金区分",
        on_delete=models.PROTECT,
        related_name="scholarship_quotas",
    )

    quota = models.PositiveIntegerField(
        "上限人数",
        default=0,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "奨学生枠"
        verbose_name_plural = "奨学生枠"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "fiscal_year",
                    "club",
                    "category",
                ],
                name="unique_scholarship_quota",
            )
        ]

        ordering = [
            "-fiscal_year",
            "club__name",
            "category__name",
        ]

    def __str__(self):

        reiwa_year = self.fiscal_year - 2018

        return (
            f"令和{reiwa_year}年度 "
            f"{self.club.name} "
            f"{self.category.name} "
            f"{self.quota}名"
        )

class DormitoryBenefitQuota(models.Model):

    fiscal_year = models.IntegerField(
        "年度（西暦）",
        help_text="例：2027",
    )

    club = models.ForeignKey(
        Club,
        verbose_name="部活動",
        on_delete=models.PROTECT,
        related_name="dormitory_benefit_quotas",
    )

    benefit = models.ForeignKey(
        DormitoryBenefitCategory,
        verbose_name="寮費区分",
        on_delete=models.PROTECT,
        related_name="dormitory_benefit_quotas",
    )

    quota = models.PositiveIntegerField(
        "上限人数",
        default=0,
    )

    created_at = models.DateTimeField(
        "登録日時",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "更新日時",
        auto_now=True,
    )

    class Meta:
        verbose_name = "寮費待遇枠"
        verbose_name_plural = "寮費待遇枠"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "fiscal_year",
                    "club",
                    "benefit",
                ],
                name="unique_dormitory_benefit_quota",
            )
        ]

        ordering = [
            "-fiscal_year",
            "club__name",
            "benefit__name",
        ]

    def __str__(self):

        reiwa_year = self.fiscal_year - 2018

        return (
            f"令和{reiwa_year}年度 "
            f"{self.club.name} "
            f"{self.benefit.name} "
            f"{self.quota}名"
        )