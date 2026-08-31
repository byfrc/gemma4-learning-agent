from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import (
    AuthSession,
    ROLE_ADMIN,
    authenticate,
    create_access_token,
    ensure_bootstrap_user,
    get_user_role,
    register_user,
    verify_access_token,
)
from .config import get_settings
from .conversation_store import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation,
    get_message,
    get_messages,
    init_db,
    list_conversations,
    migrate_legacy_conversation_owners,
    update_conversation,
    get_message_feedback,
    save_message_feedback,
)
from .document_parser import DocumentParseError, SUPPORTED_DOCUMENT_SUFFIXES
from .java_runner import (
    JavaRunnerError,
    JavaToolchainError,
    run_java_code,
)
from .providers import build_messages, generate
from .subject_rag import SubjectRAGManager
from .subjects import get_subject_spec, list_subject_specs, normalize_subject
from .schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationRenameRequest,
    ConversationSummary,
    Evidence,
    FeedbackRequest,
    JavaRunRequest,
    JavaRunResponse,
    KnowledgeStatus,
    LoginRequest,
    LoginResponse,
    MessageFeedbackResponse,
    MessageFeedbackSaveRequest,
    RegisterRequest,
    RegisterResponse,
    SubjectInfo,
)
from .storage import append_jsonl

settings = get_settings()
if init_db(settings.conversation_db_path):
    migrate_legacy_conversation_owners(
        settings.conversation_db_path,
        settings.auth_username,
    )
ensure_bootstrap_user(
    settings.conversation_db_path,
    settings.auth_username,
    settings.auth_password,
)

rag_manager = SubjectRAGManager(settings)

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthSession:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="请先登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = verify_access_token(settings, credentials.credentials)
    if session is None:
        raise HTTPException(
            status_code=401,
            detail="登录已失效，请重新登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session


def require_admin(
    user: AuthSession = Depends(require_auth),
) -> AuthSession:
    if user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="仅管理员可以上传或管理知识库。",
        )
    return user


def subject_for_user(requested_subject: str | None, user: AuthSession) -> str:
    if requested_subject is not None and normalize_subject(requested_subject) != user.subject:
        raise HTTPException(
            status_code=403,
            detail="当前登录账号没有访问该学科的权限。",
        )
    return user.subject


def get_conversation_for_user(
    conversation_id: str,
    user: AuthSession,
) -> dict:
    conversation = get_conversation(
        settings.conversation_db_path,
        conversation_id,
        username=user.username,
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在。")

    if normalize_subject(conversation.get("subject")) != user.subject:
        raise HTTPException(
            status_code=403,
            detail="当前登录账号没有访问该会话的权限。",
        )

    return conversation


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    username = payload.username.strip().lower()
    if not authenticate(
        settings.conversation_db_path,
        username,
        payload.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="账号或密码错误。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = get_user_role(settings.conversation_db_path, username) or "student"
    token, expires_at = create_access_token(
        settings,
        username=username,
        subject=payload.subject,
        role=role,
    )
    return LoginResponse(
        access_token=token,
        username=username,
        role=role,
        subject=payload.subject,
        expires_at=expires_at,
    )


@app.post("/api/auth/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest):
    if payload.password != payload.password_confirm:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致。")

    username = payload.username.strip().lower()
    try:
        registered_username = register_user(
            settings.conversation_db_path,
            username,
            payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return RegisterResponse(
        username=registered_username,
        message="注册成功，请使用新账号登录。",
    )


@app.get("/api/auth/me")
async def current_user(user: AuthSession = Depends(require_auth)):
    return {
        "username": user.username,
        "role": user.role,
    }


@app.get("/api/subjects", response_model=list[SubjectInfo])
async def get_subjects():
    return [
        SubjectInfo(
            subject=spec.key,
            label_zh=spec.label_zh,
            label_en=spec.label_en,
            description_zh=spec.description_zh,
            description_en=spec.description_en,
        )
        for spec in list_subject_specs()
    ]

@app.post("/api/conversations", response_model=ConversationSummary)
async def create_new_conversation(
    payload: ConversationCreateRequest,
    user: AuthSession = Depends(require_auth),
):
    subject = subject_for_user(payload.subject, user)
    conversation = create_conversation(
        settings.conversation_db_path,
        title=payload.title,
        agent_mode=payload.agent_mode,
        subject=subject,
        username=user.username,
    )
    return ConversationSummary(**conversation)


@app.get("/api/conversations", response_model=list[ConversationSummary])
async def get_conversation_list(
    subject: str | None = None,
    user: AuthSession = Depends(require_auth),
):
    subject = subject_for_user(subject, user)
    conversations = list_conversations(
        settings.conversation_db_path,
        subject=subject,
        username=user.username,
    )
    return [ConversationSummary(**item) for item in conversations]


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: str,
    user: AuthSession = Depends(require_auth),
):
    conversation = get_conversation_for_user(conversation_id, user)

    messages = get_messages(
        settings.conversation_db_path,
        conversation_id,
    )

    return ConversationDetail(
        **conversation,
        messages=messages,
    )


@app.patch("/api/conversations/{conversation_id}", response_model=ConversationSummary)
async def rename_conversation(
    conversation_id: str,
    payload: ConversationRenameRequest,
    user: AuthSession = Depends(require_auth),
):
    get_conversation_for_user(conversation_id, user)
    conversation = update_conversation(
        settings.conversation_db_path,
        conversation_id,
        title=payload.title,
        agent_mode=payload.agent_mode,
        username=user.username,
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在。")

    return ConversationSummary(**conversation)


@app.delete("/api/conversations/{conversation_id}")
async def remove_conversation(
    conversation_id: str,
    user: AuthSession = Depends(require_auth),
):
    get_conversation_for_user(conversation_id, user)
    deleted = delete_conversation(
        settings.conversation_db_path,
        conversation_id,
        username=user.username,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在。")

    return {
        "message": "会话已删除。",
        "conversation_id": conversation_id,
    }

@app.get("/api/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: str = "markdown",
    user: AuthSession = Depends(require_auth),
):
    conversation = get_conversation_for_user(conversation_id, user)

    messages = get_messages(
        settings.conversation_db_path,
        conversation_id,
    )

    normalized_format = format.strip().lower()

    if normalized_format not in {"markdown", "json"}:
        raise HTTPException(
            status_code=400,
            detail="format 仅支持 markdown 或 json。",
        )

    export_payload = {
        "conversation": conversation,
        "messages": messages,
    }

    if normalized_format == "json":
        content = json.dumps(
            export_payload,
            ensure_ascii=False,
            indent=2,
        )

        return Response(
            content=content,
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="conversation_{conversation_id}.json"'
                )
            },
        )

    lines = [
        f"# {conversation['title']}",
        "",
        "## 会话信息",
        "",
        f"- 会话 ID：`{conversation_id}`",
        f"- 学科：`{conversation['subject']}`",
        f"- 智能体模式：`{conversation['agent_mode']}`",
        f"- 创建时间：{conversation['created_at']}",
        f"- 最后更新时间：{conversation['updated_at']}",
        "",
        "---",
        "",
    ]

    for index, message in enumerate(messages, start=1):
        role_name = "用户" if message["role"] == "user" else "Gemma4 学习助教"

        lines.extend(
            [
                f"## {index}. {role_name}",
                "",
                message["content"],
                "",
            ]
        )

        evidence = message.get("evidence") or []

        if evidence:
            lines.extend(
                [
                    "### RAG 证据",
                    "",
                ]
            )

            for item in evidence:
                source_file = item.get("source_file", "未知来源")
                score = item.get("score", "未知")
                text = item.get("text", "")
                location = item.get("location")
                document_type = item.get("document_type")

                lines.extend(
                    [
                        f"- **来源**：{source_file}",
                        f"- **位置**：{location}" if location else "- **位置**：未标注",
                        f"- **文档类型**：{document_type}" if document_type else "- **文档类型**：未标注",
                        f"- **相关度**：{score}",
                        f"- **片段**：{text}",
                        "",
                    ]
                )

        if message.get("model_used"):
            lines.extend(
                [
                    f"> 模型：`{message['model_used']}`",
                    "",
                ]
            )

        lines.extend(
            [
                "---",
                "",
            ]
        )

    content = "\n".join(lines)

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="conversation_{conversation_id}.md"'
            )
        },
    )

@app.post(
    "/api/messages/{message_id}/feedback",
    response_model=MessageFeedbackResponse,
)
async def save_quality_feedback(
    message_id: str,
    payload: MessageFeedbackSaveRequest,
    user: AuthSession = Depends(require_auth),
):
    message = get_message(settings.conversation_db_path, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="目标消息不存在。")
    get_conversation_for_user(message["conversation_id"], user)

    try:
        result = save_message_feedback(
            settings.conversation_db_path,
            assistant_message_id=message_id,
            rating=payload.rating,
            feedback=payload.feedback,
            training_selected=payload.training_selected,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MessageFeedbackResponse(**result)


@app.get(
    "/api/messages/{message_id}/feedback",
    response_model=MessageFeedbackResponse,
)
async def get_quality_feedback(
    message_id: str,
    user: AuthSession = Depends(require_auth),
):
    message = get_message(settings.conversation_db_path, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="目标消息不存在。")
    get_conversation_for_user(message["conversation_id"], user)

    result = get_message_feedback(
        settings.conversation_db_path,
        message_id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="该消息暂无评分记录。")

    return MessageFeedbackResponse(**result)


@app.get("/api/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/health")
async def health(
    subject: str | None = None,
    user: AuthSession = Depends(require_auth),
):
    subject_key = subject_for_user(subject, user)
    files, chunks, _ = rag_manager.status(subject_key)
    spec = get_subject_spec(subject_key)
    return {
        "status": "ok",
        "subject": subject_key,
        "subject_label": spec.label_zh,
        "provider": settings.model_provider,
        "model": settings.vllm_model if settings.model_provider == "openai_compatible" else settings.ollama_model,
        "knowledge_files": files,
        "knowledge_chunks": chunks,
    }


@app.get("/api/knowledge/status", response_model=KnowledgeStatus)
async def knowledge_status(
    subject: str | None = None,
    user: AuthSession = Depends(require_auth),
):
    subject_key = subject_for_user(subject, user)
    file_count, chunk_count, sources = rag_manager.status(subject_key)
    return KnowledgeStatus(
        subject=subject_key,
        file_count=file_count,
        chunk_count=chunk_count,
        sources=sources,
    )


@app.post("/api/java/run", response_model=JavaRunResponse)
async def run_java(
    payload: JavaRunRequest,
    user: AuthSession = Depends(require_auth),
):
    if user.subject != "java":
        raise HTTPException(
            status_code=403,
            detail="在线IDE仅对 Java 学科开放。",
        )
    if not settings.java_run_enabled:
        raise HTTPException(
            status_code=503,
            detail="在线IDE运行服务当前未启用。",
        )

    try:
        result = await asyncio.to_thread(
            run_java_code,
            payload.code,
            payload.stdin,
            javac_command=settings.java_javac_command,
            java_command=settings.java_runtime_command,
            timeout_seconds=settings.java_timeout_seconds,
            compile_timeout_seconds=settings.java_compile_timeout_seconds,
            max_code_bytes=settings.java_max_code_kb * 1024,
            max_stdin_bytes=settings.java_max_stdin_kb * 1024,
            max_output_bytes=settings.java_max_output_kb * 1024,
        )
    except JavaRunnerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except JavaToolchainError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"代码运行失败：{exc}") from exc

    return JavaRunResponse(
        success=result.success,
        output=result.output,
        error=result.error,
        compile_output=result.compile_output,
        duration_ms=result.duration_ms,
        timed_out=result.timed_out,
    )


@app.post("/api/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    subject: str | None = None,
    user: AuthSession = Depends(require_admin),
):
    subject_key = subject_for_user(subject, user)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="支持 TXT、MD、CSV、PDF、PPT、PPTX 文件。",
        )

    payload = await file.read()
    if len(payload) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件超过 {settings.max_upload_mb}MB 限制。")

    safe_name = Path(file.filename or "knowledge.txt").name
    target = settings.knowledge_dir_for(subject_key) / safe_name
    rag = rag_manager.get(subject_key)
    previous_payload = target.read_bytes() if target.exists() else None
    target.write_bytes(payload)
    try:
        parsed_sections = rag.parse_file(target)
        if not parsed_sections:
            raise DocumentParseError(
                "文件中没有提取到可用文本。扫描型 PDF 请安装 PaddleOCR，"
                "或检查 PPT/PDF 是否包含文字内容。"
            )
        rag.rebuild()
    except DocumentParseError as exc:
        if previous_payload is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(previous_payload)
        raise HTTPException(status_code=400, detail=f"文件解析失败：{exc}") from exc
    except Exception as exc:
        if previous_payload is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(previous_payload)
        raise HTTPException(status_code=500, detail=f"知识库重建失败：{exc}") from exc

    files, chunks, sources = rag_manager.status(subject_key)
    return {
        "message": "上传成功，已完成知识库重建。",
        "subject": subject_key,
        "file_count": files,
        "chunk_count": chunks,
        "sources": sources,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: AuthSession = Depends(require_auth),
):
    incoming_history = [item.model_dump() for item in payload.messages]

    current_question = next(
        (
            item["content"]
            for item in reversed(incoming_history)
            if item["role"] == "user"
        ),
        "",
    )

    if not current_question:
        raise HTTPException(
            status_code=400,
            detail="本轮请求中没有找到用户问题。",
        )

    conversation_id = payload.conversation_id
    conversation = None
    subject = subject_for_user(payload.subject, user)

    # 新版：携带 conversation_id 时，从 SQLite 恢复真实历史。
    if conversation_id:
        conversation = get_conversation(
            settings.conversation_db_path,
            conversation_id,
            username=user.username,
        )

        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在。")

        conversation_subject = normalize_subject(conversation.get("subject"))
        if conversation_subject != user.subject:
            raise HTTPException(
                status_code=403,
                detail="当前登录账号没有访问该会话的权限。",
            )
        subject = conversation_subject

        stored_messages = get_messages(
            settings.conversation_db_path,
            conversation_id,
        )

        history = [
            {
                "role": item["role"],
                "content": item["content"],
            }
            for item in stored_messages
        ]

        # 保存本轮用户消息，再拼入模型上下文。
        add_message(
            settings.conversation_db_path,
            conversation_id,
            role="user",
            content=current_question,
            username=user.username,
        )

        history.append(
            {
                "role": "user",
                "content": current_question,
            }
        )

    # 旧版兼容：未提供 conversation_id 时，继续沿用前端完整传递历史。
    else:
        history = incoming_history

    rag = rag_manager.get(subject)
    evidence_rows = (
        rag.retrieve(current_question, payload.top_k)
        if payload.use_rag and payload.top_k > 0
        else []
    )

    messages = build_messages(
        history,
        rag.format_evidence(evidence_rows),
        payload.agent_mode,
        payload.language,
        subject,
    )

    try:
        answer, model_used = await generate(
            settings=settings,
            messages=messages,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"模型服务调用失败：{exc}",
        ) from exc

    evidence = [
        Evidence(
            chunk_id=item.chunk_id,
            doc_id=item.doc_id,
            source_file=item.source_file,
            score=item.score,
            text=item.text,
            location=item.location,
            document_type=item.document_type,
        )
        for item in evidence_rows
    ]

    title = current_question[:24] + (
        "…" if len(current_question) > 24 else ""
    )
    title = title or "新对话"
    saved_assistant_message = None

    # 新版：保存真实模型回答、RAG 证据和模型名称。
    if conversation_id:
        saved_assistant_message = add_message(
            settings.conversation_db_path,
            conversation_id,
            role="assistant",
            content=answer,
            evidence=[item.model_dump() for item in evidence],
            model_used=model_used,
            username=user.username,
        )
        # 首次提问时自动把“新对话”改成问题标题。
        if conversation and conversation["title"] == "新对话":
            update_conversation(
                settings.conversation_db_path,
                conversation_id,
                title=title,
                agent_mode=payload.agent_mode,
                username=user.username,
            )
        else:
            update_conversation(
                settings.conversation_db_path,
                conversation_id,
                agent_mode=payload.agent_mode,
                username=user.username,
            )

    # 旧版：继续保留 JSONL 日志，保证原前端功能不受影响。
    else:
        append_jsonl(
            settings.chat_log_path_for(subject),
            {
                "subject": subject,
                "agent_mode": payload.agent_mode,
                "messages": history,
                "answer": answer,
                "model_used": model_used,
                "evidence": [item.model_dump() for item in evidence],
            },
        )

    return ChatResponse(
        answer=answer,
        model_used=model_used,
        evidence=evidence,
        title=title,
        subject=subject,
        conversation_id=conversation_id,
        assistant_message_id=(
            saved_assistant_message["message_id"]
            if saved_assistant_message
            else None
        ),
    )

@app.post("/api/feedback")
async def feedback(
    payload: FeedbackRequest,
    user: AuthSession = Depends(require_auth),
):
    subject = subject_for_user(payload.subject, user)
    feedback_payload = payload.model_dump()
    feedback_payload["subject"] = subject
    append_jsonl(settings.feedback_log_path_for(subject), feedback_payload)
    return {"message": "反馈已保存，可用于后续整理为 LoRA / QLoRA 训练样本。"}
