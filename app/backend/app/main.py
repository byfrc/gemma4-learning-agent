from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .conversation_store import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation,
    get_messages,
    init_db,
    list_conversations,
    update_conversation,
    get_message_feedback,
    save_message_feedback,
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
    KnowledgeStatus,
    MessageFeedbackResponse,
    MessageFeedbackSaveRequest,
    SubjectInfo,
)
from .storage import append_jsonl

settings = get_settings()
init_db(settings.conversation_db_path)

rag_manager = SubjectRAGManager(settings)

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def create_new_conversation(payload: ConversationCreateRequest):
    subject = normalize_subject(payload.subject)
    conversation = create_conversation(
        settings.conversation_db_path,
        title=payload.title,
        agent_mode=payload.agent_mode,
        subject=subject,
    )
    return ConversationSummary(**conversation)


@app.get("/api/conversations", response_model=list[ConversationSummary])
async def get_conversation_list(subject: str | None = None):
    conversations = list_conversations(
        settings.conversation_db_path,
        subject=subject,
    )
    return [ConversationSummary(**item) for item in conversations]


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(conversation_id: str):
    conversation = get_conversation(
        settings.conversation_db_path,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在。")

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
):
    conversation = update_conversation(
        settings.conversation_db_path,
        conversation_id,
        title=payload.title,
        agent_mode=payload.agent_mode,
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在。")

    return ConversationSummary(**conversation)


@app.delete("/api/conversations/{conversation_id}")
async def remove_conversation(conversation_id: str):
    deleted = delete_conversation(
        settings.conversation_db_path,
        conversation_id,
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
):
    conversation = get_conversation(
        settings.conversation_db_path,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在。")

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

                lines.extend(
                    [
                        f"- **来源**：{source_file}",
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
):
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
async def get_quality_feedback(message_id: str):
    result = get_message_feedback(
        settings.conversation_db_path,
        message_id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="该消息暂无评分记录。")

    return MessageFeedbackResponse(**result)


@app.get("/api/health")
async def health(subject: str | None = None):
    subject_key = normalize_subject(subject)
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
async def knowledge_status(subject: str | None = None):
    subject_key = normalize_subject(subject)
    file_count, chunk_count, sources = rag_manager.status(subject_key)
    return KnowledgeStatus(
        subject=subject_key,
        file_count=file_count,
        chunk_count=chunk_count,
        sources=sources,
    )


@app.post("/api/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    subject: str = settings.default_subject,
):
    subject_key = normalize_subject(subject)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".txt", ".md", ".csv"}:
        raise HTTPException(status_code=400, detail="当前部署版支持 TXT、MD、CSV；PDF/DOCX 可作为第二阶段接入解析器。")

    payload = await file.read()
    if len(payload) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件超过 {settings.max_upload_mb}MB 限制。")

    safe_name = Path(file.filename or "knowledge.txt").name
    target = settings.knowledge_dir_for(subject_key) / safe_name
    target.write_bytes(payload)
    rag_manager.rebuild(subject_key)

    files, chunks, sources = rag_manager.status(subject_key)
    return {
        "message": "上传成功，已完成知识库重建。",
        "subject": subject_key,
        "file_count": files,
        "chunk_count": chunks,
        "sources": sources,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
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
    subject = normalize_subject(payload.subject)

    # 新版：携带 conversation_id 时，从 SQLite 恢复真实历史。
    if conversation_id:
        conversation = get_conversation(
            settings.conversation_db_path,
            conversation_id,
        )

        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在。")

        subject = normalize_subject(conversation.get("subject"))

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
        )
        # 首次提问时自动把“新对话”改成问题标题。
        if conversation and conversation["title"] == "新对话":
            update_conversation(
                settings.conversation_db_path,
                conversation_id,
                title=title,
                agent_mode=payload.agent_mode,
            )
        else:
            update_conversation(
                settings.conversation_db_path,
                conversation_id,
                agent_mode=payload.agent_mode,
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
async def feedback(payload: FeedbackRequest):
    subject = normalize_subject(payload.subject)
    append_jsonl(settings.feedback_log_path_for(subject), payload.model_dump())
    return {"message": "反馈已保存，可用于后续整理为 LoRA / QLoRA 训练样本。"}
