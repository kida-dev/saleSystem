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
            "scholarship_category",
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
    keyword = request.GET.get("q", "").strip()
    prefecture = request.GET.get("prefecture", "").strip()

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
        schools = schools.filter(
            Q(name__icontains=keyword)
            | Q(city__icontains=keyword)
            | Q(official_address__icontains=keyword)
            | Q(school_code__icontains=keyword)
        )
    else:
        # 未入力時に全国の学校を大量返却しない
        schools = schools.none()

    schools = schools[:30]

    results = [
        {
            "id": school.id,
            "name": school.name,
            "prefecture": school.prefecture,
            "city": school.city,
            "principal_name": (
                school.principal_name
                or ""
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
                f"（{school.prefecture}"
                f"{school.city}）"
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