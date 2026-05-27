from django.contrib import admin
from .models import JuniorHighSchool, JuniorHighClass


class JuniorHighClassInline(admin.TabularInline):
    model = JuniorHighClass
    extra = 0


@admin.register(JuniorHighSchool)
class JuniorHighSchoolAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "name",
        "city",
        "principal_name",
        "tel",
        "third_grade_total",
    )
    search_fields = ("name", "city", "principal_name", "address")
    list_filter = ("city",)
    inlines = [JuniorHighClassInline]


@admin.register(JuniorHighClass)
class JuniorHighClassAdmin(admin.ModelAdmin):
    list_display = ("school", "class_name", "boys", "girls", "total")
    search_fields = ("school__name", "class_name")