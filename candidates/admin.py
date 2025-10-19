# candidates/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Candidate, Application, ChatSession, BotMessage, CandidateResponse


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'city', 'experience_years',
        'preferred_employment_type', 'has_complete_profile', 'created_at'
    ]
    list_filter = [
        'city', 'experience_years', 'preferred_employment_type',
        'willing_to_relocate', 'created_at'
    ]
    search_fields = ['name', 'email', 'resume_text']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'email', 'phone', 'city')
        }),
        ('Профессиональная информация', {
            'fields': (
                'resume_text', 'experience_years', 'education',
                'skills', 'languages'
            )
        }),
        ('Предпочтения', {
            'fields': (
                'preferred_employment_type', 'expected_salary',
                'willing_to_relocate', 'notice_period'
            )
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_complete_profile(self, obj):
        return obj.has_complete_profile

    has_complete_profile.boolean = True
    has_complete_profile.short_description = 'Полный профиль'


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'candidate_name', 'vacancy_title', 'status',
        'current_score', 'has_active_chat', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'vacancy']
    search_fields = [
        'candidate__name', 'candidate__email', 'vacancy__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'chat_completed_at']
    raw_id_fields = ['vacancy', 'candidate']

    def candidate_name(self, obj):
        return obj.candidate.name

    candidate_name.short_description = 'Кандидат'

    def vacancy_title(self, obj):
        return obj.vacancy.title

    vacancy_title.short_description = 'Вакансия'

    def has_active_chat(self, obj):
        return obj.has_active_chat

    has_active_chat.boolean = True
    has_active_chat.short_description = 'Активный чат'


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'application_info', 'is_active', 'status',
        'questions_answered', 'total_questions', 'last_activity'
    ]
    list_filter = ['is_active', 'status', 'created_at']
    search_fields = [
        'application__candidate__name',
        'application__vacancy__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_activity']
    raw_id_fields = ['application']

    def application_info(self, obj):
        return f"{obj.application.candidate.name} -> {obj.application.vacancy.title}"

    application_info.short_description = 'Отклик'


class CandidateResponseInline(admin.TabularInline):
    model = CandidateResponse
    extra = 0
    readonly_fields = ['created_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BotMessage)
class BotMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'chat_session_info', 'sender', 'message_type',
        'is_question', 'text_preview', 'created_at'
    ]
    list_filter = ['sender', 'message_type', 'is_question', 'created_at']
    search_fields = ['text', 'chat_session__application__candidate__name']
    readonly_fields = ['created_at']
    raw_id_fields = ['chat_session', 'parent_message']
    inlines = [CandidateResponseInline]

    def chat_session_info(self, obj):
        if obj.chat_session:
            app = obj.chat_session.application
            return f"{app.candidate.name} -> {app.vacancy.title}"
        return "Нет сессии"

    chat_session_info.short_description = 'Чат сессия'

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    text_preview.short_description = 'Текст'


@admin.register(CandidateResponse)
class CandidateResponseAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'application_info', 'question_preview',
        'answer_preview', 'sentiment_score', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'answer_text',
        'question_message__text',
        'application__candidate__name'
    ]
    readonly_fields = ['created_at']
    raw_id_fields = ['application', 'question_message']

    def application_info(self, obj):
        return f"{obj.application.candidate.name} -> {obj.application.vacancy.title}"

    application_info.short_description = 'Отклик'

    def question_preview(self, obj):
        question = obj.question_message.text
        return question[:50] + "..." if len(question) > 50 else question

    question_preview.short_description = 'Вопрос'

    def answer_preview(self, obj):
        return obj.answer_text[:50] + "..." if len(obj.answer_text) > 50 else obj.answer_text

    answer_preview.short_description = 'Ответ'


# Опционально: можно добавить кастомные действия
def mark_chat_sessions_completed(modeladmin, request, queryset):
    for session in queryset:
        session.mark_completed()
    modeladmin.message_user(request, f"{queryset.count()} чат-сессий завершено")


mark_chat_sessions_completed.short_description = "Завершить выбранные чат-сессии"

ChatSessionAdmin.actions = [mark_chat_sessions_completed]