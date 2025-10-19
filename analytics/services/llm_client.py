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
"score": <integer 0-100>,
"summary": "<concise reasoning paragraph>"


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
