# Gemma4 学习智能体 Windows 原生一键本地部署

文档日期：2026-09-03

本方案不使用 WSL、虚拟机或 Ubuntu，所有服务直接运行在 Windows 中：

```text
Windows 双击入口
  -> PowerShell 检查或安装 Python、JDK、Ollama
  -> Windows Ollama 提供本地模型服务
  -> Windows Python 启动 FastAPI 和前端静态服务
  -> Windows 浏览器访问 http://127.0.0.1:8080
```

LM Studio/Bionic 模式的链路为：

```text
Windows 双击入口
  -> PowerShell 检查或安装 Python、JDK
  -> 从 LM Studio/Bionic 官方地址下载并安装客户端
  -> lms 初始化 daemon、启动本地 OpenAI-compatible 服务并加载模型
  -> Windows Python 启动 FastAPI 和前端静态服务
  -> Windows 浏览器访问 http://127.0.0.1:8080
```

## 一、部署入口

项目根目录提供三个双击入口：

```text
start_windows.bat    启动 Windows 原生部署
start_lmstudio_windows.bat
                      启动 LM Studio/Bionic 模式
stop_windows.bat     停止本项目启动器创建的服务
```

实际脚本位于：

```text
app\deploy\start_windows.bat
app\deploy\start_lmstudio_windows.bat
app\deploy\stop_windows.bat
app\deploy\start_windows.ps1
```

不需要安装 WSL 或 Ubuntu。

## 二、前置条件

需要准备：

- Windows 10 或 Windows 11；
- 首次安装依赖和下载模型时可以联网；
- 建议安装 Windows App Installer，以便自动安装 Python 3.12 和 JDK 17；
- 模型、Python 依赖和运行数据需要额外磁盘空间；
- 如果使用 Java 在线 IDE，需要安装或允许脚本安装 JDK 17。

如果电脑没有 Python 或 JDK，启动器会尝试通过 `winget` 自动安装。
如果电脑没有 Ollama，Ollama 模式会从官方地址下载 Windows 安装包，并显示下载进度条：

```text
Python 3.12
Microsoft OpenJDK 17
```

Ollama 官方下载地址为：

```text
https://ollama.com/download/OllamaSetup.exe
```

如果下载进度长时间不变化，通常是当前网络无法访问下载地址。此时可以按
`Ctrl+C` 停止启动器，先手动安装 Ollama，再重新运行启动脚本；启动器检测到
Ollama 已安装后会跳过安装步骤。

LM Studio/Bionic 模式会从以下地址下载客户端，并显示下载进度条：

```text
https://bionic-installers.lmstudio.ai/win32/x64/1.1.1-5/Bionic-1.1.1-5-x64.exe
```

下载、安装、Python 依赖安装、`lms` 模型加载和服务启动等长时间操作都会显示
进度条，并每隔约 10 秒输出一次已用时间。网络下载连接超过 30 秒没有响应，
或单个安装/命令超过设定时限时，脚本会主动失败并显示错误，而不是无限等待。

如果电脑没有 `winget`，请先手动安装 Python 3.12 和 JDK 17，或者安装
Windows App Installer。Ollama 仍可从官方地址手动下载安装。

## 三、一键启动

在项目根目录双击：

```text
start_windows.bat
```

也可以在 PowerShell 中执行：

```powershell
.\start_windows.bat
```

脚本会自动完成：

1. 检查 Windows Python；
2. 检查 JDK，并确认 `java.exe` 和 `javac.exe`；
3. 创建 `app\.venv-windows\`；
4. 安装 `app\backend\requirements.txt` 中的 Python 依赖；
5. 根据模式检查并启动 Ollama 或 LM Studio；
6. Ollama 模式自动拉取指定模型，默认是 `gemma4:e4b`；
7. LM Studio 模式自动选择并加载客户端中已下载或导入的 Gemma 模型；
8. 创建临时前端副本；
9. 将前端 API 地址指向 `http://127.0.0.1:8000/api`；
10. 启动 FastAPI；
11. 启动前端静态服务；
12. 自动打开浏览器。

启动成功后访问：

```text
http://127.0.0.1:8080
```

默认账号：

```text
账号：admin
密码：admin123
```

如果 `app\backend\data\learning_agent.db` 已经存在，管理员密码以数据库中的已有记录为准。

## 四、常用启动方式

### 4.1 Mock 模式

Mock 模式不调用真实模型，适合先检查前端、后端、登录、RAG 和 Java 在线 IDE：

```powershell
.\start_windows.bat -Mode mock
```

### 4.2 指定其他 Ollama 模型

```powershell
.\start_windows.bat -OllamaModel "模型tag"
```

模型 tag 必须是 Ollama 中存在的准确名称。可以在 Ollama 模型库确认名称，
或执行：

```powershell
ollama list
```

### 4.3 LM Studio/Bionic 模式

根目录可以直接双击：

```text
start_lmstudio_windows.bat
```

也可以在 PowerShell 中执行：

```powershell
.\start_windows.bat -Mode lmstudio
```

LM Studio 模式使用本地 OpenAI-compatible API，默认地址为：

```text
http://127.0.0.1:1234/v1
```

脚本会先启动 LM Studio 本地服务，再从已下载或导入的模型中查找 Gemma 模型并尝试
加载。首次使用前，请在 LM Studio 中下载或导入 Gemma 模型。如果检测到多个 Gemma
模型，请指定准确模型 ID：

```powershell
.\start_windows.bat -Mode lmstudio -LMStudioModel "模型ID"
```

也可以修改 LM Studio 服务端口：

```powershell
.\start_windows.bat -Mode lmstudio -LMStudioPort 1234
```

LM Studio 安装包下载地址：

```text
https://bionic-installers.lmstudio.ai/win32/x64/1.1.1-5/Bionic-1.1.1-5-x64.exe
```

### 4.4 修改端口

```powershell
.\start_windows.bat -ApiPort 8100 -FrontendPort 8180
```

访问：

```text
http://127.0.0.1:8180
```

### 4.5 不自动打开浏览器

```powershell
.\start_windows.bat -NoBrowser
```

### 4.6 跳过 Python 依赖安装

已经完成过依赖安装后，可以加快启动：

```powershell
.\start_windows.bat -SkipInstall
```

此参数不会跳过 Python、JDK、Ollama 的存在性检查。如果依赖缺失，请去掉
`-SkipInstall` 后重试。

### 4.7 安装 LibreOffice

普通 PDF、PPTX、TXT、MD、CSV 不需要 LibreOffice。只有旧版 `.ppt` 解析需要：

```powershell
.\start_windows.bat -InstallOffice
```

该选项会尝试通过 `winget` 安装 LibreOffice，并自动查找 `soffice.exe`。

## 五、停止服务

启动窗口中按：

```text
Ctrl+C
```

或者在项目根目录双击：

```text
stop_windows.bat
```

停止脚本只会停止本项目启动器记录的 FastAPI、前端，以及由启动器创建的
Ollama 或 LM Studio 本地服务。LM Studio/Bionic 客户端窗口不会被关闭。
如果启动时检测到已有 Ollama 或 LM Studio 服务，停止脚本不会关闭它们。

## 六、日志

日志目录：

```text
app\backend\logs\local_deploy\
```

主要日志：

```text
api.log
api.error.log
frontend.log
frontend.error.log
ollama.log
ollama.error.log
```

在 PowerShell 中查看：

```powershell
Get-Content .\app\backend\logs\local_deploy\api.log -Tail 80
Get-Content .\app\backend\logs\local_deploy\api.error.log -Tail 80
Get-Content .\app\backend\logs\local_deploy\frontend.log -Tail 80
Get-Content .\app\backend\logs\local_deploy\ollama.log -Tail 80
```

## 七、数据和配置

一键部署不会修改 `app\backend\.env`。启动器通过当前进程环境变量配置：

```ini
MODEL_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e4b
API_HOST=127.0.0.1
API_PORT=8000
```

LM Studio 模式使用 OpenAI-compatible 配置：

```ini
MODEL_PROVIDER=openai_compatible
VLLM_BASE_URL=http://127.0.0.1:1234/v1
VLLM_API_KEY=EMPTY
VLLM_MODEL=LM Studio 中显示的模型 ID
```

运行数据会保存在项目目录：

```text
app\backend\data\learning_agent.db
app\backend\data\hybrid_rag.joblib
app\backend\data\subjects\java\hybrid_rag.joblib
app\backend\data\qa_history.jsonl
```

首次启动时没有这些文件是正常的，系统会自动创建。

Ollama 模型文件由 Windows Ollama 管理，不保存在项目目录中。
LM Studio 模型文件由 LM Studio 管理，不保存在项目目录中。

## 八、RAG 知识库

AI 学科资料目录：

```text
app\backend\data\knowledge\
```

Java 学科资料目录：

```text
app\backend\data\subjects\java\knowledge\
```

管理员登录后可以通过网页上传资料。上传后系统会自动解析、切块并重建对应
学科的 RAG 索引。

## 九、Java 在线 IDE

启动器会检查：

```text
java.exe
javac.exe
```

如果不存在并且可以使用 `winget`，脚本会尝试安装 Microsoft OpenJDK 17。

Java 代码会在 Windows 本机执行。当前执行器适合本地或内网教学环境，不建议
直接开放到公网。

## 十、旧版 PPT

PPTX 可以直接由 Python 依赖解析。旧版 `.ppt` 需要 LibreOffice。

如果 LibreOffice 没有加入 PATH，可以在 `app\backend\.env` 中写入完整路径：

```ini
OFFICE_CONVERTER=C:\Program Files\LibreOffice\program\soffice.exe
```

启动器使用 `-InstallOffice` 时，会把找到的 `soffice.exe` 路径传给后端。

## 十一、常见问题

### 11.1 提示找不到 winget

脚本无法自动安装缺少的软件。请先手动安装：

```text
Python 3.12
JDK 17
```

安装完成后重新打开 PowerShell，再运行：

```powershell
.\start_windows.bat
```

### 11.2 Python 已安装但仍提示找不到

安装 Python 后，当前 PowerShell 可能还没有刷新 PATH。关闭当前窗口，
重新打开 PowerShell，再次运行启动脚本。

也可以检查：

```powershell
py -3 --version
python --version
```

### 11.3 Ollama 没有启动

检查 Ollama API：

```powershell
Invoke-WebRequest http://127.0.0.1:11434/api/tags
```

查看 Ollama 模型：

```powershell
ollama list
```

如果 11434 端口被其他程序占用，启动器会停止并提示错误。

### 11.4 Ollama 模型下载失败

Ollama 模式首次运行需要下载模型。请确认网络正常，并检查模型 tag 是否准确：

```powershell
ollama pull gemma4:e4b
```

下载完成后重新运行：

```powershell
.\start_windows.bat
```

### 11.5 LM Studio 没有启动

检查 LM Studio API：

```powershell
Invoke-WebRequest http://127.0.0.1:1234/v1/models
```

如果提示找不到 `lms`，请先手动启动一次 LM Studio/Bionic，再重新运行：

```powershell
.\start_lmstudio_windows.bat
```

如果服务正常但没有模型，请在 LM Studio 中下载或导入 Gemma 模型。脚本会使用
`lms load` 自动加载匹配到的模型；如果自动识别失败，可在 LM Studio 中查看模型
ID 后通过 `-LMStudioModel` 指定。

如果知识库状态接口中的中文文件名显示为 `鍏ラ棬`、`瀛︿範` 等乱码，请先停止并
重新启动后端。启动时会自动恢复这类被错误编码的文件名，并重建对应的 RAG 索引；
JSON 接口也会返回 `application/json; charset=utf-8`。

### 11.6 端口被占用

默认端口：

```text
FastAPI：8000
前端：8080
Ollama：11434
LM Studio：1234
```

可以更换 FastAPI、前端和 LM Studio 端口：

```powershell
.\start_windows.bat -Mode lmstudio -ApiPort 8100 -FrontendPort 8180 -LMStudioPort 8200
```

Ollama 端口默认固定为 11434，LM Studio 端口默认是 1234。

### 11.7 浏览器打不开页面

先检查 FastAPI：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/healthz
```

再检查前端：

```powershell
Invoke-WebRequest http://127.0.0.1:8080
```

如果请求失败，请查看：

```text
app\backend\logs\local_deploy\api.error.log
app\backend\logs\local_deploy\frontend.error.log
```

### 11.8 `.ppt` 上传失败

安装 LibreOffice：

```powershell
.\start_windows.bat -InstallOffice
```

或在 `.env` 中配置 `OFFICE_CONVERTER` 的完整 Windows 路径。

## 十二、安全说明

- 默认管理员密码 `admin123` 只适合本地首次验证；
- 正式使用前请在 `app\backend\.env` 中设置强密码和随机 `AUTH_SECRET_KEY`；
- 不要将 8000、8080 或 11434 端口直接暴露到公网；
- Java 在线执行器不应在公网裸露运行；
- `.env`、SQLite 数据库、RAG 索引、日志和模型文件不要提交到 Git。
