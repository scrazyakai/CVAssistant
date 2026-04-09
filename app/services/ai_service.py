import asyncio
import json
import logging
from pathlib import Path
import re
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.models.schemas import CandidateProfile, MatchBreakdown, ResumeAnalyzeLLMResponse

logger = logging.getLogger(__name__)
PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompt"
STRUCTURED_OUTPUT_MODELS = (
    "qwen3.5-plus",
    "qwen3.5-flash",
    "qwen-plus",
    "qwen-flash",
    "qwen-turbo",
    "qwen-max",
    "qwen-long",
)


class AIService:
    def __init__(self, api_key: str, model: str, base_url: str, timeout_seconds: int) -> None:
        self.model_name = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.client = (
            AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_seconds,
            )
            if api_key
            else None
        )

    async def extract_candidate_info_from_pdf(
        self,
        stored_file_path: Path,
        parsed_resume_text: str,
    ) -> CandidateProfile:
        if self.client is None:
            raise RuntimeError("LLM_API_KEY is not configured.")

        logger.info(
            "Calling AI for PDF resume extraction with model=%s base_url=%s file=%s size=%s",
            self.model_name,
            self.base_url,
            stored_file_path.name,
            stored_file_path.stat().st_size,
        )
        prompt = _load_prompt("resume_parse_prompt.txt").replace(
            "{{RESUME_TEXT}}",
            parsed_resume_text[:12000],
        )
        result = await self._run_file_prompt(
            stored_file_path,
            prompt,
            CandidateProfile,
            "resume_parse_response",
        )
        logger.info("AI PDF resume extraction succeeded file=%s", stored_file_path.name)
        return CandidateProfile.model_validate(_normalize_candidate_profile(result.model_dump()))

    async def analyze_resume_pdf_against_job(
        self,
        stored_file_path: Path,
        parsed_resume_text: str,
        parsed_resume_profile: CandidateProfile | None,
        job_description: str,
    ) -> tuple[CandidateProfile, MatchBreakdown]:
        if self.client is None:
            raise RuntimeError("LLM_API_KEY is not configured.")

        logger.info(
            "Calling AI for PDF resume analysis with model=%s base_url=%s file=%s size=%s jd_length=%s",
            self.model_name,
            self.base_url,
            stored_file_path.name,
            stored_file_path.stat().st_size,
            len(job_description),
        )
        resume_json = (
            json.dumps(parsed_resume_profile.model_dump(mode="json"), ensure_ascii=False, indent=2)
            if parsed_resume_profile is not None
            else "{}"
        )
        prompt = (
            _load_prompt("resume_analyze_prompt.txt")
            .replace("{{JOB_DESCRIPTION}}", job_description[:6000])
            .replace("{{RESUME_TEXT}}", parsed_resume_text[:12000])
            .replace("{{RESUME_JSON}}", resume_json)
        )
        result = await self._run_file_prompt(
            stored_file_path,
            prompt,
            ResumeAnalyzeLLMResponse,
            "resume_analyze_response",
        )
        logger.info("AI PDF resume analysis succeeded file=%s", stored_file_path.name)
        return (
            CandidateProfile.model_validate(
                _normalize_candidate_profile(result.extracted_info.model_dump(mode="json"))
            ),
            MatchBreakdown.model_validate(
                _normalize_match_breakdown(result.match.model_dump(mode="json"))
            ),
        )

    async def _run_file_prompt(
        self,
        stored_file_path: Path,
        prompt: str,
        output_model: type[BaseModel],
        schema_name: str,
    ) -> BaseModel:
        uploaded_file_id = await self._upload_pdf(stored_file_path)
        try:
            return await self._create_completion_with_retry(uploaded_file_id, prompt, output_model, schema_name)
        finally:
            await self._delete_file(uploaded_file_id)

    async def _upload_pdf(self, stored_file_path: Path) -> str:
        if self.client is None:
            raise RuntimeError("LLM_API_KEY is not configured.")

        last_error = None
        for attempt in range(3):
            try:
                with stored_file_path.open("rb") as file_handle:
                    uploaded = await self.client.files.create(
                        file=(stored_file_path.name, file_handle, "application/pdf"),
                        purpose="file-extract",
                        timeout=self.timeout_seconds,
                    )
                logger.info(
                    "Uploaded PDF to AI provider file=%s file_id=%s attempt=%s",
                    stored_file_path.name,
                    uploaded.id,
                    attempt + 1,
                )
                return uploaded.id
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Uploading PDF to AI provider failed file=%s attempt=%s error=%s",
                    stored_file_path.name,
                    attempt + 1,
                    exc,
                )
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Failed to upload PDF to AI provider: {last_error}")

    async def _create_completion_with_retry(
        self,
        file_id: str,
        prompt: str,
        output_model: type[BaseModel],
        schema_name: str,
    ) -> BaseModel:
        if self.client is None:
            raise RuntimeError("LLM_API_KEY is not configured.")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": "You are a strict JSON response engine. Return JSON only."},
            {
                "role": "system",
                "content": (
                    "You must obey this JSON Schema exactly:\n"
                    f"{json.dumps(output_model.model_json_schema(), ensure_ascii=False)}"
                ),
            },
            {"role": "system", "content": f"fileid://{file_id}"},
            {"role": "user", "content": prompt},
        ]
        response_format = self._build_response_format(output_model, schema_name)
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                request_kwargs: dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0,
                    "timeout": self.timeout_seconds,
                }
                if response_format is not None:
                    request_kwargs["response_format"] = response_format
                if _should_disable_thinking(self.model_name):
                    request_kwargs["extra_body"] = {"enable_thinking": False}

                response = await self.client.chat.completions.create(**request_kwargs)
                content = _extract_content(response.choices[0].message.content)
                parsed = self._parse_json(content)
                try:
                    return output_model.model_validate(parsed)
                except ValidationError as exc:
                    last_error = exc
                    logger.warning(
                        "AI JSON validation failed file_id=%s attempt=%s error=%s",
                        file_id,
                        attempt + 1,
                        exc,
                    )
                    if attempt == 2:
                        break
                    messages.extend(
                        [
                            {"role": "assistant", "content": content},
                            {
                                "role": "user",
                                "content": _build_validation_retry_message(output_model, exc),
                            },
                        ]
                    )
            except Exception as exc:
                last_error = exc
                error_text = str(exc).lower()
                if "parsing" in error_text or "processing" in error_text or "not ready" in error_text:
                    logger.warning(
                        "Uploaded PDF is not ready yet file_id=%s attempt=%s",
                        file_id,
                        attempt + 1,
                    )
                    await asyncio.sleep(2)
                    continue
                if attempt == 2:
                    logger.exception("AI completion failed after retries file_id=%s", file_id)
                    break
                logger.warning(
                    "AI completion failed file_id=%s attempt=%s error=%s",
                    file_id,
                    attempt + 1,
                    exc,
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response failed to parse as valid JSON or violated the required "
                            "JSON Schema. Error details:\n"
                            f"{exc}\nRequired schema:\n"
                            f"{json.dumps(output_model.model_json_schema(), ensure_ascii=False)}\n"
                            "Please try again and return JSON only."
                        ),
                    }
                )

        raise RuntimeError(f"AI response did not match schema after 3 attempts: {last_error}")

    async def _delete_file(self, file_id: str) -> None:
        if self.client is None:
            return
        try:
            await self.client.files.delete(file_id)
            logger.info("Deleted uploaded AI file file_id=%s", file_id)
        except Exception:
            logger.warning("Failed to delete uploaded AI file file_id=%s", file_id)

    def _build_response_format(
        self,
        output_model: type[BaseModel],
        schema_name: str,
    ) -> dict[str, Any] | None:
        if not _supports_structured_output(self.model_name):
            logger.warning(
                "Model %s may not support response_format json_object; using prompt+validation retry only",
                self.model_name,
            )
            return None
        return {
            "type": "json_object",
        }

    @staticmethod
    def _parse_json(raw_content: str) -> dict[str, Any]:
        cleaned = raw_content.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)


def _supports_structured_output(model_name: str) -> bool:
    lowered = model_name.lower()
    return any(lowered.startswith(prefix) for prefix in STRUCTURED_OUTPUT_MODELS)


def _should_disable_thinking(model_name: str) -> bool:
    lowered = model_name.lower()
    return lowered.startswith("qwen3")


def _extract_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        if parts:
            return "".join(parts)
    raise ValueError("AI response content is empty.")


def _build_validation_retry_message(output_model: type[BaseModel], exc: ValidationError) -> str:
    return (
        "The JSON you returned does not match the required JSON Schema. "
        "Do not explain anything. Return corrected JSON only.\n"
        f"Validation errors:\n{exc}\n"
        f"Required schema:\n{json.dumps(output_model.model_json_schema(), ensure_ascii=False)}"
    )


def _normalize_candidate_profile(payload: dict[str, Any]) -> dict[str, Any]:
    basic_info = payload.get("basic_info")
    if not isinstance(basic_info, dict):
        basic_info = {}

    return {
        "basic_info": {
            "name": _to_optional_string(basic_info.get("name")),
            "phone": _to_optional_string(basic_info.get("phone")),
            "email": _to_optional_string(basic_info.get("email")),
            "address": _to_optional_string(basic_info.get("address")),
        },
        "job_intention": _to_optional_string(payload.get("job_intention")),
        "expected_salary": _to_optional_string(payload.get("expected_salary")),
        "years_of_experience": _to_optional_string(payload.get("years_of_experience")),
        "education_background": _normalize_string_list(payload.get("education_background")),
        "projects": _normalize_string_list(payload.get("projects")),
        "skills": _normalize_string_list(payload.get("skills")),
        "summary": _to_optional_string(payload.get("summary")),
    }


def _normalize_match_breakdown(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "overall_score": _to_score(payload.get("overall_score")),
        "keyword_match_score": _to_score(payload.get("keyword_match_score")),
        "experience_relevance_score": _to_score(payload.get("experience_relevance_score")),
        "education_score": _to_score(payload.get("education_score")),
        "strengths": _normalize_string_list(payload.get("strengths")),
        "gaps": _normalize_string_list(payload.get("gaps")),
        "keywords": _normalize_string_list(payload.get("keywords")),
        "reasoning": _to_optional_string(payload.get("reasoning")),
    }


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        converted = _to_optional_string(item)
        if converted:
            normalized.append(converted)
    return normalized


def _to_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    if isinstance(value, list):
        parts = [_to_optional_string(item) for item in value]
        joined = "；".join(part for part in parts if part)
        return joined or None
    return str(value)


def _to_score(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, round(numeric, 2)))


def _load_prompt(file_name: str) -> str:
    return (PROMPT_DIR / file_name).read_text(encoding="utf-8")
