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


class ProspectiveStudent(models.Model):
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

    class Meta:
        ordering = [
            "-created_at",
            "name",
        ]

        verbose_name = "募集対象生徒"
        verbose_name_plural = "募集対象生徒"

    def __str__(self):
        return f"{self.name}（{self.junior_high_school.name}）"

    @property
    def principal_name(self):
        return self.junior_high_school.principal_name or ""

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