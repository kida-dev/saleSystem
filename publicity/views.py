from django.shortcuts import render, get_object_or_404, redirect

from .models import JuniorHighSchool
from .models import JuniorHighClass
from .forms import JuniorHighSchoolForm, JuniorHighClassForm

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

import os
from django.conf import settings


def top(request):
    return render(request, "publicity/top.html")


def school_list(request):
    schools = JuniorHighSchool.objects.prefetch_related("classes").order_by("number", "id")

    return render(request, "publicity/school_list.html", {
        "schools": schools
    })


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


def school_delete(request, pk):
    school = get_object_or_404(JuniorHighSchool, pk=pk)
    school.delete()

    return redirect("publicity:school_list")


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


def label_select(request):
    schools = JuniorHighSchool.objects.all().order_by("number", "id")

    return render(request, "publicity/label_select.html", {
        "schools": schools
    })


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