from django.contrib import admin
from .models import Vacancy

@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "employer", "city",
        "employment_type", "experience_years",
        "salary_from", "salary_to", "is_active", "created_at"
    )
    search_fields = ("title", "employer__company_name", "city")
    list_filter = ("city", "employment_type", "is_active")
    ordering = ("-created_at",)
