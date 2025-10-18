from django.db import models
from employers.models import Employer

EMPLOYMENT_TYPE_CHOICES = (
    ("full_time", "Full time"),
    ("part_time", "Part time"),
    ("remote", "Remote"),
    ("contract", "Contract"),
    ("internship", "Internship"),
)

class Vacancy(models.Model):
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="vacancies")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)  # e.g. Алматы
    experience_years = models.FloatField(null=True, blank=True, help_text="Required minimal experience in years")
    employment_type = models.CharField(max_length=32, choices=EMPLOYMENT_TYPE_CHOICES, default="full_time")
    salary_from = models.IntegerField(null=True, blank=True)
    salary_to = models.IntegerField(null=True, blank=True)
    requirements = models.JSONField(default=list, blank=True)  # list of requirement strings
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["employment_type"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.employer.company_name}"
