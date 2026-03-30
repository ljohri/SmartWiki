/**
 * SmartWiki chat widget — inject after marked.js:
 * <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
 * <script src="/chat-widget.js"></script>
 */
(function () {
  window.SMARTWIKI_CHAT_CONFIG = window.SMARTWIKI_CHAT_CONFIG || {
    chatbotUrl: "http://localhost:3002",
    chatbotApiKey: "REPLACE_WITH_CHATBOT_API_KEY",
  };

  const cfg = window.SMARTWIKI_CHAT_CONFIG;
  const root = document.createElement("div");
  root.id = "smartwiki-chat-root";
  root.innerHTML =
    '<button id="smartwiki-chat-toggle" type="button" title="Chat" aria-label="Open chat">💬</button>' +
    '<div id="smartwiki-chat-panel" aria-live="polite">' +
    '<div id="smartwiki-chat-header">Wiki assistant <button type="button" id="smartwiki-chat-close" style="border:none;background:transparent;cursor:pointer;font-size:1.1rem">×</button></div>' +
    '<div id="smartwiki-chat-messages"></div>' +
    '<div id="smartwiki-chat-sources"></div>' +
    '<div id="smartwiki-chat-input-row">' +
    '<input id="smartwiki-chat-input" type="text" placeholder="Ask about our wiki…" />' +
    '<button id="smartwiki-chat-send" type="button">Send</button>' +
    "</div></div>";

  document.body.appendChild(root);

  const panel = document.getElementById("smartwiki-chat-panel");
  const toggle = document.getElementById("smartwiki-chat-toggle");
  const close = document.getElementById("smartwiki-chat-close");
  const messagesEl = document.getElementById("smartwiki-chat-messages");
  const sourcesEl = document.getElementById("smartwiki-chat-sources");
  const input = document.getElementById("smartwiki-chat-input");
  const sendBtn = document.getElementById("smartwiki-chat-send");

  const history = [];

  function renderMarkdown(text) {
    if (window.marked && typeof window.marked.parse === "function") {
      return window.marked.parse(text, { mangle: false, headerIds: false });
    }
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function appendMessage(role, html) {
    const div = document.createElement("div");
    div.className = "smartwiki-msg " + role;
    div.innerHTML = html;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setSources(sources) {
    sourcesEl.innerHTML = "";
    if (!sources || !sources.length) return;
    const label = document.createElement("div");
    label.textContent = "Sources:";
    sourcesEl.appendChild(label);
    const ul = document.createElement("ul");
    ul.style.margin = "0.25rem 0 0";
    ul.style.paddingLeft = "1rem";
    sources.forEach((s) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = s.url || "#";
      a.textContent = (s.title || s.path || "page") + " (" + (s.path || "") + ")";
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      li.appendChild(a);
      ul.appendChild(li);
    });
    sourcesEl.appendChild(ul);
  }

  toggle.addEventListener("click", () => panel.classList.toggle("open"));
  close.addEventListener("click", () => panel.classList.remove("open"));

  async function send() {
    const q = (input.value || "").trim();
    if (!q) return;
    if (!cfg.chatbotUrl || !cfg.chatbotApiKey || String(cfg.chatbotApiKey).startsWith("REPLACE")) {
      appendMessage("assistant", "<p>Configure SMARTWIKI_CHAT_CONFIG.</p>");
      return;
    }
    input.value = "";
    appendMessage("user", renderMarkdown(q));
    history.push({ role: "user", content: q });
    sendBtn.disabled = true;
    try {
      const res = await fetch(cfg.chatbotUrl.replace(/\/$/, "") + "/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + cfg.chatbotApiKey,
        },
        body: JSON.stringify({ question: q, history: history.slice(0, -1) }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || res.statusText);
      }
      const answer = data.answer || "";
      history.push({ role: "assistant", content: answer });
      appendMessage("assistant", renderMarkdown(answer));
      setSources(data.sources || []);
    } catch (e) {
      appendMessage("assistant", "<p style='color:#b91c1c'>" + (e.message || String(e)) + "</p>");
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") send();
  });
})();
