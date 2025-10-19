# candidates/serializers.py
from rest_framework import serializers
from .models import Candidate, Application, BotMessage, ChatSession, CandidateResponse


class CandidateSerializer(serializers.ModelSerializer):
    """Сериализатор для кандидата"""

    has_complete_profile = serializers.ReadOnlyField()

    class Meta:
        model = Candidate
        fields = [
            'id', 'name', 'email', 'phone', 'resume_text', 'city',
            'experience_years', 'education', 'languages',
            'preferred_employment_type', 'expected_salary', 'skills',
            'willing_to_relocate', 'notice_period', 'has_complete_profile',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApplicationSerializer(serializers.ModelSerializer):
    """Сериализатор для отклика"""

    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    vacancy_title = serializers.CharField(source='vacancy.title', read_only=True)
    has_active_chat = serializers.BooleanField(read_only=True)
    current_score = serializers.FloatField(read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'vacancy', 'candidate', 'candidate_name', 'candidate_email',
            'vacancy_title', 'status', 'initial_score', 'final_score',
            'current_score', 'has_active_chat', 'chat_completed_at',
            'created_at', 'updated_at', 'meta'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'initial_score',
            'final_score', 'chat_completed_at', 'has_active_chat',
            'current_score'
        ]


class BotMessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщений бота (базовый)"""

    class Meta:
        model = BotMessage
        fields = [
            'id', 'application', 'sender', 'text', 'created_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщений в чате (расширенный)"""

    is_answered = serializers.BooleanField(read_only=True)

    class Meta:
        model = BotMessage
        fields = [
            'id', 'sender', 'message_type', 'text', 'is_question',
            'question_category', 'expected_answer_type', 'is_answered',
            'parent_message', 'created_at', 'read_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'is_answered']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Сериализатор для чат-сессии"""

    application_id = serializers.IntegerField(source='application.id', read_only=True)
    candidate_name = serializers.CharField(source='application.candidate.name', read_only=True)
    vacancy_title = serializers.CharField(source='application.vacancy.title', read_only=True)
    unread_messages_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id', 'application_id', 'candidate_name', 'vacancy_title',
            'is_active', 'status', 'current_question_index', 'total_questions',
            'questions_answered', 'unread_messages_count', 'last_activity',
            'created_at', 'updated_at', 'session_data'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_unread_messages_count(self, obj):
        return obj.messages.filter(read_at__isnull=True, sender='candidate').count()


class CandidateResponseSerializer(serializers.ModelSerializer):
    """Сериализатор для ответов кандидатов"""

    question_text = serializers.CharField(source='question_message.text', read_only=True)
    candidate_name = serializers.CharField(source='application.candidate.name', read_only=True)

    class Meta:
        model = CandidateResponse
        fields = [
            'id', 'application', 'candidate_name', 'question_text',
            'answer_text', 'sentiment_score', 'confidence_score',
            'extracted_data', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']