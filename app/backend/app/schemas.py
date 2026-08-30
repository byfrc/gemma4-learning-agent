from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

SubjectKey = Literal["ai", "java"]
UserRole = Literal["admin", "student"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=16000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=24)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)
    agent_mode: Literal["qa", "learning_path", "quiz", "coach"] = "qa"
    subject: SubjectKey | None = None
    
    # 前端语言模式
    language: Literal["zh", "en"] = "zh"
    
    use_rag: bool = True  
    top_k: int = Field(default=3, ge=0, le=6)
    temperature: float = Field(default=0.35, ge=0, le=1.5)
    max_tokens: int = Field(default=768, ge=64, le=2048)


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

class ConversationCreateRequest(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=120)
    agent_mode: Literal["qa", "learning_path", "quiz", "coach"] = "qa"
    subject: SubjectKey | None = None


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    agent_mode: Literal["qa", "learning_path", "quiz", "coach"] | None = None


class ConversationSummary(BaseModel):
    conversation_id: str
    subject: SubjectKey
    title: str
    agent_mode: str
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


class StoredMessage(BaseModel):
    message_id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    model_used: str | None = None
    created_at: str
    quality_feedback: MessageFeedbackResponse | None = None

class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage] = Field(default_factory=list)
