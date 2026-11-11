"""RabbitMQ consumer for durable, idempotent interview PDF exports."""

import io
import json
import logging
import os
import time
import uuid
from html import escape

import pika
import psycopg
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

# Broker topology: keep in sync with voice_ai_service/.../services/feedback_publisher.py
EVENTS_EXCHANGE = "maharych.events"
DLX_EXCHANGE = "maharych.dlx"
ROUTING_KEY = "feedback.ready"
DEAD_KEY = "feedback.pdf.dead"
QUEUE_NAME = "feedback.pdf"
RETRY_QUEUE = "feedback.pdf.retry"
DLQ_NAME = "feedback.pdf.dlq"
HEARTBEAT_FILE = os.environ.get("HEARTBEAT_FILE", "")
HEARTBEAT_INTERVAL = 30
RETRY_DELAY_MS = int(os.environ.get("PDF_RETRY_DELAY_MS", "10000"))
MAX_ATTEMPTS = int(os.environ.get("PDF_MAX_ATTEMPTS", "5"))
FONT = os.environ.get("PDF_FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
logger = logging.getLogger(__name__)


def paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value or "")), style)


def render_report_pdf(position: str, feedback: dict, questions: list[tuple]) -> bytes:
    pdfmetrics.registerFont(TTFont("DejaVu", FONT))
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="DejaVu", fontSize=17, leading=24)
    section = ParagraphStyle("ReportSection", parent=styles["Heading2"], fontName="DejaVu", fontSize=12, leading=17, spaceBefore=12)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName="DejaVu", fontSize=9, leading=14, spaceAfter=5)
    result = io.BytesIO()
    document = SimpleDocTemplate(result, pagesize=(210 * mm, 297 * mm), leftMargin=22 * mm,
                                 rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    story = [paragraph("Результат навчальної співбесіди", title),
             paragraph(f"Посада: {position}", body),
             paragraph(f"Загальна оцінка: {feedback.get('overall_score', 0)}/{feedback.get('score_scale', 10)}", body),
             paragraph(feedback.get("summary", ""), body),
             paragraph("Рекомендації", section), paragraph(feedback.get("recommendation", ""), body)]
    for heading, key in [("Сильні сторони", "top_strengths"), ("Що покращити", "top_weaknesses")]:
        story.append(paragraph(heading, section))
        for item in feedback.get(key) or []:
            story.append(paragraph("• " + str(item), body))
    story.append(paragraph("Запитання та відповіді", section))
    for index, question, answer, score, comment in questions:
        story.extend([HRFlowable(width="100%", thickness=0.4, color=colors.grey), Spacer(1, 3 * mm),
                      paragraph(f"{index}. {question}", section),
                      paragraph(f"Відповідь: {answer}", body),
                      paragraph(f"Оцінка: {score if score is not None else '—'}", body),
                      paragraph(comment, body)])
    document.build(story)
    return result.getvalue()


def parse_event(body: bytes) -> tuple[str, str, dict, list[tuple]]:
    """Validate a self-contained event before opening a database connection.

    Returns (interview_id, position, feedback, questions) as render_report_pdf expects.
    """
    event = json.loads(body)
    interview_id = str(uuid.UUID(event["interview_id"]))
    feedback = event["feedback"]
    if not isinstance(feedback, dict):
        raise ValueError("feedback must be an object")
    questions = [
        (q["index"], q["question"], q["answer"], q["score"], q["comment"])
        for q in event["questions"]
    ]
    return interview_id, event.get("position") or "", feedback, questions


def report_exists(cursor, interview_id: str) -> bool:
    cursor.execute("SELECT 1 FROM feedback_reports WHERE interview_id = %s", (interview_id,))
    return cursor.fetchone() is not None


def save_report(cursor, interview_id: str, pdf: bytes) -> None:
    cursor.execute(
        "INSERT INTO feedback_reports (interview_id, pdf_data) VALUES (%s, %s) "
        "ON CONFLICT (interview_id) DO NOTHING",
        (interview_id, pdf),
    )


def handle_message(database_url: str, body: bytes) -> None:
    interview_id, position, feedback, questions = parse_event(body)
    with psycopg.connect(database_url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            if report_exists(cursor, interview_id):
                return
            pdf = render_report_pdf(position, feedback, questions)
            save_report(cursor, interview_id, pdf)


def declare_topology(channel) -> None:
    """Declare exchanges, work queue, TTL retry queue and DLQ (must match the publisher)."""
    channel.exchange_declare(exchange=EVENTS_EXCHANGE, exchange_type="direct", durable=True)
    channel.exchange_declare(exchange=DLX_EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(queue=DLQ_NAME, exchange=DLX_EXCHANGE, routing_key=DEAD_KEY)
    channel.queue_declare(queue=RETRY_QUEUE, durable=True, arguments={
        "x-message-ttl": RETRY_DELAY_MS,
        "x-dead-letter-exchange": EVENTS_EXCHANGE,
        "x-dead-letter-routing-key": ROUTING_KEY,
    })
    channel.queue_declare(queue=QUEUE_NAME, durable=True, arguments={
        "x-dead-letter-exchange": DLX_EXCHANGE,
        "x-dead-letter-routing-key": DEAD_KEY,
    })
    channel.queue_bind(queue=QUEUE_NAME, exchange=EVENTS_EXCHANGE, routing_key=ROUTING_KEY)


def attempt_of(properties) -> int:
    try:
        return int((properties.headers or {}).get("x-attempt", 0))
    except (TypeError, ValueError):
        return 0


def settle_failure(channel, method, properties, body: bytes, permanent: bool) -> None:
    """Retry via the TTL queue up to MAX_ATTEMPTS, then dead-letter. Never blocks the consumer."""
    attempt = attempt_of(properties) + 1
    if permanent or attempt >= MAX_ATTEMPTS:
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)  # -> DLX -> DLQ
        return
    channel.basic_publish(
        exchange="", routing_key=RETRY_QUEUE, body=body,
        properties=pika.BasicProperties(delivery_mode=2, headers={"x-attempt": attempt}),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def touch_heartbeat(path: str) -> None:
    """Update the liveness file read by the container healthcheck."""
    if not path:
        return
    try:
        with open(path, "a"):
            os.utime(path, None)
    except OSError:
        logger.warning("Cannot update heartbeat file %s", path)


def schedule_heartbeat(connection, path: str) -> None:
    """Touch the file now and every HEARTBEAT_INTERVAL seconds while the consumer loop is alive."""
    def beat():
        touch_heartbeat(path)
        connection.call_later(HEARTBEAT_INTERVAL, beat)
    beat()


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    rabbitmq_url = os.environ["RABBITMQ_URL"]
    database_url = os.environ["DATABASE_URL"]
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            channel = connection.channel()
            declare_topology(channel)
            channel.basic_qos(prefetch_count=1)
            schedule_heartbeat(connection, HEARTBEAT_FILE)

            def consume(ch, method, properties, body):
                try:
                    handle_message(database_url, body)
                except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                    logger.exception("Invalid feedback export event; dead-lettering")
                    settle_failure(ch, method, properties, body, permanent=True)
                except Exception:
                    logger.exception("PDF export failed (attempt %s)", attempt_of(properties) + 1)
                    settle_failure(ch, method, properties, body, permanent=False)
                else:
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=consume)
            channel.start_consuming()
        except Exception:
            logger.exception("Feedback worker disconnected; reconnecting")
            time.sleep(5)


if __name__ == "__main__":
    run()
