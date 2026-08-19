import re

from django import forms
from django.forms import modelformset_factory
from django.utils import timezone

from .models import (
    Club,
    JuniorHighSchool,
    JuniorHighClass,
    ProspectiveStudent,
    ScholarshipCategory,
    Teacher,
)


class JuniorHighSchoolForm(forms.ModelForm):
    class Meta:
        model = JuniorHighSchool

        fields = [
            "number",
            "name",
            "city",
            "principal_name",
            "tel",
            "address",
            "third_grade_total",
        ]

        labels = {
            "number": "No",
            "name": "学校名",
            "city": "市町村",
            "principal_name": "校長名",
            "tel": "電話番号",
            "address": "住所",
            "third_grade_total": "3年合計",
        }


class JuniorHighClassForm(forms.ModelForm):
    class Meta:
        model = JuniorHighClass

        fields = [
            "class_name",
            "boys",
            "girls",
            "total",
        ]

        labels = {
            "class_name": "クラス",
            "boys": "男子",
            "girls": "女子",
            "total": "合計",
        }


class TeacherPermissionForm(forms.ModelForm):
    class Meta:
        model = Teacher

        fields = [
            "role",
            "is_active",
        ]

        widgets = {
            "role": forms.Select(
                attrs={
                    "class": "role-select",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "active-checkbox",
                }
            ),
        }


TeacherPermissionFormSet = modelformset_factory(
    Teacher,
    form=TeacherPermissionForm,
    extra=0,
    can_delete=False,
)


class ProspectiveStudentForm(forms.ModelForm):
    class Meta:
        model = ProspectiveStudent

        fields = [
            "name",
            "name_kana",
            "junior_high_school",
            "club",
            "dormitory",
            "postal_code",
            "address",
            "scholarship_wanted",
            "junior_high_loan_scholarship_applied",
            "notes",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：小林 太郎",
                    "autocomplete": "name",
                }
            ),

            "club": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "postal_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：886-0001",
                    "inputmode": "numeric",
                    "autocomplete": "postal-code",
                }
            ),

            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：宮崎県小林市○○町1番地",
                    "autocomplete": "street-address",
                }
            ),

            "junior_high_school": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_junior_high_school",
                }
            ),

            "scholarship_category": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "必要な補足事項があれば入力してください。",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["club"].queryset = (
            Club.objects
            .filter(is_active=True)
            .order_by("name")
        )

        # ---------------------------------
        # 中学校（Tom Select対応）
        # ---------------------------------
        school_field = self.fields["junior_high_school"]

        # 初期状態では全国の学校をHTMLへ出力しない
        school_field.queryset = (
            JuniorHighSchool.objects.none()
        )

        school_field.empty_label = (
            "学校名・市町村名を入力して検索してください"
        )

        # 登録ボタン押下後（POST）
        if self.is_bound:
            school_id = self.data.get(
                "junior_high_school"
            )

            if school_id:
                school_field.queryset = (
                    JuniorHighSchool.objects
                    .filter(
                        pk=school_id,
                        is_active=True,
                    )
                )

        # 編集画面
        elif (
            self.instance
            and self.instance.pk
            and self.instance.junior_high_school_id
        ):
            school_field.queryset = (
                JuniorHighSchool.objects
                .filter(
                    pk=self.instance.junior_high_school_id
                )
            )

        self.fields["club"].empty_label = (
            "部活動を選択してください"
        )


    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError(
                "氏名を入力してください。"
            )

        return name

    def clean_postal_code(self):
        postal_code = (
            self.cleaned_data
            .get("postal_code", "")
            .strip()
        )

        if not postal_code:
            return ""

        # 全角数字を半角数字へ変換
        postal_code = postal_code.translate(
            str.maketrans(
                "０１２３４５６７８９",
                "0123456789",
            )
        )

        # ハイフンの表記を統一
        postal_code = (
            postal_code
            .replace("ー", "-")
            .replace("―", "-")
            .replace("−", "-")
            .replace("‐", "-")
            .replace("―", "-")
        )

        # 7桁数字だけなら、自動的にハイフンを付ける
        if re.fullmatch(r"\d{7}", postal_code):
            postal_code = (
                f"{postal_code[:3]}-{postal_code[3:]}"
            )

        if not re.fullmatch(
            r"\d{3}-\d{4}",
            postal_code,
        ):
            raise forms.ValidationError(
                "郵便番号は「886-0001」の形式で入力してください。"
            )

        return postal_code

    def clean_address(self):
        address = (
            self.cleaned_data
            .get("address", "")
            .strip()
        )

        return address
def get_reiwa_year(year):
    return year - 2018


def get_japanese_date(date_obj):
    reiwa_year = get_reiwa_year(
        date_obj.year
    )

    return (
        f"令和{reiwa_year}年"
        f"{date_obj.month}月"
        f"{date_obj.day}日"
    )


def get_fiscal_year_label(date_obj):
    fiscal_year = (
        date_obj.year
        if date_obj.month >= 4
        else date_obj.year - 1
    )

    reiwa_year = get_reiwa_year(
        fiscal_year
    )

    return f"令和{reiwa_year}年度"


def get_seasonal_greeting(month):
    greetings = {
        1: "新春の候",
        2: "立春の候",
        3: "早春の候",
        4: "春暖の候",
        5: "新緑の候",
        6: "梅雨の候",
        7: "盛夏の候",
        8: "残暑の候",
        9: "秋分の候",
        10: "秋冷の候",
        11: "晩秋の候",
        12: "師走の候",
    }

    return greetings.get(
        month,
        "",
    )


class ScholarshipRequestDocumentForm(
    forms.Form
):
    fiscal_year = forms.CharField(
        label="募集年度",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": True,
            }
        ),
    )

    document_number = forms.CharField(
        label="文書番号",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": True,
            }
        ),
    )

    issue_date = forms.DateField(
        label="発行日",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    seasonal_greeting = forms.CharField(
        label="時候の挨拶",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "list": (
                    "seasonal-greeting-list"
                ),
            }
        ),
    )

    principal_name = forms.CharField(
        label="校長名",
        max_length=100,
        initial="竹元 和寛",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    school = forms.ModelChoiceField(
        label="送付先中学校",
        queryset=(
            JuniorHighSchool.objects.none()
        ),
        empty_label=(
            "中学校を選択してください"
        ),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    def __init__(
        self,
        *args,
        next_document_number=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()

        self.fields["issue_date"].initial = today

        self.fields["fiscal_year"].initial = (
            get_fiscal_year_label(today)
        )

        self.fields["seasonal_greeting"].initial = (
            get_seasonal_greeting(today.month)
        )

        if next_document_number:
            self.fields["document_number"].initial = (
                next_document_number
            )
        else:
            self.fields["document_number"].initial = (
                "PDF発行時に自動採番"
            )

        school_ids = (
            ProspectiveStudent.objects
            .filter(is_active=True)
            .values_list(
                "junior_high_school_id",
                flat=True,
            )
            .distinct()
        )

        self.fields["school"].queryset = (
            JuniorHighSchool.objects
            .filter(
                id__in=school_ids,
                is_active=True,
            )
            .order_by(
                "prefecture",
                "city",
                "name",
            )
        )