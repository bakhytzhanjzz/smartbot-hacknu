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
You are an expert HR analyst. Compare the following job vacancy with the candidate's resume
and estimate how well the candidate fits the position.

Return ONLY a JSON object in the following format:
{{
  "score": <0-100 integer>,
  "summary": "<short reasoning>"
}}

Vacancy:
{vacancy_text}

Resume:
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
