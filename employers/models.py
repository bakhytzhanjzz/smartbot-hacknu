from django.db import models
from django.conf import settings

class Employer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Работодатель"
        verbose_name_plural = "Работодатели"

    def __str__(self):
        return f"{self.company_name} ({self.user.username})"
