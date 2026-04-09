from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.models.schemas import (
    JobMatchRequest,
    ResumeAnalysisResponse,
    ResumeMatchResponse,
    ResumeParseResponse,
)
from app.services.ai_service import AIService
from app.services.cache_service import FileCacheService
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/api/v1", tags=["resume"])

settings = get_settings()
cache_service = FileCacheService(settings.cache_dir)
resume_service = ResumeService()
ai_service = AIService(settings.openai_api_key, settings.openai_model)


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/resumes/parse", response_model=ResumeParseResponse)
async def parse_resume(file: UploadFile = File(...)) -> ResumeParseResponse:
    try:
        resume_service.validate_pdf(file.filename or "", file.content_type)
        file_bytes = await file.read()
        text = resume_service.clean_text(resume_service.extract_text_from_pdf(file_bytes))
        cache_key = cache_service.build_key("parse", file.filename or "resume.pdf", text)
        cached = cache_service.get(cache_key)
        if cached:
            return ResumeParseResponse.model_validate({**cached, "cache_hit": True})

        try:
            extracted = await ai_service.extract_candidate_info(text)
        except Exception:
            extracted = ai_service.fallback_extract_candidate_info(text)

        payload = ResumeParseResponse(
            file_name=file.filename or "resume.pdf",
            text_length=len(text),
            cleaned_text=text,
            extracted_info=extracted,
        )
        cache_service.set(cache_key, payload.model_dump(mode="json"))
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to parse resume.") from exc


@router.post("/resumes/match", response_model=ResumeMatchResponse)
async def match_resume(
    request: JobMatchRequest,
) -> ResumeMatchResponse:
    if not request.resume_text or not request.extracted_info:
        raise HTTPException(
            status_code=400,
            detail="resume_text and extracted_info are required for matching.",
        )

    cache_key = cache_service.build_key(
        "match",
        request.job_description,
        request.resume_text,
        request.extracted_info.model_dump_json(),
    )
    cached = cache_service.get(cache_key)
    if cached:
        return ResumeMatchResponse.model_validate({**cached, "cache_hit": True})

    try:
        match = await ai_service.match_resume_to_job(
            request.resume_text,
            request.extracted_info,
            request.job_description,
        )
    except Exception:
        match = ai_service.fallback_match_resume_to_job(
            request.resume_text,
            request.extracted_info,
            request.job_description,
        )

    payload = ResumeMatchResponse(
        job_description=request.job_description,
        extracted_info=request.extracted_info,
        match=match,
        cleaned_text=request.resume_text,
    )
    cache_service.set(cache_key, payload.model_dump(mode="json"))
    return payload


@router.post("/resumes/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    job_description: str = Form(...),
    file: UploadFile = File(...),
) -> ResumeAnalysisResponse:
    try:
        resume_service.validate_pdf(file.filename or "", file.content_type)
        file_bytes = await file.read()
        text = resume_service.clean_text(resume_service.extract_text_from_pdf(file_bytes))
        cache_key = cache_service.build_key(
            "analyze",
            file.filename or "resume.pdf",
            text,
            job_description,
        )
        cached = cache_service.get(cache_key)
        if cached:
            return ResumeAnalysisResponse.model_validate({**cached, "cache_hit": True})

        try:
            extracted = await ai_service.extract_candidate_info(text)
        except Exception:
            extracted = ai_service.fallback_extract_candidate_info(text)

        try:
            match = await ai_service.match_resume_to_job(
                text,
                extracted,
                job_description,
            )
        except Exception:
            match = ai_service.fallback_match_resume_to_job(
                text,
                extracted,
                job_description,
            )

        payload = ResumeAnalysisResponse(
            file_name=file.filename or "resume.pdf",
            text_length=len(text),
            cleaned_text=text,
            extracted_info=extracted,
            match=match,
            job_description=job_description,
        )
        cache_service.set(cache_key, payload.model_dump(mode="json"))
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to analyze resume.") from exc
