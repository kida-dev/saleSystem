import re

from django import forms
from django.forms import modelformset_factory

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
            "club",
            "dormitory",
            "postal_code",
            "address",
            "junior_high_school",
            "scholarship_category",
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

        # ---------------------------------
        # 奨学金区分
        # ---------------------------------
        self.fields["scholarship_category"].queryset = (
            ScholarshipCategory.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["club"].empty_label = (
            "部活動を選択してください"
        )

        self.fields["scholarship_category"].required = False

        self.fields["scholarship_category"].empty_label = (
            "未設定"
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