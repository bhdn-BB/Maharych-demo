"""Private HTTP transport for interview lifecycle and report retrieval."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from voice_ai_service.app.core.dependencies import get_interview_lifecycle
from voice_ai_service.app.services.interview_lifecycle import InterviewLifecycleService, InvalidInterviewID, ReportNotFound

router = APIRouter(prefix="/interview", tags=["Interview"])


@router.post("/by-interview-id/{interview_id}/finish", include_in_schema=False)
async def finish_by_interview_id(interview_id: str, service: InterviewLifecycleService = Depends(get_interview_lifecycle)):
    try:
        return {"stage": await service.finish(interview_id)}
    except InvalidInterviewID as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not finalize interview; retry") from exc


@router.get("/by-interview-id/{interview_id}/feedback", include_in_schema=False)
async def feedback_by_interview_id(interview_id: str, service: InterviewLifecycleService = Depends(get_interview_lifecycle)):
    try:
        return await service.feedback(interview_id)
    except InvalidInterviewID as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReportNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/by-interview-id/{interview_id}/report.pdf", include_in_schema=False)
async def report_pdf_by_interview_id(interview_id: str, service: InterviewLifecycleService = Depends(get_interview_lifecycle)):
    try:
        return Response(content=await service.report_pdf(interview_id), media_type="application/pdf")
    except InvalidInterviewID as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReportNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
