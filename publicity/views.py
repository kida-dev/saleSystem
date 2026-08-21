import os
import re

from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Font,
    PatternFill,
)
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.platypus import Table, TableStyle

from .decorators import (
    active_teacher_required,
    club_advisor_required,
    publicity_admin_required,
    system_admin_required,
)

from .forms import (
    get_seasonal_greeting,
    JuniorHighSchoolForm,
    JuniorHighClassForm,
    ProspectiveStudentForm,
    ScholarshipRequestDocumentForm,
    TeacherPermissionFormSet,
)

from .models import (
    Club,
    DocumentHistory,
    DocumentNumberSequence,
    DormitoryBenefitCategory,
    DormitoryBenefitHistory,
    JuniorHighClass,
    JuniorHighSchool,
    ProspectiveStudent,
    ScholarshipAssignment,
    ScholarshipCategory,
    ScholarshipInterview,
    ScholarshipRankHistory,
    ScholarshipRequestDocument,
    Teacher,
)

def top(request):
    teacher = None

    if request.user.is_authenticated:
        try:
            teacher = request.user.publicity_teacher
        except Teacher.DoesNotExist:
            teacher = None

    # --------------------------------------------------------
    # システムを利用できるか
    # --------------------------------------------------------

    can_use_system = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or (
                teacher is not None
                and teacher.is_active
            )
        )
    )

    # --------------------------------------------------------
    # 広報機能を管理できるか
    # --------------------------------------------------------

    can_manage_publicity = (
        request.user.is_superuser
        or (
            teacher is not None
            and teacher.is_active
            and teacher.role in [
                "system_admin",
                "publicity_admin",
            ]
        )
    )

    # --------------------------------------------------------
    # 教員・権限管理を操作できるか
    # --------------------------------------------------------

    can_manage_permissions = (
        request.user.is_superuser
        or (
            teacher is not None
            and teacher.is_active
            and teacher.role == "system_admin"
        )
    )

    # --------------------------------------------------------
    # 奨学生・面談管理を利用できるか
    # --------------------------------------------------------

    can_manage_scholarship = (
        request.user.is_superuser
        or (
            teacher is not None
            and teacher.is_active
            and teacher.role in {
                "club_advisor",
                "publicity_admin",
                "system_admin",
            }
        )
    )

    # --------------------------------------------------------
    # TOP表示
    # --------------------------------------------------------

    return render(
        request,
        "publicity/top.html",
        {
            "teacher": teacher,
            "can_use_system": can_use_system,
            "can_manage_publicity": can_manage_publicity,
            "can_manage_permissions": can_manage_permissions,

            # ★これが必要
            "can_manage_scholarship": can_manage_scholarship,
        },
    )

@active_teacher_required
def school_list(request):
    schools = JuniorHighSchool.objects.prefetch_related("classes").order_by("number", "id")

    return render(request, "publicity/school_list.html", {
        "schools": schools
    })

@club_advisor_required
def school_edit(request, pk):
    school = get_object_or_404(JuniorHighSchool, pk=pk)

    if request.method == "POST":
        form = JuniorHighSchoolForm(request.POST, instance=school)

        if form.is_valid():
            form.save()
            return redirect("publicity:school_list")

    else:
        form = JuniorHighSchoolForm(instance=school)

    return render(request, "publicity/school_form.html", {
        "form": form,
        "school": school,
    })

@publicity_admin_required
def school_delete(request, pk):
    school = get_object_or_404(JuniorHighSchool, pk=pk)
    school.delete()

    return redirect("publicity:school_list")

@active_teacher_required
def school_print(request):
    school_ids = request.GET.getlist("school_ids")

    if school_ids:
        schools = JuniorHighSchool.objects.filter(
            id__in=school_ids
        ).order_by("number", "id")
    else:
        schools = JuniorHighSchool.objects.all().order_by("number", "id")

    return render(request, "publicity/school_print.html", {
        "schools": schools
    })

@publicity_admin_required
def label_select(request):
    schools = JuniorHighSchool.objects.all().order_by("number", "id")

    return render(request, "publicity/label_select.html", {
        "schools": schools
    })

@publicity_admin_required
def label_pdf(request):
    school_ids = request.GET.getlist("school_ids")

    if school_ids:
        schools = JuniorHighSchool.objects.filter(
            id__in=school_ids
        ).order_by("number", "id")
    else:
        schools = JuniorHighSchool.objects.all().order_by("number", "id")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="junior_high_labels.pdf"'

    p = canvas.Canvas(response, pagesize=A4)

    font_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "fonts",
        "ipaexm.ttf"
    )

    pdfmetrics.registerFont(TTFont("IPAexMincho", font_path))

    page_width, page_height = A4

    label_width = 83.8 * mm
    label_height = 42.3 * mm

    margin_left = 21.2 * mm
    margin_top = 21.2 * mm

    cols = 2
    labels_per_page = 12

    label_index = 0

    for school in schools:
        pos = label_index % labels_per_page

        col = pos % cols
        row = pos // cols

        x = margin_left + (col * label_width)
        y = page_height - margin_top - ((row + 1) * label_height)

        text_x = x + 5 * mm
        text_y = y + label_height - 9 * mm

        p.setFont("IPAexMincho", 8)
        p.drawString(text_x, text_y, school.address or "")

        p.setFont("IPAexMincho", 10)
        p.drawString(text_x, text_y - 9 * mm, school.name)

        p.setFont("IPAexMincho", 9)
        p.drawString(
            text_x,
            text_y - 18 * mm,
            "校長様"
        )

        p.setFont("IPAexMincho", 7)
        p.drawString(
            text_x,
            text_y - 27 * mm,
            f"TEL：{school.tel}"
        )

        label_index += 1

        if label_index % labels_per_page == 0:
            p.showPage()

    p.save()

    return response

@publicity_admin_required
def class_label_pdf(request):
    school_ids = request.GET.getlist("school_ids")

    if school_ids:
        classes = JuniorHighClass.objects.select_related(
            "school"
        ).filter(
            school_id__in=school_ids
        ).order_by("school__number", "school__name", "class_name")
    else:
        classes = JuniorHighClass.objects.select_related(
            "school"
        ).order_by("school__number", "school__name", "class_name")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="class_labels.pdf"'

    p = canvas.Canvas(response, pagesize=A4)

    font_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "fonts",
        "ipaexm.ttf"
    )

    pdfmetrics.registerFont(TTFont("IPA", font_path))

    p.setFont("IPA", 10)

    width, height = A4

    label_width = 83.8 * mm
    label_height = 42.3 * mm

    margin_left = 21.2 * mm
    margin_top = 21.2 * mm

    cols = 2
    labels_per_page = 12

    label_index = 0

    for cls in classes:
        pos = label_index % labels_per_page
        col = pos % cols
        row = pos // cols

        x = margin_left + col * label_width
        y = height - margin_top - (row + 1) * label_height

        p.roundRect(
            x + 3 * mm,
            y + 5 * mm,
            label_width - 6 * mm,
            label_height - 10 * mm,
            3 * mm
        )

        p.setFont("IPA", 10)
        p.drawCentredString(
            x + label_width / 2,
            y + 25 * mm,
            cls.school.name
        )

        p.setFont("IPA", 10)
        p.drawCentredString(
            x + label_width / 2,
            y + 15 * mm,
            f"{cls.class_name}　{cls.total}名"
        )

        label_index += 1

        if label_index % labels_per_page == 0:
            p.showPage()
            p.setFont("IPA", 10)

    p.save()

    return response

@club_advisor_required
def class_edit(request, pk):
    school_class = get_object_or_404(JuniorHighClass, pk=pk)

    if request.method == "POST":
        form = JuniorHighClassForm(request.POST, instance=school_class)

        if form.is_valid():
            form.save()
            return redirect("publicity:school_list")

    else:
        form = JuniorHighClassForm(instance=school_class)

    return render(request, "publicity/class_form.html", {
        "form": form,
        "school_class": school_class,
    })

@system_admin_required
def teacher_permission_manage(request):
    queryset = Teacher.objects.all().order_by(
        "employee_number"
    )

    if request.method == "POST":
        formset = TeacherPermissionFormSet(
            request.POST,
            queryset=queryset,
        )

        if formset.is_valid():
            changed_teachers = formset.save()

            messages.success(
                request,
                f"{len(changed_teachers)}件の権限情報を更新しました。",
            )

            return redirect(
                "publicity:teacher_permission_manage"
            )

    else:
        formset = TeacherPermissionFormSet(
            queryset=queryset
        )

    teacher_rows = zip(
        queryset,
        formset.forms,
    )

    return render(
        request,
        "publicity/teacher_permission_manage.html",
        {
            "formset": formset,
            "teacher_rows": teacher_rows,
        },
    )

def login_denied(request):
    return render(
        request,
        "publicity/login_denied.html",
        status=403,
    )

@club_advisor_required
def prospective_student_list(request):
    teacher = request.teacher

    students = (
        ProspectiveStudent.objects
        .select_related(
            "junior_high_school",
            "club",
            "scholarship_category",
            "registered_by",
            "assigned_teacher",
        )
        .filter(is_active=True)
    )

    # 広報管理者・システム管理者は全件表示
    if teacher.role not in {
        "publicity_admin",
        "system_admin",
    }:
        students = students.filter(
            Q(registered_by=teacher)
            | Q(assigned_teacher=teacher)
        )

    keyword = request.GET.get("q", "").strip()
    school_id = request.GET.get("school", "").strip()
    club_id = request.GET.get("club", "").strip()

    if keyword:
        students = students.filter(
            Q(name__icontains=keyword)
            | Q(junior_high_school__name__icontains=keyword)
            | Q(club__name__icontains=keyword)
        )

    if school_id.isdigit():
        students = students.filter(
            junior_high_school_id=school_id
        )

    if club_id.isdigit():
        students = students.filter(
            club_id=club_id
        )

    students = students.order_by(
        "-created_at",
        "name",
    )

    visible_school_ids = (
        students
        .values_list(
            "junior_high_school_id",
            flat=True,
        )
        .distinct()
    )

    visible_club_ids = (
        students
        .values_list(
            "club_id",
            flat=True,
        )
        .distinct()
    )

    schools = (
        JuniorHighSchool.objects
        .filter(id__in=visible_school_ids)
        .order_by("city", "name")
    )

    clubs = (
        Club.objects
        .filter(id__in=visible_club_ids)
        .order_by("name")
    )

    return render(
        request,
        "publicity/prospective_student_list.html",
        {
            "students": students,
            "schools": schools,
            "clubs": clubs,
            "keyword": keyword,
            "selected_school": school_id,
            "selected_club": club_id,
        },
    )

@club_advisor_required
def prospective_student_excel(request):
    teacher = request.teacher

    students = (
        ProspectiveStudent.objects
        .select_related(
            "junior_high_school",
            "club",
            "scholarship_category",
            "registered_by",
            "assigned_teacher",
        )
        .filter(is_active=True)
    )

    # 一覧画面と同じ権限制御
    if teacher.role not in {
        "publicity_admin",
        "system_admin",
    }:
        students = students.filter(
            Q(registered_by=teacher)
            | Q(assigned_teacher=teacher)
        )

    # 一覧画面と同じ検索条件
    keyword = request.GET.get(
        "q",
        "",
    ).strip()

    school_id = request.GET.get(
        "school",
        "",
    ).strip()

    club_id = request.GET.get(
        "club",
        "",
    ).strip()

    if keyword:
        students = students.filter(
            Q(name__icontains=keyword)
            | Q(name_kana__icontains=keyword)
            | Q(
                junior_high_school__name__icontains=keyword
            )
            | Q(club__name__icontains=keyword)
        )

    if school_id.isdigit():
        students = students.filter(
            junior_high_school_id=school_id
        )

    if club_id.isdigit():
        students = students.filter(
            club_id=club_id
        )

    students = students.order_by(
        "junior_high_school__prefecture",
        "junior_high_school__city",
        "junior_high_school__name",
        "name_kana",
        "name",
    )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "募集対象生徒一覧"

    headers = [
        "氏名",
        "ふりがな",
        "中学校",
        "都道府県",
        "市町村",
        "部活動",
        "寮予定",
        "奨学金金額",
        "貸与型奨学金申込済"
        "郵便番号",
        "住所",
        "担当教員",
        "登録者",
        "登録日",
        "備考",
    ]

    worksheet.append(headers)

    # 見出しの装飾
    header_fill = PatternFill(
        fill_type="solid",
        fgColor="28556B",
    )

    header_font = Font(
        color="FFFFFF",
        bold=True,
    )

    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for student in students:
        school = student.junior_high_school

        worksheet.append(
            [
                student.name,
                student.name_kana or "",
                school.name if school else "",
                (
                    school.prefecture
                    if school
                    else ""
                ),
                (
                    school.city
                    if school
                    else ""
                ),
                (
                    student.club.name
                    if student.club
                    else ""
                ),
                (
                    "入寮予定"
                    if student.dormitory
                    else ""
                ),
                (
                    "希望あり"
                    if student.scholarship_wanted
                    else ""
                ),
                (
                    "申込済"
                    if student.junior_high_loan_scholarship_applied
                    else ""
                ),
                student.postal_code or "",
                student.address or "",
                (
                    student.assigned_teacher.name
                    if student.assigned_teacher
                    else ""
                ),
                (
                    student.registered_by.name
                    if student.registered_by
                    else ""
                ),
                (
                    student.created_at.strftime(
                        "%Y/%m/%d"
                    )
                    if student.created_at
                    else ""
                ),
                student.notes or "",
            ]
        )

    # 先頭行固定
    worksheet.freeze_panes = "A2"

    # オートフィルター
    worksheet.auto_filter.ref = (
        worksheet.dimensions
    )

    # 行の高さ
    worksheet.row_dimensions[1].height = 24

        # 列幅
    column_widths = {
        "A": 16,  # 氏名
        "B": 18,  # ふりがな
        "C": 32,  # 中学校
        "D": 12,  # 都道府県
        "E": 16,  # 市町村
        "F": 18,  # 部活動
        "G": 12,  # 寮予定
        "H": 14,  # 奨学金希望
        "I": 22,  # 貸与型奨学金申込済
        "J": 12,  # 郵便番号
        "K": 38,  # 住所
        "L": 16,  # 担当教員
        "M": 16,  # 登録者
        "N": 12,  # 登録日
        "O": 35,  # 備考
    }

    for column, width in (
        column_widths.items()
    ):
        worksheet.column_dimensions[
            column
        ].width = width

    # セルを折り返す
    for row in worksheet.iter_rows(
        min_row=2
    ):
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    # 印刷設定
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 0
    worksheet.page_orientation = "landscape"
    worksheet.print_title_rows = "1:1"

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = (
        "募集対象生徒一覧.xlsx"
    )

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
    )

    response[
        "Content-Disposition"
    ] = (
        "attachment; "
        "filename*=UTF-8''"
        f"{quote(filename)}"
    )

    return response

def _get_school_principals():
    return {
        str(school.id): school.principal_name or "未登録"
        for school in JuniorHighSchool.objects.all().only(
            "id",
            "principal_name",
        )
    }

@club_advisor_required
def prospective_student_create(request):
    teacher = request.teacher

    if request.method == "POST":
        form = ProspectiveStudentForm(
            request.POST
        )

        if form.is_valid():
            student = form.save(commit=False)

            # 登録者・担当者はログイン中の先生
            student.registered_by = teacher
            student.assigned_teacher = teacher
            student.is_active = True

            student.save()

            messages.success(
                request,
                f"{student.name}さんを登録しました。",
            )

            return redirect(
                "publicity:prospective_student_list"
            )

    else:
        form = ProspectiveStudentForm()

    return render(
        request,
        "publicity/prospective_student_form.html",
        {
            "form": form,
            "page_title": "募集対象生徒を登録",
            "submit_label": "登録する",
            "school_principals": _get_school_principals(),
            "is_edit": False,
        },
    )

@club_advisor_required
def prospective_student_edit(request, pk):
    teacher = request.teacher

    queryset = (
        ProspectiveStudent.objects
        .select_related(
            "junior_high_school",
            "club",
            "registered_by",
            "assigned_teacher",
        )
        .filter(is_active=True)
    )

    if teacher.role not in {
        "publicity_admin",
        "system_admin",
    }:
        queryset = queryset.filter(
            Q(registered_by=teacher)
            | Q(assigned_teacher=teacher)
        )

    student = get_object_or_404(
        queryset,
        pk=pk,
    )

    if request.method == "POST":
        form = ProspectiveStudentForm(
            request.POST,
            instance=student,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"{student.name}さんの情報を更新しました。",
            )

            return redirect(
                "publicity:prospective_student_list"
            )

    else:
        form = ProspectiveStudentForm(
            instance=student
        )

    return render(
        request,
        "publicity/prospective_student_form.html",
        {
            "form": form,
            "student": student,
            "page_title": "募集対象生徒を編集",
            "submit_label": "変更を保存",
            "school_principals": _get_school_principals(),
            "is_edit": True,
        },
    )

@club_advisor_required
def junior_high_school_search(request):
    keyword = (
        request.GET
        .get("q", "")
        .strip()
    )

    prefecture = (
        request.GET
        .get("prefecture", "")
        .strip()
    )

    schools = (
        JuniorHighSchool.objects
        .filter(is_active=True)
        .order_by(
            "prefecture",
            "city",
            "name",
        )
    )

    if prefecture:
        schools = schools.filter(
            prefecture=prefecture
        )

    if keyword:
        # 全角スペースを半角スペースへ統一し、
        # スペース区切りで複数の検索語に分割
        search_words = (
            keyword
            .replace("　", " ")
            .split()
        )

        # 各検索語についてfilterを重ねることで
        # AND検索にする
        for word in search_words:
            schools = schools.filter(
                Q(name__icontains=word)
                | Q(prefecture__icontains=word)
                | Q(city__icontains=word)
                | Q(address__icontains=word)
                | Q(
                    official_address__icontains=word
                )
                | Q(
                    official_postal_code__icontains=word
                )
                | Q(school_code__icontains=word)
            )

    else:
        # 未入力時に全国の学校を返さない
        schools = schools.none()

    # 候補を最大30校に制限
    schools = schools[:30]

    results = [
        {
            "id": school.id,
            "name": school.name,
            "prefecture": (
                school.prefecture or ""
            ),
            "city": school.city or "",
            "principal_name": (
                school.principal_name or ""
            ),
            "postal_code": (
                school.official_postal_code
                or ""
            ),
            "address": (
                school.address
                or school.official_address
                or ""
            ),
            "label": (
                f"{school.name}"
                f"（{school.prefecture or ''}"
                f"{school.city or ''}）"
            ),
        }
        for school in schools
    ]

    return JsonResponse(
        {
            "results": results,
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )

@system_admin_required
def document_management_top(request):
    return render(
        request,
        "publicity/document_management_top.html",
    )

@system_admin_required
def scholarship_document_student_select(request):
    students = (
        ProspectiveStudent.objects
        .filter(is_active=True)
        .select_related(
            "junior_high_school",
            "club",
            "assigned_teacher",
        )
        .order_by(
            "junior_high_school__prefecture",
            "junior_high_school__city",
            "junior_high_school__name",
            "name",
        )
    )

    keyword = request.GET.get(
        "q",
        "",
    ).strip()

    school_id = request.GET.get(
        "school",
        "",
    ).strip()

    club_id = request.GET.get(
        "club",
        "",
    ).strip()

    if keyword:
        students = students.filter(
            Q(name__icontains=keyword)
            | Q(name_kana__icontains=keyword)
            | Q(
                junior_high_school__name__icontains=keyword
            )
            | Q(club__name__icontains=keyword)
        )

    if school_id.isdigit():
        students = students.filter(
            junior_high_school_id=school_id
        )

    if club_id.isdigit():
        students = students.filter(
            club_id=club_id
        )

    schools = (
        JuniorHighSchool.objects
        .filter(
            id__in=students.values_list(
                "junior_high_school_id",
                flat=True,
            )
        )
        .order_by(
            "prefecture",
            "city",
            "name",
        )
        .distinct()
    )

    clubs = (
        Club.objects
        .filter(
            id__in=students.values_list(
                "club_id",
                flat=True,
            )
        )
        .order_by("name")
        .distinct()
    )

    return render(
        request,
        "publicity/scholarship_document_student_select.html",
        {
            "students": students,
            "schools": schools,
            "clubs": clubs,
            "keyword": keyword,
            "selected_school": school_id,
            "selected_club": club_id,
        },
    )

@login_required
def scholarship_request_document_create(request):
    """
    奨学生募集依頼文書の作成画面
    """

    today = timezone.localdate()

    # -----------------------------
    # 現在年度を取得
    # -----------------------------
    fiscal_year = get_fiscal_year_from_date(
        today
    )

    # -----------------------------
    # 次回文書番号を確認
    # ※ここではまだ正式採番しない
    # -----------------------------
    sequence = (
        DocumentNumberSequence.objects
        .filter(
            fiscal_year=fiscal_year
        )
        .first()
    )

    if sequence:
        next_number = (
            sequence.last_number + 1
        )
    else:
        next_number = 1

    next_document_number = (
        f"小林西発第"
        f"{next_number:03d}"
        f"号"
    )

    # -----------------------------
    # 選択された中学校
    # -----------------------------
    school_id = (
        request.GET
        .get("school", "")
        .strip()
    )

    # -----------------------------
    # Form
    #
    # request.GETを直接渡さない。
    # schoolだけinitialとして設定する。
    # これで年度・日付・季語・文書番号の
    # initialが正常に表示される。
    # -----------------------------
    initial_data = {}

    if school_id.isdigit():
        initial_data["school"] = (
            school_id
        )

    form = ScholarshipRequestDocumentForm(
        next_document_number=(
            next_document_number
        ),
        initial=initial_data,
    )

    selected_school = None

    students = (
        ProspectiveStudent.objects.none()
    )

    # -----------------------------
    # 中学校・対象生徒取得
    # -----------------------------
    if school_id.isdigit():

        selected_school = (
            form.fields["school"]
            .queryset
            .filter(
                pk=school_id
            )
            .first()
        )

        if selected_school:

            students = (
                ProspectiveStudent.objects
                .filter(
                    junior_high_school=(
                        selected_school
                    ),
                    is_active=True,
                )
                .select_related(
                    "club",
                    "junior_high_school",
                )
                .order_by(
                    "club__name",
                    "name_kana",
                    "name",
                )
            )

    context = {
        "form": form,
        "selected_school": (
            selected_school
        ),
        "students": students,
        "next_document_number": (
            next_document_number
        ),
    }

    return render(
        request,
        (
            "publicity/"
            "scholarship_request_document_create.html"
        ),
        context,
    )

def get_fiscal_year_from_date(date_obj):
    """
    発行日から年度（西暦）を取得する。
    4月～翌年3月を同一年度として扱う。
    """

    if date_obj.month >= 4:
        return date_obj.year

    return date_obj.year - 1


@transaction.atomic
def issue_document_number(issue_date):
    """
    文書番号を正式発行する。

    PDF生成時など、
    本当に文書を発行するときだけ呼び出す。
    """

    fiscal_year = get_fiscal_year_from_date(
        issue_date
    )

    sequence, created = (
        DocumentNumberSequence.objects
        .select_for_update()
        .get_or_create(
            fiscal_year=fiscal_year,
            defaults={
                "last_number": 0,
            },
        )
    )

    sequence.last_number += 1

    sequence.save(
        update_fields=[
            "last_number",
            "updated_at",
        ]
    )

    document_number = (
        f"小林西発第"
        f"{sequence.last_number:03d}"
        f"号"
    )

    return document_number

@system_admin_required
def scholarship_document_confirm(request):

    if request.method != "POST":
        return redirect(
            "publicity:scholarship_document_student_select"
        )

    student_ids = request.POST.getlist(
        "student_ids"
    )

    if not student_ids:
        messages.error(
            request,
            "文書を発行する生徒を選択してください。",
        )

        return redirect(
            "publicity:scholarship_document_student_select"
        )

    students = (
        ProspectiveStudent.objects
        .filter(
            id__in=student_ids,
            is_active=True,
        )
        .select_related(
            "junior_high_school",
            "club",
            "assigned_teacher",
        )
        .order_by(
            "junior_high_school__prefecture",
            "junior_high_school__city",
            "junior_high_school__name",
            "club__name",
            "name",
        )
    )

    # --------------------------------
    # 中学校単位でグループ化
    # --------------------------------

    grouped_schools = {}

    for student in students:

        school = (
            student.junior_high_school
        )

        if school.id not in grouped_schools:

            grouped_schools[
                school.id
            ] = {
                "school": school,
                "students": [],
            }

        grouped_schools[
            school.id
        ]["students"].append(
            student
        )

    school_groups = list(
        grouped_schools.values()
    )

    today = timezone.localdate()

    fiscal_year = (
        get_fiscal_year_from_date(
            today
        )
    )

    sequence = (
        DocumentNumberSequence.objects
        .filter(
            fiscal_year=fiscal_year
        )
        .first()
    )

    if sequence:
        last_number = sequence.last_number
    else:
        last_number = 0

    for index, group in enumerate(
        school_groups,
        start=1,
    ):
        group[
            "suggested_document_number"
        ] = (
            f"小林西発第"
            f"{last_number + index:03d}"
            f"号"
        )

    reiwa_year = (
        fiscal_year - 2018
    )

    issue_reiwa_year = (
        today.year - 2018
    )

    issue_date_label = (
        f"令和{issue_reiwa_year}年"
        f"{today.month}月"
        f"{today.day}日"
    )

    seasonal_greeting = (
        get_seasonal_greeting(
            today.month
        )
    )

    return render(
        request,
        "publicity/scholarship_document_confirm.html",
        {
            "students": students,
            "school_groups": school_groups,
            "student_ids": student_ids,
            "student_count": students.count(),
            "school_count": len(
                school_groups
            ),
            "fiscal_year_label": (
                f"令和{reiwa_year}年度"
            ),
            "issue_date": today,
            "issue_date_label": (
                issue_date_label
            ),
            "seasonal_greeting": (
                seasonal_greeting
            ),
        },
    )

@club_advisor_required
@transaction.atomic
def scholarship_request_document_pdf(request):
    """
    奨学生募集依頼文書を正式発行し、
    PDFを生成する。
    """

    if request.method != "POST":
        return HttpResponse(
            "不正なアクセスです。",
            status=405,
        )

    form = ScholarshipRequestDocumentForm(
        request.POST
    )

    if not form.is_valid():
        return HttpResponse(
            "文書設定に入力エラーがあります。"
            f"<br>{form.errors}",
            status=400,
        )

    school = form.cleaned_data["school"]
    issue_date = form.cleaned_data["issue_date"]

    seasonal_greeting = (
        form.cleaned_data[
            "seasonal_greeting"
        ]
    )

    principal_name = (
        form.cleaned_data[
            "principal_name"
        ]
    )

    students = (
        ProspectiveStudent.objects
        .filter(
            junior_high_school=school,
            is_active=True,
        )
        .select_related(
            "club",
            "junior_high_school",
        )
        .order_by(
            "club__name",
            "name_kana",
            "name",
        )
    )

    if not students.exists():
        return HttpResponse(
            "対象生徒が登録されていません。",
            status=400,
        )

    # ========================================
    # 年度判定
    # ========================================

    fiscal_year = (
        get_fiscal_year_from_date(
            issue_date
        )
    )

    # ========================================
    # 正式採番
    # ========================================

    sequence, created = (
        DocumentNumberSequence.objects
        .select_for_update()
        .get_or_create(
            fiscal_year=fiscal_year,
            defaults={
                "last_number": 0,
            },
        )
    )

    document_number = (
        request.POST.get(
            f"document_number_{school.id}",
            "",
        )
        .strip()
    )

    # ========================================
    # 発行履歴保存
    # ========================================

    document = (
        ScholarshipRequestDocument.objects
        .create(
            school=school,
            fiscal_year=fiscal_year,
            document_number=document_number,
            issue_date=issue_date,
            seasonal_greeting=(
                seasonal_greeting
            ),
            principal_name=principal_name,
            created_by=request.teacher,
        )
    )

    document.students.set(students)

    # ========================================
    # PDF作成
    # ========================================

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    width, height = A4

    # 日本語フォント
    pdfmetrics.registerFont(
        UnicodeCIDFont(
            "HeiseiMin-W3"
        )
    )

    pdfmetrics.registerFont(
        UnicodeCIDFont(
            "HeiseiKakuGo-W5"
        )
    )

    font_min = "HeiseiMin-W3"
    font_gothic = "HeiseiKakuGo-W5"

    # ========================================
    # 右上：文書番号・発行日
    # ========================================

    pdf.setFont(
        font_min,
        10.5,
    )

    pdf.drawRightString(
        width - 25 * mm,
        height - 25 * mm,
        document_number,
    )

    reiwa_year = (
        issue_date.year - 2018
    )

    japanese_date = (
        f"令和{reiwa_year}年"
        f"{issue_date.month}月"
        f"{issue_date.day}日"
    )

    pdf.drawRightString(
        width - 25 * mm,
        height - 32 * mm,
        japanese_date,
    )

    # ========================================
    # 左上：宛先
    # ========================================

    em = 11

    address_x = 28 * mm
    address_y = height - 43 * mm

    pdf.setFont(
        font_min,
        11,
    )

    pdf.drawString(
        address_x,
        address_y,
        school.name,
    )

    pdf.drawString(
        address_x + em,
        address_y - 7 * mm,
        "学校長　様",
    )

    pdf.drawString(
        address_x + em,
        address_y - 14 * mm,
        "進学生徒　様",
    )


    # ========================================
    # 右側：差出人
    # ========================================

    sender_x = width - 82 * mm

    # 宛先ブロックより下から開始
    sender_y = height - 65 * mm

    pdf.setFont(
        font_min,
        10.5,
    )

    pdf.drawString(
        sender_x,
        sender_y,
        "学校法人　高千穂学園",
    )

    pdf.drawString(
        sender_x + em,
        sender_y - 7 * mm,
        "小林西高等学校",
    )

    pdf.drawString(
        sender_x + 2 * em,
        sender_y - 14 * mm,
        f"校長　{principal_name}",
    )
    # ========================================
    # 校長印
    # ========================================

    seal_path = finders.find(
        "publicity/images/principal_seal.png"
    )

    if seal_path:
        pdf.drawImage(
            seal_path,

            # 校長名の右側へ配置
            width - 45 * mm,
            sender_y - 20 * mm,

            # 印影サイズ
            width=22 * mm,
            height=22 * mm,

            mask="auto",
            preserveAspectRatio=True,
        )

    # ========================================
    # 件名
    # ========================================

    title_y = height - 100 * mm

    reiwa_fiscal_year = (
        fiscal_year - 2018
    )

    title = (
        f"令和{reiwa_fiscal_year}年度"
        "高千穂学園奨学生の募集について（ご依頼）"
    )

    pdf.setFont(
        font_gothic,
        12.5,
    )

    pdf.drawCentredString(
        width / 2,
        title_y,
        title,
    )

    # ========================================
    # 本文
    # ========================================

    body_style = ParagraphStyle(
        name="JapaneseBody",
        fontName=font_min,
        fontSize=10.5,
        leading=14,
        alignment=TA_LEFT,
        firstLineIndent=10,
        spaceAfter=0,
    )

    body_width = (
        width - 46 * mm
    )

    body_x = 23 * mm

    current_y = (
        title_y - 18 * mm
    )

    paragraphs = [
        (
            f"謹啓　{seasonal_greeting}、"
            "貴校におかれましてはますます"
            "ご清栄のこととお喜び申し上げます。"
            "また、平素より本校の教育活動につきましては、"
            "格別のご厚情を賜り、"
            "衷心より感謝申し上げます。"
        ),
        (
            f"さて本校では、令和{reiwa_fiscal_year}年度"
            "高千穂学園奨学生（文化・スポーツ）を"
            "募集いたしております。"
        ),
        (
            "そこでこの度、貴校の生徒様を"
            "高千穂学園奨学生として募集いたしたく、"
            "ご依頼申し上げる次第です。"
            "つきましては、下記の生徒様ならびに"
            "保護者の皆様に本件をご案内いただき、"
            "面談の機会を設けていただけると幸いです。"
        ),
        (
            "一方的な申し出にて誠に恐縮に存じますが、"
            "よろしくお取り計らい下さいますよう"
            "お願い申し上げます。"
        ),
        (
            "なお、御返信に際し校長不在の時は、"
            "教頭が対応いたします。"
            "（TEL 0984-22-5155）"
        ),
    ]

    for text in paragraphs:

        para = Paragraph(
            text,
            body_style,
        )

        para_width, para_height = (
            para.wrap(
                body_width,
                100 * mm,
            )
        )

        para.drawOn(
            pdf,
            body_x,
            current_y - para_height,
        )

        # 本文終了位置を更新
        current_y -= (
            para_height + 2.5 * mm
        )

    # ========================================
    # 「記」
    # ========================================

    # 重要：
    # body_yではなく、
    # 本文終了位置 current_y を使う
    current_y -= 2 * mm

    pdf.setFont(
        font_gothic,
        11,
    )

    pdf.drawCentredString(
        width / 2,
        current_y,
        "記",
    )

    current_y -= 12 * mm

    # ========================================
    # 生徒一覧 見出し
    # ========================================

    pdf.setFont(
        font_min,
        10.5,
    )

    pdf.drawString(
        74 * mm,
        current_y,
        "部活動名",
    )

    pdf.drawString(
        118 * mm,
        current_y,
        "生徒名",
    )

    current_y -= 8 * mm

    # ========================================
    # 生徒一覧
    # ========================================

    for index, student in enumerate(
        students,
        start=1,
    ):

        pdf.drawString(
            57 * mm,
            current_y,
            str(index),
        )

        pdf.drawString(
            73 * mm,
            current_y,
            student.club.name,
        )

        pdf.drawString(
            118 * mm,
            current_y,
            f"{student.name} さん",
        )

        current_y -= 8 * mm

    # ========================================
    # PDF終了
    # ========================================

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    filename = (
        f"{document_number}_"
        f"{school.name}.pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="{filename}"'
    )

    return response

def draw_scholarship_request_page(
    pdf,
    school,
    students,
    document_number,
    issue_date,
    fiscal_year,
    seasonal_greeting,
    principal_name,
):
    """
    高千穂学園奨学生募集依頼文書を
    PDFの1ページとして描画する。

    ※ showPage() / save() はここでは行わない。
    """

    width, height = A4

    # ============================================================
    # フォント
    # ============================================================

    font_min = "HeiseiMin-W3"
    font_gothic = "HeiseiKakuGo-W5"

    pdfmetrics.registerFont(
        UnicodeCIDFont(font_min)
    )

    pdfmetrics.registerFont(
        UnicodeCIDFont(font_gothic)
    )

    # 日本語1文字分の字下げ
    em = 11

    # ============================================================
    # 右上：文書番号・発行日
    # ============================================================

    pdf.setFont(
        font_min,
        10.5,
    )

    pdf.drawRightString(
        width - 25 * mm,
        height - 25 * mm,
        document_number,
    )

    reiwa_year = (
        issue_date.year - 2018
    )

    japanese_date = (
        f"令和{reiwa_year}年"
        f"{issue_date.month}月"
        f"{issue_date.day}日"
    )

    pdf.drawRightString(
        width - 25 * mm,
        height - 32 * mm,
        japanese_date,
    )

    # ============================================================
    # 左側：宛先
    # ============================================================

    address_x = 28 * mm
    address_y = height - 48 * mm

    pdf.setFont(
        font_min,
        11,
    )

    pdf.drawString(
        address_x,
        address_y,
        school.name,
    )

    pdf.drawString(
        address_x + em,
        address_y - 7 * mm,
        "学校長　様",
    )

    pdf.drawString(
        address_x + em,
        address_y - 14 * mm,
        "進学生徒　様",
    )

    # ============================================================
    # 右側：差出人
    # ============================================================

    sender_x = width - 82 * mm
    sender_y = height - 72 * mm

    pdf.setFont(
        font_min,
        10.5,
    )

    pdf.drawString(
        sender_x,
        sender_y,
        "学校法人　高千穂学園",
    )

    pdf.drawString(
        sender_x + em,
        sender_y - 7 * mm,
        "小林西高等学校",
    )

    pdf.drawString(
        sender_x + 2 * em,
        sender_y - 14 * mm,
        f"校長　{principal_name}",
    )

    # ============================================================
    # 校長印
    # ============================================================

    seal_path = finders.find(
        "publicity/images/principal_seal.png"
    )

    if seal_path:

        pdf.drawImage(
            seal_path,
            width - 45 * mm,
            sender_y - 20 * mm,
            width=22 * mm,
            height=22 * mm,
            mask="auto",
            preserveAspectRatio=True,
        )

    # ============================================================
    # 件名
    # ============================================================

    title_y = height - 108 * mm

    reiwa_fiscal_year = (
        fiscal_year - 2018
    )

    title = (
        f"令和{reiwa_fiscal_year}年度"
        "高千穂学園奨学生の募集について（ご依頼）"
    )

    pdf.setFont(
        font_gothic,
        12.5,
    )

    pdf.drawCentredString(
        width / 2,
        title_y,
        title,
    )

    # ============================================================
    # 本文
    # ============================================================

    body_style = ParagraphStyle(
        name="JapaneseBody",
        fontName=font_min,
        fontSize=10.5,
        leading=16,
        alignment=TA_LEFT,
        firstLineIndent=10.5,
        spaceAfter=0,
    )

    body_width = (
        width - 46 * mm
    )

    body_x = 23 * mm

    current_y = (
        title_y - 11 * mm
    )

    paragraphs = [
        (
            f"謹啓　{seasonal_greeting}、"
            "貴校におかれましてはますますご清栄のことと"
            "お喜び申し上げます。"
            "また、平素より本校の教育活動につきましては、"
            "格別のご厚情を賜り、心より感謝申し上げます。"
        ),
        (
            f"さて、本校では令和{reiwa_fiscal_year}年度"
            "高千穂学園奨学生（文化・スポーツ）を"
            "募集しております。"
        ),
        (
            "そこでこの度、貴校の生徒様を奨学生として"
            "募集いたしたく、ご依頼申し上げる次第です。"
            "つきましては、下記の生徒様ならびに"
            "保護者の皆様へ本件をご案内いただき、"
            "面談の機会を設けていただけますと幸いです。"
        ),
        (
            "誠に恐縮に存じますが、"
            "よろしくお取り計らいくださいますよう"
            "お願い申し上げます。"
        ),
        (
            "なお、御返信に際し校長不在の時は、"
            "教頭が対応いたします。"
            "（TEL 0984-22-5155）"
        ),
    ]

    for text in paragraphs:

        para = Paragraph(
            text,
            body_style,
        )

        _, para_height = para.wrap(
            body_width,
            100 * mm,
        )

        para.drawOn(
            pdf,
            body_x,
            current_y - para_height,
        )

        current_y -= (
            para_height + 2.5 * mm
        )

    # ============================================================
    # 「記」
    # ============================================================

    current_y -= 2 * mm

    pdf.setFont(
        font_gothic,
        11,
    )

    pdf.drawCentredString(
        width / 2,
        current_y,
        "記",
    )

    current_y -= 8 * mm

    # ============================================================
    # 生徒一覧を表形式で作成
    # ============================================================

    table_data = [
        [
            "No.",
            "部活動名",
            "生徒名",
        ]
    ]

    for index, student in enumerate(
        students,
        start=1,
    ):

        club_name = ""

        if student.club:
            club_name = student.club.name

        table_data.append(
            [
                str(index),
                club_name,
                f"{student.name} さん",
            ]
        )

    # ============================================================
    # 表
    # ============================================================

    student_table = Table(
        table_data,
        colWidths=[
            18 * mm,
            55 * mm,
            70 * mm,
        ],
        repeatRows=1,
    )

    student_table.setStyle(
        TableStyle(
            [
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    font_min,
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9.5,
                ),

                (
                    "LEADING",
                    (0, 0),
                    (-1, -1),
                    11,
                ),

                # 見出し
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    font_gothic,
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, 0),
                    "CENTER",
                ),

                # No.
                (
                    "ALIGN",
                    (0, 1),
                    (0, -1),
                    "CENTER",
                ),

                # 部活動・氏名
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "LEFT",
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                # 罫線
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),

                # 見出し背景
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    # ============================================================
    # 表のサイズを計算
    # ============================================================

    table_width, table_height = (
        student_table.wrap(
            width - 50 * mm,
            100 * mm,
        )
    )

    # ============================================================
    # 表を中央配置
    # ============================================================

    table_x = (
        width - table_width
    ) / 2

    table_y = (
        current_y - table_height
    )

    student_table.drawOn(
        pdf,
        table_x,
        table_y,
    )

    # ============================================================
    # 「以上」
    # ============================================================

    current_y = (
        table_y - 7 * mm
    )

    pdf.setFont(
        font_min,
        10.5,
    )

    pdf.drawRightString(
        width - 28 * mm,
        current_y,
        "以上",
    )

@club_advisor_required
@transaction.atomic
def scholarship_request_document_pdf(request):
    """
    1校分の奨学生募集依頼文書を正式発行し、PDFを生成する。
    """

    if request.method != "POST":
        return HttpResponse(
            "不正なアクセスです。",
            status=405,
        )

    form = ScholarshipRequestDocumentForm(
        request.POST
    )

    if not form.is_valid():
        return HttpResponse(
            "文書設定に入力エラーがあります。"
            f"<br>{form.errors}",
            status=400,
        )

    school = form.cleaned_data["school"]
    issue_date = form.cleaned_data["issue_date"]
    seasonal_greeting = form.cleaned_data[
        "seasonal_greeting"
    ]
    principal_name = form.cleaned_data[
        "principal_name"
    ]

    students = (
        ProspectiveStudent.objects
        .filter(
            junior_high_school=school,
            is_active=True,
        )
        .select_related(
            "club",
            "junior_high_school",
        )
        .order_by(
            "club__name",
            "name_kana",
            "name",
        )
    )

    if not students.exists():
        return HttpResponse(
            "対象生徒が登録されていません。",
            status=400,
        )

    fiscal_year = get_fiscal_year_from_date(
        issue_date
    )

    # 正式採番
    sequence, _ = (
        DocumentNumberSequence.objects
        .select_for_update()
        .get_or_create(
            fiscal_year=fiscal_year,
            defaults={
                "last_number": 0,
            },
        )
    )

    sequence.last_number += 1

    sequence.save(
        update_fields=[
            "last_number",
            "updated_at",
        ]
    )

    document_number = (
        f"小林西発第"
        f"{sequence.last_number:03d}"
        f"号"
    )

    # 発行履歴保存
    document = (
        ScholarshipRequestDocument.objects
        .create(
            school=school,
            fiscal_year=fiscal_year,
            document_number=document_number,
            issue_date=issue_date,
            seasonal_greeting=seasonal_greeting,
            principal_name=principal_name,
            created_by=request.teacher,
        )
    )

    document.students.set(students)

    # PDF作成
    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    draw_scholarship_request_page(
        pdf=pdf,
        school=school,
        students=students,
        document_number=document_number,
        issue_date=issue_date,
        fiscal_year=fiscal_year,
        seasonal_greeting=seasonal_greeting,
        principal_name=principal_name,
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    filename = (
        f"{document_number}_"
        f"{school.name}.pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="{quote(filename)}"'
    )

    return response

@system_admin_required
@transaction.atomic
def scholarship_document_batch_issue(request):
    """
    選択された生徒を中学校ごとにまとめ、
    1つの共通文書番号を使用して
    複数ページPDFとして正式発行する。

    ・文書番号は今回の発行処理で1つ
    ・複数校でも同じ文書番号を使用
    ・文書番号は事務と連携して手入力
    ・1校あたり最大10名
    ・すべて検証後にDB保存
    """

    if request.method != "POST":

        return redirect(
            "publicity:scholarship_document_student_select"
        )

    # ============================================================
    # POSTデータ
    # ============================================================

    student_ids = request.POST.getlist(
        "student_ids"
    )

    issue_date_text = request.POST.get(
        "issue_date",
        "",
    ).strip()

    seasonal_greeting = request.POST.get(
        "seasonal_greeting",
        "",
    ).strip()

    principal_name = request.POST.get(
        "principal_name",
        "",
    ).strip()

    # ★今回から共通文書番号は1つだけ
    document_number = request.POST.get(
        "document_number",
        "",
    ).strip()

    # ============================================================
    # 必須項目チェック
    # ============================================================

    if not student_ids:

        messages.error(
            request,
            "対象生徒が選択されていません。",
        )

        return redirect(
            "publicity:scholarship_document_student_select"
        )

    if not document_number:

        return HttpResponse(
            "文書番号が入力されていません。",
            status=400,
        )

    if not issue_date_text:

        return HttpResponse(
            "発行日が指定されていません。",
            status=400,
        )

    if not seasonal_greeting:

        return HttpResponse(
            "時候の挨拶が指定されていません。",
            status=400,
        )

    if not principal_name:

        return HttpResponse(
            "校長名が指定されていません。",
            status=400,
        )

    # ============================================================
    # 発行日
    # ============================================================

    try:

        issue_date = datetime.strptime(
            issue_date_text,
            "%Y-%m-%d",
        ).date()

    except ValueError:

        return HttpResponse(
            "発行日の形式が正しくありません。",
            status=400,
        )

    # ============================================================
    # 対象生徒取得
    # ============================================================

    students = list(
        ProspectiveStudent.objects
        .filter(
            id__in=student_ids,
            is_active=True,
        )
        .select_related(
            "junior_high_school",
            "club",
            "assigned_teacher",
        )
        .order_by(
            "junior_high_school__prefecture",
            "junior_high_school__city",
            "junior_high_school__name",
            "club__name",
            "name",
        )
    )

    if not students:

        return HttpResponse(
            "有効な対象生徒が見つかりません。",
            status=400,
        )

    # ============================================================
    # 中学校別にまとめる
    # ============================================================

    school_groups = {}

    for student in students:

        school = (
            student.junior_high_school
        )

        if school.id not in school_groups:

            school_groups[
                school.id
            ] = {
                "school": school,
                "students": [],
            }

        school_groups[
            school.id
        ]["students"].append(
            student
        )

    groups = list(
        school_groups.values()
    )

    # ============================================================
    # 1校10名まで
    # ============================================================

    for group in groups:

        school = group["school"]

        school_students = (
            group["students"]
        )

        if len(school_students) > 10:

            return HttpResponse(
                f"{school.name}の対象生徒が"
                "10名を超えています。"
                "1文書につき10名以内で"
                "選択してください。",
                status=400,
            )

    # ============================================================
    # 年度
    # ============================================================

    fiscal_year = (
        get_fiscal_year_from_date(
            issue_date
        )
    )

    # ============================================================
    # 文書番号の既存チェック
    #
    # 今回は同じ発行処理で複数校に
    # 同じ文書番号を使うため、
    # 「番号が存在するだけ」でNGにはしない。
    #
    # 同じ日付・同じ番号・同じ学校の
    # 二重発行だけ防止する。
    # ============================================================

    school_ids = [
        group["school"].id
        for group in groups
    ]

    duplicate_documents = (
        ScholarshipRequestDocument.objects
        .filter(
            document_number=document_number,
            issue_date=issue_date,
            school_id__in=school_ids,
        )
    )

    if duplicate_documents.exists():

        duplicate_school_names = (
            duplicate_documents
            .values_list(
                "school__name",
                flat=True,
            )
        )

        duplicate_text = "、".join(
            duplicate_school_names
        )

        return HttpResponse(
            "同じ文書がすでに発行されています。"
            f"<br>文書番号：{document_number}"
            f"<br>発行日：{issue_date}"
            f"<br>対象校：{duplicate_text}",
            status=400,
        )

    # ============================================================
    # PDF準備
    # ============================================================

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    # ============================================================
    # 正式発行
    #
    # ★すべての学校で同じ document_number を使用
    # ============================================================

    for group in groups:

        school = group["school"]

        school_students = (
            group["students"]
        )

        # --------------------------------------------------------
        # 発行履歴保存
        # --------------------------------------------------------

        document = (
            ScholarshipRequestDocument.objects
            .create(
                school=school,
                fiscal_year=fiscal_year,
                document_number=document_number,
                issue_date=issue_date,
                seasonal_greeting=(
                    seasonal_greeting
                ),
                principal_name=(
                    principal_name
                ),
                created_by=request.teacher,
                status="issued",
            )
        )

        document.students.set(
            school_students
        )

        # --------------------------------------------------------
        # PDF描画
        # --------------------------------------------------------

        draw_scholarship_request_page(
            pdf=pdf,
            school=school,
            students=school_students,

            # ★全学校で共通
            document_number=(
                document_number
            ),

            issue_date=issue_date,
            fiscal_year=fiscal_year,
            seasonal_greeting=(
                seasonal_greeting
            ),
            principal_name=(
                principal_name
            ),
        )

        # 1校につき1ページ
        pdf.showPage()

    # ============================================================
    # Sequence更新
    #
    # 手入力された
    # 「小林西発第100号」
    # の100を取得し、
    # 候補番号表示用Sequenceを追従させる。
    #
    # ※番号を巻き戻すことはしない。
    # ============================================================

    match = re.search(
        r"第\s*(\d+)\s*号",
        document_number,
    )

    if match:

        numeric_number = int(
            match.group(1)
        )

        sequence, _ = (
            DocumentNumberSequence.objects
            .select_for_update()
            .get_or_create(
                fiscal_year=fiscal_year,
                defaults={
                    "last_number": 0,
                },
            )
        )

        if (
            numeric_number
            > sequence.last_number
        ):

            sequence.last_number = (
                numeric_number
            )

            sequence.save(
                update_fields=[
                    "last_number",
                    "updated_at",
                ]
            )

    # ============================================================
    # PDF完了
    # ============================================================

    pdf.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    filename = (
        "高千穂学園奨学生募集依頼_"
        f"{document_number}_"
        f"{issue_date.strftime('%Y%m%d')}_"
        f"{len(groups)}校.pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="{quote(filename)}"'
    )

    return response

@system_admin_required
def scholarship_document_history(request):

    documents = (
        ScholarshipRequestDocument.objects
        .select_related(
            "school",
            "created_by",
        )
        .prefetch_related(
            "students",
        )
        .order_by(
            "-issue_date",
            "-created_at",
        )
    )

    keyword = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip()

    if keyword:
        documents = documents.filter(
            Q(document_number__icontains=keyword)
            | Q(school__name__icontains=keyword)
            | Q(students__name__icontains=keyword)
        ).distinct()

    if status:
        documents = documents.filter(
            status=status
        )

    return render(
        request,
        "publicity/scholarship_document_history.html",
        {
            "documents": documents,
            "keyword": keyword,
            "selected_status": status,
        },
    )

@system_admin_required
def scholarship_document_reprint(
    request,
    document_id,
):

    # ========================================
    # 対象文書取得
    # ========================================

    document = get_object_or_404(
        ScholarshipRequestDocument,
        pk=document_id,
    )

    # ========================================
    # 対象生徒取得
    # ========================================

    students = (
        document.students
        .select_related(
            "club",
            "junior_high_school",
        )
        .order_by(
            "club__name",
            "name_kana",
            "name",
        )
    )

    # ========================================
    # PDF準備
    # ========================================

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    # ========================================
    # PDF描画
    # ========================================

    draw_scholarship_request_page(
        pdf=pdf,
        school=document.school,
        students=students,
        document_number=(
            document.document_number
        ),
        issue_date=(
            document.issue_date
        ),

        # ★今回抜けていた部分
        fiscal_year=(
            document.fiscal_year
        ),

        seasonal_greeting=(
            document.seasonal_greeting
        ),
        principal_name=(
            document.principal_name
        ),
    )

    pdf.showPage()

    pdf.save()

    buffer.seek(0)

    # ========================================
    # PDF返却
    # ========================================

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    filename = (
        f"{document.document_number}_"
        f"{document.school.name}_再印刷.pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="{quote(filename)}"'
    )

    return response

@system_admin_required
@transaction.atomic
def scholarship_document_cancel(
    request,
    document_id,
):

    document = get_object_or_404(
        ScholarshipRequestDocument,
        pk=document_id,
    )

    if request.method != "POST":
        return HttpResponse(
            "不正なアクセスです。",
            status=405,
        )

    # すでに取消済みなら何もしない
    if document.status == "cancelled":

        messages.info(
            request,
            "この文書はすでに取消済みです。",
        )

        return redirect(
            "publicity:scholarship_document_history"
        )

    document.status = "cancelled"

    document.save(
        update_fields=[
            "status",
        ]
    )

    messages.success(
        request,
        (
            f"{document.document_number} "
            f"{document.school.name} の文書を"
            "取消しました。"
        ),
    )

    return redirect(
        "publicity:scholarship_document_history"
    )

@system_admin_required
@transaction.atomic
def scholarship_document_correct(
    request,
    document_id,
):

    original = get_object_or_404(
        ScholarshipRequestDocument,
        pk=document_id,
    )

    # 取消済みは訂正不可
    if original.status == "cancelled":

        messages.error(
            request,
            "取消済みの文書は訂正できません。",
        )

        return redirect(
            "publicity:scholarship_document_history"
        )

    # 旧版は再訂正しない
    if original.status == "corrected":

        messages.error(
            request,
            "この文書はすでに訂正済みです。"
            "最新の訂正版を訂正してください。",
        )

        return redirect(
            "publicity:scholarship_document_history"
        )

    # ========================================
    # 元文書の対象生徒
    # ========================================

    original_students = list(
        original.students
        .select_related(
            "club",
            "junior_high_school",
        )
        .order_by(
            "club__name",
            "name_kana",
            "name",
        )
    )

    # ========================================
    # 同中学校の現在有効な生徒
    # ========================================

    available_students = list(
        ProspectiveStudent.objects
        .filter(
            junior_high_school=original.school,
            is_active=True,
        )
        .select_related(
            "club",
            "junior_high_school",
        )
        .order_by(
            "club__name",
            "name_kana",
            "name",
        )
    )

    selected_student_ids = {
        student.id
        for student in original_students
    }

    # ========================================
    # POST：訂正版作成
    # ========================================

    if request.method == "POST":

        document_number = request.POST.get(
            "document_number",
            "",
        ).strip()

        issue_date_text = request.POST.get(
            "issue_date",
            "",
        ).strip()

        seasonal_greeting = request.POST.get(
            "seasonal_greeting",
            "",
        ).strip()

        principal_name = request.POST.get(
            "principal_name",
            "",
        ).strip()

        correction_reason = request.POST.get(
            "correction_reason",
            "",
        ).strip()

        student_ids = request.POST.getlist(
            "student_ids"
        )

        # ====================================
        # 必須チェック
        # ====================================

        if not document_number:
            messages.error(
                request,
                "文書番号を入力してください。",
            )
            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        if not issue_date_text:
            messages.error(
                request,
                "発行日を入力してください。",
            )
            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        if not seasonal_greeting:
            messages.error(
                request,
                "時候の挨拶を入力してください。",
            )
            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        if not principal_name:
            messages.error(
                request,
                "校長名を入力してください。",
            )
            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        if not correction_reason:
            messages.error(
                request,
                "訂正理由を入力してください。",
            )
            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        # ====================================
        # 発行日
        # ====================================

        try:
            issue_date = datetime.strptime(
                issue_date_text,
                "%Y-%m-%d",
            ).date()

        except ValueError:

            messages.error(
                request,
                "発行日の形式が正しくありません。",
            )

            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        # ====================================
        # 対象生徒
        #
        # 画面で選択があればそれを採用。
        # 何も取れなければ元文書を引き継ぐ。
        # ====================================

        if student_ids:

            correction_students = list(
                ProspectiveStudent.objects
                .filter(
                    id__in=student_ids,
                    junior_high_school=original.school,
                    is_active=True,
                )
                .select_related(
                    "club",
                    "junior_high_school",
                )
            )

        else:

            correction_students = (
                original_students
            )

        if not correction_students:

            messages.error(
                request,
                "訂正版に掲載する生徒がいません。",
            )

            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        if len(correction_students) > 10:

            messages.error(
                request,
                "対象生徒は10名以内にしてください。",
            )

            return redirect(
                "publicity:scholarship_document_correct",
                document_id=original.id,
            )

        # ====================================
        # 年度
        # ====================================

        fiscal_year = (
            get_fiscal_year_from_date(
                issue_date
            )
        )

        # ====================================
        # 新しいDBレコードとして訂正版作成
        # ====================================

        corrected_document = (
            ScholarshipRequestDocument.objects
            .create(
                school=original.school,
                fiscal_year=fiscal_year,
                document_number=document_number,
                issue_date=issue_date,
                seasonal_greeting=(
                    seasonal_greeting
                ),
                principal_name=(
                    principal_name
                ),
                created_by=request.teacher,
                status="issued",

                corrected_from=original,
                correction_reason=(
                    correction_reason
                ),
            )
        )

        corrected_document.students.set(
            correction_students
        )

        # ====================================
        # 元文書を訂正済みに変更
        # ====================================

        original.status = "corrected"

        original.save(
            update_fields=[
                "status",
            ]
        )

        messages.success(
            request,
            (
                f"{original.document_number} "
                f"{original.school.name} の訂正版を"
                f"作成しました。"
                f"新しい内部IDは "
                f"{corrected_document.id} です。"
            ),
        )

        return redirect(
            "publicity:scholarship_document_history"
        )

    # ========================================
    # GET：訂正画面表示
    # ========================================

    return render(
        request,
        "publicity/scholarship_document_correct.html",
        {
            "original": original,
            "selected_students": (
                original_students
            ),
            "selected_student_ids": (
                selected_student_ids
            ),
            "available_students": (
                available_students
            ),
        },
    )

# ============================================================
# 奨学生・面談管理一覧
# ============================================================

@club_advisor_required
def scholarship_management_list(request):
    """
    部顧問用
    奨学生候補・面談管理一覧

    原則として、
    ログイン中の教員が担当している募集対象生徒のみ表示する。
    """

    # --------------------------------------------------------
    # 検索条件
    # --------------------------------------------------------

    keyword = (
        request.GET
        .get("q", "")
        .strip()
    )

    club_id = (
        request.GET
        .get("club", "")
        .strip()
    )

    status = (
        request.GET
        .get("status", "")
        .strip()
    )


    # --------------------------------------------------------
    # 基本QuerySet
    #
    # 部顧問は自分が担当する生徒のみ表示
    # --------------------------------------------------------

    students = (
        ProspectiveStudent.objects
        .filter(
            is_active=True,
            assigned_teacher=request.teacher,
        )
        .select_related(
            "junior_high_school",
            "club",
            "assigned_teacher",

            # 奨学生管理
            "scholarship_assignment",

            # 奨学生ランク
            "scholarship_assignment__interview_rank",
            "scholarship_assignment__current_rank",
            "scholarship_assignment__final_rank",

            # 寮費区分
            "scholarship_assignment__interview_dormitory_benefit",
            "scholarship_assignment__current_dormitory_benefit",
            "scholarship_assignment__final_dormitory_benefit",
        )
        .order_by(
            "club__name",
            "junior_high_school__name",
            "name_kana",
            "name",
        )
    )


    # --------------------------------------------------------
    # キーワード検索
    # --------------------------------------------------------

    if keyword:

        students = students.filter(

            Q(
                name__icontains=keyword
            )

            | Q(
                name_kana__icontains=keyword
            )

            | Q(
                junior_high_school__name__icontains=keyword
            )

            | Q(
                club__name__icontains=keyword
            )
        )


    # --------------------------------------------------------
    # 部活動絞り込み
    # --------------------------------------------------------

    if club_id.isdigit():

        students = students.filter(
            club_id=club_id
        )


    # --------------------------------------------------------
    # 進行状況絞り込み
    # --------------------------------------------------------

    if status:

        # 「未対応」の場合は、
        # ScholarshipAssignment自体がまだ存在しない生徒も含める
        if status == "not_started":

            students = students.filter(

                Q(
                    scholarship_assignment__isnull=True
                )

                | Q(
                    scholarship_assignment__status=(
                        "not_started"
                    )
                )
            )

        else:

            students = students.filter(
                scholarship_assignment__status=(
                    status
                )
            )


    # --------------------------------------------------------
    # 部活動選択肢
    #
    # ログイン教員が担当している生徒に使われている
    # 部活動のみ表示
    # --------------------------------------------------------

    clubs = (
        Club.objects
        .filter(
            prospective_students__assigned_teacher=(
                request.teacher
            ),
            prospective_students__is_active=True,
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    # --------------------------------------------------------
    # 件数集計
    # --------------------------------------------------------

    total_count = students.count()

    not_started_count = (
        students.filter(
            Q(
                scholarship_assignment__isnull=True
            )
            | Q(
                scholarship_assignment__status=(
                    "not_started"
                )
            )
        )
        .count()
    )

    interview_count = (
        students.filter(
            scholarship_assignment__status__in=[
                "interview_scheduled",
                "interviewed",
                "temporary_accepted",
            ]
        )
        .count()
    )

    adjusting_count = (
        students.filter(
            scholarship_assignment__status=(
                "adjusting"
            )
        )
        .count()
    )

    finalized_count = (
        students.filter(
            scholarship_assignment__status__in=[
                "conference_confirmed",
                "finalized",
                "accepted",
            ]
        )
        .count()
    )


    # --------------------------------------------------------
    # ステータス選択肢
    # ScholarshipAssignmentと同じ内容
    # --------------------------------------------------------

    status_choices = [
        (
            "",
            "すべて",
        ),
        (
            "not_started",
            "未対応",
        ),
        (
            "rank_set",
            "ランク設定済",
        ),
        (
            "interview_scheduled",
            "面談予定",
        ),
        (
            "interviewed",
            "面談済",
        ),
        (
            "temporary_accepted",
            "仮承諾済",
        ),
        (
            "adjusting",
            "ランク調整中",
        ),
        (
            "conference_confirmed",
            "連絡会確認済",
        ),
        (
            "finalized",
            "最終確定",
        ),
        (
            "accepted",
            "正式承諾",
        ),
        (
            "declined",
            "辞退",
        ),
    ]


    # --------------------------------------------------------
    # Template
    # --------------------------------------------------------

    context = {

        "students": students,

        "clubs": clubs,

        "keyword": keyword,

        "selected_club": club_id,

        "selected_status": status,

        "status_choices": (
            status_choices
        ),

        # 件数
        "total_count": (
            total_count
        ),

        "not_started_count": (
            not_started_count
        ),

        "interview_count": (
            interview_count
        ),

        "adjusting_count": (
            adjusting_count
        ),

        "finalized_count": (
            finalized_count
        ),
    }


    return render(
        request,
        (
            "publicity/"
            "scholarship_management_list.html"
        ),
        context,
    )

# ============================================================
# 奨学生・面談 個人管理
# ============================================================

@club_advisor_required
def scholarship_assignment_detail(request, student_id):

    teacher = request.teacher

    # --------------------------------------------------------
    # 対象生徒取得
    #
    # 部顧問
    #   → 自分の担当生徒のみ
    #
    # 広報管理者・システム管理者
    #   → 全生徒
    # --------------------------------------------------------

    student_queryset = (
        ProspectiveStudent.objects
        .select_related(
            "junior_high_school",
            "club",
            "assigned_teacher",
            "registered_by",
        )
        .filter(
            is_active=True,
        )
    )

    if teacher.role not in {
        "publicity_admin",
        "system_admin",
    }:

        student_queryset = student_queryset.filter(
            Q(assigned_teacher=teacher)
            | Q(registered_by=teacher)
        )

    student = get_object_or_404(
        student_queryset,
        id=student_id,
    )


    # --------------------------------------------------------
    # 奨学生管理レコード取得
    #
    # 初回アクセス時にはまだ存在しないため、
    # ここで自動作成する
    # --------------------------------------------------------

    assignment, created = (
        ScholarshipAssignment.objects
        .get_or_create(
            student=student,
        )
    )


    # --------------------------------------------------------
    # 使用中の奨学金ランク
    # --------------------------------------------------------

    scholarship_categories = (
        ScholarshipCategory.objects
        .filter(
            is_active=True
        )
        .order_by(
            "name"
        )
    )


    # --------------------------------------------------------
    # 使用中の寮費区分
    # --------------------------------------------------------

    dormitory_categories = (
        DormitoryBenefitCategory.objects
        .filter(
            is_active=True
        )
        .order_by(
            "name"
        )
    )


    # --------------------------------------------------------
    # 面談履歴
    # --------------------------------------------------------

    interviews = (
        assignment.interviews
        .select_related(
            "interviewer",
            "presented_rank",
            "presented_dormitory_benefit",
        )
        .all()
    )


    # --------------------------------------------------------
    # ランク変更履歴
    # --------------------------------------------------------

    rank_histories = (
        assignment.rank_histories
        .select_related(
            "previous_rank",
            "new_rank",
            "changed_by",
        )
        .all()
    )


    # --------------------------------------------------------
    # 寮費変更履歴
    # --------------------------------------------------------

    dormitory_histories = (
        assignment.dormitory_benefit_histories
        .select_related(
            "previous_benefit",
            "new_benefit",
            "changed_by",
        )
        .all()
    )


    # --------------------------------------------------------
    # 面談前条件の登録
    # --------------------------------------------------------

    if request.method == "POST":

        action = request.POST.get(
            "action"
        )

        if action == "set_initial_conditions":

            rank_id = request.POST.get(
                "interview_rank"
            )

            dormitory_id = request.POST.get(
                "interview_dormitory_benefit"
            )

            # ----------------------------------------------------
            # 変更前の値を保持
            # ----------------------------------------------------

            old_rank = assignment.current_rank

            old_dormitory_benefit = (
                assignment.current_dormitory_benefit
            )

            # ----------------------------------------------------
            # 新しいランク取得
            # ----------------------------------------------------

            rank = None

            if rank_id:

                rank = get_object_or_404(
                    ScholarshipCategory,
                    id=rank_id,
                    is_active=True,
                )

            # ----------------------------------------------------
            # 新しい寮費区分取得
            # ----------------------------------------------------

            dormitory_benefit = None

            if dormitory_id:

                dormitory_benefit = get_object_or_404(
                    DormitoryBenefitCategory,
                    id=dormitory_id,
                    is_active=True,
                )

            # ----------------------------------------------------
            # ランク変更履歴
            # ----------------------------------------------------

            if old_rank != rank:

                # 新しいランクが設定される場合のみ履歴を作る
                if rank is not None:

                    ScholarshipRankHistory.objects.create(
                        assignment=assignment,
                        previous_rank=old_rank,
                        new_rank=rank,
                        reason="面談前条件の設定・変更",
                        changed_by=teacher,
                    )

            # ----------------------------------------------------
            # 寮費区分変更履歴
            # ----------------------------------------------------

            if old_dormitory_benefit != dormitory_benefit:

                # 新しい寮費区分が設定される場合のみ履歴を作る
                if dormitory_benefit is not None:

                    DormitoryBenefitHistory.objects.create(
                        assignment=assignment,
                        previous_benefit=old_dormitory_benefit,
                        new_benefit=dormitory_benefit,
                        reason="面談前条件の設定・変更",
                        changed_by=teacher,
                    )

            # ----------------------------------------------------
            # 面談前条件を保存
            # ----------------------------------------------------

            assignment.interview_rank = rank

            assignment.current_rank = rank

            assignment.interview_dormitory_benefit = (
                dormitory_benefit
            )

            assignment.current_dormitory_benefit = (
                dormitory_benefit
            )

            if rank is not None:

                assignment.status = "rank_set"

            else:

                assignment.status = "not_started"

            assignment.save()

            messages.success(
                request,
                "面談前の奨学生条件を保存しました。",
            )

            return redirect(
                "publicity:scholarship_assignment_detail",
                student_id=student.id,
            )


    # --------------------------------------------------------
    # Template
    # --------------------------------------------------------

    context = {

        "teacher": teacher,

        "student": student,

        "assignment": assignment,

        "scholarship_categories": (
            scholarship_categories
        ),

        "dormitory_categories": (
            dormitory_categories
        ),

        "interviews": interviews,

        "rank_histories": (
            rank_histories
        ),

        "dormitory_histories": (
            dormitory_histories
        ),

        "assignment_created": created,
    }


    return render(
        request,
        "publicity/scholarship_assignment_detail.html",
        context,
    )