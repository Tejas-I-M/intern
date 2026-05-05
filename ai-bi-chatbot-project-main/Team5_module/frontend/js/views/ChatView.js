import { reportService as sharedReportService } from "../services/ReportService.js?v=2";
import { stateManager as sharedStateManager } from "../core/StateManager.js";
import { toast as sharedToast } from "../components/Toast.js";
import { Sidebar } from "../components/Sidebar.js";

function safeText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMessageHtml(value) {
  return escapeHtml(value || "").replace(/\n/g, "<br>");
}

export class ChatView {
  constructor(options = {}) {
    this.router = options?.router || null;
    this.reportService = options?.reportService || sharedReportService;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.toast = options?.toast || sharedToast;

    this.host = null;
    this.container = null;
    this.sidebar = null;
    this.unsubscribe = null;

    this.fileId = null;
    this.canAsk = false;
    this.isBusy = false;
    this.messages = [];
    this.predefinedQuestions = [];

    this.boundClickHandler = this.handleClick.bind(this);
    this.boundSubmitHandler = this.handleSubmit.bind(this);
  }

  mount(root) {
    if (!root) {
      return () => {};
    }

    this.host = root;
    this.host.innerHTML = this.render();
    this.container = this.host.querySelector(".chat-view");

    const sidebarHost = this.host.querySelector("[data-sidebar-mount]");
    this.sidebar = new Sidebar({
      router: this.router,
      stateManager: this.stateManager,
      toast: this.toast
    });

    if (sidebarHost) {
      this.sidebar.mount(sidebarHost);
    }

    if (this.container) {
      this.container.addEventListener("click", this.boundClickHandler);
      this.container.addEventListener("submit", this.boundSubmitHandler);
    }

    this.unsubscribe = this.stateManager.subscribe((nextState) => {
      this.syncState(nextState);
    });

    this.syncState(this.stateManager.getState());
    this.loadPredefinedQuestions();
    this.loadChatHistory();
    this.renderMessages();

    return () => this.unmount();
  }

  unmount() {
    if (typeof this.unsubscribe === "function") {
      this.unsubscribe();
      this.unsubscribe = null;
    }

    if (this.container) {
      this.container.removeEventListener("click", this.boundClickHandler);
      this.container.removeEventListener("submit", this.boundSubmitHandler);
      this.container = null;
    }

    if (this.sidebar) {
      this.sidebar.unmount();
      this.sidebar = null;
    }

    this.host = null;
  }

  render() {
    return `
      <section class="chat-view app-grid" aria-label="Full chat view">
        <div data-sidebar-mount class="sidebar-slot"></div>

        <article class="chat-main glass-card">
          <header class="chat-head">
            <h2>Chat Assistant</h2>
            <p>Ask questions about your analyzed dataset.</p>
          </header>

          <p class="upload-status" data-chat-status data-variant="info">
            Run analysis before chatting.
          </p>

          <section class="quick-wrap">
            <h3>Suggested Questions</h3>
            <div class="quick-list" data-chat-quicklist>
              <span class="quick-pill is-empty">Loading...</span>
            </div>
          </section>

          <section class="chat-thread" data-chat-thread aria-live="polite"></section>

          <form class="chat-form" data-chat-form novalidate>
            <label>
              <span>Your Question</span>
              <textarea
                rows="4"
                maxlength="1200"
                data-chat-input
                placeholder="Example: Show top 5 products by revenue"
              ></textarea>
            </label>

            <div class="chat-actions">
              <button type="submit" class="auth-submit" data-chat-send>Ask</button>
              <button type="button" class="ghost-btn" data-chat-clear>Clear Chat</button>
              <button type="button" class="ghost-btn" data-go-report>Go to Report</button>
            </div>
          </form>
        </article>
      </section>
    `;
  }

  handleClick(event) {
    const quickTrigger = event?.target?.closest?.("[data-chat-quick]");
    if (quickTrigger) {
      const question = safeText(quickTrigger.getAttribute("data-chat-quick"), "");
      if (question) {
        this.askQuestion(question, { clearComposer: false });
      }
      return;
    }

    const clearButton = event?.target?.closest?.("[data-chat-clear]");
    if (clearButton) {
      this.clearChat();
      return;
    }

    const reportButton = event?.target?.closest?.("[data-go-report]");
    if (reportButton && this.router && typeof this.router.navigate === "function") {
      this.router.navigate("/reports");
    }
  }

  handleSubmit(event) {
    const form = event?.target?.closest?.("[data-chat-form]");
    if (!form) {
      return;
    }

    event.preventDefault();

    const input = form.querySelector("[data-chat-input]");
    const question = safeText(input?.value, "");
    if (!question) {
      this.toast.show("Please enter a question.", { type: "error" });
      return;
    }

    this.askQuestion(question, { clearComposer: true });
  }

  async askQuestion(question, options = {}) {
    if (!this.canAsk || !this.fileId) {
      this.toast.show("Complete analysis before using chat.", { type: "error" });
      return;
    }

    if (this.isBusy) {
      return;
    }

    const cleanedQuestion = safeText(question, "");
    if (!cleanedQuestion) {
      return;
    }

    this.appendMessage({ role: "user", message: cleanedQuestion });
    this.setBusy(true);

    let result = { success: false, message: "Chat request failed.", data: null };

    try {
      result = await this.reportService.askQuestion(this.fileId, cleanedQuestion, { useGemini: false });
    } catch (error) {
      result = {
        success: false,
        message: `Chat request failed: ${error?.message || "unknown error"}`,
        data: null
      };
    }

    if (result?.success) {
      this.appendMessage({
        role: "assistant",
        message: result?.data?.answer || "No answer returned."
      });
      this.setStatus("Answer received.", "success");
    } else {
      this.appendMessage({
        role: "system",
        message: result?.message || "Unable to fetch answer right now."
      });
      this.setStatus(result?.message || "Chat failed.", "error");
      this.toast.show(result?.message || "Chat failed.", { type: "error" });
    }

    if (options?.clearComposer) {
      const input = this.container?.querySelector?.("[data-chat-input]");
      if (input) {
        input.value = "";
      }
    }

    this.setBusy(false);
  }

  appendMessage(entry) {
    this.messages.push({
      role: safeText(entry?.role, "system"),
      message: safeText(entry?.message, ""),
      timestamp: new Date().toISOString()
    });

    this.renderMessages();
  }

  async loadChatHistory() {
    if (!this.fileId || !this.canAsk) {
      return;
    }

    const result = await this.reportService.getChatHistory(this.fileId);
    if (!result?.success) {
      return;
    }

    this.messages = Array.isArray(result?.data) ? result.data : [];
    this.renderMessages();
  }

  async clearChat() {
    this.messages = [];
    this.renderMessages();
    this.setStatus("Chat cleared.", "info");

    if (this.fileId) {
      await this.reportService.clearChatHistory(this.fileId);
    }
  }

  renderMessages() {
    const thread = this.container?.querySelector?.("[data-chat-thread]");
    if (!thread) {
      return;
    }

    if (!this.messages.length) {
      thread.innerHTML = '<p class="chat-empty">No conversation yet.</p>';
      return;
    }

    const messageMarkup = this.messages
      .map((entry) => {
        const role = safeText(entry?.role, "system");
        const label = role === "assistant" ? "AI" : role === "user" ? "You" : "System";
        return `
          <article class="chat-message chat-${escapeHtml(role)}">
            <header>${escapeHtml(label)}</header>
            <p>${formatMessageHtml(entry?.message || "")}</p>
          </article>
        `;
      })
      .join("");

    thread.innerHTML = messageMarkup;
    thread.scrollTop = thread.scrollHeight;
  }

  async loadPredefinedQuestions() {
    let result = { success: false, data: [] };

    try {
      result = await this.reportService.getPredefinedQuestions();
    } catch (_error) {
      result = { success: false, data: [] };
    }

    this.predefinedQuestions = Array.isArray(result?.data) ? result.data.slice(0, 8) : [];
    this.renderQuickQuestions();
  }

  renderQuickQuestions() {
    const holder = this.container?.querySelector?.("[data-chat-quicklist]");
    if (!holder) {
      return;
    }

    if (!this.predefinedQuestions.length) {
      holder.innerHTML = '<span class="quick-pill is-empty">No suggestions available.</span>';
      return;
    }

    holder.innerHTML = this.predefinedQuestions
      .map(
        (question) =>
          `<button type="button" class="quick-pill" data-chat-quick="${escapeHtml(question)}">${escapeHtml(question)}</button>`
      )
      .join("");
  }

  syncState(state) {
    const isAuthenticated = Boolean(state?.auth?.isAuthenticated);
    const fileId = state?.dataset?.fileId || null;
    const analysisComplete = Boolean(state?.dataset?.analysisComplete);

    this.fileId = fileId;
    this.canAsk = isAuthenticated && Boolean(fileId) && analysisComplete;

    if (!isAuthenticated) {
      this.setStatus("Login required before chat.", "error");
      this.setComposerEnabled(false);
      return;
    }

    if (!fileId) {
      this.setStatus("Upload a dataset first.", "error");
      this.setComposerEnabled(false);
      return;
    }

    if (!analysisComplete) {
      this.setStatus("Run analysis first.", "error");
      this.setComposerEnabled(false);
      return;
    }

    this.setStatus("Chat ready.", "success");
    this.setComposerEnabled(true);
  }

  setComposerEnabled(enabled) {
    const isEnabled = Boolean(enabled);
    const input = this.container?.querySelector?.("[data-chat-input]");
    const sendButton = this.container?.querySelector?.("[data-chat-send]");

    if (input) {
      input.disabled = !isEnabled;
    }

    if (sendButton) {
      sendButton.disabled = !isEnabled || this.isBusy;
    }
  }

  setBusy(isBusy) {
    this.isBusy = Boolean(isBusy);

    const sendButton = this.container?.querySelector?.("[data-chat-send]");
    if (sendButton) {
      sendButton.disabled = this.isBusy || !this.canAsk;
      sendButton.textContent = this.isBusy ? "Thinking..." : "Ask";
    }
  }

  setStatus(message, variant = "info") {
    const status = this.container?.querySelector?.("[data-chat-status]");
    if (!status) {
      return;
    }

    status.textContent = safeText(message, "Ready.");
    status.setAttribute("data-variant", variant);
  }
}
