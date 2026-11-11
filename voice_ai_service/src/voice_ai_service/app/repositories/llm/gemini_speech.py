"""Gemini speech generation transport."""
import httpx


class GeminiSpeechRepository:
    async def generate(self, api_key: str, model: str, text: str, voice: str, style: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                headers={"x-goog-api-key": api_key},
                json={
                    "model": model,
                    "input": [{"type": "user_input", "content": [{
                        "type": "text", "text": text,
                        "annotations": [{"type": "speech_metadata", "style": style}],
                    }]}],
                    "response_format": {"type": "audio", "mime_type": "audio/wav"},
                    "generation_config": {"speech_config": [{"voice": voice}]},
                    "store": False,
                },
            )
            response.raise_for_status()
            return response.json()
