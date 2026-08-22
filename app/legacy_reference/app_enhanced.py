import json
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# 大模型相关依赖采用延迟导入，避免 Streamlit 启动阶段直接崩溃

from enhanced_rag import HybridRAGEngine, load_uploaded_knowledge_files

st.set_page_config(page_title="私有垂域AI学习平台", page_icon="🧠", layout="wide")
APP_PATCH_VERSION = "qa_multiturn_ai_tutor_prompt_20260607"

# ========== Windows/本地项目路径适配 ==========
PROJECT_DIR = Path(__file__).resolve().parent
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma2"

# ============================================================
# LoRA 智能体模型路径
# ============================================================
GEMMA2_BASE_MODEL_PATH = PROJECT_DIR / "models" / "gemma" / "gemma-2-2b-it"
GEMMA2_LORA_ADAPTER_PATH = PROJECT_DIR / "trained_models" / "gemma_lora" / "adapter"

GEMMA4_BASE_MODEL_PATH = PROJECT_DIR / "models" / "gemma" / "gemma-4-E2B-it"
GEMMA4_LORA_ADAPTER_PATH = PROJECT_DIR / "trained_models" / "gemma4_e2b_lora" / "adapter"

# 兼容旧代码：默认指向 Gemma2-LoRA
BASE_MODEL_PATH = GEMMA2_BASE_MODEL_PATH
LORA_ADAPTER_PATH = GEMMA2_LORA_ADAPTER_PATH

# Gemma4 推理专用 Python 环境。Gemma4 需要较新的 transformers，
# 不建议在 lawdebate2 主环境中直接加载。
DEFAULT_GEMMA4_PYTHON = r"D:\conda_envs\gemma4_test\python.exe"
GEMMA4_INFER_SCRIPT = PROJECT_DIR / "scripts" / "gemma4_lora_infer_cli.py"



AI_TUTOR_SYSTEM_PROMPT = """
你是一个面向学生的本地化 AI 学习助教，不是普通聊天机器人。

【身份定位】
1. 你要像耐心的助教一样回答问题：先给结论，再解释原因，最后给学习建议。
2. 你服务于“私有垂域 AI 学习平台”，需要优先结合本地 RAG 知识库证据。
3. 你擅长课程问答、学习路径规划、AI 出题、错题讲解和陪练式多轮对话。

【回答原则】
1. 回答必须使用中文。
2. 面向本科生或初学者，不要故意使用复杂术语。
3. 不要只堆砌概念，要结合例子说明。
4. 如果问题包含 RAG 检索证据，必须优先依据证据回答。
5. 如果证据不足，明确说明“知识库中没有足够依据”，再给出一般性解释。
6. 不要编造不存在的文件、论文、接口或训练结果。
7. 多轮对话时，要记住前文学生的问题和你的回答，避免重复解释。
8. 如果学生追问“为什么/怎么做/举例”，要基于上一轮继续展开，而不是重新开始。

【推荐输出结构】
- 直接结论：用 1-2 句话先回答。
- 分点解释：按 2-5 点说明核心原因或步骤。
- 举例说明：必要时给一个简单例子。
- 学习建议：给学生下一步可以做什么。
- 依据来源：如果使用了 RAG 证据，简要说明参考了哪些资料。

【风格要求】
- 具体、清晰、可执行。
- 避免空泛套话。
- 避免重复同一句话。
- 对学习计划、出题、错题讲解要格式规范。
"""

@st.cache_resource
def load_lora_agent_model():
    """
    加载 Gemma-2-2B 基座模型 + LoRA Adapter。
    采用延迟导入，避免 Streamlit 启动阶段因 transformers/peft/torch 依赖问题直接崩溃。
    """
    if not BASE_MODEL_PATH.exists():
        raise FileNotFoundError(f"基座模型路径不存在：{BASE_MODEL_PATH}")

    if not LORA_ADAPTER_PATH.exists():
        raise FileNotFoundError(f"LoRA Adapter 路径不存在：{LORA_ADAPTER_PATH}")

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel
    except Exception as e:
        raise RuntimeError(
            "LoRA模型依赖导入失败。请检查当前conda环境中的 transformers / peft / torch 是否正常。"
            f"\n原始错误：{e}"
        )

    tokenizer = AutoTokenizer.from_pretrained(
        str(BASE_MODEL_PATH),
        trust_remote_code=True
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        str(BASE_MODEL_PATH),
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True
    )

    model = PeftModel.from_pretrained(
        base_model,
        str(LORA_ADAPTER_PATH)
    )

    model.eval()
    return tokenizer, model

DATA_DIR = PROJECT_DIR / "runtime_data"
DATA_DIR.mkdir(exist_ok=True)
QA_LOG = DATA_DIR / "qa_history.jsonl"
FEEDBACK_LOG = DATA_DIR / "feedback.jsonl"
TRAIN_OUTPUT_DIR = PROJECT_DIR / "training_outputs"
TRAIN_OUTPUT_DIR.mkdir(exist_ok=True)
TRAIN_LOG = TRAIN_OUTPUT_DIR / "metrics_log.jsonl"
TRAIN_RUN_LOG = TRAIN_OUTPUT_DIR / "lora_train_run.log"
TRAIN_PID_FILE = TRAIN_OUTPUT_DIR / "lora_train.pid"
TRAIN_CONFIG_FILE = TRAIN_OUTPUT_DIR / "last_lora_train_config.json"

DEFAULT_GEMMA_MODEL_PATH = PROJECT_DIR / "models" / "gemma" / "gemma-2-2b-it"
DEFAULT_GEMMA_DATASET = PROJECT_DIR / "data" / "lora_data" / "train_data_instruction_output.jsonl"
DEFAULT_GEMMA_OUTPUT = PROJECT_DIR / "trained_models" / "gemma_lora"
DEFAULT_GENERAL_MODEL_PATH = PROJECT_DIR / "models" / "base_model"
DEFAULT_GENERAL_OUTPUT = PROJECT_DIR / "trained_models" / "vertical_lora"

if "rag" not in st.session_state:
    st.session_state.rag = HybridRAGEngine(str(PROJECT_DIR / "models" / "hybrid_rag.joblib"))
    st.session_state.rag.load()
if "selected_model" not in st.session_state:
    st.session_state.selected_model = DEFAULT_MODEL
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def gemma4_lora_generate_via_subprocess(
    prompt: str,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    system_prompt: str = AI_TUTOR_SYSTEM_PROMPT,
) -> str:
    import tempfile

    if not Path(DEFAULT_GEMMA4_PYTHON).exists():
        return f"Gemma4 专用 Python 不存在：{DEFAULT_GEMMA4_PYTHON}"

    if not GEMMA4_INFER_SCRIPT.exists():
        return f"Gemma4 推理脚本不存在：{GEMMA4_INFER_SCRIPT}"

    final_prompt = f"""
【系统身份设定】
{system_prompt}

【用户任务】
{prompt}
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        prompt_file = tmpdir / "prompt.txt"
        output_file = tmpdir / "answer.txt"
        prompt_file.write_text(final_prompt, encoding="utf-8")

        cmd = [
            DEFAULT_GEMMA4_PYTHON,
            str(GEMMA4_INFER_SCRIPT),
            "--model_path", str(GEMMA4_BASE_MODEL_PATH),
            "--adapter_path", str(GEMMA4_LORA_ADAPTER_PATH),
            "--prompt_file", str(prompt_file),
            "--output_file", str(output_file),
            "--max_new_tokens", str(max_new_tokens),
            "--temperature", str(temperature),
            "--top_p", str(top_p),
        ]

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=900,
        )

        if proc.returncode != 0:
            return (
                "Gemma4-LoRA 子进程推理失败。\n\n"
                f"返回码 returncode：{proc.returncode}\n\n"
                f"命令：{' '.join(cmd)}\n\n"
                f"STDOUT:\n{proc.stdout}\n\n"
                f"STDERR:\n{proc.stderr}"
            )

        if output_file.exists():
            return output_file.read_text(encoding="utf-8", errors="ignore").strip()

        return (
            "Gemma4-LoRA 子进程已结束，但没有生成输出文件。\n\n"
            f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
        )


def lora_generate(
    prompt: str,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    model_version: str = "Gemma2-LoRA",
    system_prompt: str = AI_TUTOR_SYSTEM_PROMPT,
) -> str:
    if model_version == "Gemma4-LoRA":
        return gemma4_lora_generate_via_subprocess(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            system_prompt=system_prompt,
        )

    import torch

    tokenizer, model, model_type = load_lora_agent_model("Gemma2-LoRA")

    final_prompt = f"""
【系统身份设定】
{system_prompt}

【用户任务】
{prompt}
"""

    messages = [{"role": "user", "content": final_prompt}]
    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

def ollama_models():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def generate(prompt: str, model: str, temperature: float = 0.4):
    try:
        with requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True, "temperature": temperature},
            stream=True,
            timeout=120,
        ) as r:
            if r.status_code != 200:
                try:
                    detail = r.text
                except Exception:
                    detail = ""
                yield f"模型调用失败：HTTP {r.status_code}\n\n详细信息：{detail}"
                return
            for line in r.iter_lines():
                if not line:
                    continue
                data = json.loads(line.decode("utf-8"))
                if "response" in data:
                    yield data["response"]
    except Exception as e:
        yield f"无法连接Ollama或生成失败：{e}"


def log_jsonl(path: Path, data: dict):
    data["timestamp"] = datetime.now().isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def is_pid_running(pid: int) -> bool:
    try:
        if os.name == "nt":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def read_train_pid() -> int | None:
    if not TRAIN_PID_FILE.exists():
        return None
    try:
        pid = int(TRAIN_PID_FILE.read_text(encoding="utf-8").strip())
        return pid if is_pid_running(pid) else None
    except Exception:
        return None


def tail_file(path: Path, max_lines: int = 120) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(lines[-max_lines:])


def start_lora_training(config: dict) -> tuple[bool, str]:
    running_pid = read_train_pid()
    if running_pid:
        return False, f"已有训练任务正在运行，PID={running_pid}"

    script_name = "lora_train_gemma.py" if config.get("model_family") == "Gemma/Gemma4" else "lora_train_enhanced.py"
    script_path = PROJECT_DIR / "training" / script_name
    if not script_path.exists():
        return False, f"未找到 {script_path}"

    # 每次新训练前，清理项目级训练曲线日志，避免前端展示旧数据。
    if TRAIN_LOG.exists():
        TRAIN_LOG.unlink(missing_ok=True)

    cmd = [
        sys.executable,
        str(script_path),
        "--model_path", config["model_path"],
        "--dataset", config["dataset"],
        "--output_dir", config["output_dir"],
        "--epochs", str(config["epochs"]),
        "--eval_size", str(config["eval_size"]),
        "--max_length", str(config["max_length"]),
        "--lr", str(config["lr"]),
        "--batch", str(config["batch"]),
        "--grad_accum", str(config["grad_accum"]),
        "--r", str(config["r"]),
        "--alpha", str(config["alpha"]),
    ]
    if config.get("model_family") == "Gemma/Gemma4":
        cmd += ["--target", config.get("target", "attention")]
        if config.get("load_in_8bit"):
            cmd.append("--load_in_8bit")
    if config.get("merge_after_train"):
        cmd.append("--merge_after_train")

    TRAIN_CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    TRAIN_RUN_LOG.parent.mkdir(parents=True, exist_ok=True)

    with TRAIN_RUN_LOG.open("a", encoding="utf-8") as logf:
        logf.write(f"\n\n========== {datetime.now().isoformat()} 启动LoRA训练 ==========" + "\n")
        logf.write("项目目录：" + str(PROJECT_DIR) + "\n")
        logf.write("命令：" + " ".join([f'\"{x}\"' if " " in str(x) else str(x) for x in cmd]) + "\n")
        logf.flush()

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # 关键修改：解决 Windows 默认 GBK 编码导致 TRL 读取 jinja 模板失败
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        popen_kwargs = {
            "stdout": logf,
            "stderr": subprocess.STDOUT,
            "cwd": str(PROJECT_DIR),
            "env": env
        }

        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd, **popen_kwargs)

    TRAIN_PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    return True, f"训练已启动，PID={proc.pid}"


def stop_lora_training() -> str:
    pid = read_train_pid()
    if not pid:
        TRAIN_PID_FILE.unlink(missing_ok=True)
        return "当前没有运行中的训练任务。"
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        TRAIN_PID_FILE.unlink(missing_ok=True)
        return f"已发送停止信号，PID={pid}"
    except Exception as e:
        return f"停止失败：{e}"


def hero():
    st.markdown("""
    <div style="padding:28px;border-radius:18px;background:linear-gradient(135deg,#1f4f9a,#53a6ff);color:white;margin-bottom:18px">
      <h1 style="margin:0">🧠 私有垂域AI学习平台</h1>
      <p style="margin:8px 0 0 0;font-size:18px">本地RAG检索 · Gemma/Gemma4 LoRA持续训练 · 多智能体学习功能 · Ollama本地部署闭环</p>
    </div>
    """, unsafe_allow_html=True)


def sidebar():
    st.sidebar.title("导航")
    models = ollama_models()
    if models:
        st.session_state.selected_model = st.sidebar.selectbox("Ollama模型", models, index=0)
    else:
        st.sidebar.warning("未检测到Ollama模型，可先运行 ollama serve / ollama pull gemma2")
    st.sidebar.caption(f"项目目录：{PROJECT_DIR}")
    st.sidebar.write("RAG状态：", "✅ 已构建" if st.session_state.rag.ready() else "⚠️ 未构建")
    st.sidebar.write("知识块数：", len(st.session_state.rag.chunks))
    return st.sidebar.radio("功能区", ["一键运维", "知识库/RAG", "学生智能体", "训练可视化", "教师分析"])


def page_ops():
    st.header("🚀 一键式启动运维")
    running_pid = read_train_pid()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ollama", "已连接" if ollama_models() else "未连接")
    c2.metric("本地知识块", len(st.session_state.rag.chunks))
    c3.metric("QA日志", sum(1 for _ in QA_LOG.open(encoding="utf-8")) if QA_LOG.exists() else 0)
    c4.metric("反馈日志", sum(1 for _ in FEEDBACK_LOG.open(encoding="utf-8")) if FEEDBACK_LOG.exists() else 0)
    c5.metric("LoRA训练", f"运行中 PID {running_pid}" if running_pid else "未运行")

    st.subheader("闭环流程")
    st.info("数据上传/清洗 → Hybrid RAG构建 → 学生多Agent使用 → 反馈采集 → Gemma/Gemma4 LoRA增量训练 → 保存/合并模型 → 导入Ollama → 再次服务")

    st.subheader("🔥 一键LoRA训练中心")
    st.caption("已按你的Windows本地项目目录做了路径适配；默认使用项目内 models/gemma/gemma-2-2b-it、data/lora_data/train_data_instruction_output.jsonl、trained_models/gemma_lora。")

    with st.form("lora_train_form"):
        model_family = st.selectbox("选择训练模型类型", ["Gemma/Gemma4", "DeepSeek/Qwen/Llama通用"], index=0)
        if model_family == "Gemma/Gemma4":
            default_model = str(DEFAULT_GEMMA_MODEL_PATH)
            default_dataset = str(DEFAULT_GEMMA_DATASET)
            default_output = str(DEFAULT_GEMMA_OUTPUT)
            default_epochs, default_batch, default_grad, default_len = 1.0, 1, 8, 512
            default_r, default_alpha = 8, 16
        else:
            default_model = str(DEFAULT_GENERAL_MODEL_PATH)
            default_dataset = str(DEFAULT_GEMMA_DATASET)
            default_output = str(DEFAULT_GENERAL_OUTPUT)
            default_epochs, default_batch, default_grad, default_len = 2.0, 1, 8, 1024
            default_r, default_alpha = 16, 32

        col_a, col_b = st.columns(2)
        model_path = col_a.text_input("基座模型路径", default_model)
        dataset = col_b.text_input("训练数据JSONL", default_dataset)
        output_dir = st.text_input("输出目录", default_output)

        col1, col2, col3, col4 = st.columns(4)
        epochs = col1.number_input("epochs", min_value=0.1, max_value=20.0, value=default_epochs, step=0.5)
        lr = col2.number_input("learning_rate", min_value=1e-6, max_value=1e-3, value=1e-4, format="%.6f")
        batch = col3.number_input("batch_size", min_value=1, max_value=32, value=default_batch, step=1)
        grad_accum = col4.number_input("grad_accum", min_value=1, max_value=64, value=default_grad, step=1)

        col5, col6, col7, col8 = st.columns(4)
        max_length = col5.number_input("max_length", min_value=256, max_value=8192, value=default_len, step=256)
        eval_size = col6.number_input("eval_size", min_value=1, max_value=20000, value=1, step=1)
        r = col7.number_input("LoRA r", min_value=1, max_value=256, value=default_r, step=1)
        alpha = col8.number_input("LoRA alpha", min_value=1, max_value=512, value=default_alpha, step=1)

        target = "attention"
        load_in_8bit = False
        if model_family == "Gemma/Gemma4":
            col9, col10 = st.columns(2)
            target = col9.selectbox("Gemma LoRA注入层", ["attention", "all"], index=0, help="16GB显存建议先选attention；跑通后再试all。")
            load_in_8bit = col10.checkbox("使用8bit加载（Windows原生环境不建议）", value=False, help="当前Windows本地训练已默认关闭bitsandbytes量化，建议不要勾选。")

        merge_after_train = st.checkbox("训练完成后自动合并LoRA到基座模型，便于导入Ollama", value=False, help="16GB显存建议第一轮先不合并，只保存adapter；确认可用后再合并。")
        submitted = st.form_submit_button("🚀 一键启动LoRA训练", use_container_width=True)

    if submitted:
        missing = []
        if not Path(model_path).exists():
            missing.append(f"基座模型路径不存在：{model_path}")
        if not Path(dataset).exists():
            missing.append(f"训练数据不存在：{dataset}")
        if missing:
            st.error("\n".join(missing))
        else:
            config = {
                "model_family": model_family,
                "model_path": model_path.strip(),
                "dataset": dataset.strip(),
                "output_dir": output_dir.strip(),
                "epochs": float(epochs),
                "eval_size": int(eval_size),
                "max_length": int(max_length),
                "lr": float(lr),
                "batch": int(batch),
                "grad_accum": int(grad_accum),
                "r": int(r),
                "alpha": int(alpha),
                "target": target,
                "load_in_8bit": bool(load_in_8bit),
                "merge_after_train": bool(merge_after_train),
            }
            ok, msg = start_lora_training(config)
            (st.success if ok else st.error)(msg)

    colx, coly, colz = st.columns(3)
    if colx.button("🔄 刷新训练状态", use_container_width=True):
        st.rerun()
    if coly.button("⛔ 停止当前训练", use_container_width=True):
        st.warning(stop_lora_training())
    if colz.button("📊 跳转查看训练曲线", use_container_width=True):
        st.info("请在左侧切换到“训练可视化”。")

    if TRAIN_CONFIG_FILE.exists():
        with st.expander("最近一次训练配置"):
            st.json(json.loads(TRAIN_CONFIG_FILE.read_text(encoding="utf-8")))

    with st.expander("实时训练日志", expanded=bool(running_pid)):
        st.code(tail_file(TRAIN_RUN_LOG, 160) or "暂无日志", language="text")

    st.subheader("模型下载与路径检查")
    st.code(f'''# 进入你的项目目录
cd /d "{PROJECT_DIR}"

# 下载模型到项目内目录。把仓库名替换成你实际要用的Gemma/Gemma4基础模型。
huggingface-cli download <HF_GEMMA_MODEL_REPO> ^
  --local-dir "{DEFAULT_GEMMA_MODEL_PATH}" ^
  --local-dir-use-symlinks False

# 本地推理测试
python test_gemma_local.py''', language="bash")

    st.subheader("Ollama导入")
    merged_model_dir = st.text_input("合并模型目录", str(Path(output_dir) / "merged_model") if 'output_dir' in locals() else str(DEFAULT_GEMMA_OUTPUT / "merged_model"))
    ollama_name = st.text_input("Ollama模型名", "gemma-local-lora")
    with st.expander("Ollama导入命令模板"):
        st.code(f'''# 训练完成并合并模型后，建议先转GGUF再导入Ollama
# Windows下建议在WSL或Linux环境中使用llama.cpp转换GGUF
python convert_hf_to_gguf.py "{merged_model_dir}" --outfile "{Path(merged_model_dir).parent / 'model.gguf'}" --outtype f16

# 创建Modelfile后导入
ollama create {ollama_name} -f Modelfile
ollama run {ollama_name}''', language="bash")


def page_rag():
    st.header("📚 知识库与RAG检索优化")

    st.info(
        "支持一次上传多个 CSV / TXT / MD 文件。"
        "CSV 会按“每一行一条知识”处理；TXT/MD 会按“每个文件一篇文档”处理，后续再自动切块。"
    )

    uploaded_files = st.file_uploader(
        "上传CSV/TXT/MD知识库",
        type=["csv", "txt", "md"],
        accept_multiple_files=True
    )

    col1, col2, col3 = st.columns(3)
    chunk_size = col1.slider("切块长度", 200, 1000, 420, 20)
    overlap = col2.slider("重叠长度", 0, 200, 80, 10)
    top_k = col3.slider("召回数量", 1, 10, 5)

    col4, col5 = st.columns(2)
    show_preview = col4.checkbox("构建前预览数据", value=True)
    force_rebuild = col5.checkbox("强制重建索引", value=True)

    if uploaded_files:
        st.success(f"已选择 {len(uploaded_files)} 个文件：")
        for f in uploaded_files:
            st.write(f"- {f.name}")

        try:
            preview_df = load_uploaded_knowledge_files(uploaded_files)

            if show_preview:
                st.subheader("知识库数据预览")
                st.write(f"共读取到 {len(preview_df)} 条知识记录")
                st.dataframe(preview_df.head(20), use_container_width=True)

        except Exception as e:
            st.error(f"读取上传文件失败：{e}")
            preview_df = None

        if st.button("构建增强RAG索引", use_container_width=True):
            if preview_df is None or preview_df.empty:
                st.warning("没有可用于构建知识库的数据。")
                return

            with st.spinner("正在清洗、切块、构建 word + char 混合索引..."):
                stats = st.session_state.rag.build_from_dataframe(
                    preview_df,
                    text_columns=["content"],
                    metadata_columns=["source_file", "file_type", "row_index", "title"],
                    chunk_size=chunk_size,
                    overlap=overlap
                )

            st.success(f"RAG 知识库构建完成：{stats}")

            with st.expander("本次构建的数据来源统计", expanded=True):
                if "source_file" in preview_df.columns:
                    st.dataframe(
                        preview_df.groupby(["source_file", "file_type"]).size().reset_index(name="records"),
                        use_container_width=True
                    )
    else:
        st.warning("请先上传一个或多个 CSV / TXT / MD 文件。")

    st.divider()

    st.subheader("检索调试台")
    q = st.text_input("输入检索问题", "RAG 和 LoRA 有什么区别？")

    col_a, col_b, col_c = st.columns(3)
    min_score = col_a.slider("最低相似度阈值", 0.0, 0.3, 0.03, 0.01)
    candidate_k = col_b.slider("候选召回数量", 5, 100, 30, 5)
    mmr_lambda = col_c.slider("MMR相关性权重", 0.1, 1.0, 0.72, 0.01)

    if st.button("测试检索", use_container_width=True):
        docs = st.session_state.rag.retrieve(
            q,
            top_k=top_k,
            candidate_k=candidate_k,
            min_score=min_score,
            mmr_lambda=mmr_lambda
        )

        if not docs:
            st.warning("未召回内容。可以尝试降低最低相似度阈值，或补充知识库。")
            return

        st.success(f"召回 {len(docs)} 条证据")

        for i, d in enumerate(docs, 1):
            source_file = d.metadata.get("source_file", "未知来源")
            file_type = d.metadata.get("file_type", "")
            row_index = d.metadata.get("row_index", "")

            title = f"证据{i}｜score={d.score:.3f}｜{source_file}"
            if row_index != "":
                title += f"｜row={row_index}"

            with st.expander(title, expanded=(i == 1)):
                st.write(d.text)
                st.json({
                    "chunk_id": d.chunk_id,
                    "doc_id": d.doc_id,
                    "score": d.score,
                    "source_file": source_file,
                    "file_type": file_type,
                    "row_index": row_index,
                    "metadata": d.metadata
                })


def format_recent_history(history: list, max_turns: int = 6) -> str:
    if not history:
        return "暂无历史对话。"
    recent = history[-max_turns:]
    lines = []
    for i, msg in enumerate(recent, 1):
        role = "学生" if msg.get("role") == "user" else "AI助教"
        content = str(msg.get("content", "")).strip()
        if content:
            lines.append(f"{i}. {role}：{content}")
    return "\n".join(lines) if lines else "暂无历史对话。"


def ask_agent(task_name: str, user_input: str, extra: str = ""):
    docs = st.session_state.rag.retrieve(user_input, top_k=3) if st.session_state.rag.ready() else []

    role_map = {
        "AI问答": """
你是严谨的 AI 学习助教。
你的任务是结合本地知识库和历史对话帮助学生理解问题，而不是只给结论。
回答要求：
1. 先给一句话结论。
2. 再分点解释。
3. 如果涉及专业概念，要用通俗例子说明。
4. 如果使用了知识库资料，要说明依据来自哪些资料。
5. 如果学生是在追问上一轮内容，要承接上下文，不要重新开始。
""",
        "学习路径规划": """
你是学习路径规划智能体。
你的任务是把学生的学习目标拆解为可执行计划。
回答要求：
1. 给出总体目标。
2. 按阶段划分学习任务。
3. 给出每日或每周安排。
4. 给出练习任务。
5. 给出检测方式和复习建议。
""",
        "AI出题": """
你是 AI 命题智能体。skills
你的任务是根据知识点生成适合学生练习的题目。
回答要求：
1. 每道题包含题干。
2. 选择题必须包含 A/B/C/D 选项。
3. 每道题必须给出答案。
4. 每道题必须给出解析。
5. 解析要说明为什么正确、为什么其他选项不合适。
""",
        "AI聊天室": """
你是苏格拉底式 AI 陪练。
你的任务不是直接灌输答案，而是通过提示和追问帮助学生思考。
回答要求：
1. 先回应学生的问题。
2. 用通俗语言解释关键点。
3. 最后提出一个有帮助的追问。
""",
    }

    role = role_map.get(task_name, "你是AI学习助教")

    if st.session_state.rag.ready() and docs:
        prompt = st.session_state.rag.build_prompt(
            user_input + "\n" + extra,
            docs,
            role=role
        )
    else:
        prompt = f"""
{role}

【学生问题】
{user_input}

【补充要求】
{extra}

请以 AI 学习助教的身份回答。
"""
    return prompt, docs

def _render_agent_answer(prompt: str, docs: list, model_mode: str, temperature: float, max_new_tokens: int = 512) -> str:
    st.caption(f"DEBUG 当前 model_mode = [{model_mode}]")

    if "LoRA" in str(model_mode):
        return lora_generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature, model_version=model_mode)

    ans = ""
    box = st.empty()
    for ch in generate(prompt, st.session_state.selected_model, temperature):
        ans += ch
        box.markdown(ans)
    return ans

def page_student_agents():
    st.header("🎓 学生多智能体功能区")

    if "qa_chat_history" not in st.session_state:
        st.session_state.qa_chat_history = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    model_mode = st.radio(
        "选择智能体调用模型",
        ["Ollama基础模型", "Gemma2-LoRA", "Gemma4-LoRA"],
        horizontal=True,
        help=(
            "Ollama基础模型走本地Ollama接口；"
            "Gemma2-LoRA 调用 Gemma-2-2B + trained_models/gemma_lora/adapter；"
            "Gemma4-LoRA 通过 gemma4_test 环境调用 Gemma-4-E2B-it + trained_models/gemma4_e2b_lora/adapter。"
        )
    )

    if model_mode == "Gemma4-LoRA":
        active_base_path = GEMMA4_BASE_MODEL_PATH
        active_adapter_path = GEMMA4_LORA_ADAPTER_PATH
    elif model_mode == "Gemma2-LoRA":
        active_base_path = GEMMA2_BASE_MODEL_PATH
        active_adapter_path = GEMMA2_LORA_ADAPTER_PATH
    else:
        active_base_path = None
        active_adapter_path = None

    if model_mode in ["Gemma2-LoRA", "Gemma4-LoRA"]:
        col_info1, col_info2 = st.columns(2)
        col_info1.caption(f"基座模型：{active_base_path}")
        col_info2.caption(f"LoRA Adapter：{active_adapter_path}")

        if model_mode == "Gemma4-LoRA":
            st.caption(f"Gemma4 推理 Python：{DEFAULT_GEMMA4_PYTHON}")
            st.caption(f"Gemma4 推理脚本：{GEMMA4_INFER_SCRIPT}")

        col_reload, col_test = st.columns(2)
        if col_reload.button("🔄 重新加载LoRA模型缓存", use_container_width=True):
            load_lora_agent_model.clear()
            st.success("LoRA模型缓存已清理。Gemma4-LoRA 是子进程推理，不受该缓存影响。")
        if col_test.button("✅ 检查LoRA路径", use_container_width=True):
            missing = []
            if not active_base_path.exists():
                missing.append(f"基座模型不存在：{active_base_path}")
            if not active_adapter_path.exists():
                missing.append(f"Adapter不存在：{active_adapter_path}")
            if model_mode == "Gemma4-LoRA":
                if not Path(DEFAULT_GEMMA4_PYTHON).exists():
                    missing.append(f"Gemma4专用Python不存在：{DEFAULT_GEMMA4_PYTHON}")
                if not GEMMA4_INFER_SCRIPT.exists():
                    missing.append(f"Gemma4推理脚本不存在：{GEMMA4_INFER_SCRIPT}")
            if missing:
                st.error("\n".join(missing))
            else:
                st.success("基座模型、LoRA Adapter 和推理环境均存在。")
    else:
        st.caption(f"当前使用 Ollama 模型：{st.session_state.selected_model}")

    tab1, tab2, tab3, tab4 = st.tabs(["AI问答", "学习路径规划", "AI出题", "AI聊天室"])

    with tab1:
        st.subheader("💬 多轮 AI 问答")
        st.caption("支持类似 ChatGPT 的连续追问。系统会保留最近几轮上下文，并结合 RAG 检索证据回答。")

        col_a, col_b, col_c = st.columns([1, 1, 2])
        qa_top_k = col_a.slider("RAG证据数", 0, 5, 3, 1, key="qa_top_k")
        max_tokens = col_b.slider("最大生成长度", 128, 2048, 768, 64, key="qa_max_tokens")
        show_sources = col_c.checkbox("显示本轮检索证据", value=True)

        if st.button("🧹 清空 AI问答历史", use_container_width=True):
            st.session_state.qa_chat_history = []
            st.rerun()

        for msg in st.session_state.qa_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("role") == "assistant" and msg.get("sources"):
                    with st.expander("查看本轮 RAG 证据", expanded=False):
                        for i, src in enumerate(msg["sources"], 1):
                            st.markdown(f"**证据 {i}｜score={src.get('score', 0):.3f}｜{src.get('source_file', '未知来源')}**")
                            st.write(src.get("text", ""))

        user_q = st.chat_input("请输入你的问题，可以继续追问上一轮内容", key="qa_chat_input")
        if user_q and user_q.strip():
            st.session_state.qa_chat_history.append({"role": "user", "content": user_q})
            with st.chat_message("user"):
                st.markdown(user_q)

            history_text = format_recent_history(st.session_state.qa_chat_history[:-1], max_turns=6)

            docs = []
            if qa_top_k > 0 and st.session_state.rag.ready():
                docs = st.session_state.rag.retrieve(user_q, top_k=qa_top_k)

            extra = f"""
【最近历史对话】
{history_text}

【回答要求】
1. 如果学生是在追问上一轮内容，请承接历史上下文回答。
2. 如果 RAG 证据与问题相关，优先依据证据回答。
3. 如果 RAG 证据不足，明确说明“知识库中没有足够依据”，再给出一般性解释。
4. 回答结构建议：直接结论 → 分点解释 → 举例说明 → 学习建议。
"""
            role = """
你是严谨的 AI 学习助教。
你的任务是结合本地知识库和历史对话帮助学生理解问题。
你需要像 ChatGPT 一样支持多轮追问，但回答风格要更像课程助教。
"""
            if st.session_state.rag.ready() and docs:
                prompt = st.session_state.rag.build_prompt(
                    user_q + "\n" + extra,
                    docs,
                    role=role
                )
            else:
                prompt = f"""
{role}

【最近历史对话】
{history_text}

【学生当前问题】
{user_q}

【回答要求】
{extra}
"""

            st.caption(f"RAG召回 {len(docs)} 条证据；当前模型：{model_mode}")

            with st.chat_message("assistant"):
                with st.spinner("AI助教正在思考..."):
                    ans = _render_agent_answer(prompt, docs, model_mode, temperature=0.35, max_new_tokens=max_tokens)
                if "LoRA" in str(model_mode):
                    st.markdown(ans)

            sources = []
            for d in docs:
                sources.append({
                    "chunk_id": getattr(d, "chunk_id", ""),
                    "doc_id": getattr(d, "doc_id", ""),
                    "score": float(getattr(d, "score", 0.0)),
                    "source_file": d.metadata.get("source_file", "未知来源"),
                    "text": d.text,
                    "metadata": d.metadata,
                })

            if show_sources and sources:
                with st.expander("查看本轮 RAG 证据", expanded=False):
                    for i, src in enumerate(sources, 1):
                        st.markdown(f"**证据 {i}｜score={src.get('score', 0):.3f}｜{src.get('source_file', '未知来源')}**")
                        st.write(src.get("text", ""))

            st.session_state.qa_chat_history.append({
                "role": "assistant",
                "content": ans,
                "sources": sources,
                "model_mode": model_mode,
            })

            log_jsonl(QA_LOG, {
                "agent": "qa_multiturn",
                "model_mode": model_mode,
                "question": user_q,
                "answer": ans,
                "history": st.session_state.qa_chat_history[-8:],
                "evidence": sources,
            })

    with tab2:
        goal = st.text_input("学习目标", "两周内入门机器学习")
        level = st.selectbox("当前基础", ["零基础", "了解一点", "中等", "较好"])
        hours = st.slider("每周可投入小时", 1, 40, 14)
        duration_days = st.number_input("学习周期（天）", min_value=3, max_value=90, value=14, step=1)
        max_tokens = st.slider("最大生成长度", 256, 2048, 1024, 128, key="path_max_tokens")
        if st.button("生成学习路径", key="path"):
            extra = f"""
当前基础：{level}
学习周期：{duration_days}天
每周可投入时间：{hours}小时

请生成一个具体、可执行、避免空泛重复的学习路径。
每一天都要包含：学习主题、学习内容、实践任务、当天产出。
如果是两周计划，必须分成第1周和第2周。
必须设计一个最终实践项目，例如鸢尾花分类、泰坦尼克生存预测、手写数字分类。

请严格按以下格式输出：
# 学习路径标题
## 一、总体目标
## 二、学习前提
## 三、第1周：基础概念与核心算法
## 四、第2周：实践项目与综合应用
## 五、最终小项目
## 六、检测方式
## 七、复习建议
"""
            prompt, docs = ask_agent("学习路径规划", goal, extra)
            st.caption(f"当前模型：{model_mode}")
            with st.spinner("正在生成学习路径..."):
                ans = _render_agent_answer(prompt, docs, model_mode, temperature=0.25, max_new_tokens=max_tokens)
            if "LoRA" in str(model_mode):
                st.markdown(ans)
            log_jsonl(QA_LOG, {"agent": "learning_path", "model_mode": model_mode, "question": goal, "level": level, "duration_days": duration_days, "hours_per_week": hours, "answer": ans})

    with tab3:
        topic = st.text_input("出题知识点", "课程核心概念")
        qtype = st.multiselect("题型", ["单选", "多选", "判断", "简答", "案例分析"], default=["单选", "简答"])
        diff = st.select_slider("难度", ["简单", "中等", "困难"], value="中等")
        n = st.slider("题目数量", 1, 20, 5)
        max_tokens = st.slider("最大生成长度", 128, 2048, 1024, 64, key="quiz_max_tokens")
        if st.button("生成题目和解析", key="quiz"):
            prompt, docs = ask_agent("AI出题", topic, f"题型：{','.join(qtype)}；难度：{diff}；数量：{n}。每题包含答案、解析、考点和易错点。")
            st.caption(f"当前模型：{model_mode}")
            with st.spinner("正在生成题目..."):
                ans = _render_agent_answer(prompt, docs, model_mode, temperature=0.5, max_new_tokens=max_tokens)
            if "LoRA" in str(model_mode):
                st.markdown(ans)
            log_jsonl(QA_LOG, {"agent": "quiz", "model_mode": model_mode, "question": topic, "answer": ans})

    with tab4:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        msg = st.chat_input("和AI陪练聊聊你的学习困惑", key="practice_chat_input")
        if msg:
            st.session_state.chat_history.append({"role": "user", "content": msg})
            with st.chat_message("user"):
                st.markdown(msg)
            prompt, docs = ask_agent("AI聊天室", msg, "请采用陪练式对话，先回应，再提出一个有帮助的追问。")
            with st.chat_message("assistant"):
                with st.spinner("AI陪练正在回复..."):
                    ans = _render_agent_answer(prompt, docs, model_mode, temperature=0.6, max_new_tokens=768)
                if "LoRA" in str(model_mode):
                    st.markdown(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            log_jsonl(QA_LOG, {"agent": "chat", "model_mode": model_mode, "question": msg, "answer": ans})

    st.divider()
    with st.expander("提交反馈，进入循环训练池"):
        feedback = st.text_area("反馈/新知识/纠错样本")
        rating = st.slider("质量评分", 1, 5, 4)
        if st.button("保存反馈") and feedback.strip():
            log_jsonl(FEEDBACK_LOG, {"feedback": feedback, "rating": rating})
            st.success("已保存到本地反馈池，可用于后续LoRA增量训练。")

def page_training():
    st.header("📉 LoRA训练过程可视化")
    running_pid = read_train_pid()
    st.info(f"当前训练状态：{'运行中，PID=' + str(running_pid) if running_pid else '未运行'}")

    uploaded = st.file_uploader("上传训练日志 metrics_log.jsonl", type=["jsonl"])
    path = None
    if uploaded:
        path = DATA_DIR / "uploaded_metrics.jsonl"
        path.write_bytes(uploaded.read())
    elif TRAIN_LOG.exists():
        path = TRAIN_LOG
    else:
        # 如果训练输出在独立output_dir中，尝试读取最近一次配置里的metrics_log.jsonl
        if TRAIN_CONFIG_FILE.exists():
            cfg = json.loads(TRAIN_CONFIG_FILE.read_text(encoding="utf-8"))
            candidate = Path(cfg.get("output_dir", "")) / "metrics_log.jsonl"
            if candidate.exists():
                path = candidate

    if path:
        rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
        if rows:
            df = pd.DataFrame(rows).sort_values("step")
            st.dataframe(df.tail(50), use_container_width=True)
            numeric_cols = [c for c in ["loss", "task_loss", "eval_loss", "learning_rate", "grad_norm"] if c in df.columns]
            for col in numeric_cols:
                st.line_chart(df.set_index("step")[[col]])
        else:
            st.warning("日志为空")
    else:
        st.info("暂未发现训练日志。启动一键LoRA训练后会自动生成。")

    with st.expander("训练后台日志"):
        st.code(tail_file(TRAIN_RUN_LOG, 160) or "暂无日志", language="text")

    with st.expander("Gemma/Gemma4训练脚本运行示例"):
        st.code(f'''python training/lora_train_gemma.py ^
  --model_path "{DEFAULT_GEMMA_MODEL_PATH}" ^
  --dataset "{DEFAULT_GEMMA_DATASET}" ^
  --output_dir "{DEFAULT_GEMMA_OUTPUT}" ^
  --epochs 1 ^
  --batch 1 ^
  --grad_accum 8 ^
  --max_length 512 ^
  --r 8 ^
  --alpha 16''', language="bash")


def page_teacher():
    st.header("📈 教师分析")
    if QA_LOG.exists():
        df = pd.DataFrame([json.loads(x) for x in QA_LOG.open(encoding="utf-8") if x.strip()])
        st.metric("总交互数", len(df))
        if "agent" in df:
            st.bar_chart(df["agent"].value_counts())
        st.dataframe(df.tail(30), use_container_width=True)
    else:
        st.info("暂无学习数据。")


hero()
page = sidebar()
if page == "一键运维":
    page_ops()
elif page == "知识库/RAG":
    page_rag()
elif page == "学生智能体":
    page_student_agents()
elif page == "训练可视化":
    page_training()
else:
    page_teacher()
