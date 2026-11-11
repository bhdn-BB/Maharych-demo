"""Private voice preview endpoint, accessed through the authenticated gateway."""
import logging

from fastapi import APIRouter, HTTPException, Response

from voice_ai_service.app.services.tts import VOICE_NAMES, synthesize

router = APIRouter(prefix="/voices", tags=["Voices"])
logger = logging.getLogger(__name__)


@router.get("/{voice_id}/preview", include_in_schema=False)
async def preview_voice(voice_id: str, language: str):
    if voice_id not in VOICE_NAMES or language not in {"uk", "en"}:
        raise HTTPException(status_code=400, detail="Unsupported voice or language")
    text = ("Вітаю! Я ваш інтерв'юер. Почнімо співбесіду." if language == "uk"
            else "Hello! I'm your interviewer. Let's begin.")
    try:
        audio = await synthesize(text, language, voice_id)
    except Exception as exc:
        logger.warning("Voice preview failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Voice preview unavailable") from exc
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
