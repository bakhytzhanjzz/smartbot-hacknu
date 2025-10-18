# analytics/tasks.py
from celery import shared_task
from .services import llm_client  # реализуем ниже
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from candidates.models import BotMessage, Application
from analytics.models import RelevanceResult

channel_layer = get_channel_layer()

@shared_task
def analyze_application_task(application_id: int):
    """
    Начальная аналитика: извлечь данные вакансии и кандидата, сгенерировать первые вопросы
    и записать initial bot message(s). Также рассчитает initial relevance (можно quick rule-based).
    """
    try:
        application = Application.objects.get(pk=application_id)
    except Application.DoesNotExist:
        return

    vacancy = application.vacancy
    candidate = application.candidate

    # вызов LLM-адаптера (реализация ниже)
    questions = llm_client.generate_questions(vacancy, candidate, history=[])
    # сохранить сообщения и послать их через channel layer
    for q in questions:
        BotMessage.objects.create(application=application, sender="bot", text=q, metadata={"stage": "initial"})
        async_to_sync(channel_layer.group_send)(f"application_{application.id}", {
            "type": "bot_message",
            "text": q,
            "meta": {"stage": "initial"},
        })

    # compute initial relevance
    result = llm_client.compute_relevance(vacancy, candidate, messages=[])
    RelevanceResult.objects.update_or_create(
        application=application,
        defaults={
            "score": result.get("score", 0.0),
            "reasons": result.get("reasons", []),
            "summary": result.get("summary", ""),
        }
    )
    # push relevance update
    async_to_sync(channel_layer.group_send)(f"application_{application.id}", {
        "type": "relevance_update",
        "score": result.get("score", 0.0),
        "reasons": result.get("reasons", []),
        "summary": result.get("summary", ""),
    })


@shared_task
def process_candidate_message_task(application_id: int, text: str, meta: dict = None):
    """
    Когда кандидат отвечает, отправляем ответ в LLM для анализа и следующего вопроса.
    """
    try:
        application = Application.objects.get(pk=application_id)
    except Application.DoesNotExist:
        return

    vacancy = application.vacancy
    candidate = application.candidate

    # сохраняем кандидатское сообщение (в случае, если не было)
    BotMessage.objects.create(application=application, sender="candidate", text=text, metadata=meta or {})

    # вызов адаптера LLM: получаем ответ/вопрос от бота
    bot_responses = llm_client.handle_candidate_reply(vacancy, candidate, text, history=[])
    # bot_responses может быть список сообщений
    for resp in bot_responses:
        BotMessage.objects.create(application=application, sender="bot", text=resp, metadata={"stage": "followup"})
        async_to_sync(channel_layer.group_send)(f"application_{application_id}", {
            "type": "bot_message",
            "text": resp,
            "meta": {"stage": "followup"},
        })

    # после получения ответов можно пересчитать релевантность
    result = llm_client.compute_relevance(vacancy, candidate, messages=list(application.messages.all().values("sender", "text", "created_at")))
    RelevanceResult.objects.update_or_create(application=application, defaults={
        "score": result.get("score", 0.0),
        "reasons": result.get("reasons", []),
        "summary": result.get("summary", ""),
    })
    async_to_sync(channel_layer.group_send)(f"application_{application_id}", {
        "type": "relevance_update",
        "score": result.get("score", 0.0),
        "reasons": result.get("reasons", []),
        "summary": result.get("summary", ""),
    })
