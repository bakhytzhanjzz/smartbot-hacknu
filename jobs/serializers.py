# jobs/serializers.py
from rest_framework import serializers
from .models import Vacancy

class VacancySerializer(serializers.ModelSerializer):
    # временно указываем empty queryset, затем заменим в __init__
    employer_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Vacancy.objects.none(), source='employer'
    )
    employer = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Vacancy
        fields = (
            'id', 'employer', 'employer_id', 'title', 'description', 'city',
            'experience_years', 'employment_type', 'salary_from', 'salary_to',
            'requirements', 'created_at', 'is_active'
        )
        read_only_fields = ('id', 'created_at', 'employer')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Импортируем Employer здесь, чтобы избежать циклических импортов при импорте модулей
        try:
            from employers.models import Employer
            self.fields['employer_id'].queryset = Employer.objects.all()
        except Exception:
            # если импорт не сработал (например в ранней стадии миграций), оставляем пустой queryset
            self.fields['employer_id'].queryset = Vacancy.objects.none()

    def get_employer(self, obj):
        # возвращаем минимальную инфу об employer
        if getattr(obj, 'employer', None):
            return {
                "id": obj.employer_id,
                "company_name": getattr(obj.employer, "company_name", None)
            }
        return None
