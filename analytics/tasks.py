# analytics/tasks.py
import logging
from celery import shared_task
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from candidates.models import Application, BotMessage
from analytics.models import RelevanceResult
from analytics.services.llm_client import GeminiClient

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def analyze_application_task(self, application_id):
    """
    1) Выполняет rule-based анализ (город, опыт, title).
    2) Дозвоночивает LLM через GeminiClient.evaluate_fit(...) и получает llm_score/summary.
    3) Комбинирует результаты (по умолчанию 50/50).
    4) Сохраняет/обновляет RelevanceResult.
    5) Создаёт BotMessage с уточняющими вопросами, если LLM вернёт questions через generate_questions (необязательное).
    """
    try:
        app = Application.objects.select_related("vacancy", "candidate").get(pk=application_id)
    except Application.DoesNotExist:
        logger.error("Application %s not found", application_id)
        return {"error": "application_not_found"}

    vacancy = app.vacancy
    candidate = app.candidate

    # -------------------------
    # 1) Rule-based scoring
    # -------------------------
    base_score = 0.0
    reasons = []

    # city (25)
    try:
        if vacancy.city and candidate.city:
            if vacancy.city.strip().lower() == candidate.city.strip().lower():
                base_score += 25.0
            else:
                reasons.append({
                    "field": "city",
                    "expected": vacancy.city,
                    "actual": candidate.city,
                    "explanation": "candidate city differs from vacancy city"
                })
        else:
            base_score += 25.0  # neutral if no city constraint
    except Exception:
        logger.exception("Error during city check")

    # experience (30)
    try:
        req_exp = float(vacancy.experience_years or 0.0)
        cand_exp = float(candidate.experience_years or 0.0)
        if req_exp <= 0:
            base_score += 30.0
        else:
            ratio = min(cand_exp / req_exp, 1.0)
            base_score += 30.0 * ratio
            if ratio < 1.0:
                reasons.append({
                    "field": "experience",
                    "required": req_exp,
                    "actual": cand_exp,
                    "explanation": "candidate has less experience than required"
                })
    except Exception:
        logger.exception("Error during experience check")

    # title / keywords (20)
    try:
        title_ok = False
        if vacancy.title and candidate.resume_text:
            if vacancy.title.strip().lower() in candidate.resume_text.strip().lower():
                title_ok = True
        if title_ok:
            base_score += 20.0
        else:
            reasons.append({
                "field": "title",
                "explanation": "Title not mentioned in resume text"
            })
    except Exception:
        logger.exception("Error during title check")

    # education (10) - simple heuristic: if candidate.education not empty give points
    try:
        if candidate.education and candidate.education.strip():
            base_score += 10.0
        else:
            # do not penalize much, keep neutral
            pass
    except Exception:
        logger.exception("Error during education check")

    # languages (10) - simple heuristic: if languages present, give full points
    try:
        if candidate.languages:
            # if it's JSON list, give points
            if isinstance(candidate.languages, (list, tuple)) and len(candidate.languages) > 0:
                base_score += 10.0
        else:
            pass
    except Exception:
        logger.exception("Error during languages check")

    base_score = min(base_score, 100.0)

    # -------------------------
    # 2) LLM analysis (Gemini)
    # -------------------------
    llm_score = None
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
        # Expect llm_result = {"score": int/float, "summary": "text"}; be defensive
        llm_score = float(llm_result.get("score", base_score))
        llm_summary = llm_result.get("summary", "") or ""
        # optional: if GeminiClient exposes generate_questions(), try to call it
        try:
            if hasattr(llm, "generate_questions"):
                llm_questions = llm.generate_questions(vacancy=vacancy_text, candidate=resume_text) or []
        except Exception:
            # ignore questions errors
            logger.exception("LLM generate_questions failed (ignored)")
    except Exception as e:
        logger.exception("LLM augmentation failed for app %s: %s", application_id, e)
        # fallback: use base_score as llm_score to avoid dropping to 0
        llm_score = base_score
        llm_summary = "LLM failed or not available (fallback to rule-based)"

    # -------------------------
    # 3) Combine scores
    # -------------------------
    # Simple ensemble: average of rule and llm. If llm_score is None, fallback to base_score
    if llm_score is None:
        final_score = base_score
    else:
        final_score = (base_score + llm_score) / 2.0

    final_score = max(0.0, min(final_score, 100.0))

    # -------------------------
    # 4) Save RelevanceResult
    # -------------------------
    try:
        rr, created = RelevanceResult.objects.update_or_create(
            application=app,
            defaults={
                "score": final_score,
                "reasons": reasons,
                "summary": f"Rule-based score: {base_score:.1f}%. LLM score: {llm_score:.1f}%. {llm_summary[:400]}",
            }
        )
    except Exception:
        logger.exception("Failed to save RelevanceResult for app %s", application_id)

    # -------------------------
    # 5) Save bot questions (if any) and push to channel group
    # -------------------------
    if llm_questions:
        channel_layer = get_channel_layer()
        group_name = f"application_{application_id}"
        for q in llm_questions:
            try:
                bm = BotMessage.objects.create(application=app, sender="bot", text=q)
                # push into group (consumer should handle type 'bot.message' -> 'bot_message' or similar)
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
        "Application %s analyzed successfully. Final score %.1f (rule %.1f / llm %.1f)",
        application_id, final_score, base_score, llm_score or base_score
    )

    return {
        "application_id": application_id,
        "final_score": final_score,
        "rule_score": base_score,
        "llm_score": llm_score,
    }
