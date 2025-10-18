# candidates/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from utils.ws_token import verify_ws_token
from candidates.models import Application, BotMessage
from asgiref.sync import sync_to_async
from analytics.tasks import process_candidate_message_task

class ApplicationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # token in query params
        query_string = self.scope.get("query_string", b"").decode()
        params = dict(x.split("=") for x in query_string.split("&") if "=" in x)
        token = params.get("token", None)
        data = verify_ws_token(token) if token else None
        if not data:
            await self.close(code=4001)
            return
        self.application_id = data["application_id"]
        self.group_name = f"application_{self.application_id}"

        # verify application exists
        app_exists = await sync_to_async(Application.objects.filter(pk=self.application_id).exists)()
        if not app_exists:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # ожидаем структуру: {"type":"candidate.message","text":"...","meta":{...}}
        msg_type = content.get("type")
        if msg_type == "candidate.message":
            text = content.get("text", "").strip()
            meta = content.get("meta", {})
            if not text:
                await self.send_json({"type": "error", "message": "empty_message"})
                return
            # сохранить сообщение синхронно в БД
            await sync_to_async(BotMessage.objects.create)(
                application_id=self.application_id,
                sender="candidate",
                text=text,
                metadata=meta,
            )
            # триггерить фоновую задачу, чтобы LLM сгенерировал ответ/вопрос
            try:
                await process_candidate_message_task.delay(self.application_id, text, meta)
            except Exception:
                # если Celery недоступен — можно вызвать обработчик локально (не делаем здесь)
                pass

            # подтвердить приём
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "message.from.candidate",
                    "text": text,
                    "meta": meta,
                }
            )
        else:
            await self.send_json({"type": "error", "message": "unknown_type"})

    # group message handler to broadcast candidate message back if needed
    async def message_from_candidate(self, event):
        await self.send_json({
            "type": "candidate.message",
            "text": event["text"],
            "meta": event.get("meta", {}),
        })

    # бот отправляет сообщения в группу (see tasks)
    async def bot_message(self, event):
        await self.send_json({
            "type": "bot.message",
            "text": event["text"],
            "meta": event.get("meta", {}),
        })

    # relevance update
    async def relevance_update(self, event):
        await self.send_json({
            "type": "relevance.update",
            "score": event["score"],
            "reasons": event.get("reasons", []),
            "summary": event.get("summary", ""),
        })
