"""Explicit local integration harness: real Go/gRPC/PostgreSQL/RabbitMQ/PDF, fake AI.

Requires a disposable *_test database and test RabbitMQ. Never a live demo.
"""
import asyncio
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import uuid

import httpx
import psycopg
import websockets

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/adaptive-integration"


def voice_process():
    from test_adaptive_dialogue import DialogueLLM
    from voice_ai_service.app.core import dependencies
    from voice_ai_service.app.grpc import interview_servicer
    import uvicorn

    dependencies.get_gemini_client = lambda: DialogueLLM()
    dependencies.DialogueModel = lambda llm: llm

    async def fake_tts(_text, _language, _voice_id=""):
        return (ARTIFACTS / "tone.mp3").read_bytes()

    interview_servicer.synthesize = fake_tts
    uvicorn.run("voice_ai_service.main:app", host="127.0.0.1", port=8001, log_level="warning")


async def collect(socket):
    events = []
    while True:
        message = await asyncio.wait_for(socket.recv(), 15)
        if isinstance(message, bytes):
            assert message, "Missing MP3"
            return events
        event = json.loads(message)
        events.append(event)
        assert event["type"] != "ERROR", event.get("error")
        if event["type"] == "INTERVIEW_FINISHED":
            return events


async def exercise():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8080/api/v1", timeout=65) as client:
        async def request(method, path, expected=200, **kwargs):
            response = await client.request(method, path, **kwargs)
            assert response.status_code == expected, (path, response.status_code, response.text[:200])
            return response

        account = (await request("POST", "/auth/register", 201, json={
            "email": f"integration-{uuid.uuid4().hex}@example.com", "password": secrets.token_urlsafe(24) + "A1"
        })).json()
        client.headers["Authorization"] = "Bearer " + account["token"]
        await request("PUT", "/profile", json={"name": "Test", "surname": "Candidate",
            "phoneNumber": "+380501234567", "yearsOfExperience": 3, "techStack": ["Python"], "resume": ""})
        audio = (ARTIFACTS / "answer.webm").read_bytes()
        results = []
        for language in ("uk", "en"):
            interview = (await request("POST", "/interviews", 201, json={
                "level": "middle", "position": "backend", "focus": "system-design", "language": language
            })).json()
            identifier = interview["id"]
            uri = f"ws://127.0.0.1:8080/api/v1/interviews/{identifier}/audio?token={account['token']}"
            socket = await websockets.connect(uri, origin="http://localhost:3000")
            try:
                events = await collect(socket)
                for turn in range(6):
                    current = next(e for e in events if e["type"] == "STAGE_UPDATE")
                    command = {"type": "answer", "answerId": str(uuid.uuid4()), "questionId": current["questionId"]}
                    await socket.send(json.dumps({**command, "type": "start_recording"}))
                    reserved = json.loads(await asyncio.wait_for(socket.recv(), 15))
                    assert reserved["type"] == "STAGE_UPDATE" and reserved["stage"] == "recording"
                    assert reserved["answerId"] == command["answerId"]
                    await socket.send(json.dumps(command))
                    await socket.send(audio)
                    events = await collect(socket)
                    assert any(e["type"] == "TRANSCRIPTION" for e in events)
                    if turn == 0:
                        question = next(e["questionId"] for e in events if e["type"] == "STAGE_UPDATE")
                        await socket.send(json.dumps(command))
                        await socket.send(audio)
                        duplicate = await collect(socket)
                        assert next(e["questionId"] for e in duplicate if e["type"] == "STAGE_UPDATE") == question
                        await socket.close()
                        socket = await websockets.connect(uri, origin="http://localhost:3000")
                        events = await collect(socket)
                        assert next(e["questionId"] for e in events if e["type"] == "STAGE_UPDATE") == question
                assert any(e["type"] == "INTERVIEW_FINISHED" for e in events)
            finally:
                await socket.close()
            assert (await request("GET", f"/interviews/{identifier}")).json()["status"] == "completed"
            report = (await request("GET", f"/interviews/{identifier}/feedback")).json()
            assert report["score_scale"] == 100 and report["overall_score"] == 80
            assert len(report["questions"]) == 6 and len(report["topic_scores"]) == 3
            assert not report["partial"]
            await request("POST", f"/interviews/{identifier}/end")
            for _ in range(60):
                pdf = await client.get(f"/interviews/{identifier}/report.pdf")
                if pdf.status_code == 200:
                    assert pdf.content.startswith(b"%PDF-")
                    (ARTIFACTS / f"report-{language}.pdf").write_bytes(pdf.content)
                    break
                assert pdf.status_code == 404
                await asyncio.sleep(0.5)
            else:
                raise AssertionError("PDF worker did not produce a report")
            with psycopg.connect(os.environ["TEST_DATABASE_URL"].replace("+asyncpg", "")) as connection:
                count = connection.execute("SELECT count(*) FROM question_records q JOIN conversations c "
                    "ON c.id=q.conversation_id WHERE c.interview_id=%s", (identifier,)).fetchone()[0]
                assert count == 6, "Duplicate answer persisted"
            results.append({"language": language, "interview_id": identifier, "questions": 6, "pdf": "passed"})
        empty = (await request("POST", "/interviews", 201, json={
            "level": "middle", "position": "backend", "focus": "behavioral", "language": "uk"})).json()
        ended = (await request("POST", f"/interviews/{empty['id']}/end")).json()
        assert ended["status"] == "abandoned"
        await request("GET", f"/interviews/{empty['id']}/feedback", 404)
        stranger = (await request("POST", "/auth/register", 201, json={
            "email": f"other-{uuid.uuid4().hex}@example.com", "password": secrets.token_urlsafe(24) + "A1"})).json()
        client.headers["Authorization"] = "Bearer " + stranger["token"]
        for suffix in ("", "/feedback", "/report.pdf"):
            await request("GET", f"/interviews/{results[0]['interview_id']}{suffix}", 404)
        (ARTIFACTS / "results.json").write_text(json.dumps({"providers": "FAKE; not a live demo", "cases": results,
            "duplicates": "passed", "reconnect": "passed", "empty_finish": "passed", "ownership": "passed"}, indent=2), encoding="utf-8")
        print("Integration passed: Go / WebSocket / gRPC / PostgreSQL / RabbitMQ / PDF; AI and TTS were FAKE")


def main():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.startswith("postgresql+asyncpg://") or not url.rsplit("/", 1)[-1].endswith("_test"):
        raise SystemExit("Require an explicit disposable *_test TEST_DATABASE_URL")
    if "--voice" in sys.argv:
        voice_process()
        return
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("Install ffmpeg")
    for filename, codec, fmt in (("answer.webm", "libopus", "webm"), ("tone.mp3", "libmp3lame", "mp3")):
        subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
                        "-t", "1", "-c:a", codec, "-f", fmt, str(ARTIFACTS / filename)], check=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "voice_ai_service/src"), "DATABASE_URL": url,
        "GRPC_PORT": "50052", "RABBITMQ_URL": os.environ.get("TEST_RABBITMQ_URL", "amqp://test:adaptive-test-only@127.0.0.1:5673/"),
        "JWT_SECRET": secrets.token_urlsafe(32), "CORS_ORIGINS": "http://localhost:3000", "DB_HOST": "127.0.0.1",
        "DB_PORT": "55432", "DB_USER": "postgres", "DB_PASSWORD": "adaptive-test-only", "DB_NAME": "maharych_test",
        "AI_SERVICE_GRPC_ADDR": "127.0.0.1:50052", "AI_SERVICE_HTTP_URL": "http://127.0.0.1:8001",
        "PDF_FONT_PATH": os.environ.get("PDF_FONT_PATH", "C:/Windows/Fonts/arial.ttf")}
    subprocess.run([sys.executable, "-m", "alembic", "-c", str(ROOT / "voice_ai_service/src/voice_ai_service/app/alembic.ini"), "upgrade", "head"], env=env, check=True)
    processes, logs = [], []
    try:
        commands = [("voice", [sys.executable, __file__, "--voice"], env),
            ("worker", [sys.executable, str(ROOT / "feedback_service/worker.py")], {**env, "DATABASE_URL": url.replace("+asyncpg", "")}),
            ("go", [os.environ.get("TEST_BACKEND_BINARY", str(ROOT / "tmp/adaptive-api.exe"))], {**env, "DATABASE_URL": url.replace("+asyncpg", "")})]
        for name, command, environment in commands:
            log = (ARTIFACTS / f"{name}.log").open("w", encoding="utf-8")
            logs.append(log)
            processes.append(subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log, stderr=log))
        for _ in range(60):
            try:
                if httpx.get("http://127.0.0.1:8080/api/v1/health").is_success and httpx.get("http://127.0.0.1:8001/health").is_success:
                    break
            except httpx.HTTPError:
                pass
            if any(p.poll() is not None for p in processes):
                raise RuntimeError("Integration service exited; inspect artifacts/adaptive-integration logs")
            time.sleep(0.5)
        asyncio.run(exercise())
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=15)
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
