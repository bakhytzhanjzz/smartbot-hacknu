# candidates/serializers.py
from rest_framework import serializers
from .models import Candidate, Application, BotMessage
from jobs.models import Vacancy

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ["id", "name", "email", "phone", "resume_text", "city", "experience_years", "education", "languages", "created_at"]
        read_only_fields = ["id", "created_at"]

class ApplicationCreateSerializer(serializers.Serializer):
    # поля которые фронтэнд должен прислать при отклике
    vacancy_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=64, allow_blank=True, required=False)
    resume_text = serializers.CharField(allow_blank=True, required=False)
    city = serializers.CharField(max_length=128, allow_blank=True, required=False)
    experience_years = serializers.FloatField(required=False)
    education = serializers.CharField(allow_blank=True, required=False)
    languages = serializers.ListField(child=serializers.DictField(), required=False)
    meta = serializers.DictField(required=False)

    def validate_vacancy_id(self, value):
        try:
            Vacancy.objects.get(pk=value)
        except Vacancy.DoesNotExist:
            raise serializers.ValidationError("Vacancy not found")
        return value

class ApplicationSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer(read_only=True)
    class Meta:
        model = Application
        fields = ["id", "vacancy", "candidate", "status", "created_at", "meta"]
        read_only_fields = ["id", "created_at"]
