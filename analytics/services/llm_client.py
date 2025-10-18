import os
import json
import logging
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
        try:
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
            response = self.model.generate_content(prompt)

            if not response or not getattr(response, "text", None):
                return {"score": 75, "summary": "No response from model (fallback)"}

            text = response.text.strip()
            logger.info(f"Gemini raw response: {text[:200]}...")

            try:
                # Parse JSON from model output
                data = json.loads(text)
                score = int(data.get("score", 75))
                summary = data.get("summary", "")
                return {"score": score, "summary": summary}
            except json.JSONDecodeError:
                # If model didn't return JSON, just extract text
                return {"score": 80, "summary": text[:150]}

        except Exception as e:
            logger.exception(f"Gemini evaluation failed: {e}")
            return {"score": 75, "summary": f"LLM error: {e}"}
