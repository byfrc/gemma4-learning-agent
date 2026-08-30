const API = window.__API_BASE__ || "/api";

const state = {

  chats: [],

  active: null,

  subject: "ai",

  mode:"qa",

  language:"zh",

  auth: null,

  messageCache: new Map()

};
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
        "上传后系统会自动切块并建立混合检索索引。",

    select_material:
        "选择课程资料",

    upload_desc:
        "支持 TXT、MD、CSV、PDF、PPT、PPTX，单个文件不超过 30 MB。",

    upload_button:
        "上传并构建索引",

    source_title:
        "已入库资料",

    source_desc:
        "上传新文件会自动刷新索引",

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
        "Uploaded documents will be chunked and indexed automatically.",

    select_material:
        "Select Learning Materials",

    upload_desc:
        "Supports TXT, MD, CSV, PDF, PPT and PPTX files, up to 30 MB each.",

    upload_button:
        "Upload and Build Index",

    source_title:
        "Indexed Documents",

    source_desc:
        "Uploading new files will refresh the index automatically",

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
        "你可以围绕 Java 课程资料连续追问，也可以切换到学习路径、AI 出题与 AI 陪练。",
      placeholders: {
        qa: "例如：Java 的继承和封装有什么区别？",
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
        "You can ask follow-up questions about Java course materials, or switch to Learning Path, AI Quiz and AI Coach.",
      placeholders: {
        qa: "For example: what is the difference between inheritance and encapsulation in Java?",
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

  updateKnowledgeAccess();
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
    sourceDescription.textContent = isAdmin
      ? languagePack.source_desc
      : languagePack.source_readonly;
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
  state.auth = null;
  state.active = null;
  state.chats = [];
  state.messageCache.clear();
  sessionStorage.removeItem("gemma4_auth");
  showLogin(message);
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.auth?.token) {
    headers.set("Authorization", `Bearer ${state.auth.token}`);
  }

  const response = await fetch(`${API}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && state.auth) {
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
  changeLanguage("zh");
}


/*语言切换函数*/
function changeLanguage(lang){

    state.language = lang;


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
    updateComposerPlaceholder();
    updateModeTitle();

}


function updateModeTitle(){

const titles={

zh:{
qa:"多轮 AI 问答",
learning_path:"学习路径规划",
quiz:"AI 出题",
coach:"AI 陪练"
},


en:{
qa:"Multi-turn AI Q&A",
learning_path:"Learning Path",
quiz:"AI Quiz",
coach:"AI Coach"
}

};


$("#modeHeading").textContent =
titles[state.language][state.mode];

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
  state.mode = mode;

  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });

  updateComposerPlaceholder();
  updateModeTitle();
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


function renderMessages() {
  const chat = getChat();

  if (!chat) {
    messagesBox.innerHTML = "";
    return;
  }

  if (!chat.messages || !chat.messages.length) {
    const copy = getSubjectCopy();
    messagesBox.innerHTML = `
      <div class="welcome">
        <span class="eyebrow">Gemma4 Learning Agent</span>
        <h3>${copy.welcome_title}</h3>
        <p>${copy.welcome_desc}</p>
      </div>
    `;

    document.querySelectorAll("[data-q]").forEach((button) => {
      button.onclick = () => {
        $("#userInput").value = button.dataset.q;
        $("#userInput").focus();
      };
    });
  } else {
    messagesBox.innerHTML = chat.messages
      .map(
        (message) => `
          <section class="message ${message.role}">
            <span class="who">
              ${message.role === "user" ? "Student" : "Gemma4 study-agent"}
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


    chat.messages.forEach((message, index)=>{

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

  }
  bindQualityActions();
  messagesBox.scrollTop = messagesBox.scrollHeight;
}

function addMessage(message) {
  const chat = getChat();

  if (!chat) {
    return;
  }

  chat.messages.push(message);
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
    created_at: detail.created_at,
    updated_at: detail.updated_at,
    messages: (detail.messages || []).map((message) => ({
      message_id: message.message_id,
      role: message.role,
      content: message.content,
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
      agent_mode: state.mode,
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
    created_at: item.created_at,
    updated_at: item.updated_at,
    messages: [],
  };

  state.chats.unshift(chat);
  state.active = chat.id;
  cacheConversation(chat);

  renderHistory();
  renderMessages();

  return chat;
}

async function send() {
  const input = $("#userInput");
  const raw = input.value.trim();
  const chat = getChat();

  if (!raw || !chat) {
    return;
  }

  input.value = "";

  addMessage({
    role: "user",
    content: raw,
  });

  const button = $("#sendBtn");
  button.disabled = true;
  button.textContent = "生成中…";

  try {
    const response = await apiFetch(`/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        conversation_id: chat.id,
        messages: [
          {
            role: "user",
            content: raw,
          },
        ],
        agent_mode: state.mode,
        language: state.language,
        subject: state.subject,
        use_rag: $("#useRag").checked,
        top_k: Number($("#topK").value),
        temperature: 0.35,
        max_tokens: Number($("#maxTokens").value),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "模型请求失败。");
    }

    chat.title = data.title || chat.title;
    chat.agent_mode = state.mode;
    chat.subject = data.subject || chat.subject || state.subject;

    addMessage({
      message_id: data.assistant_message_id || null,
      role: "assistant",
      content: data.answer,
      evidence: data.evidence || [],
      model_used: data.model_used || null,
      quality_feedback: null,
    });

    cacheConversation(chat);

    await loadConversationList(state.subject);
    renderMessages();
  } catch (error) {
    addMessage({
      role: "assistant",
      content: `### 模型调用失败\n${error.message}\n\n请检查 FastAPI、vLLM 与模型服务日志。`,
      evidence: [],
    });
  } finally {
    button.disabled = false;
    button.textContent = "发送 ↗";
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
        .map((source) => `<div class="source">${esc(source)}</div>`)
        .join("")
    : `<div class="source">${emptyText}</div>`;
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

$("#closeKnowledgeBtn").onclick = () => {
  $("#knowledgeDialog").close();
};

$("#sendBtn").onclick = send;

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
  button.onclick = () => {
    setMode(button.dataset.mode);
  };
});

$("#logoutBtn").onclick = logout;
$("#loginForm").onsubmit = submitLogin;
$("#registerForm").onsubmit = submitRegistration;
$("#showRegisterBtn").onclick = () => setAuthMode("register");
$("#backToLoginBtn").onclick = () => setAuthMode("login");

$("#uploadForm").onsubmit = async (event) => {
  event.preventDefault();

  const file = $("#knowledgeFile").files[0];

  if (!file) {
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const button = event.currentTarget.querySelector("button");
  button.disabled = true;
  button.textContent = "索引构建中…";

  try {
    const response = await apiFetch(
      `/knowledge/upload?subject=${encodeURIComponent(state.subject)}`,
      {
      method: "POST",
      body: formData,
      },
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "上传失败");
    }

    await refreshKnowledge();
    alert(data.message);
  } catch (error) {
    alert(`上传失败：${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = "上传并重建索引";
  }
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
  changeLanguage("zh");

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
