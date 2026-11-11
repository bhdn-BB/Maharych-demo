"""Interview-specific generation built on the provider repository."""
from voice_ai_service.app.services.prompts import load_prompt, render_prompt
from voice_ai_service.app.models.dto import AudioEvaluationSchema


class DialogueModel:
    def __init__(self, repository):
        self.repository = repository

    async def generate_response(self, args):
        if args.streaming:
            return self.repository.generate_stream(args)
        return await self.repository.generate(args)

    async def evaluate_audio(self, audio, mime_type, question, criteria):
        if mime_type not in {"audio/webm", "audio/ogg", "audio/wav", "audio/mpeg", "audio/mp4"}:
            raise ValueError("Unsupported audio MIME type")
        if not audio or len(audio) > 8 * 1024 * 1024:
            raise ValueError("Audio answer must contain at most 8 MiB")
        return await self.repository.generate_audio(
            audio, mime_type, load_prompt("audio_system"),
            [render_prompt("audio_question", question=question),
             render_prompt("audio_criteria", criteria=criteria)], AudioEvaluationSchema,
        )
