import { Toast } from "../components/Toast.js";
import { stateManager } from "./StateManager.js";

function normalizePath(pathValue) {
  const raw = String(pathValue || "").trim();
  if (!raw || raw === "#") {
    return "/";
  }

  let path = raw.replace(/^#/, "");
  if (!path.startsWith("/")) {
    path = `/${path}`;
  }

  return path;
}

export class Router {
  constructor(options = {}) {
    this.rootSelector = options?.rootSelector || "#app-root";
    this.rootEl = null;
    this.routes = new Map();
    this.currentView = null;
    this.currentUnmount = null;
    this.isStarted = false;
    this.toast = options?.toastInstance || new Toast();
    this.notFoundRenderer = options?.notFoundRenderer || this.createNotFoundRenderer();
    this.boundRouteHandler = this.handleRouteChange.bind(this);
  }

  register(path, renderer) {
    if (typeof renderer !== "function") {
      return;
    }

    const normalized = normalizePath(path);
    this.routes.set(normalized, renderer);
  }

  init() {
    this.rootEl = typeof document !== "undefined" ? document.querySelector(this.rootSelector) : null;

    if (!this.rootEl) {
      this.toast.show("App root container is missing.", { type: "error" });
      return;
    }

    if (typeof window !== "undefined" && !this.isStarted) {
      window.addEventListener("hashchange", this.boundRouteHandler);
      window.addEventListener("popstate", this.boundRouteHandler);
      this.isStarted = true;
    }

    this.handleRouteChange();
  }

  navigate(path) {
    if (typeof window === "undefined") {
      return;
    }

    const normalized = normalizePath(path);
    const targetHash = `#${normalized}`;

    if (window.location.hash !== targetHash) {
      window.location.hash = targetHash;
      return;
    }

    this.handleRouteChange();
  }

  getCurrentPath() {
    if (typeof window === "undefined") {
      return "/";
    }

    return normalizePath(window.location?.hash || "/");
  }

  async handleRouteChange() {
    const path = this.getCurrentPath();
    stateManager.updatePath("routing.currentPath", path);

    const renderer = this.routes.get(path) || this.notFoundRenderer;

    if (!this.rootEl && typeof document !== "undefined") {
      this.rootEl = document.querySelector(this.rootSelector);
    }

    if (!this.rootEl) {
      return;
    }

    await this.unmountCurrentView();
    this.rootEl.innerHTML = "";
    this.resetScrollPosition();

    try {
      const nextView = await renderer({
        path,
        router: this,
        state: stateManager.getState()
      });

      this.currentView = nextView;

      if (typeof nextView === "string") {
        this.rootEl.innerHTML = nextView;
        this.resetScrollPosition();
        return;
      }

      const hasHTMLElement = typeof HTMLElement !== "undefined";
      if (hasHTMLElement && nextView instanceof HTMLElement) {
        this.rootEl.appendChild(nextView);
        this.resetScrollPosition();
        return;
      }

      if (nextView && typeof nextView.mount === "function") {
        const unmountFn = await nextView.mount(this.rootEl);
        if (typeof unmountFn === "function") {
          this.currentUnmount = unmountFn;
        } else if (typeof nextView.unmount === "function") {
          this.currentUnmount = nextView.unmount.bind(nextView);
        }
        this.resetScrollPosition();
        return;
      }

      this.rootEl.innerHTML = `
        <section class="glass-card view-placeholder">
          <h2>Empty View</h2>
          <p>The route returned no renderable content.</p>
        </section>
      `;
      this.resetScrollPosition();
    } catch (error) {
      this.rootEl.innerHTML = `
        <section class="glass-card view-placeholder">
          <h2>Route Error</h2>
          <p>Unable to load the selected view.</p>
        </section>
      `;
      this.resetScrollPosition();

      this.toast.show(`Navigation failed: ${error?.message || "Unknown routing error."}`, {
        type: "error"
      });
    }
  }

  resetScrollPosition() {
    if (this.rootEl && typeof this.rootEl.scrollTo === "function") {
      this.rootEl.scrollTo({ top: 0, left: 0, behavior: "auto" });
    } else if (this.rootEl) {
      this.rootEl.scrollTop = 0;
      this.rootEl.scrollLeft = 0;
    }

    if (typeof window !== "undefined" && typeof window.scrollTo === "function") {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }

    if (typeof document !== "undefined") {
      if (document.documentElement) {
        document.documentElement.scrollTop = 0;
        document.documentElement.scrollLeft = 0;
      }

      if (document.body) {
        document.body.scrollTop = 0;
        document.body.scrollLeft = 0;
      }
    }
  }

  async unmountCurrentView() {
    if (typeof this.currentUnmount === "function") {
      try {
        await this.currentUnmount();
      } catch (error) {
        console.warn("View unmount warning:", error?.message || error);
      }
    } else if (this.currentView && typeof this.currentView.unmount === "function") {
      try {
        await this.currentView.unmount();
      } catch (error) {
        console.warn("View unmount warning:", error?.message || error);
      }
    }

    this.currentView = null;
    this.currentUnmount = null;
  }

  createNotFoundRenderer() {
    return () => ({
      mount: (root) => {
        if (!root) {
          return;
        }

        root.innerHTML = `
          <section class="glass-card view-placeholder">
            <h2>404: View Not Found</h2>
            <p>The route does not exist in the current SPA map.</p>
          </section>
        `;
      },
      unmount: () => {}
    });
  }

  destroy() {
    if (typeof window !== "undefined" && this.isStarted) {
      window.removeEventListener("hashchange", this.boundRouteHandler);
      window.removeEventListener("popstate", this.boundRouteHandler);
      this.isStarted = false;
    }

    this.unmountCurrentView();
    this.routes.clear();
  }
}
