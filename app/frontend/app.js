const API = window.__API_BASE__ || "/api";

const state = {

  chats: [],

  active: null,

  mode:"qa",

  language:"zh"

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
        "当前支持 TXT、MD、CSV，单个文件不超过 30 MB。",

    upload_button:
        "上传并构建索引",

    source_title:
        "已入库资料",

    source_desc:
        "上传新文件会自动刷新索引",
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
        "Currently supports TXT, MD and CSV files, up to 30 MB.",

    upload_button:
        "Upload and Build Index",

    source_title:
        "Indexed Documents",

    source_desc:
        "Uploading new files will refresh the index automatically",

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

const $ = (selector) => document.querySelector(selector);
const messagesBox = $("#chatMessages");
const historyBox = $("#historyList");


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


    $("#assistantSub").textContent =
    LANGUAGE_TEXT[lang].assistant_sub;



    $("#knowledgeBtn").innerHTML =
    "▣ " + LANGUAGE_TEXT[lang].knowledge;



    $("#userInput").placeholder =
    LANGUAGE_TEXT[lang].placeholder;



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

  const placeholderMap = {
    qa: "输入问题；你可以继续追问上一轮内容…",
    learning_path: "例如：我想在两周内入门机器学习，每天可学 2 小时。",
    quiz: "例如：围绕 RAG 基础生成 5 道中等难度选择题。",
    coach: "说说你目前学不懂的地方，我会陪你一步步梳理。",
  };

  $("#userInput").placeholder = placeholderMap[mode] || placeholderMap.qa;

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

    exportButton.onclick = (event) => {
      event.stopPropagation();
      downloadConversation(chat, "markdown");
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

  const response = await fetch(`${API}/conversations/${chat.id}`, {
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


function downloadConversation(chat, format = "markdown") {
  const extension = format === "json" ? "json" : "md";

  const link = document.createElement("a");
  link.href = `${API}/conversations/${chat.id}/export?format=${format}`;
  link.download = `conversation_${chat.id}.${extension}`;

  document.body.appendChild(link);
  link.click();
  link.remove();
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

  const response = await fetch(`${API}/conversations/${chat.id}`, {
    method: "DELETE",
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "服务器未能删除会话。");
  }

  state.chats = state.chats.filter((item) => item.id !== chat.id);

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
                ${esc(item.source_file)} · score=${item.score}
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
  const response = await fetch(
    `${API}/messages/${messageId}/feedback`,
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
    messagesBox.innerHTML = `
      <div class="welcome">
        <span class="eyebrow">Gemma4 Learning Agent</span>
       <h3>${state.language==="zh"?"今天想从哪里开始？":"Where would you like to start today?"}
        </h3>
        <p>${state.language==="zh"?"你可以基于本地课程资料连续追问，也可以切换到学习路径、AI 出题与 AI 陪练。":"You can ask questions based on your private knowledge base, or switch to Learning Path, AI Quiz and AI Coach."}
        </p>
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

async function loadConversationList() {
  const response = await fetch(`${API}/conversations`);

  if (!response.ok) {
    throw new Error("无法读取历史会话列表。");
  }

  const summaries = await response.json();
  const oldChats = new Map(state.chats.map((chat) => [chat.id, chat]));

  state.chats = summaries.map((item) => {
    const oldChat = oldChats.get(item.conversation_id);

    return {
      id: item.conversation_id,
      title: item.title,
      agent_mode: item.agent_mode,
      created_at: item.created_at,
      updated_at: item.updated_at,
      messages: oldChat?.messages || [],
    };
  });

  renderHistory();
}

async function openConversation(conversationId) {
  const response = await fetch(`${API}/conversations/${conversationId}`);

  if (!response.ok) {
    throw new Error("会话不存在或读取失败。");
  }

  const detail = await response.json();

  const chat = {
    id: detail.conversation_id,
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
  setMode(chat.agent_mode);
  renderHistory();
  renderMessages();
}

async function newChat() {
  const response = await fetch(`${API}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: "新对话",
      agent_mode: state.mode,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "创建会话失败。");
  }

  const item = await response.json();

  const chat = {
    id: item.conversation_id,
    title: item.title,
    agent_mode: item.agent_mode,
    created_at: item.created_at,
    updated_at: item.updated_at,
    messages: [],
  };

  state.chats.unshift(chat);
  state.active = chat.id;

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
    const response = await fetch(`${API}/chat`, {
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

    addMessage({
      message_id: data.assistant_message_id || null,
      role: "assistant",
      content: data.answer,
      evidence: data.evidence || [],
      model_used: data.model_used || null,
      quality_feedback: null,
    });

    await loadConversationList();
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
    const response = await fetch(`${API}/health`);
    const data = await response.json();

    $("#statusText").textContent =
    `在线 · ${data.model}`;
    $("#fileMetric").textContent = data.knowledge_files;
    $("#chunkMetric").textContent = data.knowledge_chunks;
  } catch {
    $("#statusDot").style.background = "#ff7180";
    $("#statusText").textContent = "后端未连接";
  }
}

async function refreshKnowledge() {
  const response = await fetch(`${API}/knowledge/status`);
  const data = await response.json();

  $("#fileMetric").textContent = data.file_count;
  $("#chunkMetric").textContent = data.chunk_count;

  $("#sourceList").innerHTML = data.sources.length
    ? data.sources
        .map((source) => `<div class="source">${esc(source)}</div>`)
        .join("")
    : `<div class="source">暂未上传知识库文件。</div>`;
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
    const response = await fetch(`${API}/knowledge/upload`, {
      method: "POST",
      body: formData,
    });

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
    await loadConversationList();

    if (state.chats.length > 0) {
      await openConversation(state.chats[0].id);
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
  await boot();

});
