# analytics/services/analysis_service.py
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Сервис для rule-based анализа соответствия кандидата и вакансии
    """

    @staticmethod
    def analyze_discrepancies(vacancy, candidate) -> Tuple[List[str], float]:
        """
        Анализирует базовые расхождения и возвращает preliminary score
        """
        discrepancies = []
        base_score = 100.0
        penalty_per_item = 5.0  # Уменьшил штраф

        # 1. Анализ локации (мягкая проверка)
        if hasattr(vacancy, 'city') and hasattr(candidate, 'city'):
            if vacancy.city and candidate.city and vacancy.city.lower() != candidate.city.lower():
                discrepancies.append(f"Локация: вакансия в {vacancy.city}, кандидат в {candidate.city}")
                base_score -= penalty_per_item

        # 2. Анализ опыта (мягкая проверка)
        if hasattr(vacancy, 'experience_years') and hasattr(candidate, 'experience_years'):
            if vacancy.experience_years and candidate.experience_years:
                if candidate.experience_years < vacancy.experience_years:
                    gap = vacancy.experience_years - candidate.experience_years
                    if gap > 1:  # Штраф только если разница больше 1 года
                        discrepancies.append(
                            f"Опыт: требуется {vacancy.experience_years} лет, у кандидата {candidate.experience_years} лет")
                        base_score -= penalty_per_item * min(gap, 2)  # макс. штраф 10%

        # 3. Анализ формата работы (информационно)
        if hasattr(vacancy, 'employment_type') and hasattr(candidate, 'preferred_employment_type'):
            if vacancy.employment_type and candidate.preferred_employment_type:
                if vacancy.employment_type != candidate.preferred_employment_type:
                    discrepancies.append(
                        f"Формат работы: вакансия - {vacancy.employment_type}, предпочтение кандидата - {candidate.preferred_employment_type}")
                    # Не штрафуем, только информируем

        # 4. Анализ зарплатных ожиданий (мягкая проверка)
        if hasattr(vacancy, 'salary_range') and hasattr(candidate, 'expected_salary'):
            if vacancy.salary_range and candidate.expected_salary:
                max_salary = getattr(vacancy, 'max_salary', None)
                if max_salary and candidate.expected_salary > max_salary * 1.2:  # +20% допустимо
                    discrepancies.append("Зарплатные ожидания выше предложения")
                    base_score -= penalty_per_item

        base_score = max(50.0, base_score)  # Минимальный балл 50%
        return discrepancies, base_score