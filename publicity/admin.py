from django.contrib import admin
from .models import (
    Club,
    DeliveryMethod,
    DocumentType,
    DocumentHistory,
    DormitoryBenefitCategory,
    DormitoryBenefitHistory,
    JuniorHighSchool, 
    JuniorHighClass,
    ProspectiveStudent,
    ScholarshipAssignment,
    ScholarshipCategory,
    ScholarshipInterview,
    ScholarshipRankHistory,
    ScholarshipRequestDocument,
    Teacher,
    TeacherLoginEmail
)

admin.site.register(ScholarshipAssignment)
admin.site.register(ScholarshipRankHistory)
admin.site.register(ScholarshipInterview)
admin.site.register(DormitoryBenefitCategory)
admin.site.register(DormitoryBenefitHistory)

class TeacherLoginEmailInline(admin.TabularInline):
    model = TeacherLoginEmail
    extra = 1


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "employee_number",
        "name",
        "position",
        "club",
        "role",
        "is_active",
    )

    list_editable = (
        "role",
        "is_active",
    )

    list_filter = (
        "role",
        "position",
        "club",
        "is_active",
    )

    search_fields = (
        "name",
        "assignment",
        "responsibility",
        "club",
        "login_emails__email",
    )

    ordering = (
        "employee_number",
    )

    inlines = [
        TeacherLoginEmailInline,
    ]

@admin.register(TeacherLoginEmail)
class TeacherLoginEmailAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "email",
        "email_type",
        "is_primary",
        "is_allowed",
    )

    list_filter = (
        "email_type",
        "is_primary",
        "is_allowed",
    )

    search_fields = (
        "teacher__name",
        "email",
    )

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

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "updated_at",
    )

    list_editable = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    list_filter = (
        "is_active",
    )


@admin.register(ScholarshipCategory)
class ScholarshipCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "updated_at",
    )

    list_editable = (
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    list_filter = (
        "is_active",
    )


@admin.register(ProspectiveStudent)
class ProspectiveStudentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "name_kana",
        "junior_high_school",
        "club",
        "dormitory",
        "scholarship_category",
        "assigned_teacher",
        "registered_by",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "club",
        "dormitory",
        "scholarship_category",
        "junior_high_school",
        "assigned_teacher",
    )

    search_fields = (
        "name",
        "name_kana",
        "address",
        "junior_high_school__name",
        "assigned_teacher__name",
    )

    autocomplete_fields = (
        "junior_high_school",
        "assigned_teacher",
        "registered_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "updated_at",
    )

    list_editable = (
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    ordering = (
        "name",
    )


@admin.register(DeliveryMethod)
class DeliveryMethodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
    )

    list_editable = (
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


@admin.register(DocumentHistory)
class DocumentHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "document_type",
        "delivery_method",
        "sent_date",
        "sent_by",
        "created_at",
    )

    list_filter = (
        "document_type",
        "delivery_method",
        "sent_date",
        "sent_by",
    )

    search_fields = (
        "student__name",
        "student__junior_high_school__name",
        "document_type__name",
        "sent_by__name",
        "memo",
    )

    autocomplete_fields = (
        "student",
        "document_type",
        "delivery_method",
        "sent_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    date_hierarchy = "sent_date"

    ordering = (
        "-sent_date",
        "-created_at",
    )

@admin.register(ScholarshipRequestDocument)
class ScholarshipRequestDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "document_number",
        "school",
        "issue_date",
        "status",
        "corrected_from",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "issue_date",
        "school",
    )

    search_fields = (
        "document_number",
        "school__name",
        "students__name",
        "correction_reason",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    filter_horizontal = (
        "students",
    )

    ordering = (
        "-issue_date",
        "-created_at",
    )