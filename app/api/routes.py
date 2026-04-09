import logging
from hashlib import sha256

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.models.schemas import (
    ResumeAnalysisResponse,
    ResumeMatchResponse,
    ResumeParseResponse,
)
from app.services.ai_service import AIService
from app.services.cache_service import CacheService
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/api/v1", tags=["resume"])
PARSER_CACHE_VERSION = "v5"
logger = logging.getLogger(__name__)

settings = get_settings()
cache_service = CacheService(settings.redis_host, settings.redis_port, settings.redis_password, settings.redis_db)
resume_service = ResumeService()
ai_service = AIService(
    settings.llm_api_key,
    settings.llm_model,
    settings.llm_base_url,
    settings.llm_timeout_seconds,
)


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/resumes/parse", response_model=ResumeParseResponse)
async def parse_resume(file: UploadFile = File(...)) -> ResumeParseResponse:
    try:
        logger.info("Received /resumes/parse request file=%s", file.filename or "resume.pdf")
        resume_service.validate_pdf(file.filename or "", file.content_type)
        file_bytes = await file.read()
        file_digest = sha256(file_bytes).hexdigest()
        stored_path = resume_service.save_uploaded_pdf(
            settings.resume_storage_dir,
            file_bytes,
            file_digest,
        )
        logger.info("Stored uploaded resume file at path=%s", stored_path)
        raw_text = resume_service.extract_text_from_pdf(file_bytes)
        cleaned_text = resume_service.clean_text(raw_text)
        cached = cache_service.get_resume_record(file_digest)
        if cached and cached.get("parse_result"):
            logger.info("Returning cached parse result file=%s", file.filename or "resume.pdf")
            return ResumeParseResponse.model_validate({**cached["parse_result"], "cache_hit": True})

        try:
            extracted = await ai_service.extract_candidate_info_from_pdf(
                stored_path,
                cleaned_text,
            )
            logger.info("Parse request used AI extraction file=%s", file.filename or "resume.pdf")
        except Exception as exc:
            logger.exception("Parse request failed during AI extraction file=%s", file.filename or "resume.pdf")
            raise HTTPException(status_code=502, detail=f"AI extraction failed: {exc}") from exc

        payload = ResumeParseResponse(
            file_name=file.filename or "resume.pdf",
            text_length=len(cleaned_text),
            cleaned_text=cleaned_text,
            extracted_info=extracted,
        )
        record = cached or {}
        record.update(
            {
                "file_md5": file_digest,
                "file_name": file.filename or "resume.pdf",
                "parse_result": payload.model_dump(mode="json"),
                "analysis_jd": record.get("analysis_jd"),
                "analysis_result": record.get("analysis_result"),
            }
        )
        cache_service.set_resume_record(file_digest, record)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to parse resume.") from exc


@router.post("/resumes/match", response_model=ResumeMatchResponse)
async def match_resume(
    job_description: str = Form(..., min_length=2),
    file: UploadFile = File(...),
) -> ResumeMatchResponse:
    logger.info(
        "Received /resumes/match request file=%s jd_length=%s",
        file.filename or "resume.pdf",
        len(job_description),
    )
    try:
        resume_service.validate_pdf(file.filename or "", file.content_type)
        file_bytes = await file.read()
        file_digest = sha256(file_bytes).hexdigest()
        stored_path = resume_service.save_uploaded_pdf(
            settings.resume_storage_dir,
            file_bytes,
            file_digest,
        )
        logger.info("Stored uploaded resume file at path=%s", stored_path)
        raw_text = resume_service.extract_text_from_pdf(file_bytes)
        cleaned_text = resume_service.clean_text(raw_text)
        cached = cache_service.get_resume_record(file_digest)
        if (
            cached
            and cached.get("analysis_result")
            and cached.get("analysis_jd") == job_description
        ):
            logger.info("Returning cached match result file=%s", file.filename or "resume.pdf")
            return ResumeMatchResponse.model_validate({**cached["analysis_result"], "cache_hit": True})

        parse_result = cached.get("parse_result") if cached else None
        extracted_info = None
        if parse_result:
            extracted_info = ResumeParseResponse.model_validate(parse_result).extracted_info

        extracted_info, match = await ai_service.analyze_resume_pdf_against_job(
            stored_path,
            cleaned_text,
            extracted_info,
            job_description,
        )
        logger.info("Match request used AI scoring")
        payload = ResumeMatchResponse(
            job_description=job_description,
            extracted_info=extracted_info,
            match=match,
            cleaned_text=cleaned_text,
        )
        record = cached or {}
        if not record.get("parse_result") and extracted_info is not None:
            record["parse_result"] = ResumeParseResponse(
                file_name=file.filename or "resume.pdf",
                text_length=len(cleaned_text),
                cleaned_text=cleaned_text,
                extracted_info=extracted_info,
            ).model_dump(mode="json")
        record.update(
            {
                "file_md5": file_digest,
                "file_name": file.filename or "resume.pdf",
                "analysis_jd": job_description,
                "analysis_result": payload.model_dump(mode="json"),
            }
        )
        cache_service.set_resume_record(file_digest, record)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Match request failed during AI scoring")
        raise HTTPException(status_code=502, detail=f"AI matching failed: {exc}") from exc


@router.post("/resumes/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    job_description: str = Form(...),
    file: UploadFile = File(...),
) -> ResumeAnalysisResponse:
    try:
        logger.info(
            "Received /resumes/analyze request file=%s jd_length=%s",
            file.filename or "resume.pdf",
            len(job_description),
        )
        resume_service.validate_pdf(file.filename or "", file.content_type)
        file_bytes = await file.read()
        file_digest = sha256(file_bytes).hexdigest()
        stored_path = resume_service.save_uploaded_pdf(
            settings.resume_storage_dir,
            file_bytes,
            file_digest,
        )
        logger.info("Stored uploaded resume file at path=%s", stored_path)
        raw_text = resume_service.extract_text_from_pdf(file_bytes)
        cleaned_text = resume_service.clean_text(raw_text)
        cached = cache_service.get_resume_record(file_digest)
        if (
            cached
            and cached.get("analysis_result")
            and cached.get("analysis_jd") == job_description
        ):
            logger.info("Returning cached analyze result file=%s", file.filename or "resume.pdf")
            return ResumeAnalysisResponse.model_validate({**cached["analysis_result"], "cache_hit": True})

        parse_result = cached.get("parse_result") if cached else None
        extracted_info = None
        if parse_result:
            extracted_info = ResumeParseResponse.model_validate(parse_result).extracted_info

        try:
            extracted, match = await ai_service.analyze_resume_pdf_against_job(
                stored_path,
                cleaned_text,
                extracted_info,
                job_description,
            )
            logger.info("Analyze request used AI extraction and scoring file=%s", file.filename or "resume.pdf")
        except Exception as exc:
            logger.exception(
                "Analyze request failed during AI processing file=%s",
                file.filename or "resume.pdf",
            )
            raise HTTPException(status_code=502, detail=f"AI analysis failed: {exc}") from exc

        payload = ResumeAnalysisResponse(
            file_name=file.filename or "resume.pdf",
            text_length=len(cleaned_text),
            cleaned_text=cleaned_text,
            extracted_info=extracted,
            match=match,
            job_description=job_description,
        )
        record = cached or {}
        record.update(
            {
                "file_md5": file_digest,
                "file_name": file.filename or "resume.pdf",
                "parse_result": ResumeParseResponse(
                    file_name=file.filename or "resume.pdf",
                    text_length=len(cleaned_text),
                    cleaned_text=cleaned_text,
                    extracted_info=extracted,
                ).model_dump(mode="json"),
                "analysis_jd": job_description,
                "analysis_result": payload.model_dump(mode="json"),
            }
        )
        cache_service.set_resume_record(file_digest, record)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to analyze resume.") from exc
