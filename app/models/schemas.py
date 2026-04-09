from typing import Any

from pydantic import BaseModel, Field


class BasicInfo(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class CandidateProfile(BaseModel):
    basic_info: BasicInfo
    job_intention: str | None = None
    expected_salary: str | None = None
    years_of_experience: str | None = None
    education_background: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    summary: str | None = None


class ResumeParseResponse(BaseModel):
    file_name: str
    text_length: int
    cleaned_text: str
    extracted_info: CandidateProfile
    cache_hit: bool = False


class JobMatchRequest(BaseModel):
    job_description: str = Field(..., min_length=10)
    resume_text: str | None = None
    extracted_info: CandidateProfile | None = None


class MatchBreakdown(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    keyword_match_score: float = Field(..., ge=0, le=100)
    experience_relevance_score: float = Field(..., ge=0, le=100)
    education_score: float = Field(..., ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    reasoning: str | None = None


class ResumeMatchResponse(BaseModel):
    job_description: str
    extracted_info: CandidateProfile
    match: MatchBreakdown
    cleaned_text: str
    cache_hit: bool = False


class ResumeAnalysisResponse(BaseModel):
    file_name: str
    text_length: int
    cleaned_text: str
    extracted_info: CandidateProfile
    match: MatchBreakdown
    job_description: str
    cache_hit: bool = False


class ErrorResponse(BaseModel):
    detail: str
    extra: dict[str, Any] | None = None
