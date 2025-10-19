# candidates/views.py
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Candidate, Application, BotMessage, ChatSession, CandidateResponse
from .serializers import (
    CandidateSerializer,
    ApplicationSerializer,
    BotMessageSerializer,
    ChatSessionSerializer,
    CandidateResponseSerializer,
    ChatMessageSerializer
)
from analytics.tasks import analyze_application_task, process_chat_completion_task
from analytics.services.chat_service import ChatService


class CandidateViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления кандидатами.
    """
    queryset = Candidate.objects.all().order_by('-created_at')
    serializer_class = CandidateSerializer
    permission_classes = [AllowAny]  # AllowAny для всего
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['email', 'city', 'experience_years']
    search_fields = ['name', 'email', 'resume_text', 'skills']

    def get_queryset(self):
        """
        Оптимизация запроса для кандидатов.
        """
        return Candidate.objects.all().select_related().prefetch_related(
            'applications'
        ).order_by('-created_at')


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления откликами на вакансии.
    """
    queryset = Application.objects.select_related(
        'candidate', 'vacancy'
    ).prefetch_related(
        'messages', 'chat_session', 'candidate_responses'
    ).all().order_by('-created_at')

    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]  # AllowAny для всего
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['vacancy', 'status', 'candidate']
    search_fields = [
        'candidate__name',
        'candidate__email',
        'vacancy__title'
    ]

    def perform_create(self, serializer):
        """
        Создание отклика и запуск фонового анализа.
        """
        with transaction.atomic():
            application = serializer.save()

            # Запускаем анализ в фоне
            task = analyze_application_task.delay(application.id)

            # Сохраняем ID задачи в метаданные
            application.meta.update({
                'analysis_task_id': task.id,
                'created_from_ip': self.get_client_ip()
            })
            application.save()

    def get_queryset(self):
        """
        Оптимизация queryset в зависимости от действия.
        """
        queryset = super().get_queryset()

        # Для списка - минимальные данные
        if self.action == 'list':
            queryset = queryset.only(
                'id', 'status', 'created_at', 'initial_score', 'final_score',
                'candidate__name', 'candidate__email', 'vacancy__title'
            )

        return queryset

    @action(detail=True, methods=['GET'])
    def messages(self, request, pk=None):
        """
        Получение сообщений чата для отклика.
        """
        application = self.get_object()
        messages = application.messages.all().order_by('created_at')
        serializer = BotMessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['GET'])
    def chat_session(self, request, pk=None):
        """
        Получение информации о чат-сессии отклика.
        """
        application = self.get_object()

        if not hasattr(application, 'chat_session'):
            return Response(
                {"detail": "Чат-сессия не найдена для этого отклика"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ChatSessionSerializer(application.chat_session)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def start_chat(self, request, pk=None):
        """
        Ручной запуск чат-сессии для отклика.
        """
        application = self.get_object()

        if hasattr(application, 'chat_session'):
            return Response(
                {"detail": "Чат-сессия уже существует"},
                status=status.HTTP_400_BAD_REQUEST
            )

        chat_service = ChatService()
        chat_session = chat_service.initialize_chat_for_application(application.id)

        if chat_session:
            serializer = ChatSessionSerializer(chat_session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"detail": "Не удалось инициализировать чат-сессию"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['GET'])
    def analysis_results(self, request, pk=None):
        """
        Получение результатов анализа отклика.
        """
        from analytics.models import RelevanceResult

        application = self.get_object()

        try:
            relevance_result = RelevanceResult.objects.get(application=application)
            return Response({
                "score": relevance_result.score,
                "summary": relevance_result.summary,
                "reasons": relevance_result.reasons,
                "created_at": relevance_result.created_at
            })
        except RelevanceResult.DoesNotExist:
            return Response(
                {"detail": "Результаты анализа еще не готовы"},
                status=status.HTTP_404_NOT_FOUND
            )

    def get_client_ip(self):
        """
        Получение IP адреса клиента.
        """
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class ChatSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для чтения чат-сессий.
    """
    queryset = ChatSession.objects.select_related(
        'application',
        'application__candidate',
        'application__vacancy'
    ).prefetch_related(
        'messages'
    ).all().order_by('-created_at')

    serializer_class = ChatSessionSerializer
    permission_classes = [AllowAny]  # AllowAny для всего
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'status', 'application']

    @action(detail=True, methods=['GET'])
    def messages(self, request, pk=None):
        """
        Получение сообщений чат-сессии.
        """
        chat_session = self.get_object()
        messages = chat_session.messages.all().order_by('created_at')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def send_message(self, request, pk=None):
        """
        Отправка сообщения от кандидата в чат-сессию.
        """
        chat_session = self.get_object()

        if not chat_session.is_active:
            return Response(
                {"detail": "Чат-сессия завершена"},
                status=status.HTTP_400_BAD_REQUEST
            )

        message_text = request.data.get('message', '').strip()
        if not message_text:
            return Response(
                {"detail": "Сообщение не может быть пустым"},
                status=status.HTTP_400_BAD_REQUEST
            )

        chat_service = ChatService()
        result = chat_service.process_candidate_response(chat_session.id, message_text)

        # Если чат завершен, запускаем финальный анализ
        if result.get('status') == 'completed':
            process_chat_completion_task.delay(chat_session.application.id)

        return Response(result)

    @action(detail=True, methods=['POST'])
    def complete(self, request, pk=None):
        """
        Принудительное завершение чат-сессии.
        """
        chat_session = self.get_object()

        if not chat_session.is_active:
            return Response(
                {"detail": "Чат-сессия уже завершена"},
                status=status.HTTP_400_BAD_REQUEST
            )

        chat_session.mark_completed()
        process_chat_completion_task.delay(chat_session.application.id)

        return Response({"detail": "Чат-сессия завершена"})


class BotMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления сообщениями бота.
    """
    queryset = BotMessage.objects.select_related(
        'chat_session',
        'chat_session__application',
        'parent_message'
    ).all().order_by('-created_at')

    serializer_class = BotMessageSerializer
    permission_classes = [AllowAny]  # AllowAny для всего
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['chat_session', 'sender', 'message_type', 'is_question']

    def get_queryset(self):
        """
        Оптимизация queryset для сообщений.
        """
        queryset = super().get_queryset()

        if self.action == 'list':
            queryset = queryset.only(
                'id', 'sender', 'message_type', 'text', 'is_question',
                'created_at', 'chat_session_id'
            )

        return queryset


class CandidateResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для чтения ответов кандидатов.
    """
    queryset = CandidateResponse.objects.select_related(
        'application',
        'question_message'
    ).all().order_by('-created_at')

    serializer_class = CandidateResponseSerializer
    permission_classes = [AllowAny]  # AllowAny для всего
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['application', 'question_message__question_category']