# analytics/services/chat_service.py
import logging
from typing import Dict, List, Optional
from django.utils import timezone

from candidates.models import Application, ChatSession, BotMessage
from analytics.services.analysis_service import AnalysisService
from analytics.services.llm_client import GeminiClient

logger = logging.getLogger(__name__)


class ChatService:
    """
    Сервис для управления диалогом с кандидатом через чат-бот
    """

    def __init__(self):
        self.llm = GeminiClient()
        self.analysis_service = AnalysisService()

    def initialize_chat_for_application(self, application_id: int) -> Optional[ChatSession]:
        """
        Инициализирует чат-сессию для отклика
        """
        try:
            application = Application.objects.select_related('vacancy', 'candidate').get(pk=application_id)

            # Создаем или получаем чат-сессию
            chat_session, created = ChatSession.objects.get_or_create(
                application=application,
                defaults={'is_active': True}
            )

            if created:
                # Первичный анализ и генерация вопросов
                self._start_conversation(chat_session)

            return chat_session

        except Exception as e:
            logger.exception(f"Failed to initialize chat for application {application_id}: {e}")
            return None

    def _start_conversation(self, chat_session: ChatSession):
        """
        Начинает диалог с кандидатом
        """
        application = chat_session.application
        vacancy = application.vacancy
        candidate = application.candidate

        # Приветственное сообщение
        welcome_msg = BotMessage.objects.create(
            chat_session=chat_session,
            sender='bot',
            text=f"Привет! Спасибо за отклик на вакансию '{vacancy.title}'. Давайте уточним несколько моментов для лучшего понимания вашей кандидатуры.",
            is_question=False
        )

        # Анализ расхождений и генерация вопросов
        discrepancies, preliminary_score = self.analysis_service.analyze_discrepancies(vacancy, candidate)

        if discrepancies:
            # Генерируем вопросы через LLM
            vacancy_text = self._prepare_vacancy_text(vacancy)
            resume_text = candidate.resume_text or ""

            questions = self.llm.generate_questions(
                vacancy_text=vacancy_text,
                resume_text=resume_text,
                discrepancies=discrepancies
            )

            # Сохраняем вопросы в чат
            for i, question in enumerate(questions):
                BotMessage.objects.create(
                    chat_session=chat_session,
                    sender='bot',
                    text=question,
                    is_question=True
                )

        else:
            # Нет расхождений - сообщаем об этом
            BotMessage.objects.create(
                chat_session=chat_session,
                sender='bot',
                text="Отлично! Ваш профиль хорошо соответствует требованиям вакансии. Работодатель рассмотрит вашу кандидатуру в ближайшее время.",
                is_question=False
            )
            chat_session.is_active = False
            chat_session.save()

    def process_candidate_response(self, chat_session_id: int, candidate_response: str) -> Dict:
        """
        Обрабатывает ответ кандидата и генерирует следующий вопрос или завершает диалог
        """
        try:
            chat_session = ChatSession.objects.prefetch_related('messages').get(pk=chat_session_id)

            # Сохраняем ответ кандидата
            BotMessage.objects.create(
                chat_session=chat_session,
                sender='candidate',
                text=candidate_response,
                is_question=False
            )

            # Получаем следующий вопрос или завершаем диалог
            next_question = self._get_next_question(chat_session)

            if next_question:
                return {
                    'status': 'continue',
                    'next_question': next_question,
                    'session_active': True
                }
            else:
                # Завершаем диалог и запускаем финальный анализ
                chat_session.is_active = False
                chat_session.save()

                self._finalize_analysis(chat_session.application)

                return {
                    'status': 'completed',
                    'message': 'Спасибо за ответы! Ваши данные сохранены.',
                    'session_active': False
                }

        except Exception as e:
            logger.exception(f"Failed to process candidate response: {e}")
            return {'status': 'error', 'message': 'Произошла ошибка'}

    def _get_next_question(self, chat_session: ChatSession) -> Optional[str]:
        """
        Возвращает следующий вопрос для кандидата
        """
        # Простая логика - берем следующий неотвеченный вопрос
        bot_questions = chat_session.messages.filter(sender='bot', is_question=True)
        candidate_responses = chat_session.messages.filter(sender='candidate')

        # Находим первый вопрос без ответа
        for question in bot_questions:
            # Проверяем, есть ли ответ после этого вопроса
            question_time = question.created_at
            has_response = candidate_responses.filter(created_at__gt=question_time).exists()

            if not has_response:
                return question.text

        return None

    def _finalize_analysis(self, application: Application):
        """
        Запускает финальный анализ после завершения диалога
        """
        from analytics.tasks import analyze_application_task
        analyze_application_task.delay(application.id)

    def _prepare_vacancy_text(self, vacancy) -> str:
        """Подготавливает текст вакансии для LLM"""
        return " ".join(filter(None, [
            getattr(vacancy, "title", ""),
            getattr(vacancy, "description", ""),
            f"City: {getattr(vacancy, 'city', '')}",
            f"Experience required: {getattr(vacancy, 'experience_years', '')}",
            f"Employment type: {getattr(vacancy, 'employment_type', '')}",
        ]))