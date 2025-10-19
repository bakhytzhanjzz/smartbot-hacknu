# analytics/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from candidates.models import Application


class RelevanceResult(models.Model):
    """
    Результат анализа соответствия кандидата вакансии
    """
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='relevance_result',
        verbose_name="Отклик"
    )
    score = models.FloatField(
        verbose_name="Балл релевантности",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    reasons = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Причины несоответствия"
    )
    summary = models.TextField(
        blank=True,
        verbose_name="Текстовая выжимка"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Метаданные анализа"
    )

    # Поля дат
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Результат анализа"
        verbose_name_plural = "Результаты анализов"
        indexes = [
            models.Index(fields=['score']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Анализ {self.application.id} - {self.score}%"

    @property
    def analysis_type(self):
        """Тип анализа из метаданных"""
        return self.metadata.get('analysis_type', 'initial')