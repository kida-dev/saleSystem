from django import forms
from .models import JuniorHighSchool, JuniorHighClass


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