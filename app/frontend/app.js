const API = window.__API_BASE__ || "/api";

const state = {

  chats: [],

  active: null,

  subject: "ai",

  mode:"qa",

  switchingMode: false,

  sending: false,
  uploading: false,
  savingSources: false,
  uploadGeneration: 0,
  uploadController: null,
  fileUploads: [],
  drafts: new Map(),
  draftSequence: 0,
  sendGeneration: 0,
  sendController: null,

  language:"en",

  auth: null,

  messageCache: new Map()

};

const JAVA_DEFAULT_CODE = `import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        System.out.println("Hello, Gemma4!");
        if (scanner.hasNextLine()) {
            System.out.println("你输入的是：" + scanner.nextLine());
        }
    }
}`;

/*语言切换*/
const LANGUAGE_TEXT = {

  zh: {

    workspace_title:
      "私域学习智能体工作台",

    brand_desc:"本地大模型 · 私有知识库",

    hero_title:
      "让模型 <em>懂你的资料</em>，陪你持续学习",

    hero_desc:
      "基于个人课程资料进行检索、问答、规划与陪练；",

    demo_title:"推荐体验",

    chip_rag:
      "知识库检索",

    chip_chat:
      "多轮追问",

    chip_plan:
      "学习规划",

    chip_feedback:
      "学习反馈",


    tab_qa:
      "AI 问答",

    tab_qa_desc:
      "知识解释与追问",

    tab_project: "项目助手",
    tab_project_desc: "理解代码与排查错误",
    project_mode_tip: "上传项目文档，或粘贴代码和报错，获取有依据的建议。",
    project_welcome_title: "一起梳理你的项目",
    project_welcome_desc: "点击“文件”、拖入附件或粘贴截图，然后点击发送。可以只发送图片或文件，我会自动分析；也可以添加问题，我会结合文字和附件一起回答。",
    file_context: "当前对话的文件",
    choose_sources: "选择已上传的文件",
    no_file_context: "请上传或选择文件，我会解释它的内容。",
    source_selection_hint: "勾选当前对话要使用的文件（最多 12 个）。",
    remove_source: "从当前对话中移除",
    source_save_failed: "无法更新当前对话的文件。",
    attach_files: "文件",
    attach_files_title: "添加文件或图片到待发送消息",
    drop_files: "拖放文件到这里",
    drop_files_desc: "添加附件后点击发送；问题可选",
    upload_hint: "可以只发送图片或文件，自动分析 · 问题可选 · 每个文件最大 30 MB",
    upload_queued: "等待上传",
    upload_working: "上传并处理…",
    upload_ready: "已添加到",
    upload_failed: "上传失败",
    upload_unsupported: "不支持此格式。请选择文档、代码或 PNG、JPEG、WebP 图片。",
    upload_too_large: "文件超过 30 MB。",
    upload_canceled: "上传已取消。",
    upload_admin: "请使用管理员账号上传文件。",
    project_architecture: "解释文件",
    project_architecture_question: "请解释当前对话所选文件的实际内容。如果是代码，请说明它的用途、执行过程、输入和输出。如果是文档，请概括主题和主要观点。",
    project_debug: "排查错误",
    project_debug_question: "帮我排查下面的错误，给出可能原因、最小修改和验证方法：\n\n",
    project_code: "逐步解释代码",
    project_code_question: "请逐步解释下面的代码，并给出一个简单示例：\n\n",
    file_in_context: "回答将使用此文件",
    file_not_in_context: "未选入当前上下文",
    use_file: "使用文件",
    draft_attachments: "待发送附件 · 可直接发送并分析，也可以添加问题",
    draft_limit: "每条消息最多 12 个附件，其中图片最多 4 张。",
    image_label: "图片",


    tab_plan:
      "学习路径",

    tab_plan_desc:
      "目标拆解与计划",


    tab_quiz:
      "AI 出题",

    tab_quiz_desc:
      "检测掌握程度",


    tab_coach:
      "AI 陪练",

    tab_coach_desc:
      "苏格拉底式引导",


    assistant:
      "Gemma4 学习助教",

    assistant_sub:
      "已连接私域知识库",

    knowledge:
      "知识库管理",

    placeholder:
       "输入问题；你可以继续追问上一轮内容…",

    brand_name:
       "Gemma4学习智能体",
      
    brand_sub:
       "RAG · LoRA · Agent",
      
    new_chat:
        "新建对话",

    recent_chat:
        "最近对话",

    mode_qa:
        "多轮 AI 问答",
    
    mode_tip:
        "基于你的资料回答问题，并支持连续追问。",
    
    knowledge_title:
        "知识库管理",
    
    knowledge_desc:
        "选择已有资料，或添加文件和图片后点击发送。问题可选；留空时会自动分析附件。",

    select_material:
        "选择文档、代码或图片",

    upload_desc:
        "支持文档、代码和 PNG/JPEG/WebP 图片，每个文件最大 30 MB。可以只发送附件，也可以添加问题。",

    upload_button:
        "添加到消息",

    source_title:
        "已入库资料",

    source_desc:
        "勾选此对话需要使用的已有文档",

    knowledge_readonly:
        "学生账号仅可查看资料，知识库上传由管理员完成。",

    source_readonly:
        "资料由管理员维护",

    send:
        "发送",

    enter_send:
        "Enter 发送",

    shift_enter:
        "Shift + Enter 换行",

    privacy:
        "你的资料不会被用于公共训练",
      
    feature_rag:
        "知识库检索",
      
    feature_followup:
        "多轮追问",

    feature_plan:
        "学习规划",

    feature_feedback:
        "学习反馈",
      
    kb_files:"知识库文件",

    kb_chunks:"可检索片段",

    learning_agent:"学习智能体",

    current_session:"当前会话",

    rag_sources:"📚 知识来源",

    tab_ide:"在线IDE",
    tab_ide_desc:"编写并运行 Java",
    ide_title:"Java 在线IDE",
    ide_desc:"编辑 Main.java，运行后在右侧查看标准输出和错误信息。",
    ide_reset:"重置",
    ide_run:"运行代码",
    ide_stdin:"标准输入",
    ide_stdin_desc:"需要输入时，每行填写一个值。",
    ide_output:"运行输出",
    ide_ready:"准备就绪",
    ide_running:"运行中…",
    ide_success:"运行成功",
    ide_compile_failed:"编译失败",
    ide_error:"运行失败",
    ide_timeout:"运行超时",
    ide_shortcut:"快捷键：⌘/Ctrl + Enter 运行",

  },


  en: {


    workspace_title:
      "Private Learning Agent Workspace",


    hero_title:
      "Make AI <em>understand your knowledge</em> and learn with you",

    demo_title:"Recommended Experience",


    hero_desc:
      "Retrieve, answer, plan and practice with your private knowledge base.",


    chip_rag:
      "Knowledge Retrieval",

    chip_chat:
      "Multi-turn Chat",

    chip_plan:
      "Learning Path",

    chip_feedback:
      "Learning Feedback",


    tab_qa:
      "AI Q&A",

    tab_qa_desc:
      "Knowledge Explanation & Follow-up",

    tab_project: "Project Assistant",
    tab_project_desc: "Understand code and debug errors",
    project_mode_tip: "Upload project docs, or paste code and errors for grounded guidance.",
    project_welcome_title: "Let's work through your project",
    project_welcome_desc: "Click Files, drop an attachment, or paste a screenshot, then press Send. Send just an image or file for an automatic analysis, or add a question and I will use your text and attachments together.",
    file_context: "Files in this conversation",
    choose_sources: "Choose uploaded files",
    no_file_context: "Upload or choose a file, and I will explain its contents.",
    source_selection_hint: "Select the files to use in this conversation (up to 12).",
    remove_source: "Remove from this conversation",
    source_save_failed: "Could not update this conversation's files.",
    attach_files: "Files",
    attach_files_title: "Attach files or images to your draft message",
    drop_files: "Drop files here",
    drop_files_desc: "Attach files, then Send; a question is optional",
    upload_hint: "Send an image or file for automatic analysis · Question optional · 30 MB per file",
    upload_queued: "Queued",
    upload_working: "Uploading and processing…",
    upload_ready: "Added to",
    upload_failed: "Upload failed",
    upload_unsupported: "Unsupported format. Choose documents, code, or PNG, JPEG, WebP images.",
    upload_too_large: "File exceeds the 30 MB limit.",
    upload_canceled: "Upload canceled.",
    upload_admin: "Sign in as an administrator to upload files.",
    project_architecture: "Explain file",
    project_architecture_question: "Explain the actual contents of the files selected for this conversation. For code, describe its purpose, steps, inputs and outputs. For a document, explain its subject and main points.",
    project_debug: "Debug an error",
    project_debug_question: "Help me diagnose this error. Give the likely cause, a small fix, and a way to verify it:\n\n",
    project_code: "Explain code",
    project_code_question: "Explain this code step by step with a simple example:\n\n",
    file_in_context: "Included in answers",
    file_not_in_context: "Not selected for answers",
    use_file: "Use file",
    draft_attachments: "Ready to send · Send to analyze, or add a question",
    draft_limit: "Use up to 12 attachments, including up to 4 images, per message.",
    image_label: "Image",


    tab_plan:
      "Learning Path",

    tab_plan_desc:
      "Goal Planning & Breakdown",


    tab_quiz:
      "AI Quiz",

    tab_quiz_desc:
      "Knowledge Assessment",


    tab_coach:
      "AI Coach",

    tab_coach_desc:
      "Socratic Guidance",


    assistant:
      "Gemma4 AI Tutor",


    assistant_sub:
      "Connected to Private Knowledge Base",


    knowledge:
      "Knowledge Base",


    placeholder:
      "Ask a question and continue your learning journey...",

    brand_name:
        "Gemma4 Learning Agent",

    brand_sub:
        "RAG · LoRA · Agent",

    new_chat:
        "New Chat",

    recent_chat:
        "Recent Conversations",

    mode_qa:
        "Multi-turn AI Q&A",
      
    mode_tip:
        "Answer questions based on your knowledge base and support continuous conversations.",
    
    knowledge_title:
        "Knowledge Base",

    knowledge_desc:
        "Choose existing documents or attach files and images, then Send. A question is optional; leave it blank for automatic analysis.",

    select_material:
        "Select Documents, Code, or Images",

    upload_desc:
        "Documents, source code, and PNG/JPEG/WebP images. Up to 30 MB each. Send attachments alone or add a question.",

    upload_button:
        "Add to message",

    source_title:
        "Indexed Documents",

    source_desc:
        "Select existing documents to use in this conversation",

    knowledge_readonly:
        "Student accounts can view materials only. Knowledge base uploads are managed by administrators.",

    source_readonly:
        "Materials are maintained by administrators",

    send:
        "Send",

    enter_send:
        "Press Enter to send",

    shift_enter:
        "Shift + Enter for new line",

    privacy:
        "Your data will not be used for public training",

    feature_rag:"Knowledge Retrieval",
      
    feature_followup:"Multi-turn Dialogue",
    
    feature_plan:"Learning Plan",
    
    feature_feedback:"Learning Feedback",

    kb_files:"Knowledge Files",

    kb_chunks:"Retrievable Chunks",

    learning_agent:"Learning Agent",

    current_session:"Current Session",

    brand_desc:"Local AI · Private Knowledge",

    rag_sources:"📚 Knowledge Sources",

    tab_ide:"Online IDE",
    tab_ide_desc:"Write and run Java",
    ide_title:"Java Online IDE",
    ide_desc:"Edit Main.java and inspect standard output or errors after running.",
    ide_reset:"Reset",
    ide_run:"Run Code",
    ide_stdin:"Standard Input",
    ide_stdin_desc:"Enter one value per line when your program needs input.",
    ide_output:"Run Output",
    ide_ready:"Ready",
    ide_running:"Running…",
    ide_success:"Run completed",
    ide_compile_failed:"Compilation failed",
    ide_error:"Run failed",
    ide_timeout:"Timed out",
    ide_shortcut:"Shortcut: ⌘/Ctrl + Enter to run",
  }

};
/*语言切换*/

const SUBJECT_COPY = {
  zh: {
    ai: {
      switch_label: "AI",
      full_name: "人工智能",
      knowledge_label: "AI 知识库",
      assistant_sub: "已连接 AI 知识库",
      hero_kicker: "AI 学科 · 已开启私域知识增强",
      mode_tip: "基于 AI 课程资料回答问题，并支持连续追问。",
      welcome_title: "今天想从哪里开始？",
      welcome_desc:
        "你可以围绕人工智能课程资料连续追问，也可以切换到学习路径、AI 出题与 AI 陪练。",
      placeholders: {
        qa: "输入问题；你可以继续追问上一轮内容…",
        project_assistant: "添加文件或图片后发送。问题可选；留空时会自动分析附件。",
        learning_path: "例如：我想在两周内入门机器学习，每天可学 2 小时。",
        quiz: "例如：围绕 RAG 基础生成 5 道中等难度选择题。",
        coach: "说说你目前学不懂的地方，我会陪你一步步梳理。",
      },
    },
    java: {
      switch_label: "Java",
      full_name: "Java",
      knowledge_label: "Java 知识库",
      assistant_sub: "已连接 Java 知识库",
      hero_kicker: "Java 学科 · 已开启私域知识增强",
      mode_tip: "基于 Java 课程资料回答问题，并支持连续追问。",
      welcome_title: "今天想从哪里开始？",
      welcome_desc:
        "你可以围绕 Java 课程资料连续追问，也可以切换到学习路径、AI 出题、AI 陪练或在线IDE。",
      placeholders: {
        qa: "例如：Java 的继承和封装有什么区别？",
        project_assistant: "添加 Java 源码或截图后发送。问题可选；留空时会自动分析。",
        learning_path: "例如：我想在两周内入门 Java，每天可学 2 小时。",
        quiz: "例如：围绕 Java 面向对象生成 5 道选择题。",
        coach: "例如：我看不懂 Java 的类和对象，帮我一步步理清。",
      },
    },
  },
  en: {
    ai: {
      switch_label: "AI",
      full_name: "Artificial Intelligence",
      knowledge_label: "AI Knowledge Base",
      assistant_sub: "Connected to AI knowledge base",
      hero_kicker: "AI track · Private knowledge enabled",
      mode_tip: "Answer questions based on AI course materials and continue the conversation.",
      welcome_title: "Where would you like to start today?",
      welcome_desc:
        "You can ask follow-up questions about AI course materials, or switch to Learning Path, AI Quiz and AI Coach.",
      placeholders: {
        qa: "Ask a question; you can continue from the previous turn.",
        project_assistant: "Attach a file or image, then Send. Add a question, or leave blank for automatic analysis.",
        learning_path: "For example: I want to learn machine learning in two weeks, 2 hours per day.",
        quiz: "For example: generate 5 medium-difficulty multiple-choice questions about RAG.",
        coach: "Tell me where you are stuck and I will walk through it step by step.",
      },
    },
    java: {
      switch_label: "Java",
      full_name: "Java",
      knowledge_label: "Java Knowledge Base",
      assistant_sub: "Connected to Java knowledge base",
      hero_kicker: "Java track · Private knowledge enabled",
      mode_tip: "Answer questions based on Java course materials and continue the conversation.",
      welcome_title: "Where would you like to start today?",
      welcome_desc:
        "You can ask follow-up questions about Java course materials, or use Learning Path, AI Quiz, AI Coach and the Online IDE.",
      placeholders: {
        qa: "For example: what is the difference between inheritance and encapsulation in Java?",
        project_assistant: "Attach Java code or a screenshot, then Send. A question is optional.",
        learning_path: "For example: I want to learn Java in two weeks, 2 hours per day.",
        quiz: "For example: generate 5 Java OOP multiple-choice questions.",
        coach: "For example: I do not understand Java classes and objects. Help me step by step.",
      },
    },
  },
};

function getSubjectCopy(subject = state.subject, language = state.language) {
  const langPack = SUBJECT_COPY[language] || SUBJECT_COPY.zh;
  return langPack[subject] || langPack.ai;
}

function updateSubjectChrome() {
  const copy = getSubjectCopy();
  const subjectBadge = $("#currentSubjectBadge");
  if (subjectBadge) {
    subjectBadge.textContent = copy.full_name;
    subjectBadge.title = copy.full_name;
  }

  const knowledgeButton = $("#knowledgeBtn");
  if (knowledgeButton) {
    knowledgeButton.innerHTML = `▣ ${copy.knowledge_label}`;
    knowledgeButton.title = copy.knowledge_label;
  }

  const assistantSub = $("#assistantSub");
  if (assistantSub) {
    assistantSub.textContent = copy.assistant_sub;
  }

  const heroKicker = document.querySelector(".hero-kicker");
  if (heroKicker) {
    heroKicker.innerHTML = `<span class="live-dot"></span>${copy.hero_kicker}`;
  }

  const modeTip = $("#modeTip");
  if (modeTip) {
    modeTip.textContent = copy.mode_tip;
  }

  const knowledgeSubjectLabel = $("#knowledgeSubjectLabel");
  if (knowledgeSubjectLabel) {
    knowledgeSubjectLabel.textContent = copy.knowledge_label;
  }

  const userAvatar = $("#userAvatar");
  if (userAvatar && state.auth?.username) {
    userAvatar.textContent = state.auth.username.slice(0, 1).toUpperCase();
    userAvatar.title = `${state.auth.username} · ${
      state.auth.role === "admin" ? "管理员" : "学生"
    }`;
  }

  const agentMetric = $("#agentMetric");
  if (agentMetric) {
    agentMetric.textContent = state.subject === "java" ? "6" : "5";
  }

  updateKnowledgeAccess();
  updateJavaIdeAccess();
}

function updateKnowledgeAccess() {
  const isAdmin = state.auth?.role === "admin";
  const languagePack = LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh;
  const uploadForm = $("#uploadForm");
  const readOnlyNotice = $("#knowledgeReadOnly");
  const sourceDescription = $("#sourceDesc");

  if (uploadForm) {
    uploadForm.classList.toggle("is-hidden", !isAdmin);
  }
  if (readOnlyNotice) {
    readOnlyNotice.textContent = languagePack.knowledge_readonly;
    readOnlyNotice.classList.toggle("is-hidden", isAdmin);
  }
  if (sourceDescription) {
    sourceDescription.textContent = languagePack.source_selection_hint;
  }
  updateComposerControls();
  renderFileUploads();
}

function updateComposerControls() {
  const pack = LANGUAGE_TEXT[state.language];
  const canUpload = state.auth?.role === "admin";
  const attach = $("#attachFileBtn");
  attach.disabled = !canUpload || !getChat() || state.sending || state.uploading || state.savingSources;
  attach.title = canUpload ? pack.attach_files_title : pack.upload_admin;
  attach.setAttribute("aria-label", attach.title);
  const sendButton = $("#sendBtn");
  sendButton.disabled = state.sending || state.uploading || state.switchingMode || state.savingSources;
  sendButton.textContent = state.uploading ? pack.upload_working
    : state.sending ? (state.language === "en" ? "Thinking…" : "生成中…")
    : (state.language === "en" ? "Send ↗" : "发送 ↗");
  const uploadButton = $("#uploadForm").querySelector('button[type="submit"]');
  uploadButton.disabled = !canUpload || !getChat() || state.sending || state.uploading || state.savingSources;
  uploadButton.textContent = state.uploading ? pack.upload_working : pack.upload_button;
  $("#chooseSourcesBtn").disabled = !getChat() || state.sending || state.uploading || state.savingSources;
  $("#userInput").disabled = state.sending;
  $("#sourceList").querySelectorAll("[data-source-file]").forEach(checkbox => {
    checkbox.disabled = !getChat() || state.uploading || state.savingSources;
  });
  messagesBox.querySelectorAll("[data-file-source]").forEach(button => {
    button.disabled = state.sending || state.uploading || state.savingSources;
  });
}

function renderSourceContext() {
  const chat = getChat();
  const files = chat?.source_files || [];
  const isProject = state.mode === "project_assistant";
  $("#ragEvidenceControl").classList.toggle("is-hidden", isProject || files.length > 0);
  $("#ragToggleControl").classList.toggle("is-hidden", isProject || files.length > 0);
  updateComposerControls();
}

async function saveConversationSources(files) {
  const chat = getChat();
  if (!chat || state.savingSources || state.uploading) return;
  const token = state.auth?.token;
  state.savingSources = true;
  renderSourceContext();
  try {
    const response = await apiFetch(`/conversations/${chat.id}/sources`, {
      method: "PUT", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({source_files: files}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : LANGUAGE_TEXT[state.language].source_save_failed);
    const current = state.chats.find(item => item.id === chat.id);
    if (current && state.auth?.token === token) current.source_files = data.source_files;
  } catch (error) {
    alert(error.message);
  } finally {
    state.savingSources = false;
    renderMessages();
    await refreshKnowledge().catch(() => {});
  }
}

function getDraft(chatId = state.active) {
  if (!chatId) return null;
  if (!state.drafts.has(chatId)) state.drafts.set(chatId, {text: "", files: [], error: ""});
  return state.drafts.get(chatId);
}

function releaseDraftFiles(files) {
  for (const file of files) if (file.previewUrl) URL.revokeObjectURL(file.previewUrl);
}

function restoreDraftInput() {
  $("#userInput").value = getDraft()?.text || "";
  resizeComposer();
  renderFileUploads();
}

function renderFileUploads() {
  const draft = getDraft();
  const pack = LANGUAGE_TEXT[state.language];
  const files = draft?.files || [];
  const container = $("#draftAttachments");
  container.classList.toggle("is-hidden", !files.length);
  container.innerHTML = files.length ? `<small>${pack.draft_attachments}</small><div class="draft-files">${files.map(record => `
    <div class="draft-file">
      ${record.previewUrl ? `<img src="${esc(record.previewUrl)}" alt="${esc(record.file.name)}">` : '<span aria-hidden="true">&#128206;</span>'}
      <b title="${esc(record.file.name)}">${esc(record.file.name)}</b>
      <button type="button" data-remove-draft="${record.id}" aria-label="${esc(pack.remove_source + ': ' + record.file.name)}">×</button>
    </div>`).join("")}</div>` : "";
  container.querySelectorAll("[data-remove-draft]").forEach(button => {
    button.onclick = () => {
      const removed = draft.files.filter(file => file.id === button.dataset.removeDraft);
      releaseDraftFiles(removed);
      draft.files = draft.files.filter(file => file.id !== button.dataset.removeDraft);
      renderFileUploads();
    };
  });
  for (const selector of ["#chatUploadStatus", "#knowledgeUploadStatus"]) {
    const target = $(selector);
    target.textContent = draft?.error || "";
    target.classList.toggle("is-hidden", !draft?.error);
  }
}

function stageChatFiles(selectedFiles) {
  const chat = getChat();
  if (!chat || state.sending || state.uploading || state.savingSources) return;
  if (state.auth?.role !== "admin") {
    alert(LANGUAGE_TEXT[state.language].upload_admin);
    return;
  }
  const draft = getDraft(chat.id);
  draft.text = $("#userInput").value;
  draft.error = "";
  const accepted = new Set($("#chatFileInput").accept.split(","));
  for (const file of Array.from(selectedFiles || [])) {
    const suffix = file.name.includes(".") ? `.${file.name.split(".").pop().toLowerCase()}` : "";
    const isImage = [".png", ".jpg", ".jpeg", ".webp"].includes(suffix);
    if (!accepted.has(suffix) || file.size > 30 * 1024 * 1024) {
      draft.error = LANGUAGE_TEXT[state.language][accepted.has(suffix) ? "upload_too_large" : "upload_unsupported"];
      continue;
    }
    if (draft.files.length >= 12 || (isImage && draft.files.filter(record => record.kind === "image").length >= 4)) {
      draft.error = LANGUAGE_TEXT[state.language].draft_limit;
      continue;
    }
    draft.files.push({id: String(++state.draftSequence), file, kind: isImage ? "image" : "file", previewUrl: isImage ? URL.createObjectURL(file) : null});
  }
  renderFileUploads();
  $("#userInput").focus();
}

function updateJavaIdeAccess() {
  const isJava = state.subject === "java";
  const ideTab = $("#onlineIdeTab");

  if (ideTab) {
    ideTab.classList.toggle("is-hidden", !isJava);
  }

  updateJavaIdeText();

  if (!isJava && state.mode === "online_ide") {
    setMode("qa");
  }
}

function updateJavaIdeText() {
  const languagePack = LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh;
  const stdin = $("#javaStdin");
  const output = $("#javaOutput");

  if (stdin) {
    stdin.placeholder =
      state.language === "zh"
        ? "例如：42\nGemma4"
        : "For example: 42\nGemma4";
  }
  if (output) {
    output.dataset.placeholder =
      state.language === "zh"
        ? "点击“运行代码”查看结果。"
        : 'Click "Run Code" to see the result.';
  }
  if (languagePack.ide_ready && $("#javaRunStatus")?.dataset.state !== "running") {
    const status = $("#javaRunStatus");
    if (status?.dataset.state === "ready") {
      status.textContent = languagePack.ide_ready;
    }
  }
}

function updateComposerPlaceholder() {
  const copy = getSubjectCopy();
  const placeholders = copy.placeholders || {};
  const textarea = $("#userInput");

  if (!textarea) {
    return;
  }

  textarea.placeholder = placeholders[state.mode] || placeholders.qa || "";
}

function resizeComposer() {
  const input = $("#userInput");
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
}

function cacheConversation(chat) {
  if (!chat?.id) {
    return;
  }

  state.messageCache.set(chat.id, chat.messages || []);
}

const $ = (selector) => document.querySelector(selector);
const messagesBox = $("#chatMessages");
const historyBox = $("#historyList");

function getStoredAuth() {
  try {
    const saved = JSON.parse(sessionStorage.getItem("gemma4_auth") || "null");
    if (!saved?.token || !saved?.subject || !saved?.username) {
      return null;
    }
    return saved;
  } catch {
    return null;
  }
}

function showLogin(message = "") {
  $("#appShell").classList.add("is-hidden");
  $("#loginScreen").classList.remove("is-hidden");
  setAuthMode("login");
  $("#loginError").textContent = message;
}

function showWorkspace() {
  $("#loginScreen").classList.add("is-hidden");
  $("#appShell").classList.remove("is-hidden");
  updateSubjectChrome();
  updateKnowledgeAccess();
  updateComposerPlaceholder();
  updateModeTitle();
}

function setAuth(data) {
  state.auth = {
    token: data.access_token,
    username: data.username,
    role: data.role || "student",
    subject: data.subject,
    expires_at: data.expires_at,
  };
  state.subject = data.subject;
  sessionStorage.setItem("gemma4_auth", JSON.stringify(state.auth));
}

async function refreshAuthProfile() {
  const response = await apiFetch("/auth/me");
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "登录状态校验失败。");
  }

  state.auth = {
    ...state.auth,
    username: data.username,
    role: data.role || "student",
  };
  sessionStorage.setItem("gemma4_auth", JSON.stringify(state.auth));
}

function clearAuth(message = "") {
  state.sendGeneration += 1;
  state.sendController?.abort();
  state.sendController = null;
  state.sending = false;
  for (const draft of state.drafts.values()) releaseDraftFiles(draft.files);
  state.drafts.clear();
  state.uploadGeneration += 1;
  state.uploadController?.abort();
  state.uploadController = null;
  state.uploading = false;
  state.fileUploads = [];
  state.savingSources = false;
  state.auth = null;
  state.active = null;
  state.chats = [];
  state.messageCache.clear();
  sessionStorage.removeItem("gemma4_auth");
  renderFileUploads();
  renderSourceContext();
  updateComposerControls();
  showLogin(message);
}

async function apiFetch(path, options = {}) {
  const requestToken = state.auth?.token;
  const headers = new Headers(options.headers || {});
  if (state.auth?.token) {
    headers.set("Authorization", `Bearer ${state.auth.token}`);
  }

  const response = await fetch(`${API}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && state.auth?.token === requestToken) {
    clearAuth("登录已失效，请重新登录。");
  }

  return response;
}

async function submitLogin(event) {
  event.preventDefault();

  const username = $("#loginUsername").value.trim();
  const password = $("#loginPassword").value;
  const subject = document.querySelector(
    'input[name="subject"]:checked',
  )?.value || "ai";
  const button = $("#loginBtn");

  if (!username || !password) {
    showLogin("请输入账号和密码。");
    return;
  }

  button.disabled = true;
  button.textContent = "登录中…";
  $("#loginError").textContent = "";

  try {
    const response = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password, subject }),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "登录失败。");
    }

    setAuth(data);
    showWorkspace();
    await boot();
  } catch (error) {
    showLogin(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "登录并进入学习空间 →";
  }
}

function setAuthMode(mode) {
  const registering = mode === "register";
  $("#loginForm").classList.toggle("is-hidden", registering);
  $("#registerForm").classList.toggle("is-hidden", !registering);
  $("#showRegisterBtn").classList.toggle("is-hidden", registering);
  $("#authTitle").textContent = registering ? "注册学习平台" : "登录学习平台";
  $("#authDescription").textContent = registering
    ? "创建账号后即可登录，并在登录时选择学习学科。"
    : "使用账号密码登录，并选择本次学习的课程方向。";
  $("#loginError").textContent = "";
  $("#registerError").textContent = "";
}

async function submitRegistration(event) {
  event.preventDefault();

  const username = $("#registerUsername").value.trim();
  const password = $("#registerPassword").value;
  const passwordConfirm = $("#registerPasswordConfirm").value;
  const button = $("#registerBtn");

  if (password !== passwordConfirm) {
    $("#registerError").textContent = "两次输入的密码不一致。";
    return;
  }

  button.disabled = true;
  button.textContent = "注册中…";
  $("#registerError").textContent = "";

  try {
    const response = await fetch(`${API}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username,
        password,
        password_confirm: passwordConfirm,
      }),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "注册失败。");
    }

    $("#registerForm").reset();
    $("#loginUsername").value = data.username;
    setAuthMode("login");
    $("#loginError").textContent = data.message || "注册成功，请登录。";
  } catch (error) {
    $("#registerError").textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "注册账号 →";
  }
}

function logout() {
  clearAuth();
  $("#loginForm").reset();
  $("#registerForm").reset();
  document.querySelector('input[name="subject"][value="ai"]').checked = true;
  state.subject = "ai";
  state.mode = "qa";
  setMode("qa");
  resetJavaIde();
  changeLanguage(state.language);
}


/*语言切换函数*/
function changeLanguage(lang){

    state.language = lang;
    document.documentElement.lang = lang === "en" ? "en" : "zh-CN";
    try {
      localStorage.setItem("gemma4_language", lang);
    } catch {}


    document
    .querySelector("#zhBtn")
    .classList.toggle(
        "active",
        lang==="zh"
    );


    document
    .querySelector("#enBtn")
    .classList.toggle(
        "active",
        lang==="en"
    );


    // 修改所有带 data-i18n 的文字
    document
    .querySelectorAll("[data-i18n]")
    .forEach((element)=>{

        const key = element.dataset.i18n;

        if(LANGUAGE_TEXT[lang][key]){

            element.innerHTML =
            LANGUAGE_TEXT[lang][key];

        }

    });
    // 聊天区域
    $("#assistantName").textContent =
      LANGUAGE_TEXT[lang].assistant;

    updateSubjectChrome();
    updateJavaIdeText();
    updateComposerPlaceholder();
    updateModeTitle();
    renderMessages();

}


function updateModeTitle(){

const titles={

zh:{
qa:"多轮 AI 问答",
project_assistant:"项目助手",
learning_path:"学习路径规划",
quiz:"AI 出题",
coach:"AI 陪练",
online_ide:"Java 在线IDE"
},


en:{
qa:"Multi-turn AI Q&A",
project_assistant:"Project Assistant",
learning_path:"Learning Path",
quiz:"AI Quiz",
coach:"AI Coach",
online_ide:"Java Online IDE"
}

};


$("#modeHeading").textContent =
titles[state.language][state.mode] || titles[state.language].qa;

const pack = LANGUAGE_TEXT[state.language];
$("#assistantName").textContent = state.mode === "project_assistant"
  ? pack.tab_project : pack.assistant;
$("#modeTip").textContent = state.mode === "project_assistant"
  ? pack.project_mode_tip : getSubjectCopy().mode_tip;

}
/*语言切换函数*/

function esc(text = "") {
  return text.replace(
    /[&<>"']/g,
    (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char]),
  );
}

function renderText(text = "") {

    const cleaned = text
        .replace(/\r\n/g,"\n")
        .replace(/\n[ \t]*\n[ \t]*\n+/g,"\n\n")
        .trim();


    if(window.marked){

        marked.setOptions({
            breaks:false,
            gfm:true,
        });

        return marked.parse(cleaned);

    }

    return esc(cleaned)
        .replace(/\n/g,"<br>");
}

function getChat() {
  return state.chats.find((chat) => chat.id === state.active) || null;
}

function setMode(mode) {
  if (mode === "online_ide" && state.subject !== "java") {
    mode = "qa";
  }

  state.mode = mode;

  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });

  const isIde = mode === "online_ide";
  $("#javaIdePanel")?.classList.toggle("is-hidden", !isIde);
  $(".chat-card")?.classList.toggle("is-hidden", isIde);
  updateComposerPlaceholder();
  updateModeTitle();
  if (!getChat()?.messages?.length) {
    renderMessages();
  }
}

function renderHistory() {
  historyBox.innerHTML = "";

  state.chats.forEach((chat) => {
    const row = document.createElement("div");
    row.className = `history-item ${
      chat.id === state.active ? "active" : ""
    }`;

    const titleButton = document.createElement("button");
    titleButton.type = "button";
    titleButton.className = "history-title";
    titleButton.textContent = chat.title || "新对话";
    titleButton.title = chat.title || "新对话";

    titleButton.onclick = async () => {
      try {
        await openConversation(chat.id);
      } catch (error) {
        alert(`读取会话失败：${error.message}`);
      }
    };

    const actions = document.createElement("div");
    actions.className = "history-actions";

    const renameButton = document.createElement("button");
    renameButton.type = "button";
    renameButton.className = "history-action";
    renameButton.textContent = "✎";
    renameButton.title = "重命名会话";
    renameButton.setAttribute("aria-label", "重命名会话");

    renameButton.onclick = async (event) => {
      event.stopPropagation();

      try {
        await renameConversation(chat);
      } catch (error) {
        alert(`重命名失败：${error.message}`);
      }
    };

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "history-action danger";
    deleteButton.textContent = "×";
    deleteButton.title = "删除会话";
    deleteButton.setAttribute("aria-label", "删除会话");

    const exportButton = document.createElement("button");
    exportButton.type = "button";
    exportButton.className = "history-action";
    exportButton.textContent = "⇩";
    exportButton.title = "导出 Markdown";
    exportButton.setAttribute("aria-label", "导出 Markdown");

    exportButton.onclick = async (event) => {
      event.stopPropagation();
      try {
        await downloadConversation(chat, "markdown");
      } catch (error) {
        alert(`导出失败：${error.message}`);
      }
    };


    deleteButton.onclick = async (event) => {
      event.stopPropagation();

      try {
        await removeConversation(chat);
      } catch (error) {
        alert(`删除失败：${error.message}`);
      }
    };

    actions.append(renameButton, exportButton, deleteButton);
    row.append(titleButton, actions);
    historyBox.appendChild(row);
  });
}

async function renameConversation(chat) {
  const nextTitle = window.prompt(
    "请输入新的会话名称：",
    chat.title || "新对话",
  );

  if (nextTitle === null) {
    return;
  }

  const title = nextTitle.trim();

  if (!title) {
    throw new Error("会话名称不能为空。");
  }

  const response = await apiFetch(`/conversations/${chat.id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "服务器未能更新会话名称。");
  }

  chat.title = data.title;
  chat.updated_at = data.updated_at;

  renderHistory();
}


async function downloadConversation(chat, format = "markdown") {
  const extension = format === "json" ? "json" : "md";
  const response = await apiFetch(
    `/conversations/${chat.id}/export?format=${format}`,
  );

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "服务器未能导出会话。");
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = `conversation_${chat.id}.${extension}`;

  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}


async function removeConversation(chat) {
  const title = chat.title || "这个会话";

  const confirmed = window.confirm(
    `确定删除“${title}”吗？\n\n删除后，该会话中的全部聊天记录和 RAG 证据都会从 SQLite 中移除，无法恢复。`,
  );

  if (!confirmed) {
    return;
  }

  const wasActive = state.active === chat.id;

  const response = await apiFetch(`/conversations/${chat.id}`, {
    method: "DELETE",
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "服务器未能删除会话。");
  }

  state.chats = state.chats.filter((item) => item.id !== chat.id);
  state.messageCache.delete(chat.id);

  if (wasActive) {
    state.active = null;

    if (state.chats.length > 0) {
      await openConversation(state.chats[0].id);
    } else {
      await newChat();
    }
  } else {
    renderHistory();
  }
}


function evidenceHtml(items = []) {
  if (!items.length) {
    return "";
  }

  return `
    <details>
      <summary data-i18n="rag_sources">查看本轮 RAG 证据（${items.length} 条）</summary>
      ${items
        .map(
          (item) => `
            <div class="evidence">
              <small>
                ${esc(item.source_file)}
                ${item.location ? ` · ${esc(item.location)}` : ""}
                · score=${item.score}
              </small>
              ${esc(item.text)}
            </div>
          `,
        )
        .join("")}
    </details>
  `;
}

function findMessageById(messageId) {
  for (const chat of state.chats) {
    const message = (chat.messages || []).find(
      (item) => item.message_id === messageId,
    );

    if (message) {
      return message;
    }
  }

  return null;
}


function qualityFeedbackHtml(message) {
  if (!message.message_id) {
    return "";
  }

  const quality = message.quality_feedback || null;
  const rating = quality?.rating || 0;
  const trainingSelected = Boolean(quality?.training_selected);

  const stars = Array.from(
    { length: 5 },
    (_, index) => {
      const star = index + 1;

      return `
        <button
          type="button"
          class="quality-star ${star <= rating ? "selected" : ""}"
          data-message-id="${message.message_id}"
          data-rate="${star}"
          title="评分 ${star} 星"
          aria-label="评分 ${star} 星"
        >★</button>
      `;
    },
  ).join("");

  const feedbackText = quality?.feedback
    ? "修改评价"
    : "填写评价";

  const selectedText = trainingSelected
    ? '<span class="training-tag">已加入训练候选</span>'
    : "";

  return `
    <div class="quality-panel" data-message-id="${message.message_id}">
      <div class="quality-topline">
        <span class="quality-label">回答质量</span>
        <div class="quality-stars">${stars}</div>
        <span class="quality-score">
          ${rating ? `${rating}/5` : "未评分"}
        </span>
      </div>

      <div class="quality-actions">
        <label class="training-check">
          <input
            class="training-select"
            type="checkbox"
            data-message-id="${message.message_id}"
            ${trainingSelected ? "checked" : ""}
          >
          <span>加入训练样本</span>
        </label>

        <button
          type="button"
          class="feedback-note-btn"
          data-message-id="${message.message_id}"
        >${feedbackText}</button>

        ${selectedText}
      </div>
    </div>
  `;
}


async function saveQualityFeedback(
  messageId,
  rating,
  feedback,
  trainingSelected,
) {
  const response = await apiFetch(
    `/messages/${messageId}/feedback`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        rating,
        feedback,
        training_selected: trainingSelected,
      }),
    },
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "评分保存失败。");
  }

  const message = findMessageById(messageId);

  if (message) {
    message.quality_feedback = data;
  }

  renderMessages();
}


function bindQualityActions() {
  messagesBox.querySelectorAll(".quality-star").forEach((button) => {
    button.onclick = async () => {
      const messageId = button.dataset.messageId;
      const rating = Number(button.dataset.rate);
      const message = findMessageById(messageId);

      if (!message) {
        return;
      }

      const panel = button.closest(".quality-panel");
      const trainingSelected = Boolean(
        panel?.querySelector(".training-select")?.checked,
      );

      const currentFeedback =
        message.quality_feedback?.feedback || "";

      const feedback = window.prompt(
        "可选：填写这条回答的优点、问题或改进建议。",
        currentFeedback,
      );

      if (feedback === null) {
        return;
      }

      try {
        await saveQualityFeedback(
          messageId,
          rating,
          feedback.trim(),
          trainingSelected,
        );
      } catch (error) {
        alert(`评分保存失败：${error.message}`);
      }
    };
  });

  messagesBox.querySelectorAll(".training-select").forEach((checkbox) => {
    checkbox.onchange = async () => {
      const messageId = checkbox.dataset.messageId;
      const message = findMessageById(messageId);
      const rating = message?.quality_feedback?.rating || 0;

      if (!rating) {
        checkbox.checked = false;
        alert("请先为该回答选择 1 到 5 星评分。");
        return;
      }

      try {
        await saveQualityFeedback(
          messageId,
          rating,
          message.quality_feedback?.feedback || "",
          checkbox.checked,
        );
      } catch (error) {
        checkbox.checked = !checkbox.checked;
        alert(`训练样本状态保存失败：${error.message}`);
      }
    };
  });

  messagesBox.querySelectorAll(".feedback-note-btn").forEach((button) => {
    button.onclick = async () => {
      const messageId = button.dataset.messageId;
      const message = findMessageById(messageId);
      const rating = message?.quality_feedback?.rating || 0;

      if (!rating) {
        alert("请先为该回答选择 1 到 5 星评分。");
        return;
      }

      const feedback = window.prompt(
        "填写评价或改进建议：",
        message.quality_feedback?.feedback || "",
      );

      if (feedback === null) {
        return;
      }

      try {
        await saveQualityFeedback(
          messageId,
          rating,
          feedback.trim(),
          Boolean(message.quality_feedback?.training_selected),
        );
      } catch (error) {
        alert(`评价保存失败：${error.message}`);
      }
    };
  });
}


function hasMessageText(message) {
  return Boolean(message.content) && !(message.attachments?.length === 1 && message.content === `Attached file: ${message.attachments[0].source_file}`);
}

function fileMessageHtml(attachments, chat, showText = false) {
  const pack = LANGUAGE_TEXT[state.language];
  return `<section class="message user file-message"><span class="who">Student</span>
    <div class="file-attachments">${attachments.map(file => {
      const name = file.source_file;
      const isImage = file.kind === "image";
      const selected = file.pending || (chat.source_files || []).includes(name);
      const extension = name.includes(".") ? name.split(".").pop().toUpperCase().slice(0, 8) : "FILE";
      const size = typeof file.size_bytes === "number"
        ? (file.size_bytes < 1024 ? `${file.size_bytes} B` : file.size_bytes < 1048576 ? `${(file.size_bytes / 1024).toFixed(1)} KB` : `${(file.size_bytes / 1048576).toFixed(1)} MB`)
        : "";
      const action = selected ? pack.remove_source : pack.use_file;
      return `<div class="file-card ${selected || isImage ? "is-selected" : ""}">
        ${isImage && file.preview_data_url ? `<img class="file-card-preview" src="${esc(file.preview_data_url)}" alt="${esc(name)}">` : `<span class="file-card-icon" aria-hidden="true">${esc(extension)}</span>`}
        <span class="file-card-info"><b title="${esc(name)}">${esc(name)}</b><small>${size ? `${size} · ` : ""}${isImage ? pack.image_label : selected ? pack.file_in_context : pack.file_not_in_context}</small></span>
        ${isImage ? "" : `<button type="button" data-file-source="${esc(name)}" aria-label="${esc(action + ': ' + name)}" title="${esc(action)}" ${state.sending || state.uploading || state.savingSources ? "disabled" : ""}>${selected ? "×" : esc(pack.use_file)}</button>`}
      </div>`;
    }).join("")}</div>${showText ? '<div class="bubble" data-message-content></div>' : ""}</section>`;
}

function renderMessages() {
  const chat = getChat();
  renderSourceContext();
  renderFileUploads();

  if (!chat) {
    messagesBox.innerHTML = "";
    return;
  }

  const messages = chat.messages || [];
  const textMessages = messages.filter(hasMessageText);
  if (!textMessages.length) {
    const copy = getSubjectCopy();
    const pack = LANGUAGE_TEXT[state.language];
    const isProject = state.mode === "project_assistant";
    messagesBox.innerHTML = `
      <div class="welcome">
        <span class="eyebrow">${isProject ? pack.tab_project : "Gemma4 Learning Agent"}</span>
        <h3>${isProject ? pack.project_welcome_title : copy.welcome_title}</h3>
        <p>${isProject ? pack.project_welcome_desc : copy.welcome_desc}</p>
        ${isProject ? `<div class="suggestions">
          <button type="button" data-q="${esc(pack.project_architecture_question)}">${pack.project_architecture}</button>
          <button type="button" data-q="${esc(pack.project_debug_question)}">${pack.project_debug}</button>
          <button type="button" data-q="${esc(pack.project_code_question)}">${pack.project_code}</button>
        </div>` : ""}
      </div>
    `;

  } else {
    messagesBox.innerHTML = "";
  }

  // Older conversations and previously uploaded files have a saved selection
  // but no upload message yet. Show those files without changing their history.
  const recordedFiles = new Set(messages.flatMap(message => (message.attachments || []).map(file => file.source_file)));
  const existingFiles = (chat.source_files || []).filter(name => !recordedFiles.has(name));
  if (existingFiles.length) messagesBox.innerHTML += fileMessageHtml(existingFiles.map(source_file => ({source_file})), chat);

  messagesBox.innerHTML += messages
      .map(
        (message) => message.attachments?.length ? fileMessageHtml(message.attachments, chat, hasMessageText(message)) : `
          <section class="message ${message.role}">
            <span class="who">
              ${message.role === "user" ? "Student" : chat.agent_mode === "project_assistant" ? LANGUAGE_TEXT[state.language].tab_project : "Gemma4 study-agent"}
            </span>
            <div class="bubble" data-message-content></div>
            ${
              message.role === "assistant"
                ? `${evidenceHtml(message.evidence || [])}${qualityFeedbackHtml(message)}`
                : ""
            }
          </section>
        `,
      )
      .join("");


    const bubbles = messagesBox.querySelectorAll(
      "[data-message-content]"
    );


    textMessages.forEach((message, index)=>{

      const bubble = bubbles[index];

      if(!bubble){
        return;
      }

      bubble.innerHTML = message.role === "user" ? esc(message.content) : renderText(message.content);


      if(window.renderMathInElement){

        renderMathInElement(
          bubble,
          {
            delimiters:[
              {
                left:"$$",
                right:"$$",
                display:true
              },
              {
                left:"$",
                right:"$",
                display:false
              }
            ],
            throwOnError:false
          }
        );

      }

    });

  document.querySelectorAll("[data-q]").forEach((button) => {
    button.onclick = () => {
      const input = $("#userInput");
      input.value = button.dataset.q.trimEnd();
      const draft = getDraft();
      if (draft) draft.text = input.value;
      resizeComposer();
      input.focus();
      input.scrollTop = 0;
    };
  });
  messagesBox.querySelectorAll("[data-file-source]").forEach(button => {
    button.onclick = () => {
      const files = chat.source_files || [];
      const name = button.dataset.fileSource;
      saveConversationSources(files.includes(name) ? files.filter(file => file !== name) : [...files, name]);
    };
  });
  bindQualityActions();
  messagesBox.scrollTop = messagesBox.scrollHeight;
}

function addMessage(message, chat = getChat()) {
  if (!chat) {
    return;
  }

  chat.messages.push(message);
  cacheConversation(chat);
  renderMessages();
}

async function loadConversationList(subject = state.subject) {
  const response = await apiFetch(
    `/conversations?subject=${encodeURIComponent(subject)}`,
  );

  if (!response.ok) {
    throw new Error("无法读取历史会话列表。");
  }

  const summaries = await response.json();

  state.chats = summaries.map((item) => {
    const cachedMessages = state.messageCache.get(item.conversation_id) || [];

    return {
      id: item.conversation_id,
      subject: item.subject || subject,
      title: item.title,
      agent_mode: item.agent_mode,
      source_files: item.source_files || [],
      created_at: item.created_at,
      updated_at: item.updated_at,
      messages: cachedMessages,
    };
  });

  renderHistory();
}

async function openConversation(conversationId) {
  const response = await apiFetch(`/conversations/${conversationId}`);

  if (!response.ok) {
    throw new Error("会话不存在或读取失败。");
  }

  const detail = await response.json();

  const chat = {
    id: detail.conversation_id,
    subject: detail.subject || state.subject,
    title: detail.title,
    agent_mode: detail.agent_mode || "qa",
    source_files: detail.source_files || [],
    created_at: detail.created_at,
    updated_at: detail.updated_at,
    messages: (detail.messages || []).map((message) => ({
      message_id: message.message_id,
      role: message.role,
      content: message.content,
      attachments: message.attachments || [],
      evidence: message.evidence || [],
      model_used: message.model_used || null,
      quality_feedback: message.quality_feedback || null,
    })),
  };

  const index = state.chats.findIndex((item) => item.id === chat.id);

  if (index >= 0) {
    state.chats[index] = chat;
  } else {
    state.chats.unshift(chat);
  }

  state.active = chat.id;
  restoreDraftInput();
  cacheConversation(chat);
  setMode(chat.agent_mode);
  renderHistory();
  renderMessages();
}

async function newChat() {
  const response = await apiFetch(`/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: "新对话",
      agent_mode: state.mode === "online_ide" ? "qa" : state.mode,
      subject: state.subject,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "创建会话失败。");
  }

  const item = await response.json();

  const chat = {
    id: item.conversation_id,
    subject: item.subject || state.subject,
    title: item.title,
    agent_mode: item.agent_mode,
    source_files: item.source_files || [],
    created_at: item.created_at,
    updated_at: item.updated_at,
    messages: [],
  };

  state.chats.unshift(chat);
  state.active = chat.id;
  restoreDraftInput();
  cacheConversation(chat);

  renderHistory();
  renderMessages();

  return chat;
}

async function send() {
  const input = $("#userInput");
  const raw = input.value.trim();
  const chat = getChat();
  if (!chat || state.sending || state.switchingMode || state.uploading || state.savingSources) return;

  const draft = getDraft(chat.id);
  const files = [...draft.files];
  if (!raw && !files.length) return;
  const mode = state.mode;
  const subject = state.subject;
  const token = state.auth?.token;
  const generation = ++state.sendGeneration;
  const controller = new AbortController();
  const localId = `pending-${generation}`;
  const attachments = files.map(record => ({source_file: record.file.name, size_bytes: record.file.size, kind: record.kind, preview_data_url: record.previewUrl, pending: true}));
  const payload = {
    conversation_id: chat.id, messages: raw ? [{role: "user", content: raw}] : [], agent_mode: mode,
    source_files: chat.source_files || [], language: state.language, subject,
    use_rag: $("#useRag").checked, top_k: Number($("#topK").value),
    temperature: 0.35, max_tokens: Number($("#maxTokens").value),
  };
  draft.text = "";
  draft.files = [];
  draft.error = "";
  input.value = "";
  resizeComposer();
  state.sending = true;
  state.sendController = controller;
  addMessage({localId, role: "user", content: raw, attachments}, chat);
  updateComposerControls();
  let succeeded = false;
  let retained = false;

  try {
    let response;
    if (files.length) {
      const body = new FormData();
      body.append("payload", JSON.stringify(payload));
      files.forEach(record => body.append("files", record.file));
      response = await apiFetch("/chat/attachments", {method: "POST", body, signal: controller.signal});
    } else {
      response = await apiFetch("/chat", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload), signal: controller.signal});
    }
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : LANGUAGE_TEXT[state.language].upload_failed);
    if (state.sendGeneration !== generation || state.auth?.token !== token) return;

    const current = state.chats.find(item => item.id === chat.id) || chat;
    current.messages = current.messages.filter(message => message.localId !== localId);
    const savedUser = data.user_message || {role: "user", content: raw, attachments};
    if (!savedUser.message_id || !current.messages.some(message => message.message_id === savedUser.message_id)) current.messages.push(savedUser);
    if (!data.assistant_message_id || !current.messages.some(message => message.message_id === data.assistant_message_id)) current.messages.push({
      message_id: data.assistant_message_id || null, role: "assistant", content: data.answer,
      evidence: data.evidence || [], model_used: data.model_used || null, quality_feedback: null,
    });
    current.title = data.title || current.title;
    current.agent_mode = mode;
    current.source_files = data.source_files || current.source_files || [];
    cacheConversation(current);
    succeeded = true;
    await loadConversationList(state.subject).catch(() => {});
    renderMessages();
    if (files.length) await refreshKnowledge().catch(() => {});
  } catch (error) {
    if (state.sendGeneration === generation && state.auth?.token === token) {
      const current = state.chats.find(item => item.id === chat.id) || chat;
      current.messages = current.messages.filter(message => message.localId !== localId);
      cacheConversation(current);
      draft.text = raw;
      draft.files = files;
      draft.error = error.message;
      retained = true;
      if (state.active === chat.id) restoreDraftInput();
      renderMessages();
    }
  } finally {
    if (succeeded || !retained) releaseDraftFiles(files);
    if (state.sendGeneration === generation) {
      state.sending = false;
      state.sendController = null;
      updateComposerControls();
    }
  }
}

async function refreshStatus() {
  try {
    const response = await apiFetch(
      `/health?subject=${encodeURIComponent(state.subject)}`,
    );
    const data = await response.json();

    const subjectCopy = getSubjectCopy();

    $("#statusDot").style.background = "#16b98d";
    $("#statusText").textContent =
      state.language === "zh"
        ? `在线 · ${subjectCopy.switch_label} · ${data.model}`
        : `Online · ${subjectCopy.switch_label} · ${data.model}`;
    $("#fileMetric").textContent = data.knowledge_files;
    $("#chunkMetric").textContent = data.knowledge_chunks;
  } catch {
    $("#statusDot").style.background = "#ff7180";
    $("#statusText").textContent = "后端未连接";
  }
}

async function refreshKnowledge() {
  const response = await apiFetch(
    `/knowledge/status?subject=${encodeURIComponent(state.subject)}`,
  );
  const data = await response.json();
  const copy = getSubjectCopy();
  const emptyText =
    state.language === "zh"
      ? `暂未上传${copy.knowledge_label}文件。`
      : `No ${copy.knowledge_label} files uploaded yet.`;

  $("#fileMetric").textContent = data.file_count;
  $("#chunkMetric").textContent = data.chunk_count;

  $("#sourceList").innerHTML = data.sources.length
    ? data.sources
        .map((source) => `<label class="source source-choice"><input type="checkbox" data-source-file="${esc(source)}" ${(getChat()?.source_files || []).includes(source) ? "checked" : ""} ${!getChat() || state.uploading || state.savingSources ? "disabled" : ""}><span>${esc(source)}</span></label>`)
        .join("")
    : `<div class="source">${emptyText}</div>`;
  $("#sourceList").querySelectorAll("[data-source-file]").forEach(checkbox => {
    checkbox.onchange = () => saveConversationSources(
      Array.from($("#sourceList").querySelectorAll("[data-source-file]:checked"), node => node.dataset.sourceFile)
    );
  });
}

function setJavaRunStatus(stateName, message) {
  const status = $("#javaRunStatus");
  if (!status) {
    return;
  }

  status.dataset.state = stateName;
  status.textContent = message;
  status.className = `ide-status ${stateName}`;
}

function resetJavaIde() {
  const editor = $("#javaCodeEditor");
  const stdin = $("#javaStdin");
  const output = $("#javaOutput");

  if (editor) {
    editor.value = JAVA_DEFAULT_CODE;
  }
  if (stdin) {
    stdin.value = "";
  }
  if (output) {
    output.textContent = "";
    output.classList.remove("has-error");
  }

  setJavaRunStatus(
    "ready",
    (LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh).ide_ready,
  );
}

function clearJavaOutput() {
  const output = $("#javaOutput");
  if (output) {
    output.textContent = "";
    output.classList.remove("has-error");
  }
  setJavaRunStatus(
    "ready",
    (LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh).ide_ready,
  );
}

function setJavaRunButton(isRunning) {
  const button = $("#runJavaBtn");
  if (!button) {
    return;
  }

  button.disabled = isRunning;
  const label = button.querySelector("[data-i18n]");
  if (label) {
    label.textContent = isRunning
      ? (LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh).ide_running
      : (LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh).ide_run;
  }
}

async function runJavaCode() {
  if (state.subject !== "java") {
    return;
  }

  const editor = $("#javaCodeEditor");
  const stdin = $("#javaStdin");
  const output = $("#javaOutput");
  const code = editor?.value || "";
  const input = stdin?.value || "";

  setJavaRunButton(true);
  setJavaRunStatus(
    "running",
    (LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh).ide_running,
  );
  if (output) {
    output.textContent = "";
    output.classList.remove("has-error");
  }

  try {
    const response = await apiFetch("/java/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        code,
        stdin: input,
      }),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Java 运行服务不可用。");
    }

    const languagePack = LANGUAGE_TEXT[state.language] || LANGUAGE_TEXT.zh;
    const resultParts = [];
    if (data.compile_output) {
      resultParts.push(data.compile_output);
    }
    if (data.output) {
      resultParts.push(data.output);
    }
    if (data.error) {
      resultParts.push(data.error);
    }

    if (output) {
      output.textContent = resultParts.join("\n") || "程序没有输出。";
      output.classList.toggle("has-error", !data.success);
    }

    if (data.timed_out) {
      setJavaRunStatus("error", languagePack.ide_timeout);
    } else if (data.success) {
      setJavaRunStatus(
        "success",
        `${languagePack.ide_success} · ${data.duration_ms} ms`,
      );
    } else if (data.compile_output) {
      setJavaRunStatus("error", languagePack.ide_compile_failed);
    } else {
      setJavaRunStatus("error", languagePack.ide_error);
    }
  } catch (error) {
    if (output) {
      output.textContent = error.message;
      output.classList.add("has-error");
    }
    setJavaRunStatus("error", error.message);
  } finally {
    setJavaRunButton(false);
  }
}

$("#newChatBtn").onclick = async () => {
  try {
    await newChat();
  } catch (error) {
    alert(`创建新对话失败：${error.message}`);
  }
};

$("#knowledgeBtn").onclick = async () => {
  await refreshKnowledge();
  $("#knowledgeDialog").showModal();
};
$("#chooseSourcesBtn").onclick = () => $("#knowledgeBtn").onclick();

$("#closeKnowledgeBtn").onclick = () => {
  $("#knowledgeDialog").close();
};

$("#sendBtn").onclick = send;

$("#userInput").addEventListener("input", () => {
  const draft = getDraft();
  if (draft) draft.text = $("#userInput").value;
  resizeComposer();
});
$("#userInput").addEventListener("paste", (event) => {
  const files = Array.from(event.clipboardData?.files || []);
  if (files.length) {
    event.preventDefault();
    stageChatFiles(files);
  }
});
$("#userInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send();
  }
});

$("#topK").oninput = (event) => {
  $("#topKValue").textContent = event.target.value;
};

$("#maxTokens").oninput = (event) => {
  $("#maxTokensValue").textContent = event.target.value;
};

document.querySelectorAll(".tab").forEach((button) => {
  button.onclick = async () => {
    if (state.switchingMode) return;
    const previousMode = state.mode;
    const nextMode = button.dataset.mode;
    const chat = getChat();
    setMode(nextMode);
    if (chat && chat.agent_mode !== nextMode && nextMode !== "online_ide" &&
        (nextMode === "project_assistant" || chat.agent_mode === "project_assistant")) {
      state.switchingMode = true;
      updateComposerControls();
      $("#newChatBtn").disabled = true;
      document.querySelectorAll(".tab").forEach(tab => { tab.disabled = true; });
      try {
        await newChat();
      } catch (error) {
        setMode(previousMode);
        alert(error.message);
      } finally {
        state.switchingMode = false;
        updateComposerControls();
        $("#newChatBtn").disabled = false;
        document.querySelectorAll(".tab").forEach(tab => { tab.disabled = false; });
      }
    }
  };
});

$("#runJavaBtn").onclick = runJavaCode;
$("#resetJavaBtn").onclick = resetJavaIde;
$("#clearJavaOutputBtn").onclick = clearJavaOutput;
$("#javaCodeEditor").addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    runJavaCode();
    return;
  }

  if (event.key === "Tab") {
    event.preventDefault();
    const editor = event.currentTarget;
    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    editor.value =
      editor.value.substring(0, start) +
      "    " +
      editor.value.substring(end);
    editor.selectionStart = editor.selectionEnd = start + 4;
  }
});

$("#logoutBtn").onclick = logout;
$("#loginForm").onsubmit = submitLogin;
$("#registerForm").onsubmit = submitRegistration;
$("#showRegisterBtn").onclick = () => setAuthMode("register");
$("#backToLoginBtn").onclick = () => setAuthMode("login");

$("#attachFileBtn").onclick = () => $("#chatFileInput").click();
$("#chatFileInput").onchange = async (event) => {
  const files = Array.from(event.target.files || []);
  event.target.value = "";
  stageChatFiles(files);
};

const chatDropTarget = $(".chat-card");
let chatDragDepth = 0;
const isFileDrag = event => Array.from(event.dataTransfer?.types || []).includes("Files");
const hideDropOverlay = () => {
  chatDragDepth = 0;
  $("#chatDropOverlay").classList.add("is-hidden");
};
chatDropTarget.addEventListener("dragenter", event => {
  if (!isFileDrag(event)) return;
  event.preventDefault();
  chatDragDepth += 1;
  if (state.auth?.role === "admin" && !state.uploading) {
    $("#chatDropOverlay").classList.remove("is-hidden");
  }
});
chatDropTarget.addEventListener("dragover", event => {
  if (!isFileDrag(event)) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = state.auth?.role === "admin" && !state.uploading ? "copy" : "none";
});
chatDropTarget.addEventListener("dragleave", event => {
  if (!isFileDrag(event)) return;
  chatDragDepth = Math.max(0, chatDragDepth - 1);
  if (chatDragDepth === 0) hideDropOverlay();
});
chatDropTarget.addEventListener("drop", async event => {
  if (!isFileDrag(event)) return;
  event.preventDefault();
  hideDropOverlay();
  stageChatFiles(event.dataTransfer.files);
});
// A file dropped outside the chat must not replace the page in the browser.
document.addEventListener("dragover", event => {
  if (isFileDrag(event)) event.preventDefault();
});
document.addEventListener("drop", event => {
  if (isFileDrag(event)) {
    event.preventDefault();
    hideDropOverlay();
  }
});

$("#uploadForm").onsubmit = async (event) => {
  event.preventDefault();
  stageChatFiles($("#knowledgeFile").files);
  $("#knowledgeDialog").close();
  $("#knowledgeFile").value = "";
};

async function boot() {
  try {
    await loadConversationList(state.subject);

    const rememberedChat = state.chats[0] || null;

    if (rememberedChat) {
      await openConversation(rememberedChat.id);
    } else {
      await newChat();
    }
  } catch (error) {
    messagesBox.innerHTML = `
      <div class="welcome">
        <h3>会话系统初始化失败</h3>
        <p>${esc(error.message)}</p>
      </div>
    `;
  }

  await refreshStatus();
  await refreshKnowledge();
}

document.addEventListener("DOMContentLoaded", async () => {
    
  $("#zhBtn").onclick=()=>{
  changeLanguage("zh");
  };


  $("#enBtn").onclick=()=>{
  changeLanguage("en");
  };
    
  setMode("qa");
  try {
    const savedLanguage = localStorage.getItem("gemma4_language");
    if (savedLanguage === "zh" || savedLanguage === "en") {
      state.language = savedLanguage;
    }
  } catch {}
  changeLanguage(state.language);
  resetJavaIde();

  const savedAuth = getStoredAuth();
  if (savedAuth) {
    state.auth = savedAuth;
    state.subject = savedAuth.subject;
    try {
      await refreshAuthProfile();
      showWorkspace();
      await boot();
    } catch {
      clearAuth("登录状态已失效，请重新登录。");
    }
  } else {
    showLogin();
  }

});
