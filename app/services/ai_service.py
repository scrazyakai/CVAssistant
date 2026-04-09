import json
import re
from collections import Counter

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.models.schemas import CandidateProfile, MatchBreakdown


class AIService:
    def __init__(self, api_key: str, model: str) -> None:
        self.model_name = model
        self.llm = (
            ChatOpenAI(api_key=api_key, model=model, temperature=0)
            if api_key
            else None
        )

    async def extract_candidate_info(self, resume_text: str) -> CandidateProfile:
        if self.llm is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        prompt = [
            SystemMessage(
                content=(
                    "You are an expert recruitment assistant. Extract structured "
                    "candidate information from a resume. Return strict JSON only."
                )
            ),
            HumanMessage(
                content=(
                    "Extract the resume into JSON with keys: "
                    "basic_info{name,phone,email,address}, job_intention, "
                    "expected_salary, years_of_experience, education_background, "
                    "projects, skills, summary.\n\nResume:\n"
                    f"{resume_text[:14000]}"
                )
            ),
        ]
        content = await self.llm.ainvoke(prompt)
        parsed = self._parse_json(content.content)
        return CandidateProfile.model_validate(parsed)

    async def match_resume_to_job(
        self,
        resume_text: str,
        candidate: CandidateProfile,
        job_description: str,
    ) -> MatchBreakdown:
        if self.llm is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        prompt = [
            SystemMessage(
                content=(
                    "You are a hiring copilot. Compare the resume with the job "
                    "description and return strict JSON only."
                )
            ),
            HumanMessage(
                content=(
                    "Return JSON with keys: overall_score, keyword_match_score, "
                    "experience_relevance_score, education_score, strengths, gaps, "
                    "keywords, reasoning.\n\nJob description:\n"
                    f"{job_description[:6000]}\n\nCandidate profile:\n"
                    f"{candidate.model_dump_json(indent=2)}\n\nResume text:\n"
                    f"{resume_text[:10000]}"
                )
            ),
        ]
        content = await self.llm.ainvoke(prompt)
        parsed = self._parse_json(content.content)
        return MatchBreakdown.model_validate(parsed)

    @staticmethod
    def fallback_extract_candidate_info(resume_text: str) -> CandidateProfile:
        email = _first_match(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)
        phone = _first_match(r"(?:\+?\d[\d -]{8,}\d)", resume_text)
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        name = lines[0] if lines else None
        skills = _extract_skills(resume_text)
        projects = [line for line in lines if "project" in line.lower()][:5]
        education = [
            line
            for line in lines
            if any(
                token in line.lower()
                for token in ["university", "college", "phd", "master", "bachelor"]
            )
        ]
        years = _first_match(r"(\d+\+?\s*(?:years?))", resume_text)
        return CandidateProfile(
            basic_info={
                "name": name,
                "phone": phone,
                "email": email,
                "address": None,
            },
            years_of_experience=years,
            education_background=education,
            projects=projects,
            skills=skills,
            summary="Fallback extraction generated from regex and heuristics.",
        )

    @staticmethod
    def fallback_match_resume_to_job(
        resume_text: str,
        candidate: CandidateProfile,
        job_description: str,
    ) -> MatchBreakdown:
        resume_terms = _top_keywords(resume_text)
        jd_terms = _top_keywords(job_description)
        overlap = sorted(set(resume_terms) & set(jd_terms))
        keyword_score = min(len(overlap) * 12.5, 100)
        experience_score = 80 if candidate.years_of_experience else 50
        education_score = 80 if candidate.education_background else 50
        overall = round(keyword_score * 0.5 + experience_score * 0.3 + education_score * 0.2, 2)
        return MatchBreakdown(
            overall_score=overall,
            keyword_match_score=round(keyword_score, 2),
            experience_relevance_score=round(experience_score, 2),
            education_score=round(education_score, 2),
            strengths=[f"Matched keywords: {', '.join(overlap[:5])}"]
            if overlap
            else ["Resume contains limited JD keyword overlap."],
            gaps=["Consider enriching the resume with role-specific keywords and quantified impact."],
            keywords=jd_terms[:10],
            reasoning="Fallback score generated locally because AI output was unavailable.",
        )

    @staticmethod
    def _parse_json(raw_content: str) -> dict:
        cleaned = raw_content.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(0).strip() if match else None


def _extract_skills(text: str) -> list[str]:
    skill_candidates = [
        "python",
        "java",
        "sql",
        "fastapi",
        "flask",
        "django",
        "vue",
        "react",
        "langchain",
        "openai",
        "redis",
        "docker",
        "aws",
        "git",
        "linux",
    ]
    text_lower = text.lower()
    return [skill for skill in skill_candidates if skill in text_lower]


def _top_keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z+#.]{1,20}", text.lower())
    stopwords = {
        "with",
        "and",
        "the",
        "for",
        "your",
        "you",
        "from",
        "that",
        "this",
        "have",
        "will",
        "using",
        "years",
        "experience",
    }
    filtered = [word for word in words if word not in stopwords]
    return [item for item, _ in Counter(filtered).most_common(limit)]
