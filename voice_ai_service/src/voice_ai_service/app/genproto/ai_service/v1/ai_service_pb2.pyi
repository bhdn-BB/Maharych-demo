from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Grade(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GRADE_UNSPECIFIED: _ClassVar[Grade]
    GRADE_INTERN: _ClassVar[Grade]
    GRADE_JUNIOR: _ClassVar[Grade]
    GRADE_MIDDLE: _ClassVar[Grade]
    GRADE_SENIOR: _ClassVar[Grade]
    GRADE_LEAD: _ClassVar[Grade]
GRADE_UNSPECIFIED: Grade
GRADE_INTERN: Grade
GRADE_JUNIOR: Grade
GRADE_MIDDLE: Grade
GRADE_SENIOR: Grade
GRADE_LEAD: Grade

class AudioMetadata(_message.Message):
    __slots__ = ("mime_type", "sample_rate", "channels", "encoding")
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_RATE_FIELD_NUMBER: _ClassVar[int]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    ENCODING_FIELD_NUMBER: _ClassVar[int]
    mime_type: str
    sample_rate: int
    channels: int
    encoding: str
    def __init__(self, mime_type: _Optional[str] = ..., sample_rate: _Optional[int] = ..., channels: _Optional[int] = ..., encoding: _Optional[str] = ...) -> None: ...

class CandidateInfo(_message.Message):
    __slots__ = ("name", "surname", "email", "phone_number", "linkedin_url", "github_url", "years_of_experience", "tech_stack", "resume", "applied_at", "is_active")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SURNAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    LINKEDIN_URL_FIELD_NUMBER: _ClassVar[int]
    GITHUB_URL_FIELD_NUMBER: _ClassVar[int]
    YEARS_OF_EXPERIENCE_FIELD_NUMBER: _ClassVar[int]
    TECH_STACK_FIELD_NUMBER: _ClassVar[int]
    RESUME_FIELD_NUMBER: _ClassVar[int]
    APPLIED_AT_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    name: str
    surname: str
    email: str
    phone_number: str
    linkedin_url: str
    github_url: str
    years_of_experience: int
    tech_stack: _containers.RepeatedScalarFieldContainer[str]
    resume: str
    applied_at: str
    is_active: bool
    def __init__(self, name: _Optional[str] = ..., surname: _Optional[str] = ..., email: _Optional[str] = ..., phone_number: _Optional[str] = ..., linkedin_url: _Optional[str] = ..., github_url: _Optional[str] = ..., years_of_experience: _Optional[int] = ..., tech_stack: _Optional[_Iterable[str]] = ..., resume: _Optional[str] = ..., applied_at: _Optional[str] = ..., is_active: bool = ...) -> None: ...

class PositionInfo(_message.Message):
    __slots__ = ("title", "description", "grade", "department", "required_experience", "required_skills", "nice_to_have_skills", "salary_min", "salary_max", "is_remote", "location")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    DEPARTMENT_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_EXPERIENCE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_SKILLS_FIELD_NUMBER: _ClassVar[int]
    NICE_TO_HAVE_SKILLS_FIELD_NUMBER: _ClassVar[int]
    SALARY_MIN_FIELD_NUMBER: _ClassVar[int]
    SALARY_MAX_FIELD_NUMBER: _ClassVar[int]
    IS_REMOTE_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    title: str
    description: str
    grade: Grade
    department: str
    required_experience: int
    required_skills: _containers.RepeatedScalarFieldContainer[str]
    nice_to_have_skills: _containers.RepeatedScalarFieldContainer[str]
    salary_min: int
    salary_max: int
    is_remote: bool
    location: str
    def __init__(self, title: _Optional[str] = ..., description: _Optional[str] = ..., grade: _Optional[_Union[Grade, str]] = ..., department: _Optional[str] = ..., required_experience: _Optional[int] = ..., required_skills: _Optional[_Iterable[str]] = ..., nice_to_have_skills: _Optional[_Iterable[str]] = ..., salary_min: _Optional[int] = ..., salary_max: _Optional[int] = ..., is_remote: bool = ..., location: _Optional[str] = ...) -> None: ...

class AudioStreamStartupOptions(_message.Message):
    __slots__ = ("interview_id", "user_id", "metadata", "candidate", "position", "focus", "language", "scenario_version", "voice_id")
    INTERVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CANDIDATE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FOCUS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_VERSION_FIELD_NUMBER: _ClassVar[int]
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    interview_id: str
    user_id: str
    metadata: AudioMetadata
    candidate: CandidateInfo
    position: PositionInfo
    focus: str
    language: str
    scenario_version: int
    voice_id: str
    def __init__(self, interview_id: _Optional[str] = ..., user_id: _Optional[str] = ..., metadata: _Optional[_Union[AudioMetadata, _Mapping]] = ..., candidate: _Optional[_Union[CandidateInfo, _Mapping]] = ..., position: _Optional[_Union[PositionInfo, _Mapping]] = ..., focus: _Optional[str] = ..., language: _Optional[str] = ..., scenario_version: _Optional[int] = ..., voice_id: _Optional[str] = ...) -> None: ...

class AudioStreamRequest(_message.Message):
    __slots__ = ("options", "audio_data", "timestamp_ms", "answer_id", "question_id", "command")
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    AUDIO_DATA_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    ANSWER_ID_FIELD_NUMBER: _ClassVar[int]
    QUESTION_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    options: AudioStreamStartupOptions
    audio_data: bytes
    timestamp_ms: int
    answer_id: str
    question_id: str
    command: str
    def __init__(self, options: _Optional[_Union[AudioStreamStartupOptions, _Mapping]] = ..., audio_data: _Optional[bytes] = ..., timestamp_ms: _Optional[int] = ..., answer_id: _Optional[str] = ..., question_id: _Optional[str] = ..., command: _Optional[str] = ...) -> None: ...

class AudioStreamResponse(_message.Message):
    __slots__ = ("type", "transcription", "ai_audio_data", "ai_text", "stage", "current_question", "total_questions", "error", "question_id", "answer_id", "event_id", "audio_mime_type")
    class ResponseType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RESPONSE_TYPE_UNSPECIFIED: _ClassVar[AudioStreamResponse.ResponseType]
        TRANSCRIPTION: _ClassVar[AudioStreamResponse.ResponseType]
        AI_AUDIO: _ClassVar[AudioStreamResponse.ResponseType]
        AI_TEXT: _ClassVar[AudioStreamResponse.ResponseType]
        STAGE_UPDATE: _ClassVar[AudioStreamResponse.ResponseType]
        ERROR: _ClassVar[AudioStreamResponse.ResponseType]
        INTERVIEW_FINISHED: _ClassVar[AudioStreamResponse.ResponseType]
    RESPONSE_TYPE_UNSPECIFIED: AudioStreamResponse.ResponseType
    TRANSCRIPTION: AudioStreamResponse.ResponseType
    AI_AUDIO: AudioStreamResponse.ResponseType
    AI_TEXT: AudioStreamResponse.ResponseType
    STAGE_UPDATE: AudioStreamResponse.ResponseType
    ERROR: AudioStreamResponse.ResponseType
    INTERVIEW_FINISHED: AudioStreamResponse.ResponseType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TRANSCRIPTION_FIELD_NUMBER: _ClassVar[int]
    AI_AUDIO_DATA_FIELD_NUMBER: _ClassVar[int]
    AI_TEXT_FIELD_NUMBER: _ClassVar[int]
    STAGE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_QUESTION_FIELD_NUMBER: _ClassVar[int]
    TOTAL_QUESTIONS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    QUESTION_ID_FIELD_NUMBER: _ClassVar[int]
    ANSWER_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    AUDIO_MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    type: AudioStreamResponse.ResponseType
    transcription: str
    ai_audio_data: bytes
    ai_text: str
    stage: str
    current_question: int
    total_questions: int
    error: str
    question_id: str
    answer_id: str
    event_id: str
    audio_mime_type: str
    def __init__(self, type: _Optional[_Union[AudioStreamResponse.ResponseType, str]] = ..., transcription: _Optional[str] = ..., ai_audio_data: _Optional[bytes] = ..., ai_text: _Optional[str] = ..., stage: _Optional[str] = ..., current_question: _Optional[int] = ..., total_questions: _Optional[int] = ..., error: _Optional[str] = ..., question_id: _Optional[str] = ..., answer_id: _Optional[str] = ..., event_id: _Optional[str] = ..., audio_mime_type: _Optional[str] = ...) -> None: ...
