from django.contrib import messages
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)

from .models import (
    Club,
    JuniorHighSchool,
    JuniorHighClass,
    ProspectiveStudent,
    Teacher,
)

from .forms import (
    JuniorHighSchoolForm,
    JuniorHighClassForm,
    ProspectiveStudentForm,
    TeacherPermissionFormSet,
)

from .decorators import (
    active_teacher_required,
    club_advisor_required,
    publicity_admin_required,
    system_admin_required,
)

from django.http import HttpResponse, JsonResponse
from io import BytesIO
from urllib.parse import quote
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

import os
from django.conf import settings


def top(request):
    teacher = None

    if request.user.is_authenticated:
        try:
            teacher = request.user.publicity_teacher
        except Teacher.DoesNotExist:
            teacher = None

    # システムを利用できるか
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

    # 広報機能を管理できるか
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

    # 教員・権限管理を操作できるか
    can_manage_permissions = (
        request.user.is_superuser
        or (
            teacher is not None
            and teacher.is_active
            and teacher.role == "system_admin"
        )
    )

    return render(
        request,
        "publicity/top.html",
        {
            "teacher": teacher,
            "can_use_system": can_use_system,
            "can_manage_publicity": can_manage_publicity,
            "can_manage_permissions": can_manage_permissions,
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