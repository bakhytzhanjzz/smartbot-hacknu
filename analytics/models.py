from django.db import models
from candidates.models import Application

class RelevanceResult(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="relevance")
    score = models.FloatField(help_text="0.0 - 100.0")
    reasons = models.JSONField(default=list, blank=True, help_text="List of reasons or mismatches")
    summary = models.TextField(blank=True, help_text="Short text summary for employer")
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Результат релевантности"
        verbose_name_plural = "Результаты релевантности"

    def __str__(self):
        return f"Relevance for App {self.application_id}: {self.score:.1f}%"
