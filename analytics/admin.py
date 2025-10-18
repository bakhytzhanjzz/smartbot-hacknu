from django.contrib import admin
from .models import RelevanceResult

@admin.register(RelevanceResult)
class RelevanceResultAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "score", "computed_at")
    list_filter = ("computed_at",)
    search_fields = ("application__candidate__name", "application__vacancy__title")
    readonly_fields = ("computed_at",)
