const DEFAULT_MAX_TOASTS = 5;
const DEFAULT_DURATION_MS = 3200;
let stylesInjected = false;

export class Toast {
  constructor(options = {}) {
    this.containerId = options?.containerId || "toast-root";
    this.maxToasts = Number(options?.maxToasts) > 0 ? Number(options.maxToasts) : DEFAULT_MAX_TOASTS;
    this.documentRef = typeof document !== "undefined" ? document : null;
    this.container = null;
    this.boundClickHandler = this.handleContainerClick.bind(this);

    this.injectStyles();
    this.ensureContainer();
  }

  injectStyles() {
    if (!this.documentRef || stylesInjected) {
      return;
    }

    const style = this.documentRef.createElement("style");
    style.setAttribute("data-toast-styles", "true");
    style.textContent = `
      .toast-root {
        position: fixed;
        right: 1rem;
        bottom: 1rem;
        display: grid;
        gap: 0.6rem;
        width: min(360px, calc(100vw - 2rem));
        z-index: 1200;
        pointer-events: none;
      }

      .toast-item {
        pointer-events: auto;
        border-radius: 12px;
        border: 1px solid color-mix(in srgb, var(--card-border) 72%, transparent 28%);
        background: color-mix(in srgb, var(--card-bg) 92%, black 8%);
        color: var(--text-primary);
        box-shadow: 0 18px 32px rgba(0, 0, 0, 0.34);
        padding: 0.72rem 0.9rem;
        opacity: 0;
        transform: translateY(14px);
        transition: opacity 180ms ease, transform 220ms ease;
      }

      .toast-item.is-visible {
        opacity: 1;
        transform: translateY(0);
      }

      .toast-item.toast-error {
        border-color: color-mix(in srgb, #ff4d61 64%, var(--card-border) 36%);
      }

      .toast-item.toast-success {
        border-color: color-mix(in srgb, #2de38d 64%, var(--card-border) 36%);
      }

      .toast-item.toast-info {
        border-color: color-mix(in srgb, var(--accent-primary) 62%, var(--card-border) 38%);
      }

      .toast-inner {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
      }

      .toast-message {
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.5;
        color: var(--text-secondary);
      }

      .toast-close {
        margin-left: auto;
        border: 0;
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 1rem;
      }
    `;

    if (this.documentRef.head) {
      this.documentRef.head.appendChild(style);
      stylesInjected = true;
    }
  }

  ensureContainer() {
    if (!this.documentRef) {
      return;
    }

    let container = this.documentRef.getElementById(this.containerId);

    if (!container) {
      container = this.documentRef.createElement("section");
      container.id = this.containerId;
      container.className = "toast-root";
      container.setAttribute("aria-live", "polite");
      container.setAttribute("aria-label", "Notifications");
      if (this.documentRef.body) {
        this.documentRef.body.appendChild(container);
      }
    }

    this.container = container;

    if (this.container && !this.container.dataset.toastBound) {
      this.container.addEventListener("click", this.boundClickHandler);
      this.container.dataset.toastBound = "true";
    }
  }

  show(message, options = {}) {
    if (!this.container || !this.documentRef) {
      return null;
    }

    const safeMessage = typeof message === "string" && message.trim() ? message.trim() : "Unexpected event";
    const type = typeof options?.type === "string" ? options.type.toLowerCase() : "info";
    const duration = Number(options?.duration) >= 0 ? Number(options.duration) : DEFAULT_DURATION_MS;
    const toastId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    const toast = this.documentRef.createElement("article");
    toast.className = `toast-item toast-${type}`;
    toast.dataset.toastId = toastId;
    toast.innerHTML = `
      <div class="toast-inner">
        <p class="toast-message">${this.escapeHtml(safeMessage)}</p>
        <button class="toast-close" data-toast-close="${toastId}" aria-label="Close notification">x</button>
      </div>
    `;

    this.container.appendChild(toast);

    const raf =
      typeof window !== "undefined" && typeof window.requestAnimationFrame === "function"
        ? window.requestAnimationFrame
        : (callback) => callback();

    raf(() => {
      toast.classList.add("is-visible");
    });

    this.trimToLimit();

    if (duration > 0) {
      const removeLater = () => this.remove(toastId);
      if (typeof window !== "undefined") {
        window.setTimeout(removeLater, duration);
      }
    }

    return toastId;
  }

  remove(toastId) {
    if (!this.container || !toastId) {
      return;
    }

    const target = this.container.querySelector(`[data-toast-id="${toastId}"]`);
    if (!target) {
      return;
    }

    target.classList.remove("is-visible");

    const destroyNode = () => {
      if (target.parentNode) {
        target.parentNode.removeChild(target);
      }
    };

    if (typeof window !== "undefined") {
      window.setTimeout(destroyNode, 220);
    } else {
      destroyNode();
    }
  }

  trimToLimit() {
    if (!this.container) {
      return;
    }

    while (this.container.children.length > this.maxToasts) {
      const oldest = this.container.firstElementChild;
      if (oldest?.parentNode) {
        oldest.parentNode.removeChild(oldest);
      } else {
        break;
      }
    }
  }

  handleContainerClick(event) {
    const closeTrigger = event?.target?.closest?.("[data-toast-close]");
    if (!closeTrigger) {
      return;
    }

    const targetId = closeTrigger.getAttribute("data-toast-close");
    if (targetId) {
      this.remove(targetId);
    }
  }

  destroy() {
    if (this.container) {
      this.container.removeEventListener("click", this.boundClickHandler);
      delete this.container.dataset.toastBound;
    }
  }

  escapeHtml(unsafeText) {
    return unsafeText
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}

export const toast = new Toast();

export function notify(message, options = {}) {
  return toast.show(message, options);
}
