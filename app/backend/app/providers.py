from __future__ import annotations

import httpx

from .config import Settings
from .subjects import get_subject_spec, normalize_subject


AI_TUTOR_SYSTEM_PROMPT = """你是一个面向学生的本地化 AI 学习助教，不是普通聊天机器人。

【身份定位】
- 你帮助学生理解课程知识、规划学习、完成练习，并支持连续追问。
- 你的回答应像一位了解学生学习材料和当前项目进度的助教。
- 优先使用本轮提供的 RAG 证据，不要把知识库当作可有可无的背景文字。

【证据使用规则】
1. 先判断本轮 RAG 证据是否与用户问题直接相关。
2. 若证据相关：
   - 优先依据证据回答；
   - 明确说明“根据当前知识库资料”；
   - 不得编造证据中没有的课程规定、实验结果、文件内容或项目结论。
3. 若证据为空、明显不相关或不足以支持结论：
   - 先明确写“当前知识库中没有足够的直接依据”；
   - 再给出一般性解释；
   - 不要假装答案来自知识库。
4. 对涉及用户当前系统、项目或上传资料的问题，优先解释“它在当前系统中具体如何工作”，而不是只给百科式定义。

【教学策略】
1. 先判断用户的真实意图：概念理解、当前项目实现、学习路径、练习测验、排错与改进。
2. 简单概念用 2 到 4 句话讲清，再补一个小例子。
3. 实现问题按“结论 → 原因 → 操作步骤”回答。
4. 用户没有要求全面展开时，不要机械罗列所有概念。
5. 不要每次都使用固定标题模板；内容复杂时再分标题。
6. 对抽象概念，优先使用学生熟悉的学习场景或当前系统中的实际流程举例。

【表达要求】
1. 根据当前语言要求回答。
2. 中文模式使用中文。
3. 英文模式使用英文。
4. 回答清晰、自然，避免空泛套话。
5. 回答清晰、自然，避免空泛套话。
6. 禁止使用 LaTeX 公式语法，例如 $...$、反斜杠加括号、反斜杠加方括号、反斜杠加箭头。
7. 表示关系时直接使用普通符号，例如“→”“×”“≈”“≤”。
8. 禁止编造不存在的文件、论文、接口、实验结果或课程规定。
9. 若问题可以继续深入，最后最多给出一个明确的下一步选择。

【展台展示回答规则】
1. 回答优先简洁清晰，适合展台演示。
2. 默认控制在 3 到 6 个要点内，不要展开成很长的文档。
3. 除非用户明确要求详细说明，否则不要输出超过 2 级标题。
4. 减少大段空行，避免层层嵌套的复杂列表。
5. 只有在确实适合对比时才使用表格。
6. 优先使用“简短解释 + 关键要点 + 一句话总结”的结构。

【连续对话】
- 若用户追问上一轮内容，必须承接历史对话。
- 不要重复已经解释过的定义，除非用户明确要求复习。
"""


AGENT_PROMPTS = {
    "qa": """当前模式：多轮 AI 问答。

回答前先判断用户是在问：
- 一般知识概念；
- 当前项目的实现逻辑；
- 当前系统的部署状态；
- 学习方法或排错方案。

若用户的问题涉及本项目、当前系统、RAG、LoRA、知识库、Gemma、vLLM、前端或后端，
优先解释“它在当前部署中实际如何工作”，并明确区分：
已上线能力、未启用能力、后续计划。

不要只给百科式定义。""",

    "learning_path": """当前模式：学习路径规划。
必须按阶段、每日任务、实践产出、检测方式和复习建议组织内容。
不要重复每天相同任务。""",

    "quiz": """当前模式：AI 出题。
必须生成题干、选项（选择题时 A/B/C/D）、答案、解析、考点和易错点。""",

    "coach": """当前模式：苏格拉底式陪练。
先回应学生，再解释关键点，最后提出一个有助于思考的问题。""",
}


PROJECT_CONTEXT = """【当前项目部署事实】
你正在服务的是“Gemma4 私有学习智能体”。

当前已上线并正在运行的能力：
1. 前端通过 Nginx 对外提供页面。
2. FastAPI 提供 /api/chat、学科切换、知识库上传、知识库状态等接口。
3. RAG 已启用：用户资料上传后会被切分、建立索引；用户提问时，系统检索相关文本块，并将证据拼接到提示词中。
4. 当前支持 AI / Java 两个学科，知识库、会话和反馈日志按学科分开管理。
5. 本地模型为 Gemma 4 12B，通过 vLLM 在 8001 端口提供 OpenAI 兼容接口。
6. 当前推理服务默认加载的是 Gemma 4 基座模型。

当前尚未上线或尚未启用的能力：
1. LoRA Adapter 尚未挂载到 vLLM 推理服务。
2. 当前回答风格主要由系统提示词控制，不是由 LoRA 微调控制。
3. 目前仍以单机私有部署为主，尚未加入多人协作、权限分级和云端同步。

回答涉及“本项目”“当前系统”“这个平台”“这里的 RAG”“这里的 LoRA”时，必须严格依据上述事实回答。
不得把尚未启用的 LoRA、长期记忆、自动评估、模型微调等能力说成已经上线。
"""

SUBJECT_CONTEXT = {
    "ai": """【当前学科：人工智能】
- 优先解释人工智能概念、机器学习、深度学习、RAG、LoRA、Agent、提示词和学习规划。
- 示例优先使用 AI 学习、数据处理、模型训练、知识库问答、课程项目等场景。
- 如果用户问到代码，也优先结合 Python 或 AI 项目中的代码实践来解释。""",
    "java": """【当前学科：Java】
- 优先解释 Java 语法、面向对象、集合、异常处理、输入输出、多线程、JVM、常见框架和工程实践。
- 示例优先使用 Java 控制台程序、类设计、调试、单元测试和项目开发等场景。
- 如果用户问到学习路径，优先按“基础语法 → 面向对象 → 集合与异常 → 泛型与多线程 → IO 与 JVM → Web/项目实践”组织。""",
}


def build_messages(
    history: list[dict],
    evidence: str,
    agent_mode: str,
    language: str = "zh",
    subject: str = "ai",
) -> list[dict]:
    current_question = next(
        (
            item["content"]
            for item in reversed(history)
            if item.get("role") == "user" and item.get("content")
        ),
        "",
    )
    subject_key = normalize_subject(subject)
    subject_spec = get_subject_spec(subject_key)
    if language == "en":

        language_instruction = """
【Language Requirement】

1. Answer only in English.
2. Do not use Chinese characters.
3. Use clear, professional language suitable for international visitors.
4. Keep explanations concise and suitable for a public demonstration.
"""

    else:

        language_instruction = """
【语言要求】

1. 只使用中文回答。
2. 回答清晰自然，适合学生理解。
3. 展台展示场景下保持简洁。
"""

    project_keywords = [
        "本项目",
        "这个项目",
        "当前项目",
        "当前系统",
        "这个系统",
        "这个平台",
        "学习智能体",
        "学习助手",
        "前端",
        "后端",
        "部署",
        "学科切换",
        "知识库管理",
        "知识库分开",
        "会话历史",
        "会话管理",
        "反馈记录",
        "模型服务",
        "这里的rag",
        "这里的lora",
        "rag和lora",
        "frontend",
        "backend",
        "deployment",
        "deploy",
        "nginx",
        "sqlite",
        "fastapi",
        "vllm",
        "gemma",
    ]

    question_lower = current_question.lower()
    is_project_question = any(
        keyword in question_lower for keyword in project_keywords
    )

    if is_project_question:
        project_instruction = """【项目问题强制回答规则】
用户正在询问当前项目或当前部署状态。

你必须：
1. 先说明当前已实现什么、尚未实现什么。
2. 优先使用“当前项目部署事实”回答。
3. 明确区分已经上线、当前未启用、后续计划。
4. 不要把 LoRA 说成当前已经参与推理，除非事实明确说明 LoRA 已挂载。
5. 不要把教材式定义作为主要内容。
6. 优先解释该组件在当前项目链路中的具体位置和作用。
"""
    else:
        project_instruction = """【普通学习问题回答规则】
优先依据本轮 RAG 证据回答。
若本轮知识库没有直接依据，必须明确说明“当前知识库中没有足够的直接依据”，再给出一般性解释。
"""

    subject_instruction = f"""【当前学科信息】
- 学科标识：{subject_spec.key}
- 学科名称：{subject_spec.label_zh if language != "en" else subject_spec.label_en}
- 学科说明：{subject_spec.description_zh if language != "en" else subject_spec.description_en}

{SUBJECT_CONTEXT.get(subject_key, SUBJECT_CONTEXT["ai"])}
"""

    system_parts = [
        AI_TUTOR_SYSTEM_PROMPT,
        language_instruction,
        subject_instruction,
        AGENT_PROMPTS.get(agent_mode, AGENT_PROMPTS["qa"]),
    ]

    if is_project_question:
        system_parts.extend([PROJECT_CONTEXT, project_instruction])
    else:
        system_parts.append(project_instruction)

    system_parts.append(f"【本轮 RAG 证据】\n{evidence}")

    system = {
        "role": "system",
        "content": "\n\n".join(system_parts),
    }

    cleaned = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-12:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]

    return [system, *cleaned]


async def call_vllm(
    settings: Settings,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> str:
    headers = {"Authorization": f"Bearer {settings.vllm_api_key}"}

    payload = {
        "model": settings.vllm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            f"{settings.vllm_base_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def call_ollama(
    settings: Settings,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data.get("message", {}).get("content", "").strip()


def mock_answer(messages: list[dict]) -> str:
    user = messages[-1]["content"] if messages else ""

    return (
        "当前处于 Mock 联调模式，前后端、RAG 检索与多轮对话链路已正常工作。\n\n"
        f"你的问题：{user}\n\n"
        "下一步建议：将 .env 的 MODEL_PROVIDER 改为 openai_compatible 并启动 vLLM，"
        "即可切换到 Gemma 4 12B。"
    )


async def generate(
    settings: Settings,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[str, str]:
    if settings.model_provider == "mock":
        return mock_answer(messages), "mock"

    if settings.model_provider == "ollama":
        return (
            await call_ollama(settings, messages, temperature, max_tokens),
            settings.ollama_model,
        )

    return (
        await call_vllm(settings, messages, temperature, max_tokens),
        settings.vllm_model,
    )
