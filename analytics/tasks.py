# analytics/tasks.py
import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from candidates.models import Application, ChatSession, BotMessage, CandidateResponse
from analytics.models import RelevanceResult
from analytics.services.llm_client import GeminiClient
from analytics.services.analysis_service import AnalysisService
from analytics.services.chat_service import ChatService

logger = logging.getLogger(__name__)


# analytics/tasks.py (обновленная секция анализа)

@shared_task(bind=True)
def analyze_application_task(self, application_id):
    """
    Основная задача анализа отклика с интеграцией чат-бота.
    """
    try:
        app = Application.objects.select_related(
            "vacancy", "candidate"
        ).prefetch_related('chat_session').get(pk=application_id)
    except Application.DoesNotExist:
        logger.error("Application %s not found", application_id)
        return {"error": "application_not_found", "application_id": application_id}

    vacancy = app.vacancy
    candidate = app.candidate

    logger.info("Starting analysis for application %s: %s -> %s",
                application_id, candidate.email, vacancy.title)

    # -------------------------
    # 1. Rule-based предварительный анализ
    # -------------------------
    preliminary_score = 0.0
    discrepancies = []

    try:
        analysis_service = AnalysisService()
        discrepancies, preliminary_score = analysis_service.analyze_discrepancies(vacancy, candidate)

        # Сохраняем preliminary score в Application
        app.initial_score = preliminary_score
        app.save(update_fields=['initial_score'])

        logger.info("Preliminary analysis: score=%.1f, discrepancies=%d",
                    preliminary_score, len(discrepancies))

    except Exception as e:
        logger.exception("Rule-based analysis failed for app %s: %s", application_id, e)

    # -------------------------
    # 2. LLM-анализ через Gemini
    # -------------------------
    llm_score = 0.0
    llm_summary = ""
    llm_questions = []

    try:
        llm = GeminiClient()
        vacancy_text = _prepare_vacancy_text(vacancy)
        resume_text = candidate.resume_text or ""

        # Если есть активная чат-сессия с ответами, используем контекст
        chat_context_responses = []
        if hasattr(app, 'chat_session') and not app.chat_session.is_active:
            chat_context_responses = _get_chat_responses_for_analysis(app.chat_session)

        if chat_context_responses:
            # Анализ с учетом ответов из чата
            llm_result = llm.evaluate_with_chat_context(
                vacancy_text=vacancy_text,
                resume_text=resume_text,
                chat_responses=chat_context_responses
            )
            logger.info("Using chat context for LLM analysis (%d responses)",
                        len(chat_context_responses))
        else:
            # Стандартный анализ без чата
            llm_result = llm.evaluate_fit(
                vacancy_text=vacancy_text,
                resume_text=resume_text
            )

        llm_score = float(llm_result.get("score", 0.0))
        llm_summary = llm_result.get("summary", "")

        # ОБНОВЛЕННАЯ ЛОГИКА: Генерируем вопросы почти всегда
        if not hasattr(app, 'chat_session') or not app.chat_session.is_active:
            # Запускаем чат если:
            # 1. Есть расхождения ИЛИ
            # 2. LLM score < 80 ИЛИ
            # 3. Просто для сбора дополнительной информации
            should_start_chat = (
                    discrepancies or
                    llm_score < 80 or
                    len(resume_text.strip()) < 500  # короткое резюме
            )

            if should_start_chat:
                try:
                    llm_questions = llm.generate_questions(
                        vacancy_text=vacancy_text,
                        resume_text=resume_text,
                        discrepancies=discrepancies
                    ) or []
                    logger.info("Generated %d questions for chat", len(llm_questions))
                except Exception as e:
                    logger.warning("LLM questions generation failed: %s", e)

    except Exception as e:
        logger.exception("LLM analysis failed for app %s: %s", application_id, e)
        llm_score = preliminary_score
        llm_summary = f"LLM analysis failed: {str(e)}"

        # Если LLM упал, все равно запускаем чат для сбора информации
        if not hasattr(app, 'chat_session'):
            llm_questions = [
                "Расскажите подробнее о вашем опыте работы?",
                "Какие технологии и инструменты вы используете в работе?",
                "Что вас привлекло в нашей вакансии?"
            ]

    # -------------------------
    # 3. Сохранение финального результата
    # -------------------------
    final_score = llm_score
    try:
        with transaction.atomic():
            # Сохраняем финальный score в Application
            app.final_score = final_score
            if not hasattr(app, 'chat_session') or not app.chat_session.is_active:
                if llm_questions:  # Если есть вопросы, ставим статус чата
                    app.status = 'chat_in_progress'
                else:
                    app.status = 'reviewed'
            app.save(update_fields=['final_score', 'status'])

            # Сохраняем в RelevanceResult
            RelevanceResult.objects.update_or_create(
                application=app,
                defaults={
                    "score": final_score,
                    "reasons": discrepancies,
                    "summary": llm_summary[:1000],
                    "metadata": {
                        "preliminary_score": preliminary_score,
                        "discrepancies_count": len(discrepancies),
                        "analysis_type": "with_chat" if chat_context_responses else "initial",
                        "has_chat": bool(llm_questions),
                        "timestamp": timezone.now().isoformat(),
                    }
                }
            )

        logger.info("RelevanceResult saved for app %s with score %.1f",
                    application_id, final_score)

    except Exception as e:
        logger.exception("Failed to save results for app %s: %s", application_id, e)
        return {
            "error": "save_failed",
            "application_id": application_id,
            "llm_score": final_score
        }

    # -------------------------
    # 4. Инициализация чат-сессии если есть вопросы
    # -------------------------
    if llm_questions and not hasattr(app, 'chat_session'):
        try:
            _initialize_chat_session(app, llm_questions, discrepancies)
            logger.info("Chat session initialized with %d questions", len(llm_questions))
        except Exception as e:
            logger.exception("Failed to initialize chat session for app %s: %s",
                             application_id, e)

    # -------------------------
    # 5. Уведомление через Channels (если нужно)
    # -------------------------
    _notify_frontend(application_id, final_score, llm_summary)

    logger.info(
        "Application %s analysis completed. Final score: %.1f, Chat: %s",
        application_id, final_score, "initialized" if llm_questions else "not needed"
    )

    return {
        "application_id": application_id,
        "preliminary_score": preliminary_score,
        "llm_score": final_score,
        "summary": llm_summary,
        "discrepancies_count": len(discrepancies),
        "chat_initialized": bool(llm_questions and not hasattr(app, 'chat_session'))
    }


@shared_task(bind=True)
def process_chat_completion_task(self, application_id):
    """
    Задача для финального анализа после завершения чат-сессии
    """
    try:
        app = Application.objects.select_related(
            "vacancy", "candidate", "chat_session"
        ).get(pk=application_id)

        if not hasattr(app, 'chat_session'):
            logger.warning("No chat session found for app %s", application_id)
            return {"error": "no_chat_session", "application_id": application_id}

        chat_session = app.chat_session

        if chat_session.is_active:
            logger.warning("Chat session still active for app %s", application_id)
            return {"error": "chat_still_active", "application_id": application_id}

        # Запускаем финальный анализ
        return analyze_application_task(application_id)

    except Application.DoesNotExist:
        logger.error("Application %s not found for chat completion", application_id)
        return {"error": "application_not_found", "application_id": application_id}
    except Exception as e:
        logger.exception("Chat completion processing failed for app %s: %s", application_id, e)
        return {"error": "processing_failed", "application_id": application_id}


@shared_task
def timeout_chat_sessions():
    """
    Периодическая задача для обработки зависших чат-сессий
    """
    from django.utils import timezone
    from datetime import timedelta

    timeout_threshold = timezone.now() - timedelta(hours=24)

    expired_sessions = ChatSession.objects.filter(
        is_active=True,
        last_activity__lt=timeout_threshold
    )

    count = expired_sessions.count()

    for session in expired_sessions:
        try:
            session.is_active = False
            session.status = 'timeout'
            session.save()

            # Обновляем статус отклика
            session.application.status = 'no_response'
            session.application.save(update_fields=['status'])

            logger.info("Timed out chat session for app %s", session.application.id)

        except Exception as e:
            logger.exception("Failed to timeout chat session %s: %s", session.id, e)

    return {"timed_out_sessions": count}


# Вспомогательные функции
def _prepare_vacancy_text(vacancy) -> str:
    """Подготавливает текст вакансии для LLM"""
    return " ".join(filter(None, [
        getattr(vacancy, "title", ""),
        getattr(vacancy, "description", ""),
        f"Город: {getattr(vacancy, 'city', '')}",
        f"Требуемый опыт: {getattr(vacancy, 'experience_years', '')} лет",
        f"Тип занятости: {getattr(vacancy, 'employment_type', '')}",
        f"Зарплатная вилка: {getattr(vacancy, 'salary_range', '')}",
        f"Ключевые навыки: {getattr(vacancy, 'required_skills', '')}",
    ]))


def _get_chat_responses_for_analysis(chat_session):
    """Извлекает ответы кандидата из чат-сессии для анализа"""
    responses = []
    try:
        candidate_messages = chat_session.messages.filter(
            sender='candidate',
            message_type='response'
        ).select_related('parent_message')

        for msg in candidate_messages:
            if msg.parent_message:
                responses.append(
                    f"Вопрос: {msg.parent_message.text}\nОтвет: {msg.text}"
                )
    except Exception as e:
        logger.warning("Failed to extract chat responses: %s", e)

    return responses


def _initialize_chat_session(application, questions, discrepancies):
    """Инициализирует чат-сессию с вопросами"""
    try:
        with transaction.atomic():
            # Создаем чат-сессию
            chat_session = ChatSession.objects.create(
                application=application,
                total_questions=len(questions),
                session_data={
                    'initial_discrepancies': discrepancies,
                    'questions_generated_at': timezone.now().isoformat()
                }
            )

            # Обновляем статус отклика
            application.status = 'chat_in_progress'
            application.save(update_fields=['status'])

            # Создаем приветственное сообщение
            welcome_msg = BotMessage.objects.create(
                chat_session=chat_session,
                sender='bot',
                message_type='welcome',
                text="Привет! Спасибо за отклик на вакансию. Давайте уточним несколько моментов для лучшего понимания вашей кандидатуры.",
                is_question=False
            )

            # Создаем вопросы
            question_categories = ['location', 'experience', 'skills', 'preferences']
            for i, question in enumerate(questions):
                category = question_categories[i % len(question_categories)]
                BotMessage.objects.create(
                    chat_session=chat_session,
                    sender='bot',
                    message_type='question',
                    text=question,
                    is_question=True,
                    question_category=category,
                    expected_answer_type='text',
                    parent_message=welcome_msg
                )

            # Отправляем уведомление через Channels
            _notify_chat_initialized(application.id, chat_session.id)

            return chat_session

    except Exception as e:
        logger.exception("Failed to initialize chat session: %s", e)
        raise


def _notify_frontend(application_id, score, summary):
    """Уведомляет фронтенд о результате анализа"""
    try:
        channel_layer = get_channel_layer()
        group_name = f"application_{application_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "analysis.complete",
                "data": {
                    "application_id": application_id,
                    "score": score,
                    "summary": summary,
                    "timestamp": timezone.now().isoformat(),
                }
            }
        )
    except Exception as e:
        logger.debug("Frontend notification failed for app %s: %s", application_id, e)


def _notify_chat_initialized(application_id, chat_session_id):
    """Уведомляет фронтенд о инициализации чата"""
    try:
        channel_layer = get_channel_layer()
        group_name = f"application_{application_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "chat.initialized",
                "data": {
                    "application_id": application_id,
                    "chat_session_id": chat_session_id,
                    "timestamp": timezone.now().isoformat(),
                }
            }
        )
    except Exception as e:
        logger.debug("Chat initialization notification failed: %s", e)