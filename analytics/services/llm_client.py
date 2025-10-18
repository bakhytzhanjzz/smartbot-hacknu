# analytics/services/llm_client.py
import os
from typing import List, Dict

# ---- PLACEHOLDER FOR REAL GEMINI CLIENT ----
# TODO: implement real Gemini HTTP/SDK calls here using your key.
# Example structure:
# def call_gemini(prompt: str) -> dict:
#     # call Google/PaLM REST API (or other provider)
#     # return parsed response
#     pass

def generate_questions(vacancy: 'Vacancy', candidate: 'Candidate', history: List[Dict]) -> List[str]:
    """
    Возвращает список текстовых вопросов, которые бот должен задать первыми.
    Сейчас — rule-based quick fallback.
    """
    questions = []
    # city mismatch check
    vac_city = (vacancy.city or "").strip().lower()
    cand_city = (candidate.city or "").strip().lower()
    if vac_city and cand_city and vac_city != cand_city:
        questions.append(f"Вакансия в {vacancy.city}. Вы готовы рассмотреть переезд/работу из другого города?")

    # experience check
    if vacancy.experience_years is not None and candidate.experience_years is not None:
        if candidate.experience_years < vacancy.experience_years:
            questions.append(f"Требуется опыт от {vacancy.experience_years} лет, у вас {candidate.experience_years}. Рассматриваете обучение/стажировку?")

    # employment type
    if vacancy.employment_type and vacancy.employment_type.lower() == "full_time":
        questions.append("Работа предполагает полный рабочий день. Такой формат подходит?")

    if not questions:
        # fallback friendly message
        questions.append("Спасибо за отклик! Могу уточнить пару деталей, чтобы лучше понять релевантность вашей кандидатуры.")
    return questions

def handle_candidate_reply(vacancy: 'Vacancy', candidate: 'Candidate', text: str, history: List[Dict]) -> List[str]:
    """
    Обработка ответа кандидата — возвращает ответы бота или следующие вопросы.
    В реальной интеграции: отправляем prompt с текущим контекстом в LLM.
    """
    text = (text or "").lower()
    responses = []
    if "да" in text or "готов" in text or "готова" in text:
        responses.append("Отлично, спасибо — это поможет при оценке. Есть ли у вас дополнительные вопросы по вакансии?")
    else:
        responses.append("Спасибо за ответ, я учту это при расчёте релевантности.")
    return responses

def compute_relevance(vacancy: 'Vacancy', candidate: 'Candidate', messages: List[Dict]) -> Dict:
    """
    Простая rule-based оценка релевантности.
    Возвращает dict: {score: float, reasons: list, summary: str}
    """
    score = 0.0
    reasons = []

    weights = {
        "city": 25,
        "experience": 35,
        "employment_type": 20,
        "salary": 20,
    }
    total = sum(weights.values())

    # city
    vac_city = (vacancy.city or "").strip().lower()
    cand_city = (candidate.city or "").strip().lower()
    if vac_city:
        if cand_city == vac_city:
            score += weights["city"]
        else:
            # check if candidate explicitly said ready to relocate in messages
            willing = any("пере" in (m.get("text","").lower()) and ("да" in m.get("text","").lower() or "готов" in m.get("text","").lower()) for m in messages if m.get("sender")=="candidate")
            if willing:
                score += weights["city"] * 0.9
            else:
                reasons.append({"field":"city","expected":vacancy.city,"actual":candidate.city,"why":"not willing to relocate"})
    else:
        score += weights["city"]

    # experience
    if vacancy.experience_years is None:
        score += weights["experience"]
    else:
        if candidate.experience_years is None:
            reasons.append({"field":"experience","expected":vacancy.experience_years,"actual":None,"why":"candidate has not provided experience"})
        else:
            if candidate.experience_years >= vacancy.experience_years:
                score += weights["experience"]
            else:
                # partial
                ratio = candidate.experience_years / vacancy.experience_years
                score += weights["experience"] * ratio
                reasons.append({"field":"experience","expected":vacancy.experience_years,"actual":candidate.experience_years,"why":"less experience"})

    # employment_type — basic exact match
    if not vacancy.employment_type:
        score += weights["employment_type"]
    else:
        if candidate.__dict__.get("employment_type", "") == vacancy.employment_type:
            score += weights["employment_type"]
        else:
            # unknown candidate employment_type -> neutral
            score += weights["employment_type"] * 0.6

    # salary — if no salary info -> neutral
    score += weights["salary"] * 0.7

    final_score = (score / total) * 100.0
    summary = "Подходит" if final_score > 70 else "Частично подходит" if final_score > 40 else "Не подходит"
    return {"score": round(final_score, 1), "reasons": reasons, "summary": summary}
