from django.shortcuts import render
from .models import JuniorHighSchool

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
    schools = JuniorHighSchool.objects.prefetch_related("classes").all()

    return render(request, "publicity/school_list.html", {
        "schools": schools
    })


def label_select(request):
    schools = JuniorHighSchool.objects.all()

    return render(request, "publicity/label_select.html", {
        "schools": schools
    })


def label_pdf(request):
    school_ids = request.GET.getlist("school_ids")

    if school_ids:
        schools = JuniorHighSchool.objects.filter(id__in=school_ids).order_by("number", "id")
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

        principal = school.principal_name or ""

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