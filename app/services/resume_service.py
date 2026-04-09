import re
from pathlib import Path

import fitz


class ResumeService:
    @staticmethod
    def validate_pdf(file_name: str, content_type: str | None) -> None:
        if not file_name.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are supported.")
        if content_type and "pdf" not in content_type.lower():
            raise ValueError("Uploaded file content type must be PDF.")

    @staticmethod
    def save_uploaded_pdf(
        storage_dir: Path,
        file_bytes: bytes,
        file_digest: str,
    ) -> Path:
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = storage_dir / f"{file_digest}.pdf"
        file_path.write_bytes(file_bytes)
        return file_path

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        document = fitz.open(stream=file_bytes, filetype="pdf")
        pages: list[str] = []
        for page in document:
            page_text = page.get_text("text")
            if page_text:
                pages.append(page_text)
        return "\n\n".join(pages)

    @staticmethod
    def clean_text(raw_text: str) -> str:
        text = raw_text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[^\S\r\n]+\n", "\n", text)
        return text.strip()
