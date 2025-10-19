# analytics/services/llm_client.py
import os
import json
import logging
import re
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Production-ready wrapper for Google Gemini LLM.
    Provides semantic evaluation between job descriptions and resumes.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def evaluate_fit(self, vacancy_text: str, resume_text: str) -> dict:
        """
        Compare a job vacancy with a candidate resume using Gemini.
        Returns a dict with {"score": int, "summary": str}.
        """
        prompt = f"""
You are an expert HR analyst. Your task is to evaluate how well a candidate fits a job vacancy. 

Follow these rules strictly:

1. **Experience**: 
   - If candidate's total years of experience >= required experience, add positive points.
   - If less than required, subtract points proportionally.

2. **Skills and Tools**:
   - Compare the candidate's skills, tools, and certifications with the vacancy requirements.
   - Match each required skill and tool; each match adds points.

3. **Job Title & Role Match**:
   - Check if candidate's current or past titles match or are closely related to the vacancy title.
   - Partial match counts partially.

4. **Industry Experience**:
   - If candidate has experience in the same industry as the vacancy, add points.
   - If experience is in a related industry, add partial points.

5. **Education**:
   - Consider minimum required degree if specified.
   - Extra points for higher or relevant education.

6. **Languages**:
   - Consider language requirements.
   - Bonus points if candidate exceeds required language level.

7. **Location**:
   - If candidate's city matches the vacancy, add points.
   - If remote is allowed, consider neutral.

8. **Soft skills / Extra factors**:
   - Consider certifications, notable achievements, and any extra relevant information mentioned in resume.

**Scoring**:
- Provide a **score from 0 to 100** indicating overall fit.
- Explain reasoning in a concise paragraph.
- Consider exceeding requirements (more experience, extra skills) as a positive factor.
- Penalize only if key requirements are missing (e.g., essential skill or experience).

**Output format**:
Return ONLY a JSON object in the following structure:
{{
"score": <integer 0-100>,
"summary": "<concise reasoning paragraph>"
}}

Vacancy:
{vacancy_text}

Candidate Resume:
{resume_text}
"""
        try:
            response = self.model.generate_content(prompt)
            text = getattr(response, "text", "").strip()
            logger.info(f"Gemini raw response: {text[:400]}...")

            if not text:
                raise ValueError("No response text from Gemini model")

            # Попытка прямого JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Пробуем вытащить JSON через regex
                match = re.search(r"\{.*\}", text, flags=re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group())
                    except json.JSONDecodeError:
                        data = {"score": 0, "summary": text[:400]}
                else:
                    data = {"score": 0, "summary": text[:400]}

            score = int(data.get("score", 0))
            summary = data.get("summary", text[:400])
            return {"score": score, "summary": summary}

        except Exception as e:
            logger.exception(f"Gemini evaluation failed: {e}")
            return {"score": 0, "summary": "LLM failed or not available"}

    def generate_questions(self, vacancy_text: str, resume_text: str, discrepancies: list = None) -> list:
        """
        Генерирует уточняющие вопросы на основе расхождений между вакансией и резюме.
        """
        prompt = f"""
Based on the job vacancy and candidate resume below, identify key discrepancies and generate 1-3 clarifying questions for the candidate.

Focus on:
- Location mismatch
- Experience gaps  
- Missing skills/qualifications
- Employment type preferences
- Salary expectations
- Willingness to relocate/commute
- Availability to start
- Willingness to learn missing skills

IMPORTANT: Generate questions in Russian language since the candidate is Russian-speaking.

Return ONLY a JSON array of questions in Russian:
["Вопрос 1?", "Вопрос 2?", "Вопрос 3?"]

Vacancy:
{vacancy_text}

Candidate Resume:
{resume_text}

Discrepancies to consider: {discrepancies or []}
"""
        try:
            response = self.model.generate_content(prompt)
            text = getattr(response, "text", "").strip()
            logger.info(f"Gemini questions raw response: {text[:200]}...")

            # Парсим JSON с вопросами
            try:
                questions = json.loads(text)
                if isinstance(questions, list):
                    return [str(q).strip() for q in questions[:3] if str(q).strip()]
            except json.JSONDecodeError:
                # Fallback: простой парсинг по строкам
                lines = text.split('\n')
                questions = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('[') and not line.startswith(']') and line != '[' and line != ']':
                        # Убираем кавычки и нумерацию
                        clean_line = re.sub(r'^[\d\-\*"]+\s*', '', line).strip('" \t\n\r,')
                        if clean_line and '?' in clean_line:
                            questions.append(clean_line)

                return questions[:3]

            return []

        except Exception as e:
            logger.exception(f"Gemini questions generation failed: {e}")
            return []

    def evaluate_with_chat_context(self, vacancy_text: str, resume_text: str, chat_responses: list) -> dict:
        """
        Оценка соответствия с учетом ответов кандидата из чата.
        """
        chat_context = "\n".join([f"Q&A: {resp}" for resp in chat_responses])

        prompt = f"""
You are an expert HR analyst. Evaluate candidate fit considering their additional responses from chat.

Candidate Resume:
{resume_text}

Chat Responses:
{chat_context}

Vacancy:
{vacancy_text}

Consider the candidate's clarifications from chat when scoring.
If they addressed discrepancies positively (e.g., willing to relocate, learn skills), adjust score accordingly.

Return JSON: {{"score": 0-100, "summary": "analysis with chat context"}}

**Important**: Be encouraging and constructive. If information is missing from the resume, 
don't penalize too harshly - assume the candidate might have the experience but didn't include it.
Focus on potential rather than just current match.

**Scoring Guidelines**:
- 80-100: Excellent match or high potential
- 60-79: Good match with some areas for discussion  
- 40-59: Partial match, needs clarification
- 20-39: Weak match but potential exists
- 0-19: Poor match

Always look for potential and transferable skills.

"""
        try:
            response = self.model.generate_content(prompt)
            text = getattr(response, "text", "").strip()

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", text, flags=re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group())
                    except json.JSONDecodeError:
                        data = {"score": 0, "summary": text[:400]}
                else:
                    data = {"score": 0, "summary": text[:400]}

            score = int(data.get("score", 0))
            summary = data.get("summary", text[:400])
            return {"score": score, "summary": summary}

        except Exception as e:
            logger.exception(f"Gemini evaluation with chat context failed: {e}")
            return {"score": 0, "summary": "LLM failed or not available"}