"""Validate and extract optional resume text without retaining the source file."""
import asyncio
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from voice_ai_service.app.repositories.resume_documents import ResumeDocumentRepository

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 10000


class ResumeTooLarge(ValueError):
    pass


class ResumeService:
    def __init__(self, documents: ResumeDocumentRepository):
        self.documents = documents

    async def read_stream(self, chunks, kind: str) -> str:
        data = bytearray()
        async for chunk in chunks:
            data.extend(chunk)
            if len(data) > MAX_FILE_BYTES:
                raise ResumeTooLarge("File exceeds 5 MiB")
        return await asyncio.to_thread(self.extract, bytes(data), kind)

    def extract(self, data: bytes, kind: str) -> str:
        if not data or len(data) > MAX_FILE_BYTES:
            raise ValueError("File must be between 1 byte and 5 MiB")
        if kind == "pdf":
            if not data.startswith(b"%PDF-"):
                raise ValueError("Invalid PDF file")
        elif kind == "docx":
            try:
                with ZipFile(BytesIO(data)) as archive:
                    entries = archive.infolist()
                    if len(entries) > 2000 or sum(entry.file_size for entry in entries) > 20 * 1024 * 1024 or "word/document.xml" not in archive.namelist():
                        raise ValueError("Invalid or oversized DOCX file")
            except BadZipFile as exc:
                raise ValueError("Invalid DOCX file") from exc
        else:
            raise ValueError("Only PDF and DOCX files are supported")
        parts, length = [], 0
        for content in self.documents.read(data, kind):
            part = content.strip()
            length += len(part) + 1
            if length > MAX_TEXT_CHARS + 1:
                raise ValueError("Resume text exceeds 10,000 characters")
            if part:
                parts.append(part)
        text = "\n".join(parts).strip()
        if not text:
            raise ValueError("No readable text found in the file")
        return text
