from django import forms

from publicity.models import Teacher

from .models import (
    TravelAttachment,
    TravelClassAdjustment,
    TravelOrder,
)


class TeacherChoiceField(forms.ModelChoiceField):
    """
    同行者選択用。
    フォーム上では氏名のみ表示する。
    """

    def label_from_instance(self, obj):
        return obj.name


class TravelOrderForm(forms.ModelForm):
    # 画面上では最大5名まで同行者を選択可能
    companion_1 = TeacherChoiceField(
        label="同行者1",
        queryset=Teacher.objects.none(),
        required=False,
    )

    companion_2 = TeacherChoiceField(
        label="同行者2",
        queryset=Teacher.objects.none(),
        required=False,
    )

    companion_3 = TeacherChoiceField(
        label="同行者3",
        queryset=Teacher.objects.none(),
        required=False,
    )

    companion_4 = TeacherChoiceField(
        label="同行者4",
        queryset=Teacher.objects.none(),
        required=False,
    )

    companion_5 = TeacherChoiceField(
        label="同行者5",
        queryset=Teacher.objects.none(),
        required=False,
    )

    class Meta:
        model = TravelOrder

        fields = [
            "destination_area",
            "destination_name",
            "purpose",
            "start_datetime",
            "end_datetime",
            "departure_place",
            "departure_place_other",
            "transportation",
            "transportation_other",
            "separate_travel_expense",
            "use_toll_road",
            "use_etc",
            "is_holiday_trip",
            "take_substitute_holiday",
            "substitute_holiday_date",
            "no_substitute_holiday_reason",
            "notes",
        ]

        widgets = {
            "destination_area": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：宮崎市",
                }
            ),
            "destination_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：シーガイア コンベンションセンター",
                }
            ),
            "purpose": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "例：私学研修に参加するため",
                }
            ),
            "start_datetime": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "departure_place": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "departure_place_other": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "出発地を入力してください",
                }
            ),
            "transportation": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "transportation_other": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "交通手段を入力してください",
                }
            ),
            "separate_travel_expense": forms.CheckboxInput(),
            "use_toll_road": forms.CheckboxInput(),
            "use_etc": forms.CheckboxInput(),
            "is_holiday_trip": forms.CheckboxInput(),
            "take_substitute_holiday": forms.CheckboxInput(),
            "substitute_holiday_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "no_substitute_holiday_reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "振替休日を取得しない理由を入力してください",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "必要に応じて入力してください",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # datetime-local用
        self.fields["start_datetime"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]
        self.fields["end_datetime"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        # 在籍中の教員だけを同行者候補にする
        teacher_queryset = Teacher.objects.filter(
            is_active=True
        ).order_by("employee_number")

        # ログインしている本人は同行者候補から除外
        if user is not None and user.is_authenticated:
            teacher_queryset = teacher_queryset.exclude(
                user=user
            )

        # 5つの同行者欄に同じ候補を設定
        for number in range(1, 6):
            field = self.fields[f"companion_{number}"]

            field.queryset = teacher_queryset

            field.widget.attrs.update(
                {
                    "class": "form-control companion-select",
                }
            )

            field.empty_label = "同行者を選択してください"

    def clean(self):
        cleaned_data = super().clean()

        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")

        departure_place = cleaned_data.get("departure_place")
        departure_place_other = cleaned_data.get(
            "departure_place_other"
        )

        transportation = cleaned_data.get("transportation")
        transportation_other = cleaned_data.get(
            "transportation_other"
        )

        is_holiday_trip = cleaned_data.get("is_holiday_trip")
        take_substitute_holiday = cleaned_data.get(
            "take_substitute_holiday"
        )
        substitute_holiday_date = cleaned_data.get(
            "substitute_holiday_date"
        )
        no_substitute_holiday_reason = cleaned_data.get(
            "no_substitute_holiday_reason"
        )

        # -------------------------
        # 出張日時
        # -------------------------
        if (
            start_datetime
            and end_datetime
            and end_datetime < start_datetime
        ):
            self.add_error(
                "end_datetime",
                "終了日時は開始日時以降にしてください。",
            )

        # -------------------------
        # 出発地「その他」
        # -------------------------
        if (
            departure_place == "other"
            and not departure_place_other
        ):
            self.add_error(
                "departure_place_other",
                "その他の出発地を入力してください。",
            )

        # -------------------------
        # 交通手段「その他」
        # -------------------------
        if (
            transportation == "other"
            and not transportation_other
        ):
            self.add_error(
                "transportation_other",
                "その他の交通手段を入力してください。",
            )

        # -------------------------
        # 休日出張・振替休日
        # -------------------------
        if is_holiday_trip:
            if (
                take_substitute_holiday
                and not substitute_holiday_date
            ):
                self.add_error(
                    "substitute_holiday_date",
                    "振替休日取得予定日を入力してください。",
                )

            if (
                not take_substitute_holiday
                and not no_substitute_holiday_reason
            ):
                self.add_error(
                    "no_substitute_holiday_reason",
                    "振替休日を取得しない理由を入力してください。",
                )

        # -------------------------
        # 同行者重複チェック
        # -------------------------
        companions = []

        for number in range(1, 6):
            field_name = f"companion_{number}"
            teacher = cleaned_data.get(field_name)

            if teacher is None:
                continue

            if teacher.pk in companions:
                self.add_error(
                    field_name,
                    "同じ先生がすでに同行者として選択されています。",
                )
            else:
                companions.append(teacher.pk)

        return cleaned_data

    def get_companions(self):
        """
        clean済みの同行者をTeacherオブジェクトのリストで返す。
        views.pyから利用する。
        """
        companions = []

        for number in range(1, 6):
            teacher = self.cleaned_data.get(
                f"companion_{number}"
            )

            if teacher is not None:
                companions.append(teacher)

        return companions

class TravelClassAdjustmentForm(forms.ModelForm):

    class Meta:
        model = TravelClassAdjustment

        fields = [
            "date",
            "period",
            "department",
            "grade",
            "class_name",
            "subject",
            "substitute_teacher",
        ]

        widgets = {
            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "period": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 7,
                }
            ),

            "department": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：商業",
                }
            ),

            "grade": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 3,
                }
            ),

            "class_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：1",
                }
            ),

            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：情報処理",
                }
            ),

            "substitute_teacher": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：山田太郎",
                }
            ),
        }

class TravelAttachmentForm(forms.ModelForm):

    class Meta:
        model = TravelAttachment

        fields = [
            "file",
        ]

        widgets = {
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")

        if not file:
            return file

        # 10MBまで
        max_size = 10 * 1024 * 1024

        if file.size > max_size:
            raise forms.ValidationError(
                "ファイルサイズは10MB以下にしてください。"
            )

        # 拡張子チェック
        allowed_extensions = {
            "pdf",
            "jpg",
            "jpeg",
            "png",
        }

        extension = (
            file.name
            .rsplit(".", 1)[-1]
            .lower()
            if "." in file.name
            else ""
        )

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                "PDF、JPG、JPEG、PNG形式の"
                "ファイルを選択してください。"
            )

        return file