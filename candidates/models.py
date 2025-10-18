from django.db import models
from jobs.models import Vacancy

class Candidate(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    resume_text = models.TextField(blank=True)  # текст резюме
    city = models.CharField(max_length=128, blank=True)
    experience_years = models.FloatField(null=True, blank=True)
    education = models.TextField(blank=True)
    languages = models.JSONField(default=list, blank=True)  # e.g. [{"lang":"ru","level":"C1"}]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Кандидат"
        verbose_name_plural = "Кандидаты"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["city"]),
        ]

    def __str__(self):
        return f"{self.name} <{self.email}>"

APPLICATION_STATUS_CHOICES = (
    ("new", "New"),
    ("in_progress", "In Progress"),
    ("reviewed", "Reviewed"),
    ("rejected", "Rejected"),
    ("hired", "Hired"),
)

class Application(models.Model):
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, choices=APPLICATION_STATUS_CHOICES, default="new")
    meta = models.JSONField(default=dict, blank=True, help_text="Доп. данные, например raw form payload")

    class Meta:
        verbose_name = "Отклик"
        verbose_name_plural = "Отклики"
        indexes = [
            models.Index(fields=["vacancy"]),
            models.Index(fields=["candidate"]),
        ]
        unique_together = ("vacancy", "candidate")  # опционально: предотвратить дубли откликов

    def __str__(self):
        return f"Application {self.id} — {self.candidate} -> {self.vacancy.title}"

class BotMessage(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=16, choices=(("bot","bot"),("candidate","candidate")))
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Сообщение бота/кандидата"
        verbose_name_plural = "Сообщения"
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.created_at.isoformat()}] {self.sender}: {self.text[:50]}"
