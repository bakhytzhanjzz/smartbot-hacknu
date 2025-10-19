# analytics/admin.py
from django.contrib import admin
from .models import RelevanceResult


@admin.register(RelevanceResult)
class RelevanceResultAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'application_info', 'score', 'get_analysis_type',
        'created_at', 'updated_at'
    ]
    list_filter = ['score', 'created_at']
    search_fields = [
        'application__candidate__name',
        'application__vacancy__title',
        'summary'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['application']

    def application_info(self, obj):
        return f"{obj.application.candidate.name} -> {obj.application.vacancy.title}"

    application_info.short_description = 'Отклик'

    def get_analysis_type(self, obj):
        return obj.analysis_type

    get_analysis_type.short_description = 'Тип анализа'