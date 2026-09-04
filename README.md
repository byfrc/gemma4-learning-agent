# Gemma4 私有学习智能体

本项目是一个基于 **Gemma4、Ollama/LM Studio/vLLM、FastAPI、RAG 和 LoRA 数据闭环** 的私有学习智能体原型系统。

系统面向人工智能与 Java 入门学习场景，支持本地大模型推理、分学科私有知识库问答、学科切换、网页交互、对话历史保存、回答质量反馈，以及高质量样本导出用于后续 LoRA 微调。

---

## 一、项目目标

本项目希望构建一个面向学习场景的闭环式 AI 助教系统。

整体流程如下：

1. 上传或维护私有知识库资料；
2. 使用 RAG 检索增强生成，提高回答依据性；
3. 通过本地 Gemma4 模型完成问答生成；
4. 在网页端为用户提供学习助手交互；
5. 保存历史会话，并收集回答质量反馈；
6. 将高质量问答样本导出为 LoRA 微调数据集。

本系统不仅用于回答问题，还可以持续收集高质量学习数据，为后续模型微调和行为风格优化提供数据基础。

---

## 二、核心功能

| 功能模块 | 说明 |
|---|---|
| 本地大模型推理 | 支持 Ollama、LM Studio 或 vLLM 部署 Gemma4，实现本地模型调用 |
| 后端服务 | 使用 FastAPI 提供聊天、知识库、会话和反馈接口 |
| Web 前端 | 提供轻量级网页交互界面 |
| 账号系统 | 支持注册、账号密码登录和退出登录；初始账号为管理员，新注册账号为学生 |
| 学科选择 | 登录时选择 AI / Java 学科，进入平台后固定当前学科 |
| 知识库权限 | 仅管理员可以上传课程资料和重建知识库，学生只能查看和使用知识库 |
| RAG 知识库问答 | 支持 TXT、MD、CSV、PDF、PPT、PPTX 知识库检索增强回答 |
| 分学科知识库 | AI 与 Java 的资料、索引和日志分开管理 |
| Java 在线IDE | Java 学科提供浏览器代码编辑、标准输入、编译运行和错误输出 |
| 对话历史 | 使用 SQLite 保存用户与助手的历史会话 |
| 会话管理 | 支持会话重命名、删除和导出 |
| 回答评分 | 支持对助手回答进行质量评价 |
| LoRA 样本标记 | 可将高质量回答标记为训练样本 |
| 数据集导出 | 支持导出 JSONL 格式 LoRA 微调数据 |
| 部署脚本 | 提供 Windows 原生 Ollama、LM Studio 一键启动脚本 |

---

## 三、项目结构

- `app/backend/`：FastAPI 后端代码
- `app/backend/app/main.py`：后端主入口
- `app/backend/app/rag.py`：RAG 检索逻辑
- `app/backend/app/providers.py`：大模型调用接口
- `app/backend/app/conversation_store.py`：SQLite 会话与反馈存储
- `app/backend/app/schemas.py`：接口数据结构定义
- `app/backend/data/knowledge/`：示例知识库文件
- `app/backend/build_lora_dataset_v1.py`：LoRA 数据集导出脚本
- `app/frontend/`：前端页面代码
- `app/deploy/`：Windows 原生部署脚本
- `WINDOWS_LOCAL_DEPLOYMENT_GUIDE_CN.md`：Windows 中文部署说明
- `.gitignore`：Git 忽略规则

---

## 四、RAG 私有知识库问答

系统支持本地 Markdown 知识库。后端会对知识库文档进行加载、切块、索引和检索，并将相关内容作为上下文传入大模型，从而提高回答的依据性。

示例知识库目录：

`app/backend/data/knowledge/`

当前示例知识库主要面向人工智能小白学习，包括：

- 人工智能基础概念
- Python 入门路线
- 数据处理基础
- 机器学习入门
- 模型评估指标
- 深度学习基础
- 大模型基础
- RAG 检索增强生成
- LoRA 微调入门
- 学习智能体设计
- 四周 AI 入门计划
- AI 伦理与学习边界

---

## 五、Gemma4 本地推理

系统后端支持多种本地模型服务：

- Windows 原生一键部署使用 Ollama；
- Windows 也可以使用 LM Studio/Bionic 提供本地 OpenAI-compatible 模型服务；
- 后端保留 OpenAI-compatible 接口，可用于其他 vLLM 部署环境。

Ollama 示例：

`ollama pull gemma4:e4b`

示例启动命令：

`vllm serve /path/to/gemma-4-12B-it --host 0.0.0.0 --port 8001 --dtype bfloat16 --max-model-len 8192`

FastAPI 后端会调用该本地模型服务完成回答生成。

---

## 六、Web 前端学习助手

前端提供浏览器交互界面，支持：

- 与学习智能体对话；
- 基于知识库进行问答；
- 查看历史会话；
- 重命名和删除会话；
- 导出会话；
- 对回答进行质量评分；
- 标记回答是否可作为 LoRA 训练样本。

前端文件位于：

`app/frontend/`

---

## 七、对话记忆与反馈系统

系统使用 SQLite 保存对话历史和反馈信息，包括：

- 会话信息；
- 用户消息；
- 助手回答；
- RAG 检索证据；
- 使用的模型信息；
- 回答质量评分；
- 是否加入 LoRA 训练样本。

运行时数据库不会上传到 GitHub，避免泄露真实对话内容。

---

## 八、LoRA 数据闭环

用户可以对高质量回答进行评分，并勾选为训练样本。随后可以通过脚本将这些样本导出为 LoRA 微调数据集。

导出脚本：

`app/backend/build_lora_dataset_v1.py`

典型数据格式为 messages JSONL，每条样本包含一轮用户问题和助手回答，同时保留评分、智能体模式和会话 ID 等元信息。

推荐数据规模：

| 阶段 | 建议数据量 |
|---|---|
| 小规模功能验证 | 50～100 条高质量样本 |
| 初步 LoRA 训练 | 300～1000 条高质量样本 |
| 稳定行为风格微调 | 1000 条以上高质量样本 |

---

## 九、快速开始

### Windows 原生一键本地部署

Windows 10/11 不需要 WSL 或 Ubuntu。项目根目录双击：

```text
start_windows.bat
```

默认会检查或通过 `winget` 安装 Python 和 JDK，从 Ollama 官方地址下载并安装
Ollama，创建 Windows Python 虚拟环境，拉取 `gemma4:e4b`，启动 FastAPI 和前端，并打开：

```text
http://127.0.0.1:8080
```

停止服务：

```text
stop_windows.bat
```

详细说明见：

`WINDOWS_LOCAL_DEPLOYMENT_GUIDE_CN.md`

### LM Studio/Bionic 本地部署

如果 Ollama 下载速度较慢，可以使用根目录的：

```text
start_lmstudio_windows.bat
```

也可以直接执行：

```powershell
.\start_windows.bat -Mode lmstudio
```

该入口会从 LM Studio/Bionic 官方安装地址下载并安装客户端，启动本地
OpenAI-compatible 服务，并自动加载 LM Studio 中已下载或导入的 Gemma 模型。
下载、安装和模型加载期间会显示进度状态；如果网络或命令长时间无响应，脚本会
在超时后输出明确错误并结束。
如果存在多个 Gemma 模型，可以指定准确的模型 ID：

```powershell
.\start_windows.bat -Mode lmstudio -LMStudioModel "模型ID"
```

### 手动开发运行

如果不使用一键脚本，可以参考：

- `app/backend/requirements.txt`：后端 Python 依赖；
- `app/backend/.env.example`：环境变量示例；
- `app/backend/app/main.py`：FastAPI 后端入口；
- `app/frontend/`：前端静态文件。

用户打开前端后，需要先使用账号密码登录，并在登录页选择 AI 或 Java 学科。
登录后的请求会固定绑定到所选学科，工作台不再提供顶部学科切换。
新注册账号及其会话数据保存在后端 SQLite 数据库中，账号之间的历史会话相互隔离。
管理员账号可以上传课程资料并重建知识库；新注册账号默认为学生，只能查看和使用已有知识库。
上传 PDF 时会优先提取 PDF 原生文字；扫描型 PDF 可通过安装 PaddleOCR 开启 OCR
兜底。PPTX 会提取幻灯片文字、表格和讲者备注，并在 RAG 证据中保留页码或幻灯片号。
登录 Java 学科后，点击“在线IDE”即可编辑 `Main.java` 并运行；代码默认限制为
教学场景下的单文件 `Main` 类，服务端会限制代码大小、编译/运行时间和输出大小，
并拦截常见文件、网络和进程控制 API。在线执行器适合内网教学环境，正式公网部署
建议进一步放入独立低权限容器或沙箱。

完整 Windows 部署参数和故障排查见：

`WINDOWS_LOCAL_DEPLOYMENT_GUIDE_CN.md`

---

## 十、仓库不包含的内容

出于安全和存储考虑，本仓库不包含：

- Gemma4 模型权重；
- Hugging Face 缓存；
- Windows Python 虚拟环境；
- Ollama 模型文件；
- SQLite 运行数据库；
- 私有 `.env` 配置文件；
- API Key 或访问 Token；
- 大型训练检查点。

这些文件均已通过 `.gitignore` 排除。

---

## 十一、适用场景

本项目适合用于：

- 人工智能教学展示；
- 私有学习智能体原型开发；
- RAG 课程资料问答；
- LoRA 微调数据采集；
- 本地大模型应用开发实验；
- 教学平台或智能助教项目验证。

当前项目仍属于教育原型系统，不是生产级多用户平台。

---

## 十二、项目链接

GitHub 仓库：

https://github.com/qianmo123321/gemma4-learning-agent

---

## 十三、说明

本项目仅用于学习、研究和教学展示。正式部署到公网前，建议进一步补充用户权限管理、数据隔离、访问控制、日志审计和安全策略。
