"""HTTP status and response contract for the private interview endpoints."""
import unittest
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI

from voice_ai_service.app.core.dependencies import get_interview_lifecycle
from voice_ai_service.app.routers.interview import router
from voice_ai_service.app.services.interview_lifecycle import InvalidInterviewID, ReportNotFound


class InterviewHTTPTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = type("Service", (), {
            "finish": AsyncMock(return_value="completed"),
            "feedback": AsyncMock(return_value={"overall_score": 80}),
            "report_pdf": AsyncMock(return_value=b"%PDF-example"),
        })()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_interview_lifecycle] = lambda: self.service
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.url = "/interview/by-interview-id/example"

    async def test_successful_finish_feedback_and_pdf(self):
        finish = await self.client.post(self.url + "/finish")
        feedback = await self.client.get(self.url + "/feedback")
        pdf = await self.client.get(self.url + "/report.pdf")
        self.assertEqual((finish.status_code, finish.json()), (200, {"stage": "completed"}))
        self.assertEqual(feedback.json(), {"overall_score": 80})
        self.assertEqual((pdf.status_code, pdf.headers["content-type"], pdf.content),
                         (200, "application/pdf", b"%PDF-example"))

    async def test_invalid_id_and_missing_report_are_mapped_to_client_errors(self):
        self.service.finish.side_effect = InvalidInterviewID("Invalid interview ID")
        self.service.feedback.side_effect = ReportNotFound("Feedback not available")
        self.service.report_pdf.side_effect = ReportNotFound("PDF report not ready")
        self.assertEqual((await self.client.post(self.url + "/finish")).status_code, 400)
        self.assertEqual((await self.client.get(self.url + "/feedback")).status_code, 404)
        self.assertEqual((await self.client.get(self.url + "/report.pdf")).status_code, 404)

    async def test_finish_failure_does_not_expose_internal_details(self):
        self.service.finish.side_effect = RuntimeError("internal secret")
        response = await self.client.post(self.url + "/finish")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("internal secret", response.text)
