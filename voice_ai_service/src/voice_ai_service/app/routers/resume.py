"""Private HTTP transport for authenticated resume extraction via the Go API."""
from fastapi import APIRouter, Depends, HTTPException, Request

from voice_ai_service.app.core.dependencies import get_resume_service
from voice_ai_service.app.services.resume import ResumeService, ResumeTooLarge

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/parse", include_in_schema=False)
async def parse_resume(request: Request, kind: str, service: ResumeService = Depends(get_resume_service)):
    try:
        return {"text": await service.read_stream(request.stream(), kind)}
    except ResumeTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read resume file") from exc
