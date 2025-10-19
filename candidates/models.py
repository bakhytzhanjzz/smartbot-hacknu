# candidates/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from jobs.models import Vacancy


class Candidate(models.Model):
    """
    Модель кандидата с расширенными полями для анализа
    """
    EMPLOYMENT_TYPE_CHOICES = (
        ('office', 'Офис'),
        ('remote', 'Удаленно'),
        ('hybrid', 'Гибрид'),
        ('any', 'Любой'),
    )

    name = models.CharField(max_length=255, verbose_name="ФИО")
    email = models.EmailField(verbose_name="Email", db_index=True)
    phone = models.CharField(max_length=64, blank=True, verbose_name="Телефон")
    resume_text = models.TextField(blank=True, verbose_name="Текст резюме")
    city = models.CharField(max_length=128, blank=True, verbose_name="Город", db_index=True)
    experience_years = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Опыт работы (лет)",
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    education = models.TextField(blank=True, verbose_name="Образование")
    languages = models.JSONField(default=list, blank=True, verbose_name="Языки")

    # Новые поля для улучшенного анализа
    preferred_employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='any',
        verbose_name="Предпочитаемый формат работы"
    )
    expected_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Ожидаемая зарплата"
    )
    skills = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Навыки"
    )
    willing_to_relocate = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Готов к переезду"
    )
    notice_period = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Период отработки (дней)"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Кандидат"
        verbose_name_plural = "Кандидаты"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["city"]),
            models.Index(fields=["experience_years"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def has_complete_profile(self):
        return all([
            self.name,
            self.email,
            self.resume_text,
            self.city,
            self.experience_years is not None
        ])


APPLICATION_STATUS_CHOICES = (
    ("new", "Новый"),
    ("chat_in_progress", "Чат с ботом"),
    ("reviewed", "Просмотрен"),
    ("rejected", "Отклонен"),
    ("hired", "Принят"),
    ("no_response", "Нет ответа в чате"),
)


class Application(models.Model):
    """
    Модель отклика на вакансию
    """
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="Вакансия"
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="Кандидат"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отклика")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    status = models.CharField(
        max_length=32,
        choices=APPLICATION_STATUS_CHOICES,
        default="new",
        verbose_name="Статус",
        db_index=True
    )
    meta = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Метаданные"
    )

    # Поля для отслеживания прогресса
    initial_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Начальный балл",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    final_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Финальный балл",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    chat_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата завершения чата"
    )

    class Meta:
        verbose_name = "Отклик"
        verbose_name_plural = "Отклики"
        indexes = [
            models.Index(fields=["vacancy"]),
            models.Index(fields=["candidate"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["final_score"]),
        ]
        unique_together = ("vacancy", "candidate")

    def __str__(self):
        return f"Отклик {self.id} — {self.candidate} -> {self.vacancy.title}"

    @property
    def has_active_chat(self):
        return hasattr(self, 'chat_session') and self.chat_session.is_active

    @property
    def current_score(self):
        return self.final_score or self.initial_score or 0


class ChatSession(models.Model):
    """
    Сессия чата между кандидатом и ботом для конкретного отклика
    """
    SESSION_STATUS_CHOICES = (
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('abandoned', 'Прервана'),
        ('timeout', 'Таймаут'),
    )

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='chat_session',
        verbose_name="Отклик"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(default=True, verbose_name="Активна", db_index=True)
    status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS_CHOICES,
        default='active',
        verbose_name="Статус сессии"
    )

    # Поля для управления диалогом
    current_question_index = models.IntegerField(default=0, verbose_name="Текущий вопрос")
    total_questions = models.IntegerField(default=0, verbose_name="Всего вопросов")
    questions_answered = models.IntegerField(default=0, verbose_name="Отвечено вопросов")

    # Метаданные сессии
    session_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Данные сессии"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя активность"
    )

    class Meta:
        verbose_name = "Сессия чата"
        verbose_name_plural = "Сессии чатов"
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["last_activity"]),
        ]

    def __str__(self):
        status = "активна" if self.is_active else "завершена"
        return f"Чат для {self.application} ({status})"

    def mark_completed(self):
        self.is_active = False
        self.status = 'completed'
        self.save()

        self.application.chat_completed_at = self.updated_at
        self.application.status = 'reviewed'
        self.application.save()


class BotMessage(models.Model):
    """
    Сообщения в чате между ботом и кандидатом
    """
    MESSAGE_TYPE_CHOICES = (
        ('welcome', 'Приветствие'),
        ('question', 'Вопрос'),
        ('info', 'Информация'),
        ('clarification', 'Уточнение'),
        ('completion', 'Завершение'),
        ('response', 'Ответ кандидата'),
    )

    # Делаем chat_session необязательным для обратной совместимости
    chat_session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Сессия чата",
        null=True,  # Добавляем null для существующих записей
        blank=True  # Разрешаем пустое значение в формах
    )

    # Сохраняем старую связь с application для обратной совместимости
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Отклик",
        null=True,  # Временно разрешаем null
        blank=True
    )

    sender = models.CharField(
        max_length=20,
        choices=(("bot", "Бот"), ("candidate", "Кандидат")),
        verbose_name="Отправитель",
        db_index=True
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='info',
        verbose_name="Тип сообщения"
    )
    text = models.TextField(verbose_name="Текст сообщения")

    # Поля для вопросов
    is_question = models.BooleanField(default=False, verbose_name="Это вопрос")
    question_category = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Категория вопроса"
    )
    expected_answer_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Тип ожидаемого ответа"
    )

    # Связь с родительским сообщением
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name="Родительское сообщение"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Прочитано")

    # Метаданные
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Метаданные"
    )

    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чатов"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["chat_session", "created_at"]),
            models.Index(fields=["application", "created_at"]),
            models.Index(fields=["sender"]),
            models.Index(fields=["is_question"]),
            models.Index(fields=["message_type"]),
        ]

    def __str__(self):
        sender = "Бот" if self.sender == "bot" else "Кандидат"
        return f"[{self.created_at.strftime('%H:%M')}] {sender}: {self.text[:50]}"

    def mark_as_read(self):
        if not self.read_at:
            self.read_at = models.DateTimeField(auto_now=True)
            self.save()

    @property
    def is_answered(self):
        if not self.is_question or self.sender != 'bot':
            return False
        return self.replies.filter(sender='candidate').exists()


class CandidateResponse(models.Model):
    """
    Детализированные ответы кандидата на вопросы бота
    """
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='candidate_responses',
        verbose_name="Отклик"
    )
    question_message = models.ForeignKey(
        BotMessage,
        on_delete=models.CASCADE,
        related_name='candidate_responses',
        verbose_name="Вопрос бота"
    )
    answer_text = models.TextField(verbose_name="Ответ кандидата")

    # Анализ ответа
    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Тональность ответа"
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Уверенность ответа",
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )

    # Извлеченные данные
    extracted_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Извлеченные данные"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата ответа")

    class Meta:
        verbose_name = "Ответ кандидата"
        verbose_name_plural = "Ответы кандидатов"
        indexes = [
            models.Index(fields=["application", "created_at"]),
        ]
        unique_together = ("application", "question_message")

    def __str__(self):
        return f"Ответ {self.id} на вопрос {self.question_message.id}"