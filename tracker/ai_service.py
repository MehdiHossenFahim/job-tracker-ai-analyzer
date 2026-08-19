"""
AI integration for the Job Application Tracker.

This module calls the Anthropic API (Claude) to analyze a job description and
extract a structured summary, required skills, experience level, key
technologies, and interview preparation suggestions.

To use this feature:
    1. Get an API key from https://console.anthropic.com/
    2. Put it in your .env file as ANTHROPIC_API_KEY=sk-ant-...
    3. Never commit your real .env file or API key to GitHub.

If no API key is configured, `analyze_job_description` raises AIServiceError,
which the view catches and reports back to the user as a friendly message.
"""

import json
import re

import requests
from django.conf import settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AIServiceError(Exception):
    """Raised when the AI service can't be reached or returns something unusable."""


ANALYSIS_SYSTEM_PROMPT = """You are an assistant embedded in a job-application-tracking tool.
Given a raw job description, extract structured information for the candidate.

Respond with ONLY a valid JSON object (no markdown fences, no commentary) with exactly these keys:
{
  "summary": "2-4 sentence plain-language summary of the role",
  "required_skills": ["skill 1", "skill 2", "..."],
  "required_experience": "one short sentence describing the experience level / years required",
  "key_technologies": ["tech 1", "tech 2", "..."],
  "interview_prep_suggestions": ["suggestion 1", "suggestion 2", "..."]
}

Keep each list to at most 8 concise items. If the job description does not mention
something, make a reasonable best-effort inference and say so briefly, or use an empty list.
"""

QUESTIONS_SYSTEM_PROMPT = """You are an assistant embedded in a job-application-tracking tool.
Given a raw job description, generate likely interview questions a candidate should prepare for.

Respond with ONLY a valid JSON object (no markdown fences, no commentary) with exactly this key:
{
  "interview_questions": ["question 1", "question 2", "..."]
}

Include a mix of behavioral, role-specific/technical, and company-fit questions.
Return at most 10 concise, realistic questions.
"""


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from the model's text response."""
    text = text.strip()
    # Strip markdown code fences if the model added them anyway.
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to grabbing the outermost { ... } block.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise AIServiceError("The AI response could not be parsed as JSON.")


def analyze_job_description(job_description: str, job_title: str = "", company_name: str = "") -> dict:
    """
    Calls the Anthropic API to analyze a job description.

    Returns a dict with keys: summary, required_skills (list), required_experience,
    key_technologies (list), interview_prep_suggestions (list).
    """
    if not job_description or not job_description.strip():
        raise AIServiceError("Please add a job description before running the AI analysis.")

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise AIServiceError(
            "No ANTHROPIC_API_KEY is configured. Add one to your .env file to enable AI analysis."
        )

    user_prompt = (
        f"Job Title: {job_title or 'N/A'}\n"
        f"Company: {company_name or 'N/A'}\n\n"
        f"Job Description:\n{job_description}"
    )

    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "system": ANALYSIS_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise AIServiceError(f"Could not reach the AI service: {exc}") from exc

    if response.status_code != 200:
        raise AIServiceError(
            f"AI service returned an error ({response.status_code}): {response.text[:300]}"
        )

    data = response.json()
    text_blocks = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
    raw_text = "\n".join(text_blocks)

    parsed = _extract_json(raw_text)

    def as_list(value):
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return {
        "summary": str(parsed.get("summary", "")).strip(),
        "required_skills": as_list(parsed.get("required_skills")),
        "required_experience": str(parsed.get("required_experience", "")).strip(),
        "key_technologies": as_list(parsed.get("key_technologies")),
        "interview_prep_suggestions": as_list(parsed.get("interview_prep_suggestions")),
    }


def generate_interview_questions(job_description: str, job_title: str = "", company_name: str = "") -> list:
    """
    Calls the Anthropic API to generate likely interview questions for a job description.
    Returns a list of question strings. (Optional AI feature: Interview Question Generation.)
    """
    if not job_description or not job_description.strip():
        raise AIServiceError("Please add a job description before generating interview questions.")

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise AIServiceError(
            "No ANTHROPIC_API_KEY is configured. Add one to your .env file to enable AI features."
        )

    user_prompt = (
        f"Job Title: {job_title or 'N/A'}\n"
        f"Company: {company_name or 'N/A'}\n\n"
        f"Job Description:\n{job_description}"
    )

    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "system": QUESTIONS_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise AIServiceError(f"Could not reach the AI service: {exc}") from exc

    if response.status_code != 200:
        raise AIServiceError(
            f"AI service returned an error ({response.status_code}): {response.text[:300]}"
        )

    data = response.json()
    text_blocks = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
    raw_text = "\n".join(text_blocks)
    parsed = _extract_json(raw_text)

    questions = parsed.get("interview_questions", [])
    if isinstance(questions, list):
        return [str(q) for q in questions]
    return []
