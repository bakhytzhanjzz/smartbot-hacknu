from django.contrib import admin
from .models import Employer

@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("id", "company_name", "user", "website", "created_at")
    search_fields = ("company_name", "user__username")
    list_filter = ("created_at",)
