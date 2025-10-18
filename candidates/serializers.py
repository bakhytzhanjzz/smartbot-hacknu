# candidates/serializers.py
from rest_framework import serializers
from .models import Candidate, Application, BotMessage

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ('id', 'name', 'email', 'phone', 'resume_text', 'city',
                  'experience_years', 'education', 'languages', 'created_at')
        read_only_fields = ('id', 'created_at')

class ApplicationSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer()
    vacancy = serializers.SerializerMethodField(read_only=True)
    # безопасный временный queryset, заменяем в __init__
    vacancy_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Application.objects.none(), source='vacancy'
    )
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Application
        fields = ('id', 'vacancy', 'vacancy_id', 'candidate', 'status', 'created_at', 'meta')
        read_only_fields = ('id', 'created_at', 'vacancy', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # импортируем Vacancy здесь, чтобы избежать циклических импортов
        try:
            from jobs.models import Vacancy
            self.fields['vacancy_id'].queryset = Vacancy.objects.all()
        except Exception:
            self.fields['vacancy_id'].queryset = Application.objects.none()

    def get_vacancy(self, obj):
        if obj.vacancy_id:
            return {
                "id": obj.vacancy_id,
                "title": getattr(obj.vacancy, "title", None),
                "city": getattr(obj.vacancy, "city", None),
            }
        return None

    def create(self, validated_data):
        candidate_data = validated_data.pop('candidate')
        # find or create candidate by email
        candidate, created = Candidate.objects.get_or_create(
            email=candidate_data.get('email'),
            defaults=candidate_data
        )
        # update candidate fields if provided
        for k, v in candidate_data.items():
            # update only when value is not None and different
            if v is not None and getattr(candidate, k, None) != v:
                setattr(candidate, k, v)
        candidate.save()
        application = Application.objects.create(candidate=candidate, **validated_data)
        return application

class BotMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotMessage
        fields = ('id', 'application', 'sender', 'text', 'created_at', 'metadata')
        read_only_fields = ('id', 'created_at')
