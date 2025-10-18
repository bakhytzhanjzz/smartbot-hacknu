from django.contrib import admin
from .models import Candidate, Application, BotMessage

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "city", "experience_years", "created_at")
    search_fields = ("name", "email", "resume_text", "city")

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "vacancy", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("candidate__name", "candidate__email")

@admin.register(BotMessage)
class BotMessageAdmin(admin.ModelAdmin):
    list_display = ("application", "sender", "created_at")
    search_fields = ("text",)
