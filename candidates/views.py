# candidates/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ApplicationCreateSerializer, ApplicationSerializer
from candidates.models import Candidate, Application
from jobs.models import Vacancy
from django.db import transaction
from utils.ws_token import generate_ws_token
from analytics.tasks import analyze_application_task  # celery task (ниже)

class ApplicationCreateAPIView(APIView):
    """
    POST /api/applications/
    Тело: { vacancy_id, name, email, phone, resume_text, city, experience_years, languages, meta }
    Возвращает: { application_id, ws_url, ws_token }
    """
    permission_classes = []  # allow any for candidates widget
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        vacancy = Vacancy.objects.get(pk=data["vacancy_id"])

        # В транзакции: создаём/получаем кандидата и создаём заявку
        with transaction.atomic():
            candidate, created = Candidate.objects.get_or_create(email=data["email"], defaults={
                "name": data.get("name", ""),
                "phone": data.get("phone", ""),
                "resume_text": data.get("resume_text", ""),
                "city": data.get("city", ""),
                "experience_years": data.get("experience_years"),
                "education": data.get("education", ""),
                "languages": data.get("languages", []),
            })

            application = Application.objects.create(
                vacancy=vacancy,
                candidate=candidate,
                meta=data.get("meta", {}),
            )

        # сгенерировать ws token и ws url
        token = generate_ws_token(application.id)
        # ws_url: формируем по протоколу и хосту — фронтэнд использует этот URL.
        # В локальной dev-среде это ws://localhost:8000/ws/applications/{application_id}/?token={token}
        ws_scheme = "wss" if not request.is_secure() else "wss"
        host = request.get_host()
        ws_url = f"ws://{host}/ws/applications/{application.id}/?token={token}"

        # триггерим фоновую задачу на анализ (Celery)
        try:
            analyze_application_task.delay(application.id)
        except Exception:
            # Если Celery не настроен — можно вызвать анализ синхронно или оставить
            pass

        return Response({
            "application_id": application.id,
            "ws_token": token,
            "ws_url": ws_url,
        }, status=status.HTTP_201_CREATED)
