import { stateManager as sharedStateManager } from "../core/StateManager.js";
import { toast as sharedToast } from "./Toast.js";
import { authService as sharedAuthService } from "../services/AuthService.js";

const NAV_ITEMS = [
  { route: "/upload", label: "Upload", gate: "auth" },
  { route: "/dashboard", label: "Dashboard", gate: "dataset" },
  { route: "/advanced", label: "Advanced Summary", gate: "analysis" },
  { route: "/chat", label: "Chat", gate: "analysis" },
  { route: "/reports", label: "Reports", gate: "analysis" }
];

export class Sidebar {
  constructor(options = {}) {
    this.router = options?.router || null;
    this.stateManager = options?.stateManager || sharedStateManager;
    this.toast = options?.toast || sharedToast;
    this.authService = options?.authService || sharedAuthService;
    this.root = null;
    this.unsubscribe = null;
    this.boundClickHandler = this.handleClick.bind(this);
  }

  mount(root) {
    if (!root) {
      return () => {};
    }

    this.root = root;
    this.root.innerHTML = this.render(this.stateManager.getState());

    this.root.addEventListener("click", this.boundClickHandler);
    this.unsubscribe = this.stateManager.subscribe((nextState) => {
      this.update(nextState);
    });

    return () => this.unmount();
  }

  unmount() {
    if (typeof this.unsubscribe === "function") {
      this.unsubscribe();
      this.unsubscribe = null;
    }

    if (this.root) {
      this.root.removeEventListener("click", this.boundClickHandler);
      this.root.innerHTML = "";
      this.root = null;
    }
  }

  update(state) {
    if (!this.root) {
      return;
    }

    this.root.innerHTML = this.render(state);
  }

  render(state) {
    const isAuthenticated = Boolean(state?.auth?.isAuthenticated);
    const fileId = state?.dataset?.fileId || null;
    const analysisComplete = Boolean(state?.dataset?.analysisComplete);
    const currentPath = state?.routing?.currentPath || "/";

    const navMarkup = NAV_ITEMS.map((item) => {
      const disabled = this.isRouteLocked(item?.gate, isAuthenticated, fileId, analysisComplete);
      const isActive = currentPath === item?.route;

      return `
        <button
          type="button"
          class="side-nav-btn ${isActive ? "is-active" : ""}"
          data-route="${item?.route || "/"}"
          ${disabled ? "disabled" : ""}
        >
          ${item?.label || "Item"}
        </button>
      `;
    }).join("");

    return `
      <aside class="sidebar-card glass-card" aria-label="App navigation">
        <p class="sidebar-title">Navigation</p>
        <nav class="side-nav" aria-label="Primary views">
          ${navMarkup}

          <!-- 🔥 Sign Out Button -->
          <button
            type="button"
            class="side-nav-btn logout-btn"
            data-action="logout"
          >
            Sign Out
          </button>
        </nav>
      </aside>
    `;
  }

  isRouteLocked(gate, isAuthenticated, fileId, analysisComplete) {
    if (gate === "none") {
      return false;
    }

    if (gate === "auth") {
      return !isAuthenticated;
    }

    if (gate === "dataset") {
      return !isAuthenticated || !fileId;
    }

    if (gate === "analysis") {
      return !isAuthenticated || !fileId || !analysisComplete;
    }

    return false;
  }

  handleClick(event) {
    // 🔥 Handle logout click
    const logoutTrigger = event?.target?.closest?.("[data-action='logout']");
    if (logoutTrigger) {
      this.handleLogout();
      return;
    }

    const routeTrigger = event?.target?.closest?.("[data-route]");
    if (!routeTrigger) {
      return;
    }

    const targetRoute = routeTrigger.getAttribute("data-route") || "/";
    if (routeTrigger.disabled) {
      this.toast.show("Complete earlier steps to unlock this section.", {
        type: "info",
        duration: 2200
      });
      return;
    }

    if (this.router && typeof this.router.navigate === "function") {
      this.router.navigate(targetRoute);
    }
  }

  //  Logout function
  async handleLogout() {
    try {
      await this.authService.logout();

      // Redirect to login
      if (this.router && typeof this.router.navigate === "function") {
        this.router.navigate("/auth");
      }

    } catch (error) {
      console.error("Logout failed:", error);
      this.toast.show("Logout failed. Try again.", { type: "error" });
    }
  }
}