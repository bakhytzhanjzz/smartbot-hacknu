# analytics/tasks.py
import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from candidates.models import Application, BotMessage
from analytics.models import RelevanceResult
from analytics.services.llm_client import GeminiClient

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def analyze_application_task(self, application_id):
    """
    1) Выполняет LLM-анализ через GeminiClient.evaluate_fit(...).
    2) Сохраняет RelevanceResult с score и summary.
    3) Создаёт BotMessage с уточняющими вопросами, если LLM вернёт questions через generate_questions (необязательное).
    """
    try:
        app = Application.objects.select_related("vacancy", "candidate").get(pk=application_id)
    except Application.DoesNotExist:
        logger.error("Application %s not found", application_id)
        return {"error": "application_not_found"}

    vacancy = app.vacancy
    candidate = app.candidate

    llm_score = 0.0
    llm_summary = ""
    llm_questions = []

    try:
        llm = GeminiClient()
        vacancy_text = " ".join(filter(None, [
            getattr(vacancy, "title", ""),
            getattr(vacancy, "description", ""),
            f"City: {getattr(vacancy, 'city', '')}",
            f"Experience required: {getattr(vacancy, 'experience_years', '')}",
            f"Employment type: {getattr(vacancy, 'employment_type', '')}",
        ]))
        resume_text = candidate.resume_text or ""
        llm_result = llm.evaluate_fit(vacancy_text=vacancy_text, resume_text=resume_text)

        llm_score = float(llm_result.get("score", 0.0))
        llm_summary = llm_result.get("summary", "")

        try:
            if hasattr(llm, "generate_questions"):
                llm_questions = llm.generate_questions(vacancy=vacancy_text, candidate=resume_text) or []
        except Exception:
            logger.exception("LLM generate_questions failed (ignored)")

    except Exception as e:
        logger.exception("LLM augmentation failed for app %s: %s", application_id, e)
        llm_score = 0.0
        llm_summary = "LLM failed or not available"

    # -------------------------
    # Save RelevanceResult
    # -------------------------
    try:
        RelevanceResult.objects.update_or_create(
            application=app,
            defaults={
                "score": llm_score,
                "reasons": [],
                "summary": llm_summary[:400],
            }
        )
    except Exception:
        logger.exception("Failed to save RelevanceResult for app %s", application_id)

    # -------------------------
    # Save bot questions (if any) and push to channel group
    # -------------------------
    if llm_questions:
        channel_layer = get_channel_layer()
        group_name = f"application_{application_id}"
        for q in llm_questions:
            try:
                bm = BotMessage.objects.create(application=app, sender="bot", text=q)
                try:
                    async_to_sync(channel_layer.group_send)(
                        group_name,
                        {
                            "type": "bot.message",
                            "message": {
                                "id": bm.id,
                                "sender": bm.sender,
                                "text": bm.text,
                                "created_at": bm.created_at.isoformat(),
                            }
                        }
                    )
                except Exception:
                    logger.exception("Failed to push BotMessage to channel layer (ignored)")
            except Exception:
                logger.exception("Failed to create BotMessage (ignored)")

    logger.info(
        "Application %s analyzed successfully. LLM score %.1f",
        application_id, llm_score
    )

    return {
        "application_id": application_id,
        "llm_score": llm_score,
        "summary": llm_summary,
    }
