from typing import Optional, Protocol, TypeVar

ConversationT = TypeVar("ConversationT")


class QuestionRecordWriter(Protocol):
    """Persistence operation used by dialogue evaluation."""

    async def add_question_record(
        self, conversation_id: int, topic_index: int, question: str,
        question_type: str, candidate_answer: str, score: Optional[int] = None,
        comment: Optional[str] = None,
    ): ...

    async def list_question_bank(self, focus: str, language: str) -> list[dict]: ...


class InterviewStore(Protocol[ConversationT]):
    """Operations needed to restore and commit a locked interview transition."""

    async def find_conversation(self, interview_id: str) -> ConversationT | None: ...

    async def add_conversation(self, **fields) -> ConversationT: ...

    async def get_conversation(self, conversation_id: int) -> ConversationT | None: ...

    async def update_conversation(self, conversation: ConversationT) -> None: ...

    async def lock_interview(self, interview_id: str) -> ConversationT | None: ...

    async def get_outbox(self, interview_id: str): ...

    async def add_outbox(self, interview_id: str) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
