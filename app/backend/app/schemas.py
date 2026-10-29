from __future__ import annotations

from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field

SubjectKey = Literal["ai", "java"]
UserRole = Literal["admin", "student"]
# Project Assistant is available in both subjects, using each subject's own data.
AgentMode = Literal["qa", "learning_path", "quiz", "coach", "project_assistant"]
SourceFile = Annotated[str, Field(min_length=1, max_length=255)]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=16000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=24)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)
    agent_mode: AgentMode = "qa"
    subject: SubjectKey | None = None
    source_files: list[SourceFile] | None = Field(default=None, max_length=12)
    
    # 前端语言模式
    language: Literal["zh", "en"] = "zh"
    
    use_rag: bool = True  
    top_k: int = Field(default=3, ge=0, le=6)
    temperature: float = Field(default=0.35, ge=0, le=1.5)
    max_tokens: int = Field(default=768, ge=64, le=2048)


class AttachmentChatMessage(ChatMessage):
    content: str = Field(default="", max_length=16000)


class AttachmentChatRequest(ChatRequest):
    # Files provide the content when no written instruction is supplied.
    messages: list[AttachmentChatMessage] = Field(default_factory=list, max_length=24)


class Evidence(BaseModel):
    chunk_id: str
    doc_id: str
    source_file: str
    score: float
    text: str
    location: str | None = None
    document_type: str | None = None


class ChatResponse(BaseModel):
    answer: str
    model_used: str
    evidence: list[Evidence]
    title: str
    subject: SubjectKey = "ai"
    conversation_id: str | None = None
    assistant_message_id: str | None = None
    user_message: dict[str, Any] | None = None
    source_files: list[str] = Field(default_factory=list)

class FeedbackRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    feedback: str = Field(default="", max_length=6000)
    subject: SubjectKey | None = None
    agent_mode: str = "qa"
    model_used: str = ""


class KnowledgeStatus(BaseModel):
    subject: SubjectKey = "ai"
    file_count: int
    chunk_count: int
    sources: list[str]


class JavaRunRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32_000)
    stdin: str = Field(default="", max_length=8_000)


class JavaRunResponse(BaseModel):
    success: bool
    output: str = ""
    error: str = ""
    compile_output: str = ""
    duration_ms: int = Field(ge=0)
    timed_out: bool = False


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=120)
    agent_mode: AgentMode = "qa"
    subject: SubjectKey | None = None


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    agent_mode: AgentMode | None = None


class ConversationSourcesRequest(BaseModel):
    source_files: list[SourceFile] = Field(default_factory=list, max_length=12)


class ConversationSummary(BaseModel):
    conversation_id: str
    subject: SubjectKey
    title: str
    agent_mode: str
    source_files: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str

class SubjectInfo(BaseModel):
    subject: SubjectKey
    label_zh: str
    label_en: str
    description_zh: str
    description_en: str

class MessageFeedbackSaveRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: str = Field(default="", max_length=6000)
    training_selected: bool = False


class MessageFeedbackResponse(BaseModel):
    assistant_message_id: str
    conversation_id: str
    rating: int
    feedback: str
    training_selected: bool
    created_at: str
    updated_at: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)
    subject: SubjectKey


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: UserRole
    subject: SubjectKey
    expires_at: int


class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    password: str = Field(min_length=6, max_length=256)
    password_confirm: str = Field(min_length=6, max_length=256)


class RegisterResponse(BaseModel):
    username: str
    message: str


class FileAttachment(BaseModel):
    source_file: str
    size_bytes: int | None = Field(default=None, ge=0)
    kind: Literal["file", "image"] = "file"
    attachment_id: str | None = None
    preview_data_url: str | None = None


class StoredMessage(BaseModel):
    message_id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[FileAttachment] = Field(default_factory=list)
    model_used: str | None = None
    created_at: str
    quality_feedback: MessageFeedbackResponse | None = None

class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage] = Field(default_factory=list)
