"""
Proto → Pydantic DTO converters.

Converts gRPC AudioStreamStartupOptions sub-messages to domain Candidate / Position models.
"""
from __future__ import annotations

from datetime import date

from voice_ai_service.app.genproto.ai_service.v1 import ai_service_pb2 as pb
from voice_ai_service.app.models.domain import Candidate, Grade, Position


def options_to_candidate(opts: pb.AudioStreamStartupOptions) -> Candidate:
    """Convert startup options CandidateInfo to a Candidate DTO."""
    c = opts.candidate
    return Candidate(
        name=c.name,
        surname=c.surname,
        email=c.email,
        phone_number=c.phone_number,
        linkedin_url=c.linkedin_url if c.HasField("linkedin_url") else None,
        github_url=c.github_url if c.HasField("github_url") else None,
        years_of_experience=c.years_of_experience,
        tech_stack=list(c.tech_stack),
        resume=c.resume,
        applied_at=date.fromisoformat(c.applied_at) if c.applied_at else date.today(),
        is_active=c.is_active,
    )


def options_to_position(opts: pb.AudioStreamStartupOptions) -> Position:
    """Convert startup options PositionInfo to a Position DTO."""
    p = opts.position
    grade = _proto_grade_to_dto(p.grade)
    return Position(
        title=p.title,
        description=p.description or f"{p.title} position",
        grade=grade,
        department=p.department or "Engineering",
        required_experience=p.required_experience,
        required_skills=list(p.required_skills),
        nice_to_have_skills=list(p.nice_to_have_skills),
        salary_min=p.salary_min if p.HasField("salary_min") else None,
        salary_max=p.salary_max if p.HasField("salary_max") else None,
        is_remote=p.is_remote,
        location=p.location if p.HasField("location") else None,
    )


_GRADE_MAP = {
    pb.GRADE_INTERN: Grade.INTERN,
    pb.GRADE_JUNIOR: Grade.JUNIOR,
    pb.GRADE_MIDDLE: Grade.MIDDLE,
    pb.GRADE_SENIOR: Grade.SENIOR,
    pb.GRADE_LEAD: Grade.LEAD,
}


def _proto_grade_to_dto(value: int) -> Grade:
    """Convert proto Grade enum to Pydantic Grade, defaulting to MIDDLE."""
    return _GRADE_MAP.get(value, Grade.MIDDLE)
