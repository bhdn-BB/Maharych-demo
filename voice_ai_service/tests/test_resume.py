import io
import unittest
from zipfile import ZipFile

from voice_ai_service.app.repositories.resume_documents import ResumeDocumentRepository
from voice_ai_service.app.services.resume import ResumeService

extract_resume = ResumeService(ResumeDocumentRepository()).extract


def docx_with_text(text):
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>'
        ))
    return output.getvalue()


class ResumeTest(unittest.TestCase):
    def test_docx_extracts_text_through_langchain(self):
        self.assertIn("Data Science and Python", extract_resume(docx_with_text("Data Science and Python"), "docx"))

    def test_pdf_extracts_text_through_langchain(self):
        from reportlab.pdfgen import canvas
        output = io.BytesIO()
        document = canvas.Canvas(output)
        document.drawString(30, 700, "Data Science and Python")
        document.save()
        self.assertIn("Data Science and Python", extract_resume(output.getvalue(), "pdf"))

    def test_rejects_invalid_and_oversized_input(self):
        for data, kind in ((b"fake", "pdf"), (b"fake", "docx"), (b"a", "txt"), (b"x" * (5 * 1024 * 1024 + 1), "pdf")):
            with self.subTest(kind=kind, size=len(data)), self.assertRaises(ValueError):
                extract_resume(data, kind)
        with self.assertRaises(ValueError):
            extract_resume(docx_with_text("x" * 10001), "docx")
